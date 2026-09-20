#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, grp, hashlib, json, os, pwd, re, secrets, socket, socketserver, struct, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_SECRET_BYTES = 512 * 1024
ALLOWED_SECRET_KINDS = {
    "API_KEY","API_TOKEN","SERVICE_TOKEN","OAUTH_CLIENT_SECRET","OAUTH_REFRESH_TOKEN",
    "PROVIDER_CREDENTIAL","PROVIDER_LOGIN_PASSWORD","SERVICE_PASSWORD","DATABASE_PASSWORD",
    "SMTP_PASSWORD","MCP_PROVIDER_CREDENTIAL","PRIVATE_CREDENTIAL_MATERIAL","GENERIC_FA3_CREDENTIAL",
}
SECRET_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,256}$")
def valid_secret_id(value:str)->bool:
    return bool(SECRET_ID_RE.fullmatch(value)) and all(part not in {"", ".", ".."} for part in value.split("/"))
DEFAULT_SOCKET = "/run/fa3-secret-broker/broker.sock"
DEFAULT_VAULT = "/run/fa3/machine-state"
DEFAULT_POLICY = "/etc/fa3/secret-policy.d"
DEFAULT_AUDIT = "/run/fa3-secret-broker/audit.jsonl"

def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".fa3-", dir=str(path.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
        dfd=os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

class SecretStore:
    def __init__(self, root: Path):
        self.root=root; self.objects=root/"objects"; self.index_path=root/"index.json"
        if not self.objects.exists():
            self.objects.mkdir(parents=True, exist_ok=True); os.chmod(self.objects,0o700)
        elif self.objects.stat().st_mode & 0o077:
            raise RuntimeError("secret object directory permissions too broad")
        if not self.index_path.exists(): _atomic_write(self.index_path,b'{"schema":"fa3.secret-index.v1","secrets":{}}\n')
    def _index(self)->dict[str,Any]:
        x=json.loads(self.index_path.read_text())
        if x.get("schema")!="fa3.secret-index.v1" or not isinstance(x.get("secrets"),dict): raise RuntimeError("invalid secret index")
        return x
    def metadata(self, secret_id:str)->dict[str,Any]|None: return self._index()["secrets"].get(secret_id)
    def list_metadata(self)->list[dict[str,Any]]:
        idx=self._index()["secrets"]
        return [{"secret_id":sid,"version":meta["version"],"classification":meta["classification"],"secret_kind":meta["secret_kind"]}
                for sid,meta in sorted(idx.items())]
    def put(self, secret_id:str, value:bytes, classification:str, secret_kind:str)->dict[str,Any]:
        if not valid_secret_id(secret_id): raise ValueError("invalid secret_id")
        if not value or len(value)>MAX_SECRET_BYTES: raise ValueError("secret size outside 1..524288 bytes")
        if classification not in {"MACHINE_SERVICE_SECRET","USER_SESSION_SECRET"}: raise ValueError("invalid classification")
        if secret_kind not in ALLOWED_SECRET_KINDS: raise ValueError("invalid secret_kind: credential secrets only")
        idx=self._index(); old=idx["secrets"].get(secret_id); obj=secrets.token_hex(32)
        _atomic_write(self.objects/obj,value)
        version=int((old or {}).get("version",0))+1
        previous=json.loads(json.dumps(idx))
        idx["secrets"][secret_id]={"object":obj,"version":version,"classification":classification,"secret_kind":secret_kind}
        try:
            _atomic_write(self.index_path,(json.dumps(idx,sort_keys=True,separators=(",",":"))+"\n").encode())
        except Exception:
            try:(self.objects/obj).unlink()
            except FileNotFoundError:pass
            raise
        if old:
            try:
                (self.objects/old["object"]).unlink()
                dfd=os.open(self.objects,os.O_DIRECTORY)
                try:os.fsync(dfd)
                finally:os.close(dfd)
            except Exception:
                _atomic_write(self.index_path,(json.dumps(previous,sort_keys=True,separators=(",",":"))+"\n").encode())
                try:(self.objects/obj).unlink()
                except FileNotFoundError:pass
                raise
        return {"secret_id":secret_id,"version":version,"classification":classification,"secret_kind":secret_kind}
    def get(self, secret_id:str)->tuple[dict[str,Any],bytes]:
        meta=self.metadata(secret_id)
        if not meta: raise KeyError("secret not found")
        obj=str(meta.get("object",""))
        if not re.fullmatch(r"[0-9a-f]{64}",obj): raise RuntimeError("invalid object reference")
        p=self.objects/obj; st=p.stat()
        if st.st_mode & 0o077: raise RuntimeError("secret object permissions too broad")
        return meta,p.read_bytes()
    def delete(self, secret_id:str)->bool:
        idx=self._index(); old=idx["secrets"].get(secret_id)
        if not old:return False
        obj=self.objects/old["object"]
        try:obj.unlink()
        except FileNotFoundError:pass
        dfd=os.open(self.objects,os.O_DIRECTORY)
        try:os.fsync(dfd)
        finally:os.close(dfd)
        idx["secrets"].pop(secret_id,None)
        _atomic_write(self.index_path,(json.dumps(idx,sort_keys=True,separators=(",",":"))+"\n").encode())
        return True

class PolicyStore:
    def __init__(self, root:Path): self.root=root
    def get(self, secret_id:str)->dict[str,Any]|None:
        if not self.root.is_dir():return None
        matches=[]
        for p in sorted(self.root.glob("*.json")):
            try:x=json.loads(p.read_text())
            except Exception:continue
            if x.get("schema")=="fa3.secret-projection-policy.v1" and x.get("secret_id")==secret_id and x.get("secret_kind") in ALLOWED_SECRET_KINDS:
                matches.append(x)
        if len(matches)!=1:return None
        x=matches[0]
        if x.get("classification")=="MACHINE_SERVICE_SECRET":
            consumers=x.get("allowed_consumers") or []
            if not consumers:return None
            for consumer in consumers:
                users=consumer.get("allowed_unix_users") or []
                if len(users)!=1 or users[0] in {"root","fa3-secret-broker"}:return None
        return x

def _peer_identity(conn:socket.socket)->tuple[int,int,int]:
    return struct.unpack("3i",conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize("3i")))
def _username(uid:int)->str:
    try:return pwd.getpwuid(uid).pw_name
    except KeyError:return str(uid)
def _is_admin(uid:int)->bool:
    if uid==0:return True
    try:g=grp.getgrnam("fa3-secret-admin"); p=pwd.getpwuid(uid)
    except KeyError:return False
    return p.pw_name in g.gr_mem or p.pw_gid==g.gr_gid
def _proc_exe(pid:int)->str:
    try:return os.readlink(f"/proc/{pid}/exe")
    except OSError:return ""
def _proc_cgroup(pid:int)->str:
    try:return Path(f"/proc/{pid}/cgroup").read_text()
    except OSError:return ""

def authorize(policy:dict[str,Any],uid:int,pid:int,consumer_id:str,projection:str)->bool:
    if policy.get("exportable") is not False:return False
    if projection not in set(policy.get("allowed_projections") or []):return False
    user=_username(uid)
    for c in policy.get("allowed_consumers") or []:
        if c.get("consumer_id")!=consumer_id or user not in set(c.get("allowed_unix_users") or []):continue
        exes=c.get("allowed_executables") or []
        if exes and _proc_exe(pid) not in exes:continue
        units=c.get("allowed_systemd_units") or []
        if units and not any(unit in _proc_cgroup(pid) for unit in units):continue
        return True
    return False

class Broker:
    def __init__(self,vault:Path,policies:Path,audit:Path):
        self.store=SecretStore(vault);self.policies=PolicyStore(policies);self.audit=audit
        self.audit.parent.mkdir(parents=True,exist_ok=True)
    def _audit(self,operation:str,secret_id:str,consumer_id:str,uid:int,projection:str,decision:str)->None:
        ev={"schema":"fa3.secret-audit-event.v1","event_id":"sae-"+secrets.token_hex(12),
            "timestamp":datetime.now(timezone.utc).isoformat(),"operation":operation,
            "secret_ref_sha256":hashlib.sha256(secret_id.encode()).hexdigest(),"consumer_id":consumer_id,
            "peer_uid":uid,"projection":projection,"decision":decision,"secret_values_collected":False}
        with self.audit.open("a",encoding="utf-8") as f:
            f.write(json.dumps(ev,sort_keys=True,separators=(",",":"))+"\n");f.flush();os.fsync(f.fileno())
    def handle(self,req:dict[str,Any],uid:int,gid:int,pid:int)->dict[str,Any]:
        op=str(req.get("op",""));sid=str(req.get("secret_id",""));consumer=str(req.get("consumer_id",""))
        projection=str(req.get("projection","UDS_SINGLE_SECRET"))
        if op=="health":return {"ok":True,"schema":"fa3.secret-broker-health.v1","raw_vault_export":False}
        if op in {"put","rotate","delete","revoke","list_metadata","admin_metadata"}:
            if not _is_admin(uid):
                self._audit(op,sid,consumer,uid,projection,"DENY_ADMIN_REQUIRED");return {"ok":False,"error":"admin authorization required"}
            if op in {"put","rotate"}:
                try:value=base64.b64decode(req.get("secret_b64",""),validate=True)
                except Exception:return {"ok":False,"error":"invalid secret payload"}
                classification=str(req.get("classification","MACHINE_SERVICE_SECRET"))
                secret_kind=str(req.get("secret_kind",""))
                old=self.store.metadata(sid)
                if op=="rotate":
                    if not old:
                        self._audit(op,sid,consumer or "ADMIN",uid,projection,"DENY_MISSING")
                        return {"ok":False,"error":"cannot rotate missing secret"}
                    if old.get("classification")!=classification or old.get("secret_kind")!=secret_kind:
                        self._audit(op,sid,consumer or "ADMIN",uid,projection,"DENY_METADATA_CHANGE")
                        return {"ok":False,"error":"rotation cannot change classification or secret_kind"}
                try:
                    meta=self.store.put(sid,value,classification,secret_kind)
                except Exception as exc:
                    self._audit(op,sid,consumer or "ADMIN",uid,projection,"DENY_STORE")
                    return {"ok":False,"error":str(exc)}
                self._audit(op,sid,consumer or "ADMIN",uid,projection,"ALLOW");return {"ok":True,"metadata":meta}
            if op=="list_metadata":
                self._audit(op,"_metadata_index",consumer or "ADMIN",uid,projection,"ALLOW")
                return {"ok":True,"secrets":self.store.list_metadata(),"secret_values_collected":False}
            if op=="admin_metadata":
                meta=self.store.metadata(sid)
                if not meta:
                    self._audit(op,sid,consumer or "ADMIN",uid,projection,"DENY_MISSING")
                    return {"ok":False,"error":"secret not found"}
                self._audit(op,sid,consumer or "ADMIN",uid,projection,"ALLOW")
                return {"ok":True,"metadata":{"secret_id":sid,"version":meta["version"],"classification":meta["classification"],"secret_kind":meta["secret_kind"]}}
            try:ok=self.store.delete(sid)
            except Exception as exc:
                self._audit(op,sid,consumer or "ADMIN",uid,projection,"DENY_STORE")
                return {"ok":False,"error":str(exc)}
            self._audit(op,sid,consumer or "ADMIN",uid,projection,"ALLOW")
            return {"ok":True,"revoked":ok} if op=="revoke" else {"ok":True,"deleted":ok}
        if op not in {"get","metadata"}:return {"ok":False,"error":"unsupported operation"}
        if not valid_secret_id(sid):return {"ok":False,"error":"invalid secret_id"}
        policy=self.policies.get(sid)
        if not policy or not authorize(policy,uid,pid,consumer,projection):
            self._audit(op,sid,consumer,uid,projection,"DENY_POLICY");return {"ok":False,"error":"policy denied"}
        try:
            if op=="metadata":
                meta=self.store.metadata(sid)
                if not meta: raise KeyError("secret not found")
                value=None
            else:
                meta,value=self.store.get(sid)
        except Exception as exc:
            self._audit(op,sid,consumer,uid,projection,"DENY_MISSING");return {"ok":False,"error":str(exc)}
        if meta.get("classification") != policy.get("classification") or meta.get("secret_kind") != policy.get("secret_kind"):
            self._audit(op,sid,consumer,uid,projection,"DENY_METADATA_POLICY_MISMATCH")
            return {"ok":False,"error":"policy metadata mismatch"}
        self._audit(op,sid,consumer,uid,projection,"ALLOW")
        out={"ok":True,"metadata":{"secret_id":sid,"version":meta["version"],"classification":meta["classification"],"secret_kind":meta["secret_kind"]}}
        if op=="get":out["secret_b64"]=base64.b64encode(value).decode("ascii")
        return out

class Handler(socketserver.StreamRequestHandler):
    def handle(self)->None:
        uid,gid,pid=_peer_identity(self.connection);line=self.rfile.readline(1024*1024+1)
        if len(line)>1024*1024:return
        try:req=json.loads(line)
        except Exception:self.wfile.write(b'{"ok":false,"error":"invalid request"}\n');return
        self.wfile.write((json.dumps(self.server.broker.handle(req,uid,gid,pid),separators=(",",":"))+"\n").encode())
class UnixServer(socketserver.UnixStreamServer):
    def __init__(self,path:str,broker:Broker):self.broker=broker;super().__init__(path,Handler)

def serve(vault:Path,policy:Path,sock:Path,audit:Path)->None:
    sock.parent.mkdir(parents=True,exist_ok=True)
    try:sock.unlink()
    except FileNotFoundError:pass
    with UnixServer(str(sock),Broker(vault,policy,audit)) as srv:
        os.chmod(sock,0o660)
        try:os.chown(sock,-1,grp.getgrnam("fa3-secret-clients").gr_gid)
        except KeyError:pass
        srv.serve_forever()

def request(sock:Path,payload:dict[str,Any])->dict[str,Any]:
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.connect(str(sock));s.sendall((json.dumps(payload,separators=(",",":"))+"\n").encode());data=b""
        while not data.endswith(b"\n"):
            chunk=s.recv(65536)
            if not chunk:break
            data+=chunk
            if len(data)>2*1024*1024:raise RuntimeError("oversized broker response")
    return json.loads(data)

def main()->int:
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True);sp=sub.add_parser("serve")
    sp.add_argument("--vault-root",default=DEFAULT_VAULT);sp.add_argument("--policy-dir",default=DEFAULT_POLICY)
    sp.add_argument("--socket",default=DEFAULT_SOCKET);sp.add_argument("--audit-log",default=DEFAULT_AUDIT)
    a=ap.parse_args();serve(Path(a.vault_root),Path(a.policy_dir),Path(a.socket),Path(a.audit_log));return 0
if __name__=="__main__":raise SystemExit(main())
