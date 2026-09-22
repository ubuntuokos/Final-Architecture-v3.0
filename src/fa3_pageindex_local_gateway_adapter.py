#!/usr/bin/env python3
from __future__ import annotations
import json,os,socket
from pathlib import Path
from typing import Any
from fa3_mcp_gateway import Adapter,GatewayDenied
PROVIDER_ID="FA3-PROVIDER-PAGEINDEX-LOCAL-001"
INDEX_ADAPTER_ID="fa3.adapter.pageindex.local.index"
RETRIEVE_ADAPTER_ID="fa3.adapter.pageindex.local.retrieve"
class PageIndexLocalRpcClient:
    def __init__(self,socket_path:Path,timeout:float=900.0):
        self.socket_path=socket_path; self.timeout=timeout
        if not self.socket_path.is_absolute(): raise GatewayDenied("PAGEINDEX_LOCAL_SOCKET_INVALID","provider socket must be absolute")
    def call(self,method:str,arguments:dict[str,Any])->dict[str,Any]:
        if method not in {"index","retrieve"}: raise GatewayDenied("PAGEINDEX_LOCAL_METHOD_DENIED","unsupported local provider method")
        payload=json.dumps({"method":method,"arguments":arguments},separators=(",",":")).encode()+b"\n"
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(self.timeout)
        try:
            s.connect(str(self.socket_path)); s.sendall(payload); chunks=[]
            while True:
                part=s.recv(65536)
                if not part: break
                chunks.append(part)
                if b"\n" in part: break
            raw=b"".join(chunks).split(b"\n",1)[0]
        except (OSError,TimeoutError) as exc:
            try:
                parent=self.socket_path.parent
                detail=(
                    f"{type(exc).__name__};socket={self.socket_path};"
                    f"socket_exists={self.socket_path.exists()};"
                    f"socket_is_socket={self.socket_path.is_socket()};"
                    f"parent_exists={parent.exists()};parent_is_dir={parent.is_dir()}"
                )
            except Exception:
                detail=type(exc).__name__
            raise GatewayDenied("PAGEINDEX_LOCAL_SERVICE_UNAVAILABLE",detail) from exc
        finally: s.close()
        try: response=json.loads(raw.decode())
        except Exception as exc: raise GatewayDenied("PAGEINDEX_LOCAL_RPC_SCHEMA","invalid provider response") from exc
        if not isinstance(response,dict): raise GatewayDenied("PAGEINDEX_LOCAL_RPC_SCHEMA","provider response must be object")
        if response.get("status")!="PASS":
            raise GatewayDenied(str(response.get("reason_code","PAGEINDEX_LOCAL_PROVIDER_ERROR")),str(response.get("message","local provider failed")))
        result=response.get("result")
        if not isinstance(result,dict): raise GatewayDenied("PAGEINDEX_LOCAL_RPC_SCHEMA","provider result must be object")
        return result
def build_adapters(socket_path:Path)->tuple[Adapter,Adapter]:
    client=PageIndexLocalRpcClient(socket_path)
    return (
      Adapter(adapter_id=INDEX_ADAPTER_ID,provider_id=PROVIDER_ID,handler=lambda a:client.call("index",a)),
      Adapter(adapter_id=RETRIEVE_ADAPTER_ID,provider_id=PROVIDER_ID,handler=lambda a:client.call("retrieve",a)),
    )
def factory_from_env()->tuple[Adapter,Adapter]:
    raw=os.environ.get("FA3_PAGEINDEX_LOCAL_SOCKET","")
    if not raw: raise GatewayDenied("PAGEINDEX_LOCAL_SOCKET_MISSING","FA3_PAGEINDEX_LOCAL_SOCKET is required")
    return build_adapters(Path(raw).expanduser())
