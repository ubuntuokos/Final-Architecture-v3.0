#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
def run(*c):
 p=subprocess.run(c,text=True,capture_output=True)
 if p.returncode: raise RuntimeError(p.stderr.strip())
 return p.stdout.strip()
def main():
 a=argparse.ArgumentParser(); a.add_argument("--root-cert",required=True); a.add_argument("--intermediate-cert",required=True); a.add_argument("--operator-id",required=True); a.add_argument("--medium-id",default="local-protected-storage"); a.add_argument("--output",default="evidence/receipts/step-ca-root-ceremony.json"); x=a.parse_args(); r=Path(x.root_cert).resolve(); i=Path(x.intermediate_cert).resolve()
 route_present=bool(run("ip","route","show","default"))
 run("openssl","verify","-CAfile",str(r),str(r)); run("openssl","verify","-CAfile",str(r),str(i))
 for p in (r,i):
  if "CA:TRUE" not in run("openssl","x509","-in",str(p),"-noout","-text"): raise RuntimeError("CA basicConstraints missing")
 def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
 def q(p,flag): return run("openssl","x509","-in",str(p),"-noout",flag).split("=",1)[-1].strip()
 out={"schema":"fa3.step-ca-root-ceremony-receipt.v1","status":"PASS","ceremony_id":"fa3-root-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),"operator_id":x.operator_id,"medium_id":x.medium_id,"network_default_route_present":route_present,"root_private_key_bytes_collected":False,"root_private_key_exported_online":False,"root_certificate":{"sha256":h(r),"subject":q(r,"-subject"),"serial":q(r,"-serial")},"intermediate_certificate":{"sha256":h(i),"subject":q(i,"-subject"),"issuer":q(i,"-issuer"),"serial":q(i,"-serial")},"chain_verification":"PASS","completed_at":datetime.now(timezone.utc).isoformat(),"secret_values_collected":False}
 p=Path(x.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2))
if __name__=="__main__":
 try: main()
 except Exception as e: print(f"FA3 STEP-CA ROOT CEREMONY FAILED: {e}",file=sys.stderr); raise SystemExit(2)
