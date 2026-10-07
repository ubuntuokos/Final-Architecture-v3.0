#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fa3_release_baseline import load_active_release_baseline

STATUS_ID = "FA3-GOVERNANCE-STATUS-PROJECTION-001"
STATUS_GATE_ID = "FA3-GOVERNANCE-STATUS-GATESET-001"


def _load_optional(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"], text=True).strip()


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _artifact_binding(root: Path, rel: str) -> dict[str, Any]:
    path=root/rel
    out={"path":rel,"present":path.is_file()}
    if not path.is_file():
        return out
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        out["parseable_json"]=False
        return out
    out["parseable_json"]=isinstance(obj,dict)
    if not isinstance(obj,dict):
        return out
    candidates={
        "source_commit":[
            obj.get("source_commit"),obj.get("commit_sha"),obj.get("tested_repository_head"),
            obj.get("source",{}).get("tested_repository_head") if isinstance(obj.get("source"),dict) else None,
            obj.get("provenance",{}).get("source_commit") if isinstance(obj.get("provenance"),dict) else None,
        ],
        "run_id":[
            obj.get("run_id"),obj.get("workflow_run_id"),
            obj.get("source",{}).get("run_id") if isinstance(obj.get("source"),dict) else None,
        ],
        "expires_at":[obj.get("expires_at"),obj.get("expiry"),obj.get("valid_until")],
        "host_id":[obj.get("host_id"),obj.get("machine_id"),obj.get("runner_name")],
    }
    for key,values in candidates.items():
        value=next((v for v in values if v not in (None,"")),None)
        if value is not None:
            out[key]=value
    return out


def project(root: Path, *, now: datetime | None=None) -> dict[str, Any]:
    root=Path(root).resolve()
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    baseline=load_active_release_baseline(root)
    evidence=_load_optional(root/"evidence/evidence-registry.json") or {}
    acceptance=_load_optional(root/"acceptance/acceptance-report.json")
    promotion=_load_optional(root/"promotion/runtime-status.json")
    gate_registry=_load_optional(root/"canonical/FA3-GATE-REGISTRY-001.json") or {}
    records=evidence.get("records",[]) if isinstance(evidence.get("records"),list) else []

    status_counts=Counter(str(r.get("status","UNKNOWN")) for r in records if isinstance(r,dict))
    runtime_counts=Counter(str(r.get("runtime_conformance","UNKNOWN")) for r in records if isinstance(r,dict))
    promotion_counts=Counter(str(r.get("promotion_state","UNKNOWN")) for r in records if isinstance(r,dict))

    expired=[]
    expiring=[]
    bindings=[]
    for rec in records:
        if not isinstance(rec,dict):
            continue
        exp=_parse_time(rec.get("expires_at"))
        if exp is not None:
            if exp <= now:
                expired.append(rec.get("subject_id"))
            elif (exp-now).total_seconds() <= 7*24*3600:
                expiring.append(rec.get("subject_id"))
        for rel in rec.get("evidence_artifacts",[]) or []:
            if isinstance(rel,str):
                b=_artifact_binding(root,rel)
                if any(k in b for k in ("source_commit","run_id","expires_at","host_id")):
                    b["subject_id"]=rec.get("subject_id")
                    bindings.append(b)

    acceptance_state="UNKNOWN_OR_PENDING"
    if acceptance is not None:
        acceptance_state=str(acceptance.get("result") or acceptance.get("status") or "UNKNOWN_OR_PENDING")
    promotion_state="UNKNOWN_OR_PENDING"
    if promotion is not None:
        promotion_state=str(promotion.get("state") or promotion.get("status") or promotion.get("result") or "UNKNOWN_OR_PENDING")

    current_host_pass=sum(1 for r in records if isinstance(r,dict) and str(r.get("status","")).upper() in {"PASS","CURRENT_HOST_PASS","CURRENT_HOST_ADMITTED"})
    current_host_pending=sum(1 for r in records if isinstance(r,dict) and "PENDING_CURRENT_HOST" in str(r.get("status","")).upper())

    return {
        "schema":"fa3.governance-status-projection.v1",
        "id":STATUS_ID,
        "generated_at":now.isoformat(),
        "non_authoritative":True,
        "source_of_truth":False,
        "repository":{
            "head_commit":_git_head(root),
            "release":baseline.release,
            "capability_count":baseline.capability_count,
        },
        "gates":{
            "registry_id":gate_registry.get("id"),
            "mandatory_reference_gate_count":len(gate_registry.get("mandatory_reference_gates",[]) or []),
        },
        "evidence":{
            "registry_status":evidence.get("status","UNKNOWN"),
            "record_count":len(records),
            "status_counts":dict(sorted(status_counts.items())),
            "runtime_conformance_counts":dict(sorted(runtime_counts.items())),
            "promotion_state_counts":dict(sorted(promotion_counts.items())),
            "current_host_explicit_pass_or_admitted_count":current_host_pass,
            "pending_current_host_count":current_host_pending,
            "expired_subjects":[x for x in expired if x],
            "expiring_within_7d_subjects":[x for x in expiring if x],
            "artifact_bindings":bindings,
        },
        "acceptance":{
            "path":"acceptance/acceptance-report.json",
            "present":acceptance is not None,
            "state":acceptance_state,
            "inferred":False,
        },
        "promotion":{
            "path":"promotion/runtime-status.json",
            "present":promotion is not None,
            "state":promotion_state,
            "inferred":False,
        },
        "invariants":{
            "missing_acceptance_is_not_pass":acceptance is not None or acceptance_state=="UNKNOWN_OR_PENDING",
            "missing_promotion_is_not_pass":promotion is not None or promotion_state=="UNKNOWN_OR_PENDING",
            "reference_or_documentation_does_not_imply_current_host_pass":True,
            "status_projection_may_not_promote":True,
        },
        "current_host_runtime_promotion_claim":False,
    }


def gate(root: Path) -> dict[str, Any]:
    root=Path(root).resolve()
    p=project(root)
    findings=[]
    baseline=load_active_release_baseline(root)
    if p["repository"]["capability_count"] != baseline.capability_count:
        findings.append({"code":"GSTAT-001","message":"capability baseline drift"})
    if p["gates"]["registry_id"] != "FA3-GATE-REGISTRY-001":
        findings.append({"code":"GSTAT-002","message":"canonical gate registry unavailable"})
    if p["evidence"]["record_count"] != baseline.capability_count:
        findings.append({"code":"GSTAT-003","message":"evidence registry cardinality differs from active capability baseline"})
    if not p["acceptance"]["present"] and p["acceptance"]["state"] != "UNKNOWN_OR_PENDING":
        findings.append({"code":"GSTAT-004","message":"missing acceptance output was inferred as a state"})
    if not p["promotion"]["present"] and p["promotion"]["state"] != "UNKNOWN_OR_PENDING":
        findings.append({"code":"GSTAT-005","message":"missing promotion output was inferred as a state"})
    if p.get("current_host_runtime_promotion_claim") is not False:
        findings.append({"code":"GSTAT-006","message":"status projection claimed runtime promotion"})
    return {
        "schema":"fa3.governance-status-gate-report.v1",
        "gate_id":STATUS_GATE_ID,
        "result":"PASS" if not findings else "FAIL",
        "projection":p,
        "findings":findings,
        "current_host_runtime_promotion_claim":False,
    }
