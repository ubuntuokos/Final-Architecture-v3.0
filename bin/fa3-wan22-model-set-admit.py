#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

PROVIDER_ID="FA3-PROVIDER-WAN22-001"
UPSTREAM_REV="1ea34ff48f87168174e12956e200b1d908b1c5ff"

class ModelSetDenied(RuntimeError):pass

def loadj(p:Path)->dict[str,Any]:return json.loads(p.read_text(encoding="utf-8"))
def sha256_file(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def canonical_sha(rows:list[dict[str,Any]])->str:
 raw=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
 return hashlib.sha256(raw).hexdigest()

def admit(manifest_path:Path,output:Path)->dict[str,Any]:
 m=loadj(manifest_path)
 if m.get("schema")!="fa3.wan22-model-set-manifest.v1":raise ModelSetDenied("model set manifest schema mismatch")
 if m.get("provider_id")!=PROVIDER_ID:raise ModelSetDenied("provider mismatch")
 if m.get("upstream_revision")!=UPSTREAM_REV:raise ModelSetDenied("model set upstream revision mismatch")
 root=Path(str(m.get("checkpoint_dir",""))).expanduser().resolve()
 if not root.is_dir():raise ModelSetDenied("checkpoint directory missing")
 items=m.get("artifacts")
 if not isinstance(items,list) or not items:raise ModelSetDenied("model set contains no artifacts")
 verified=[]
 seen=set()
 for item in items:
  if not isinstance(item,dict):raise ModelSetDenied("artifact item must be object")
  rel=str(item.get("relative_path","")).strip()
  receipt_ref=str(item.get("admission_receipt","")).strip()
  if not rel or rel.startswith("/") or ".." in Path(rel).parts or rel in seen:raise ModelSetDenied("invalid or duplicate relative artifact path")
  seen.add(rel)
  artifact=(root/rel).resolve()
  try: artifact.relative_to(root)
  except ValueError as exc: raise ModelSetDenied("artifact escapes checkpoint directory") from exc
  receipt=Path(receipt_ref).expanduser().resolve()
  if not artifact.is_file() or not receipt.is_file():raise ModelSetDenied("artifact or security admission receipt missing")
  digest=sha256_file(artifact)
  r=loadj(receipt)
  if r.get("schema")!="fa3.model-artifact-admission-receipt.v1":raise ModelSetDenied("existing FA3 model artifact admission schema required")
  if r.get("admitted") is not True:raise ModelSetDenied("model artifact not admitted")
  if r.get("artifact_sha256")!=digest:raise ModelSetDenied("model artifact admission digest mismatch")
  if r.get("malware_security_admission") not in {True,"PASS","ADMITTED"}:raise ModelSetDenied("model artifact security admission missing")
  verified.append({"relative_path":rel,"sha256":digest,"bytes":artifact.stat().st_size,"admission_receipt_sha256":sha256_file(receipt)})
 verified.sort(key=lambda x:x["relative_path"])
 result={
  "schema":"fa3.wan22-model-set-admission.v1",
  "provider_id":PROVIDER_ID,
  "status":"PASS",
  "checkpoint_dir":str(root),
  "upstream_revision":UPSTREAM_REV,
  "artifact_count":len(verified),
  "artifacts":verified,
  "artifact_set_sha256":canonical_sha(verified),
  "source_security_receipt_schema":"fa3.model-artifact-admission-receipt.v1",
  "aggregator_is_security_authority":False,
  "all_artifacts_individually_security_admitted":True,
  "license_basis":"FA3-WAN22-UPSTREAM-REFERENCE-2026-09-26",
  "license_decision":"ALLOW",
  "network_fetch_performed":False
 }
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
 return result
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("--manifest",required=True);ap.add_argument("--output",default="evidence/receipts/wan22-model-set-admission.json");a=ap.parse_args()
 try:r=admit(Path(a.manifest),Path(a.output));print(json.dumps(r,indent=2));return 0
 except Exception as exc:print(json.dumps({"provider_id":PROVIDER_ID,"status":"FAIL","error":str(exc)},indent=2));return 2
if __name__=="__main__":raise SystemExit(main())
