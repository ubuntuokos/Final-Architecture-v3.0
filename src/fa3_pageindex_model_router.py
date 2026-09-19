#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from urllib.request import Request,urlopen
ALLOWED_POST={"/v1/chat/completions","/v1/embeddings"}
ALLOWED_GET={"/v1/models"}
class Handler(BaseHTTPRequestHandler):
    upstream="http://127.0.0.1:11434"
    def log_message(self,*args): return
    def _send(self,status:int,raw:bytes,ctype:str="application/json"):
        self.send_response(status); self.send_header("Content-Type",ctype); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=="/healthz": return self._send(200,b'{"status":"ok","authority":"FA3-AUTH-MODEL-ROUTER-001","egress":"LOOPBACK_ONLY"}')
        if self.path not in ALLOWED_GET: return self._send(404,b'{"error":"ROUTE_DENIED"}')
        self._proxy("GET",None)
    def do_POST(self):
        if self.path not in ALLOWED_POST: return self._send(404,b'{"error":"ROUTE_DENIED"}')
        n=int(self.headers.get("Content-Length","0"))
        if n<=0 or n>8*1024*1024: return self._send(400,b'{"error":"INVALID_SIZE"}')
        try:
            body=json.loads(self.rfile.read(n).decode())
            model=body.get("model")
            if isinstance(model,str) and model.startswith("openai/"): body["model"]=model[len("openai/"):]
            raw=json.dumps(body,separators=(",",":")).encode()
        except Exception: return self._send(400,b'{"error":"INVALID_JSON"}')
        self._proxy("POST",raw)
    def _proxy(self,method:str,body:bytes|None):
        req=Request(self.upstream+self.path,data=body,method=method,headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=600) as r: raw=r.read(); status=r.status; ctype=r.headers.get("Content-Type","application/json")
            self._send(status,raw,ctype)
        except Exception as exc:
            self._send(502,json.dumps({"error":"LOCAL_MODEL_BACKEND_UNAVAILABLE","detail":type(exc).__name__}).encode())
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--host",default="127.0.0.1"); ap.add_argument("--port",type=int,default=18791); ap.add_argument("--upstream",default="http://127.0.0.1:11434"); a=ap.parse_args()
    if a.host not in {"127.0.0.1","::1","localhost"}: raise SystemExit("non-loopback bind denied")
    u=urlparse(a.upstream)
    if u.scheme!="http" or u.hostname not in {"127.0.0.1","::1","localhost"}: raise SystemExit("non-loopback model backend denied")
    Handler.upstream=a.upstream.rstrip("/")
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever(); return 0
if __name__=="__main__": raise SystemExit(main())
