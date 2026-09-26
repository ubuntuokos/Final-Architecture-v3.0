#!/usr/bin/env python3
import argparse,hashlib,json,pwd,stat,subprocess
from datetime import datetime,timezone
from pathlib import Path
from fa3_release_baseline import module_active_capability_count
ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cmd(x): return subprocess.run(x,text=True,capture_output=True)
def intermediate_key_boundary(p,activation,account):
 p=Path(p)
 if account is None or activation.get("intermediate_key_encrypted") is not True or p.is_symlink(): return False
 try: st=p.stat()
 except OSError: return False
 return stat.S_ISREG(st.st_mode) and st.st_uid==account.pw_uid and st.st_gid==account.pw_gid and stat.S_IMODE(st.st_mode)==0o600
def rootkey():
 for b in (Path("/etc/fa3"),Path("/var/lib/fa3-step-ca")):
  if b.exists():
   for p in b.rglob("*"):
    if p.is_file() and ("root_ca_key" in p.name.lower() or p.name.lower() in {"root.key","root_ca.key"}): return True
 return False
def main():
 a=argparse.ArgumentParser(); a.add_argument("--mode",choices=["preflight","full"],default="full"); x=a.parse_args(); fs=[]
 sp=ROOT/".fa3-current-host/step-ca/bootstrap/supply-chain.json"; cp=ROOT/"evidence/receipts/step-ca-root-ceremony.json"; ap=Path("/var/lib/fa3-step-ca/evidence/activation.json"); ep=ROOT/"evidence/runtime/step-ca-current-host/e2e.json"; bp=ROOT/"evidence/runtime/step-ca-current-host/backup-restore.json"
 s=load(sp) if sp.is_file() else {}; c=load(cp) if cp.is_file() else {}; act=load(ap) if ap.is_file() else {}
 if s.get("status")!="PASS": fs.append("SUPPLY_CHAIN"); 
 if c.get("status")!="PASS": fs.append("ROOT_CEREMONY")
 if act.get("status")!="PASS": fs.append("ACTIVATION")
 try: account=pwd.getpwnam("fa3-step-ca"); user=account.pw_name
 except KeyError: account=None; user=None; fs.append("SERVICE_USER")
 b=Path("/usr/local/lib/fa3/step-ca/0.30.2/bin/step-ca")
 if not b.is_file(): fs.append("BINARY")
 elif s.get("server",{}).get("binary_sha256")!=sha(b.resolve()): fs.append("BINARY_DIGEST")
 ik=Path("/var/lib/fa3-step-ca/secrets/intermediate_ca_key"); encrypted=intermediate_key_boundary(ik,act,account); present=act.get("root_private_key_present_online") is not False or rootkey()
 if present: fs.append("ROOT_KEY_ONLINE")
 if not encrypted: fs.append("INTERMEDIATE_ENCRYPTION")
 rc=Path("/var/lib/fa3-step-ca/certs/root_ca.crt"); ic=Path("/var/lib/fa3-step-ca/certs/intermediate_ca.crt"); chain=rc.is_file() and ic.is_file() and cmd(["openssl","verify","-CAfile",str(rc),str(ic)]).returncode==0
 if not chain: fs.append("CHAIN")
 svc=cmd(["systemctl","show","fa3-step-ca.service","-p","User","-p","ActiveState"]); active=svc.returncode==0 and "User=fa3-step-ca" in svc.stdout and "ActiveState=active" in svc.stdout
 if not active: fs.append("SERVICE")
 cfg=Path("/etc/fa3/step-ca/ca.json"); bind=load(cfg).get("address") if cfg.is_file() else None
 if bind!="127.0.0.1:9443": fs.append("BIND")
 rt={"service_active":active,"service_user":user,"bind":bind,"root_private_key_present_online":present,"intermediate_key_encrypted":encrypted,"certificate_chain_valid":chain}
 if x.mode=="preflight":
  out={"schema":"fa3.step-ca-current-host-preflight.v1","status":"PASS" if not fs else "PENDING","findings":fs,"runtime":rt,"global_promotion_claim":False,"secret_values_collected":False}; p=ROOT/"evidence/receipts/step-ca-current-host-preflight.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2)); return 0 if not fs else 2
 e=load(ep) if ep.is_file() else {}; br=load(bp) if bp.is_file() else {}
 if e.get("status")!="PASS": fs.append("E2E")
 if br.get("status")!="PASS": fs.append("RESTORE")
 st="PASS" if not fs else "FAIL"; out={"schema":"fa3.step-ca-current-host-receipt.v1","provider_id":"FA3-PROVIDER-STEP-CA-001","status":st,"evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS" if st=="PASS" else "CURRENT_HOST_EXECUTION_FAILED","synthetic":False,"completed_at":datetime.now(timezone.utc).isoformat(),"supply_chain":s,"root_ceremony":c,"activation":act,"runtime":rt,"e2e":e,"backup_restore":br,"secret_values_collected":False,"runtime_promotion_eligible":st=="PASS","global_promotion_claim":False,"new_capabilities":0,"new_architectural_authorities":0,"capability_count_after":module_active_capability_count(__file__),"findings":fs}
 p=ROOT/"evidence/receipts/step-ca-current-host.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2)); return 0 if st=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
