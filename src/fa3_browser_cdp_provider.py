#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,os,shutil,socket,struct,subprocess,tempfile,time,urllib.parse,urllib.request
from pathlib import Path
from typing import Any,Callable
from fa3_browser_action_runtime import BrowserActionDenied,MutationLedger,execute_action,normalize_observation,verify_outcome
from fa3_uaf import ActionRequest,ProviderDescriptor

PROVIDER_ID="FA3-PROVIDER-BROWSER-CDP-001"
ACTION_ID="browser.action.execute"
LOOPBACK_HOSTS={"127.0.0.1","::1","localhost"}
BROWSER_CANDIDATES=("google-chrome","google-chrome-stable","chromium","chromium-browser","brave-browser","microsoft-edge","microsoft-edge-stable")

class CdpProviderError(RuntimeError):
    def __init__(self,code:str,message:str):
        super().__init__(message); self.code=code

def discover_browser_binary(explicit:str|None=None)->str:
    value=explicit or os.environ.get("FA3_BROWSER_BINARY")
    if value:
        resolved=shutil.which(value) if os.path.sep not in value else value
        if resolved and Path(resolved).is_file() and os.access(resolved,os.X_OK): return str(Path(resolved).resolve())
        raise CdpProviderError("BROWSER-BINARY-UNAVAILABLE","explicit browser binary is not executable")
    for candidate in BROWSER_CANDIDATES:
        resolved=shutil.which(candidate)
        if resolved: return str(Path(resolved).resolve())
    raise CdpProviderError("BROWSER-BINARY-UNAVAILABLE","no admitted Chromium-compatible browser binary discovered")

def _loopback_url(url:str,*,schemes:set[str])->urllib.parse.ParseResult:
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme not in schemes or (parsed.hostname or "").lower() not in LOOPBACK_HOSTS:
        raise CdpProviderError("BROWSER-CDP-REMOTE-DENIED","CDP endpoint must remain loopback-only")
    return parsed

def _read_exact(sock:socket.socket,count:int,buffer:bytearray)->bytes:
    while len(buffer)<count:
        block=sock.recv(max(4096,count-len(buffer)))
        if not block: raise CdpProviderError("BROWSER-CDP-DISCONNECTED","CDP websocket disconnected")
        buffer.extend(block)
    out=bytes(buffer[:count]); del buffer[:count]; return out

class CdpWebSocket:
    def __init__(self,url:str,timeout:float=10.0):
        parsed=_loopback_url(url,schemes={"ws"}); port=parsed.port or 80
        self.sock=socket.create_connection((parsed.hostname or "127.0.0.1",port),timeout=timeout); self.sock.settimeout(timeout); self.buffer=bytearray()
        path=parsed.path or "/"
        if parsed.query: path+="?"+parsed.query
        key=base64.b64encode(os.urandom(16)).decode("ascii")
        request=(f"GET {path} HTTP/1.1\r\nHost: {parsed.hostname}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode("ascii")
        self.sock.sendall(request); raw=bytearray()
        while b"\r\n\r\n" not in raw:
            block=self.sock.recv(4096)
            if not block: raise CdpProviderError("BROWSER-CDP-HANDSHAKE","websocket handshake closed")
            raw.extend(block)
            if len(raw)>65536: raise CdpProviderError("BROWSER-CDP-HANDSHAKE","websocket handshake too large")
        header,extra=bytes(raw).split(b"\r\n\r\n",1); self.buffer.extend(extra); lines=header.decode("latin1").split("\r\n")
        if not lines or " 101 " not in lines[0]: raise CdpProviderError("BROWSER-CDP-HANDSHAKE","websocket upgrade rejected")
        headers={}
        for line in lines[1:]:
            if ":" in line:
                name,value=line.split(":",1); headers[name.strip().lower()]=value.strip()
        expected=base64.b64encode(hashlib.sha1((key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept")!=expected: raise CdpProviderError("BROWSER-CDP-HANDSHAKE","websocket accept mismatch")
    def _send_frame(self,opcode:int,payload:bytes)->None:
        first=0x80|opcode; mask=os.urandom(4); length=len(payload)
        if length<126: header=bytes([first,0x80|length])
        elif length<=0xFFFF: header=bytes([first,0x80|126])+struct.pack("!H",length)
        else: header=bytes([first,0x80|127])+struct.pack("!Q",length)
        masked=bytes(value^mask[index%4] for index,value in enumerate(payload)); self.sock.sendall(header+mask+masked)
    def send_text(self,text:str)->None: self._send_frame(0x1,text.encode("utf-8"))
    def _recv_frame(self)->tuple[bool,int,bytes]:
        first,second=_read_exact(self.sock,2,self.buffer); fin=bool(first&0x80); opcode=first&0x0F; masked=bool(second&0x80); length=second&0x7F
        if length==126: length=struct.unpack("!H",_read_exact(self.sock,2,self.buffer))[0]
        elif length==127: length=struct.unpack("!Q",_read_exact(self.sock,8,self.buffer))[0]
        if length>32*1024*1024: raise CdpProviderError("BROWSER-CDP-FRAME-TOO-LARGE","CDP websocket frame exceeds limit")
        mask=_read_exact(self.sock,4,self.buffer) if masked else b""; payload=_read_exact(self.sock,length,self.buffer)
        if masked: payload=bytes(value^mask[index%4] for index,value in enumerate(payload))
        return fin,opcode,payload
    def recv_text(self)->str:
        fragments=bytearray(); started=False
        while True:
            fin,opcode,payload=self._recv_frame()
            if opcode==0x8: raise CdpProviderError("BROWSER-CDP-DISCONNECTED","CDP websocket closed")
            if opcode==0x9: self._send_frame(0xA,payload); continue
            if opcode==0xA: continue
            if opcode==0x1: fragments=bytearray(payload); started=True
            elif opcode==0x0 and started: fragments.extend(payload)
            else: continue
            if fin: return fragments.decode("utf-8")
    def close(self)->None:
        try: self._send_frame(0x8,b"")
        except Exception: pass
        try: self.sock.close()
        except Exception: pass

class CdpClient:
    def __init__(self,url:str,timeout:float=10.0): self.ws=CdpWebSocket(url,timeout=timeout); self.next_id=1
    def command(self,method:str,params:dict[str,Any]|None=None)->dict[str,Any]:
        cid=self.next_id; self.next_id+=1; self.ws.send_text(json.dumps({"id":cid,"method":method,"params":params or {}},separators=(",",":")))
        while True:
            message=json.loads(self.ws.recv_text())
            if message.get("id")!=cid: continue
            if "error" in message: raise CdpProviderError("BROWSER-CDP-COMMAND",f"{method} failed")
            result=message.get("result")
            if not isinstance(result,dict): raise CdpProviderError("BROWSER-CDP-COMMAND",f"{method} returned invalid result")
            return result
    def close(self)->None: self.ws.close()

class BrowserCdpSession:
    def __init__(self,browser_binary:str|None=None,timeout:float=10.0):
        self.browser_binary=discover_browser_binary(browser_binary); self.timeout=timeout; self.process=None; self.profile_dir=None; self.port=None; self.client=None; self.target_id=None; self.headless_mode=None; self.revision=0; self._last_fingerprint=None; self._last_observation_id=None
    @property
    def pid(self): return None if self.process is None else self.process.pid
    def _port(self)->int:
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as probe: probe.bind(("127.0.0.1",0)); return int(probe.getsockname()[1])
    def _json(self,path:str)->Any:
        if self.port is None: raise CdpProviderError("BROWSER-CDP-NOT-STARTED","CDP port unavailable")
        url=f"http://127.0.0.1:{self.port}{path}"; _loopback_url(url,schemes={"http"}); opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url,timeout=self.timeout) as response: return json.loads(response.read(4*1024*1024).decode("utf-8"))
    def launch(self,url:str="about:blank")->None:
        if self.process is not None: raise CdpProviderError("BROWSER-CDP-ALREADY-STARTED","browser session already started")
        self.port=self._port(); self.profile_dir=Path(tempfile.mkdtemp(prefix="fa3-browser-cdp-")); last_error="browser did not expose CDP"
        for headless in ("--headless=new","--headless"):
            args=[self.browser_binary,headless,"--disable-gpu","--disable-background-networking","--disable-default-apps","--disable-extensions","--disable-sync","--no-first-run","--no-default-browser-check","--remote-debugging-address=127.0.0.1",f"--remote-debugging-port={self.port}",f"--user-data-dir={self.profile_dir}","about:blank"]
            self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True); deadline=time.monotonic()+self.timeout; targets=None
            while time.monotonic()<deadline:
                if self.process.poll() is not None: last_error=f"browser exited with code {self.process.returncode}"; break
                try:
                    targets=self._json("/json")
                    if isinstance(targets,list): break
                except Exception: time.sleep(0.1)
            if isinstance(targets,list):
                page=next((row for row in targets if isinstance(row,dict) and row.get("type")=="page" and row.get("webSocketDebuggerUrl")),None)
                if page is not None:
                    ws_url=str(page["webSocketDebuggerUrl"]); _loopback_url(ws_url,schemes={"ws"}); self.target_id=str(page.get("id","")); self.client=CdpClient(ws_url,timeout=self.timeout); self.client.command("Runtime.enable"); self.client.command("Page.enable"); self.headless_mode=headless; self.navigate(url); return
            self._terminate_process(); self.process=None
        self.close(); raise CdpProviderError("BROWSER-CDP-START-FAILED",last_error)
    def _command(self,method,params=None):
        if self.client is None: raise CdpProviderError("BROWSER-CDP-NOT-STARTED","CDP client unavailable")
        return self.client.command(method,params)
    def evaluate(self,expression:str)->Any:
        result=self._command("Runtime.evaluate",{"expression":expression,"returnByValue":True,"awaitPromise":True})
        if result.get("exceptionDetails"): raise CdpProviderError("BROWSER-CDP-EVALUATE","browser evaluation failed")
        remote=result.get("result")
        if not isinstance(remote,dict): raise CdpProviderError("BROWSER-CDP-EVALUATE","browser evaluation result invalid")
        return remote.get("value")
    def navigate(self,url:str)->None:
        result=self._command("Page.navigate",{"url":url})
        if result.get("errorText"): raise CdpProviderError("BROWSER-CDP-NAVIGATE","browser navigation failed")
        deadline=time.monotonic()+self.timeout
        while time.monotonic()<deadline:
            try:
                if self.evaluate("document.readyState")=="complete": return
            except CdpProviderError: pass
            time.sleep(0.05)
        raise CdpProviderError("BROWSER-CDP-NAVIGATE","browser navigation timed out")
    def observe(self)->dict[str,Any]:
        script=r"""(() => {
          const html=document.documentElement ? document.documentElement.outerHTML : "";
          if(html.length>4000000) return {error:"DOM_TOO_LARGE"};
          const nodes=Array.from(document.querySelectorAll('a[href],button,input,textarea,select,[role="button"],[contenteditable="true"]'));
          if(nodes.length>512) return {error:"TOO_MANY_ACTIONABLE_ELEMENTS"};
          window.__fa3BrowserActionMap=Object.create(null); const rows=[];
          nodes.forEach((el,index)=>{
            const elementId="el-"+String(index).padStart(4,"0"); window.__fa3BrowserActionMap[elementId]=el;
            const tag=(el.tagName||"").toLowerCase(),type=(el.getAttribute("type")||"").toLowerCase(),style=getComputedStyle(el),rect=el.getBoundingClientRect();
            const isVisible=style.visibility!=="hidden" && style.display!=="none" && Number(style.opacity||1)>0 && rect.width>0 && rect.height>0;
            let occluded=false; if(isVisible){const x=Math.max(0,Math.min(innerWidth-1,rect.left+rect.width/2)),y=Math.max(0,Math.min(innerHeight-1,rect.top+rect.height/2)),top=document.elementFromPoint(x,y);occluded=!!top&&top!==el&&!el.contains(top);}
            const enabled=!el.disabled && el.getAttribute("aria-disabled")!=="true"; const textControl=tag==="textarea"||el.isContentEditable||(tag==="input"&&!["button","submit","reset","checkbox","radio","file","hidden"].includes(type));
            const actions=tag==="select"?["SELECT","SCROLL_INTO_VIEW"]:(textControl?["TYPE_TEXT","PRESS_KEY","SCROLL_INTO_VIEW"]:["CLICK","SCROLL_INTO_VIEW"]);
            const rawLabel=el.getAttribute("aria-label")||el.innerText||el.getAttribute("placeholder")||el.getAttribute("name")||el.value||"",label=String(rawLabel).replace(/\s+/g," ").trim().slice(0,256);
            let value=null;if(tag==="select")value=String(el.value||"").slice(0,4096);else if(textControl&&type!=="password")value=String(el.value||"").slice(0,4096);
            rows.push({element_id:elementId,role:el.getAttribute("role")||(tag==="a"?"link":tag),label,value,visible:isVisible,enabled,occluded,supported_actions:actions,metadata:{sensitive:type==="password"}});
          }); return {url:location.href,timeOrigin:performance.timeOrigin,html,elements:rows};
        })()"""
        raw=self.evaluate(script)
        if not isinstance(raw,dict) or raw.get("error"): raise CdpProviderError("BROWSER-OBSERVATION-FAILED",str(raw.get("error") if isinstance(raw,dict) else "invalid observation"))
        html=raw.pop("html",""); fingerprint=hashlib.sha256((str(raw.get("url",""))+"\n"+str(html)).encode()).hexdigest()
        if fingerprint!=self._last_fingerprint: self.revision+=1; self._last_fingerprint=fingerprint; self._last_observation_id=f"obs-{self.revision}-{fingerprint[:12]}"
        document_id=hashlib.sha256(f"{self.target_id}|{raw.get('timeOrigin')}".encode()).hexdigest()
        return normalize_observation({"observation_id":self._last_observation_id,"revision":self.revision,"document_id":document_id,"page_fingerprint":fingerprint,"url":raw.get("url",""),"elements":raw.get("elements",[]),"provenance":{"provider_id":PROVIDER_ID,"transport":"CDP_LOOPBACK","target_id":self.target_id}})
    def _target_state(self,element_id):
        eid=json.dumps(element_id); value=self.evaluate(f"""(() => {{const map=window.__fa3BrowserActionMap||{{}},el=map[{eid}];if(!el||!el.isConnected)return {{missing:true}};const style=getComputedStyle(el),rect=el.getBoundingClientRect(),visible=style.visibility!=="hidden"&&style.display!=="none"&&Number(style.opacity||1)>0&&rect.width>0&&rect.height>0,x=Math.max(0,Math.min(innerWidth-1,rect.left+rect.width/2)),y=Math.max(0,Math.min(innerHeight-1,rect.top+rect.height/2)),top=visible?document.elementFromPoint(x,y):null,occluded=!!top&&top!==el&&!el.contains(top);return {{missing:false,visible,enabled:!el.disabled&&el.getAttribute("aria-disabled")!=="true",occluded,x,y}};}})()""")
        if not isinstance(value,dict): raise BrowserActionDenied("TARGET_MISSING","CDP target state unavailable")
        return value
    def execute_candidate(self,candidate,parameters):
        operation=str(candidate.get("operation")); target_id=candidate.get("target_id"); state={}
        if target_id is not None:
            state=self._target_state(str(target_id))
            if state.get("missing"): raise BrowserActionDenied("TARGET_MISSING","CDP target disappeared")
            if not state.get("visible"): raise BrowserActionDenied("TARGET_NOT_VISIBLE","CDP target not visible")
            if operation in {"CLICK","TYPE_TEXT","SELECT","PRESS_KEY"} and not state.get("enabled"): raise BrowserActionDenied("TARGET_DISABLED","CDP target disabled")
            if operation=="CLICK" and state.get("occluded"): raise BrowserActionDenied("TARGET_OCCLUDED","CDP click target occluded")
        if operation=="CLICK":
            x,y=float(state["x"]),float(state["y"]);self._command("Input.dispatchMouseEvent",{"type":"mousePressed","x":x,"y":y,"button":"left","clickCount":1});self._command("Input.dispatchMouseEvent",{"type":"mouseReleased","x":x,"y":y,"button":"left","clickCount":1})
        elif operation=="TYPE_TEXT":
            text=parameters.get("text")
            if not isinstance(text,str) or len(text)>32768: raise BrowserActionDenied("BROWSER-PARAMETERS-INVALID","bounded TYPE_TEXT text required")
            eid=json.dumps(str(target_id));self.evaluate(f"(() => {{const el=(window.__fa3BrowserActionMap||{{}})[{eid}];if(!el)return false;el.focus();return true;}})()");self._command("Input.insertText",{"text":text})
        elif operation=="PRESS_KEY":
            key=parameters.get("key");allowed={"Enter","Tab","Escape","ArrowUp","ArrowDown","ArrowLeft","ArrowRight","Backspace","Delete","Home","End","PageUp","PageDown"}
            if key not in allowed: raise BrowserActionDenied("BROWSER-PARAMETERS-INVALID","key not allowlisted")
            self._command("Input.dispatchKeyEvent",{"type":"keyDown","key":key});self._command("Input.dispatchKeyEvent",{"type":"keyUp","key":key})
        elif operation=="SCROLL_INTO_VIEW":
            eid=json.dumps(str(target_id));ok=self.evaluate(f"(() => {{const el=(window.__fa3BrowserActionMap||{{}})[{eid}];if(!el)return false;el.scrollIntoView({{block:'center',inline:'center'}});return true;}})()")
            if ok is not True: raise BrowserActionDenied("TARGET_MISSING","scroll target unavailable")
        elif operation=="WAIT":
            milliseconds=parameters.get("milliseconds",250)
            if not isinstance(milliseconds,int) or not 0<=milliseconds<=5000: raise BrowserActionDenied("BROWSER-PARAMETERS-INVALID","WAIT outside bounded range")
            time.sleep(milliseconds/1000.0)
        else: raise BrowserActionDenied("BROWSER-EXECUTION-INVALID",f"unsupported CDP operation: {operation}")
        time.sleep(0.08);return {"operation":operation,"target_id":target_id,"transport":"CDP_LOOPBACK","physical_input":operation in {"CLICK","TYPE_TEXT","PRESS_KEY"}}
    def browser_version(self):
        proc=subprocess.run([self.browser_binary,"--version"],text=True,capture_output=True,check=False,timeout=5);return(proc.stdout or proc.stderr).strip()[:256]
    def _terminate_process(self):
        if self.process is None or self.process.poll() is not None:return
        try:os.killpg(self.process.pid,15)
        except ProcessLookupError:return
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and self.process.poll() is None:time.sleep(0.05)
        if self.process.poll() is None:
            try:os.killpg(self.process.pid,9)
            except ProcessLookupError:pass
        try:self.process.wait(timeout=2)
        except Exception:pass
    def close(self):
        if self.client is not None:
            try:self.client.close()
            except Exception:pass
            self.client=None
        self._terminate_process();profile=self.profile_dir;self.process=None;self.profile_dir=None
        if profile is not None:shutil.rmtree(profile,ignore_errors=True)

class BrowserCdpProvider:
    descriptor=ProviderDescriptor(provider_id=PROVIDER_ID,action_ids=(ACTION_ID,),capabilities=("browser.cdp.loopback","browser.bounded-action-execution","browser.independent-outcome-verification"),priority=50,state="CONNECTED",metadata={"architectural_authority":False,"parent_profile":"FA3-BROWSER-ACTION-RUNTIME-001","transport":"CDP_LOOPBACK","cpu_only_supported":True})
    def __init__(self,session,*,binding_loader:Callable[[str],dict[str,Any]],receipt_sink:Callable[[str,dict[str,Any]],str]):self.session=session;self.binding_loader=binding_loader;self.receipt_sink=receipt_sink;self.ledger=MutationLedger()
    def execute(self,request:ActionRequest,resource_lease:Any=None,secret_leases:tuple[Any,...]=()):
        if request.action_id!=ACTION_ID:raise BrowserActionDenied("BROWSER-EXECUTION-INVALID","provider received unsupported action")
        if resource_lease is None:raise BrowserActionDenied("BROWSER-RESOURCE-DENIED","HRB lease required")
        if secret_leases:raise BrowserActionDenied("BROWSER-SECRET-DENIED","browser provider accepts no direct secret projection")
        ref=request.arguments.get("binding_ref")
        if not isinstance(ref,str) or not ref:raise BrowserActionDenied("BROWSER-BINDING-INVALID","binding_ref required")
        binding=self.binding_loader(ref);parameters=binding.get("execution_parameters",{})
        execution=execute_action(binding,self.session.observe(),lambda candidate,observation:self.session.execute_candidate(candidate,parameters),ledger=self.ledger)
        expected=request.arguments.get("expected_postconditions",[])
        if execution.get("status")=="EXECUTED":verification=verify_outcome(expected,self.session.observe());status=verification["result"]
        else:verification={"schema":"fa3.browser-outcome-verification.v1","result":"INDETERMINATE","checks":[],"global_promotion_claim":False};status=str(execution.get("status"))
        return {"status":status,"execution_receipt_ref":self.receipt_sink("execution",execution),"verification_ref":self.receipt_sink("verification",verification)}
