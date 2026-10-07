#!/usr/bin/env python3
from __future__ import annotations
import json,os,queue,socket,threading,time,uuid
from pathlib import Path
from typing import Any,Callable
PROTOCOL="fa3.browser-session-bridge.v1"
EXPECTED_EXTENSION_ID="hkcdjepmkpeglfgejcejjdpdidinipdc"
MAX_LINE=8*1024*1024
class BrowserSessionBridgeError(RuntimeError):
    def __init__(self,code:str,message:str|None=None):super().__init__(message or code);self.code=code
class BrowserSessionBridgeServer:
    def __init__(self,runtime_root:Path,*,timeout:float=15.0):
        self.runtime_root=runtime_root.resolve();self.socket_path=self.runtime_root/"bridge.sock";self.timeout=timeout
        self.server=None;self.conn=None;self._write_lock=threading.Lock();self._pending={};self._pending_lock=threading.Lock()
        self.events=queue.Queue();self._reader=None;self._stopped=threading.Event();self.hello=None;self.native_ready=None
    def start(self):
        self.runtime_root.mkdir(parents=True,exist_ok=True);os.chmod(self.runtime_root,0o700);st=self.runtime_root.stat()
        if st.st_uid!=os.getuid() or (st.st_mode&0o077):raise BrowserSessionBridgeError("BRIDGE_RUNTIME_ROOT_INVALID")
        try:self.socket_path.unlink()
        except FileNotFoundError:pass
        self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.server.bind(str(self.socket_path));os.chmod(self.socket_path,0o600);self.server.listen(1);self.server.settimeout(self.timeout)
    def accept(self):
        if self.server is None:raise BrowserSessionBridgeError("BRIDGE_NOT_STARTED")
        try:self.conn,_=self.server.accept()
        except socket.timeout as exc:raise BrowserSessionBridgeError("BRIDGE_NATIVE_HOST_TIMEOUT") from exc
        self.conn.settimeout(None);self._reader=threading.Thread(target=self._reader_loop,daemon=True);self._reader.start();deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            if self.native_ready is not None and self.hello is not None:break
            if self._stopped.is_set():break
            time.sleep(.02)
        if self.native_ready is None:raise BrowserSessionBridgeError("BRIDGE_NATIVE_HOST_READY_MISSING")
        if self.hello is None:raise BrowserSessionBridgeError("BRIDGE_EXTENSION_HELLO_MISSING")
        if self.hello.get("protocol")!=PROTOCOL:raise BrowserSessionBridgeError("BRIDGE_PROTOCOL_MISMATCH")
        if self.hello.get("extension_id")!=EXPECTED_EXTENSION_ID:raise BrowserSessionBridgeError("BRIDGE_EXTENSION_ID_MISMATCH")
        if self.hello.get("authority") is not False:raise BrowserSessionBridgeError("BRIDGE_AUTHORITY_CLAIM_FORBIDDEN")
    def _reader_loop(self):
        assert self.conn is not None
        buf=bytearray()
        try:
            while not self._stopped.is_set():
                block=self.conn.recv(65536)
                if not block:break
                buf.extend(block)
                if len(buf)>MAX_LINE*2:raise BrowserSessionBridgeError("BRIDGE_BUFFER_TOO_LARGE")
                while b"\n" in buf:
                    raw,_,rest=buf.partition(b"\n");buf=bytearray(rest)
                    if not raw:continue
                    obj=json.loads(raw.decode("utf-8"))
                    if not isinstance(obj,dict):raise BrowserSessionBridgeError("BRIDGE_OBJECT_REQUIRED")
                    kind=obj.get("type")
                    if kind=="native-host-ready":self.native_ready=obj
                    elif kind=="hello":self.hello=obj
                    elif kind=="response":
                        reply=str(obj.get("reply_to",""))
                        with self._pending_lock:waiter=self._pending.get(reply)
                        if waiter is not None:waiter.put(obj)
                    else:self.events.put(obj)
        except Exception as exc:self.events.put({"type":"bridge-error","error_type":type(exc).__name__})
        finally:self._stopped.set()
    def request(self,method:str,params:dict[str,Any]|None=None,*,timeout:float|None=None)->dict[str,Any]:
        if self.conn is None or self._stopped.is_set():raise BrowserSessionBridgeError("BRIDGE_NOT_CONNECTED")
        rid="req-"+uuid.uuid4().hex;waiter=queue.Queue(maxsize=1)
        with self._pending_lock:self._pending[rid]=waiter
        data=(json.dumps({"type":"request","request_id":rid,"method":method,"params":params or{}},separators=(",",":"),ensure_ascii=False)+"\n").encode()
        if len(data)>MAX_LINE:raise BrowserSessionBridgeError("BRIDGE_REQUEST_TOO_LARGE")
        try:
            with self._write_lock:self.conn.sendall(data)
            try:response=waiter.get(timeout=self.timeout if timeout is None else timeout)
            except queue.Empty as exc:raise BrowserSessionBridgeError("BRIDGE_REQUEST_TIMEOUT",method) from exc
            if response.get("ok") is not True:
                err=response.get("error") if isinstance(response.get("error"),dict) else{}
                raise BrowserSessionBridgeError(str(err.get("code") or"BRIDGE_REQUEST_DENIED"),method)
            result=response.get("result")
            if not isinstance(result,dict):raise BrowserSessionBridgeError("BRIDGE_RESPONSE_INVALID",method)
            return result
        finally:
            with self._pending_lock:self._pending.pop(rid,None)
    def wait_event(self,predicate:Callable[[dict[str,Any]],bool],*,timeout:float=10.0)->dict[str,Any]:
        deadline=time.monotonic()+timeout;deferred=[]
        try:
            while time.monotonic()<deadline:
                try:item=self.events.get(timeout=max(.01,deadline-time.monotonic()))
                except queue.Empty:break
                if predicate(item):return item
                deferred.append(item)
        finally:
            for item in deferred:self.events.put(item)
        raise BrowserSessionBridgeError("BRIDGE_EVENT_TIMEOUT")
    def close(self):
        self._stopped.set()
        if self.conn is not None:
            try:self.conn.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            try:self.conn.close()
            except OSError:pass
            self.conn=None
        if self.server is not None:
            try:self.server.close()
            except OSError:pass
            self.server=None
        if self._reader is not None:self._reader.join(timeout=1);self._reader=None
        try:
            if self.socket_path.is_socket():self.socket_path.unlink()
        except (FileNotFoundError,OSError):pass
def validate_native_host_manifest(manifest:dict[str,Any],*,executable_path:Path)->list[str]:
    out=[]
    if manifest.get("name")!="org.fa3.browser.session_bridge":out.append("NATIVE_HOST_NAME_INVALID")
    if manifest.get("type")!="stdio":out.append("NATIVE_HOST_TYPE_INVALID")
    if manifest.get("path")!=str(executable_path.resolve()):out.append("NATIVE_HOST_PATH_INVALID")
    if manifest.get("allowed_origins")!=[f"chrome-extension://{EXPECTED_EXTENSION_ID}/"]:out.append("NATIVE_HOST_ORIGIN_INVALID")
    return out
