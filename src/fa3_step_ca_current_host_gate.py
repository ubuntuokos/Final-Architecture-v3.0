#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from typing import Any
GATE_ID="FA3-GATE-STEP-CA-CURRENT-HOST-001"; PROVIDER_ID="FA3-PROVIDER-STEP-CA-001"; RECEIPT="evidence/receipts/step-ca-current-host.json"; HEX64=re.compile(r"^[0-9a-f]{64}$")
def f(code:str,msg:str,**x:Any)->dict[str,Any]: return {"code":code,"severity":"P0","message":msg,**x}
def d(v:Any)->bool: return isinstance(v,str) and HEX64.fullmatch(v) is not None
def validate_receipt(r:dict[str,Any])->list[dict[str,Any]]:
 fs=[]
 if r.get("schema")!="fa3.step-ca-current-host-receipt.v1" or r.get("provider_id")!=PROVIDER_ID: fs.append(f("STEP-CA-HOST-001","receipt identity mismatch"))
 if r.get("status")!="PASS" or r.get("evidence_level")!="CURRENT_HOST_PRODUCTION_E2E_PASS" or r.get("synthetic") is not False: fs.append(f("STEP-CA-HOST-002","real current-host PASS semantics missing"))
 s=r.get("supply_chain",{})
 if s.get("status")!="PASS" or s.get("server",{}).get("version")!="0.30.2" or s.get("client",{}).get("version")!="0.30.6": fs.append(f("STEP-CA-HOST-003","supply-chain pin mismatch"))
 for name in ("server","client"):
  x=s.get(name,{})
  if not (d(x.get("asset_sha256")) and d(x.get("binary_sha256")) and x.get("sigstore_verified") is True): fs.append(f("STEP-CA-HOST-004","artifact identity or Sigstore proof incomplete",component=name))
 c=r.get("root_ceremony",{})
 if not (c.get("status")=="PASS" and c.get("root_private_key_bytes_collected") is False and c.get("root_private_key_exported_online") is False and c.get("chain_verification")=="PASS"): fs.append(f("STEP-CA-HOST-005","offline root ceremony invariant failed"))
 a=r.get("activation",{})
 if not (a.get("status")=="PASS" and a.get("service_user")=="fa3-step-ca" and a.get("root_private_key_present_online") is False and a.get("intermediate_key_encrypted") is True and a.get("systemd_credential_unlock") is True and a.get("transfer_bundle_removed") is True): fs.append(f("STEP-CA-HOST-006","online activation boundary failed"))
 rt=r.get("runtime",{})
 if not (rt.get("service_active") is True and rt.get("bind")=="127.0.0.1:9443" and rt.get("root_private_key_present_online") is False and rt.get("certificate_chain_valid") is True): fs.append(f("STEP-CA-HOST-007","live runtime invariant failed"))
 e=r.get("e2e",{})
 for key in ("acme_issue_pass","acme_reorder_pass","mtls_pass","ssh_certificate_pass","trust_bundle_pass"):
  if e.get(key) is not True: fs.append(f("STEP-CA-HOST-008","E2E proof missing",check=key))
 try:
  if float(e.get("max_observed_tls_ttl_hours",9999))>24: fs.append(f("STEP-CA-HOST-009","TLS TTL exceeds 24h"))
 except Exception: fs.append(f("STEP-CA-HOST-009","TLS TTL unreadable"))
 b=r.get("backup_restore",{})
 if not (b.get("status")=="PASS" and b.get("root_private_key_in_backup") is False and b.get("unlock_secret_in_backup") is False and b.get("shadow_health_pass") is True and b.get("post_restore_issuance_pass") is True): fs.append(f("STEP-CA-HOST-010","backup/restore drill incomplete or secret boundary violated"))
 if r.get("secret_values_collected") is not False: fs.append(f("STEP-CA-HOST-011","secret collection boundary failed"))
 if r.get("runtime_promotion_eligible") is not True or r.get("global_promotion_claim") is not False: fs.append(f("STEP-CA-HOST-012","promotion boundary mismatch"))
 if r.get("new_capabilities")!=0 or r.get("new_architectural_authorities")!=0 or r.get("capability_count_after")!=143: fs.append(f("STEP-CA-HOST-013","capability/authority invariant drift"))
 return fs
def gate(root:Path,receipt:Path|None=None)->dict[str,Any]:
 p=receipt or root/RECEIPT
 fs=[f("STEP-CA-HOST-000","current-host receipt missing")] if not p.is_file() else []
 if p.is_file():
  try: fs.extend(validate_receipt(json.loads(p.read_text())))
  except Exception as exc: fs.append(f("STEP-CA-HOST-014","receipt unreadable",error=repr(exc)))
 out={"schema":"fa3.step-ca-current-host-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not fs else "FAIL","findings":fs,"global_promotion_claim":False}
 q=root/"reports/step-ca-current-host-gate-report.json"; q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(out,indent=2)+"\n"); return out
def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--receipt"); a=ap.parse_args(); root=Path(a.root).resolve(); out=gate(root,Path(a.receipt).resolve() if a.receipt else None); print(json.dumps(out,indent=2)); return 0 if out["result"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
