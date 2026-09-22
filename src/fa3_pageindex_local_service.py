#!/usr/bin/env python3
from __future__ import annotations
import json,os,socketserver
from pathlib import Path
from typing import Any
from fa3_mcp_gateway import GatewayDenied
from fa3_pageindex_local_provider import PageIndexLocalConfig,PageIndexLocalProvider
def _config()->PageIndexLocalConfig:
    roots=tuple(Path(x).expanduser().resolve() for x in os.environ.get("FA3_PAGEINDEX_LOCAL_ALLOWED_ROOTS","").split(":") if x)
    return PageIndexLocalConfig(
      storage_path=Path(os.environ["FA3_PAGEINDEX_LOCAL_STORAGE"]).expanduser().resolve(),
      allowed_roots=roots,
      model_router_base_url=os.environ["FA3_MODEL_ROUTER_URL"],
      index_route=os.environ.get("FA3_PAGEINDEX_INDEX_ROUTE","fa3-pageindex-index"),
      reason_route=os.environ.get("FA3_PAGEINDEX_REASON_ROUTE","fa3-pageindex-reason"),
    )
class Handler(socketserver.StreamRequestHandler):
    provider:PageIndexLocalProvider
    def handle(self)->None:
        try:
            raw=self.rfile.readline(1024*1024)
            req=json.loads(raw.decode())
            if not isinstance(req,dict) or not isinstance(req.get("arguments"),dict): raise GatewayDenied("PAGEINDEX_LOCAL_RPC_SCHEMA","invalid request")
            method=req.get("method")
            if method=="index": result=self.provider.index(req["arguments"])
            elif method=="retrieve": result=self.provider.retrieve(req["arguments"])
            else: raise GatewayDenied("PAGEINDEX_LOCAL_METHOD_DENIED","unsupported method")
            out={"status":"PASS","result":result}
        except GatewayDenied as exc: out={"status":"DENY","reason_code":exc.code,"message":exc.message}
        except Exception as exc: out={"status":"FAIL","reason_code":"PAGEINDEX_LOCAL_PROVIDER_EXCEPTION","message":type(exc).__name__}
        self.wfile.write(json.dumps(out,ensure_ascii=False,separators=(",",":")).encode()+b"\n")
class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads=True
def main()->int:
    sock=Path(os.environ.get("FA3_PAGEINDEX_LOCAL_SOCKET","")).expanduser()
    if not sock.is_absolute(): raise SystemExit("FA3_PAGEINDEX_LOCAL_SOCKET must be absolute")
    sock.parent.mkdir(parents=True,exist_ok=True); sock.unlink(missing_ok=True)
    Handler.provider=PageIndexLocalProvider(_config())
    server=Server(str(sock),Handler); os.chmod(sock,0o600)
    try: server.serve_forever()
    finally:
        server.server_close(); sock.unlink(missing_ok=True)
    return 0
if __name__=="__main__": raise SystemExit(main())
