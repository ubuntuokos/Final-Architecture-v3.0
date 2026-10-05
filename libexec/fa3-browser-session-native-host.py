#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket,stat,struct,sys,threading
from pathlib import Path
from typing import Any
MAX_FRAME=8*1024*1024
PROTOCOL="fa3.browser-session-bridge.v1"
class NativeHostError(RuntimeError): pass
def _runtime_root()->Path:
    xdg=os.environ.get("XDG_RUNTIME_DIR","").strip()
    if not xdg or not Path(xdg).is_absolute(): raise NativeHostError("XDG_RUNTIME_DIR_REQUIRED")
    return (Path(xdg)/"fa3"/"browser-session").resolve()
def _socket_path()->Path:
    raw=os.environ.get("FA3_BROWSER_SESSION_SOCKET","").strip()
    if not raw: raise NativeHostError("SOCKET_ENV_REQUIRED")
    path=Path(raw)
    if not path.is_absolute(): raise NativeHostError("SOCKET_MUST_BE_ABSOLUTE")
    parent=path.parent.resolve();root=_runtime_root()
    if parent!=root or path.name!="bridge.sock": raise NativeHostError("SOCKET_OUTSIDE_FA3_RUNTIME_ROOT")
    st=parent.stat()
    if st.st_uid!=os.getuid() or not stat.S_ISDIR(st.st_mode) or (st.st_mode&0o077): raise NativeHostError("RUNTIME_ROOT_OWNERSHIP_OR_MODE_INVALID")
    return path
def _read_exact(stream,count:int)->bytes:
    data=bytearray()
    while len(data)<count:
        block=stream.read(count-len(data))
        if not block:
            if not data:return b""
            raise NativeHostError("NATIVE_MESSAGE_TRUNCATED")
        data.extend(block)
    return bytes(data)
def read_native(stream)->dict[str,Any]|None:
    header=_read_exact(stream,4)
    if not header:return None
    (size,)=struct.unpack("<I",header)
    if size<=0 or size>MAX_FRAME:raise NativeHostError("NATIVE_MESSAGE_SIZE_INVALID")
    payload=_read_exact(stream,size)
    try:obj=json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError,json.JSONDecodeError) as exc:raise NativeHostError("NATIVE_MESSAGE_JSON_INVALID") from exc
    if not isinstance(obj,dict):raise NativeHostError("NATIVE_MESSAGE_OBJECT_REQUIRED")
    return obj
def write_native(stream,obj:dict[str,Any],lock:threading.Lock)->None:
    data=json.dumps(obj,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    if not data or len(data)>MAX_FRAME:raise NativeHostError("NATIVE_OUTPUT_SIZE_INVALID")
    with lock:
        stream.write(struct.pack("<I",len(data)));stream.write(data);stream.flush()
def send_line(sock:socket.socket,obj:dict[str,Any],lock:threading.Lock)->None:
    data=(json.dumps(obj,separators=(",",":"),ensure_ascii=False)+"\n").encode("utf-8")
    if len(data)>MAX_FRAME:raise NativeHostError("SOCKET_OUTPUT_SIZE_INVALID")
    with lock:sock.sendall(data)
def socket_to_native(sock:socket.socket,stdout,out_lock:threading.Lock,stopped:threading.Event)->None:
    buf=bytearray()
    try:
        while not stopped.is_set():
            block=sock.recv(65536)
            if not block:return
            buf.extend(block)
            if len(buf)>MAX_FRAME*2:raise NativeHostError("SOCKET_BUFFER_TOO_LARGE")
            while b"\n" in buf:
                raw,_,rest=buf.partition(b"\n");buf=bytearray(rest)
                if not raw:continue
                obj=json.loads(raw.decode("utf-8"))
                if not isinstance(obj,dict):raise NativeHostError("SOCKET_OBJECT_REQUIRED")
                write_native(stdout,obj,out_lock)
    finally:stopped.set()
def main()->int:
    if os.geteuid()==0:return 2
    try:
        path=_socket_path();sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(10);sock.connect(str(path));sock.settimeout(None)
        stopped=threading.Event();out_lock=threading.Lock();sock_lock=threading.Lock()
        reader=threading.Thread(target=socket_to_native,args=(sock,sys.stdout.buffer,out_lock,stopped),daemon=True);reader.start()
        send_line(sock,{"type":"native-host-ready","protocol":PROTOCOL,"pid":os.getpid(),"authority":False},sock_lock)
        while not stopped.is_set():
            obj=read_native(sys.stdin.buffer)
            if obj is None:break
            send_line(sock,obj,sock_lock)
        stopped.set()
        try:sock.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        sock.close();reader.join(timeout=1);return 0
    except (NativeHostError,OSError,json.JSONDecodeError,UnicodeDecodeError):return 2
if __name__=="__main__":raise SystemExit(main())
