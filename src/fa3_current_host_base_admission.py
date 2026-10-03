#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")

def load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict): raise ValueError(f"JSON object required: {path}")
    return value

def sha256_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def digest(value:dict[str,Any])->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def build_candidate(root:Path,source_sha:str,run_id:str)->dict[str,Any]:
    root=root.resolve()
    if HEX40.fullmatch(source_sha) is None: raise ValueError("source SHA invalid")
    audit=load(root/"reports/current-host-evidence-audit.json")
    acceptance=load(root/"acceptance/acceptance-report.json")
    bundles=load(root/"reports/current-host-capability-test-bundle-assembler.json")
    attest=load(root/"reports/current-host-capability-attestation-producer.json")
    handoff=load(root/"reports/current-host-capability-handoff.json")
    host=root/".fa3-current-host/global-closure/host/host-fingerprint.json"
    if not host.is_file(): raise ValueError("host fingerprint missing")
    checks=[
      audit.get("runtime_closure")=="PASS",
      audit.get("registry_pass_count")==175,
      audit.get("registry_pending_count")==0,
      audit.get("qualified_current_host_receipt_count")==175,
      acceptance.get("status")=="PASS",
      acceptance.get("criteria_passed")==19,
      acceptance.get("criteria_total")==19,
      bundles.get("bundles_materialized")==175,
      attest.get("attestations_materialized")==175,
      handoff.get("receipts_materialized")==175,
    ]
    if not all(checks): raise ValueError("full physical closure is not 175/525 + 19/19 complete")
    payload={
      "schema":"fa3.current-host-base-admission-candidate.v1",
      "status":"FULL_175_525_PHYSICAL_PASS",
      "source_commit":source_sha,
      "physical_audit_run_id":str(run_id),
      "capability_count":175,
      "obligation_count":525,
      "acceptance_criteria_passed":19,
      "acceptance_criteria_total":19,
      "host_fingerprint_sha256":sha256_file(host),
      "evidence_registry_sha256":sha256_file(root/"evidence/evidence-registry.json"),
      "bundles_receipts_attestations_complete":True,
      "positive_negative_rollback_complete":True,
      "synthetic_current_host_pass":False,
      "historical_evidence_reused":False,
      "global_promotion_claim":False,
    }
    payload["base_release_digest"]=digest(payload)
    payload["effective_host_digest"]=payload["base_release_digest"]
    return payload

def admitted_state(candidate:dict[str,Any])->dict[str,Any]:
    if candidate.get("schema")!="fa3.current-host-base-admission-candidate.v1": raise ValueError("candidate schema invalid")
    if candidate.get("status")!="FULL_175_525_PHYSICAL_PASS": raise ValueError("candidate not PASS")
    if candidate.get("capability_count")!=175 or candidate.get("obligation_count")!=525: raise ValueError("candidate baseline invalid")
    if candidate.get("acceptance_criteria_passed")!=19 or candidate.get("acceptance_criteria_total")!=19: raise ValueError("candidate acceptance invalid")
    if candidate.get("positive_negative_rollback_complete") is not True: raise ValueError("obligation proof incomplete")
    if candidate.get("bundles_receipts_attestations_complete") is not True: raise ValueError("evidence chain incomplete")
    if candidate.get("synthetic_current_host_pass") is not False: raise ValueError("synthetic PASS forbidden")
    sha=candidate.get("source_commit"); base=candidate.get("base_release_digest"); host=candidate.get("host_fingerprint_sha256")
    if not isinstance(sha,str) or HEX40.fullmatch(sha) is None: raise ValueError("source SHA invalid")
    if not isinstance(base,str) or HEX64.fullmatch(base) is None: raise ValueError("base digest invalid")
    if not isinstance(host,str) or HEX64.fullmatch(host) is None: raise ValueError("host digest invalid")
    return {
      "schema":"fa3.current-host-base-state.v1",
      "id":"FA3-CURRENT-HOST-BASE-STATE-001",
      "status":"CURRENT_HOST_BASE_ADMITTED",
      "capability_count":175,
      "obligation_count":525,
      "base_release_digest":base,
      "effective_host_digest":base,
      "admission_source_commit":sha,
      "physical_audit_run_id":candidate.get("physical_audit_run_id"),
      "physical_audit_head_sha":sha,
      "host_fingerprint_sha256":host,
      "evidence_registry_sha256":candidate.get("evidence_registry_sha256"),
      "positive_negative_rollback_complete":True,
      "bundles_receipts_attestations_complete":True,
      "acceptance_criteria_passed":19,
      "acceptance_criteria_total":19,
      "delta_authority_id":"FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001",
      "historical_evidence_relabeling":"FORBIDDEN",
      "synthetic_current_host_pass_allowed":False,
      "hosted_ci_may_admit_base":False,
      "global_promotion_claim":False,
    }

def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--root",default="."); sub=p.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("candidate"); c.add_argument("--source-sha",required=True); c.add_argument("--run-id",required=True); c.add_argument("--output",required=True)
    a=sub.add_parser("admit"); a.add_argument("--candidate",required=True); a.add_argument("--output",required=True)
    args=p.parse_args(); root=Path(args.root).resolve()
    if args.cmd=="candidate": result=build_candidate(root,args.source_sha,args.run_id)
    else: result=admitted_state(load(Path(args.candidate)))
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
