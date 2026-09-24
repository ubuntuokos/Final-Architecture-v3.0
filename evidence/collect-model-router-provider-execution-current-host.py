#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path
from typing import Any

SHA256=re.compile(r"^[0-9a-f]{64}$")
REQUIRED_CHECKS=[
 "real_provider_request_pass","credential_authentication_enforced_pass","session_affinity_pass","intra_provider_rebind_pass",
 "cross_provider_silent_fallback_denied_pass","unadmitted_provider_denied_pass","unadmitted_credential_denied_pass",
 "protocol_lossless_or_declared_degradation_pass","security_relevant_schema_loss_denied_pass",
 "raw_secret_absent_from_logs_pass","raw_secret_absent_from_evidence_pass","rollback_pass",
]
FORBIDDEN_KEYS={"api_key","authorization","password","secret_value","credential_value","access_token","refresh_token","bearer_token"}

class CollectionDenied(RuntimeError): pass

def git_head(root: Path) -> str:
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()

def loadj(path: Path) -> dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise CollectionDenied("input must be a JSON object")
    return value

def contains_secret(value: Any, key: str="") -> bool:
    if isinstance(value,dict):
        for k,v in value.items():
            lk=str(k).lower()
            if lk in FORBIDDEN_KEYS or lk.endswith(("_api_key","_password","_access_token","_refresh_token")): return True
            if contains_secret(v,lk): return True
    elif isinstance(value,list):
        return any(contains_secret(v,key) for v in value)
    elif isinstance(value,str):
        low=value.strip().lower()
        if low.startswith("bearer ") or low.startswith("sk-"): return True
    return False

def collect(root: Path, source: Path, output: Path) -> dict[str,Any]:
    raw=loadj(source)
    if contains_secret(raw): raise CollectionDenied("raw credential-like material detected in source evidence")
    if raw.get("schema")!="fa3.model-router-provider-execution-live-probe.v1": raise CollectionDenied("source schema mismatch")
    if raw.get("result")!="PASS" or raw.get("execution_scope")!="REAL_PROVIDER_CURRENT_HOST": raise CollectionDenied("real provider current-host PASS required")
    head=git_head(root)
    if raw.get("repository_head")!=head: raise CollectionDenied("repository HEAD binding mismatch")
    for field in ("provider_current_host_admission_receipt_sha256","secret_projection_receipt_sha256","credential_ref_sha256"):
        if SHA256.fullmatch(str(raw.get(field,""))) is None: raise CollectionDenied(f"invalid digest binding: {field}")
    for field in ("provider_id","logical_route","physical_model"):
        if not str(raw.get(field,"")).strip(): raise CollectionDenied(f"missing binding: {field}")
    checks=raw.get("checks")
    if not isinstance(checks,dict) or any(checks.get(name) is not True for name in REQUIRED_CHECKS): raise CollectionDenied("required positive/negative/rollback matrix incomplete")
    receipt={
      "schema":"fa3.model-router-provider-execution-current-host.v1",
      "result":"PASS","evidence_level":"CURRENT_HOST_REAL_PROVIDER_EXECUTION_E2E_PASS",
      "repository_head":head,"provider_id":raw["provider_id"],"logical_route":raw["logical_route"],"physical_model":raw["physical_model"],
      "credential_ref_sha256":raw["credential_ref_sha256"],
      "provider_current_host_admission_receipt_sha256":raw["provider_current_host_admission_receipt_sha256"],
      "secret_projection_receipt_sha256":raw["secret_projection_receipt_sha256"],
      "checks":{name:True for name in REQUIRED_CHECKS},
      "raw_secret_present":False,"synthetic_or_mock_provider":False,"global_promotion_claim":False
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    output.chmod(0o600)
    return receipt

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--input",required=True); ap.add_argument("--output",required=True)
    a=ap.parse_args()
    try:
        print(json.dumps(collect(Path(a.root).resolve(),Path(a.input).resolve(),Path(a.output).resolve()),indent=2))
        return 0
    except CollectionDenied as exc:
        print(json.dumps({"result":"FAIL","reason":str(exc)},indent=2))
        return 2
if __name__=="__main__": raise SystemExit(main())
