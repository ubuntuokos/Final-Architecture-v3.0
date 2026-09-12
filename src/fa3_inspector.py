#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

LEVELS = {"L1_STATIC", "L2_RUNTIME", "L3_PRODUCTION"}
NON_PASS = {"FAIL", "BLOCKED", "INCONCLUSIVE", "EVIDENCE_MISSING", "EVIDENCE_STALE", "DRIFT_DETECTED"}

class InspectionInputError(ValueError):
    pass

def classify_inspection(request: dict[str, Any]) -> dict[str, Any]:
    subject = str(request.get("subject_id", "")).strip()
    level = str(request.get("level", "")).strip()
    executor = str(request.get("executor_id", "")).strip()
    inspector = str(request.get("inspector_id", "")).strip()
    if not subject or level not in LEVELS or not executor or not inspector:
        raise InspectionInputError("subject_id, valid level, executor_id and inspector_id are required")

    base = {
        "subject_id": subject,
        "level": level,
        "executor_id": executor,
        "inspector_id": inspector,
        "subject_mutation_allowed": False,
        "silent_repair_allowed": False,
        "promotion_allowed": False,
        "reinspection_required_after_remediation": True,
    }
    def result(status: str, reason: str) -> dict[str, Any]:
        out = dict(base)
        out.update({"status": status, "reason": reason, "promotion_allowed": status == "PASS"})
        return out

    if executor == inspector:
        return result("BLOCKED", "separation-of-duties: executor cannot be sole accepting verifier")
    if bool(request.get("drift_detected", False)):
        return result("DRIFT_DETECTED", "canonical/runtime drift detected")
    if not bool(request.get("evidence_present", False)):
        return result("EVIDENCE_MISSING", "required inspection evidence is missing")
    if not bool(request.get("evidence_fresh", False)):
        return result("EVIDENCE_STALE", "inspection evidence is stale for requested scope")
    if level == "L3_PRODUCTION" and bool(request.get("self_attestation_only", False)):
        return result("BLOCKED", "P0/MUST production PASS cannot rely on self-attestation only")
    if not bool(request.get("canonical_compliant", False)) or not bool(request.get("implementation_verified", False)):
        return result("FAIL", "canonical or implementation verification failed")
    if level in {"L2_RUNTIME", "L3_PRODUCTION"} and not bool(request.get("reproducible", False)):
        return result("INCONCLUSIVE", "runtime/production result is not reproducible")
    if level == "L3_PRODUCTION" and not bool(request.get("runtime_verified", False)):
        return result("INCONCLUSIVE", "production runtime verification is incomplete")
    return result("PASS", "inspection requirements satisfied")

def self_check() -> None:
    blocked = classify_inspection({
        "subject_id": "CAP-P0", "level": "L3_PRODUCTION", "executor_id": "worker-a", "inspector_id": "inspector-b",
        "evidence_present": True, "evidence_fresh": True, "self_attestation_only": True,
        "canonical_compliant": True, "implementation_verified": True, "reproducible": True, "runtime_verified": True,
    })
    if blocked["status"] != "BLOCKED":
        raise RuntimeError("self-attestation-only production case must be BLOCKED")
    passed = classify_inspection({
        "subject_id": "CAP-P0", "level": "L3_PRODUCTION", "executor_id": "worker-a", "inspector_id": "inspector-b",
        "evidence_present": True, "evidence_fresh": True, "self_attestation_only": False,
        "canonical_compliant": True, "implementation_verified": True, "reproducible": True, "runtime_verified": True,
    })
    if passed["status"] != "PASS" or passed["subject_mutation_allowed"] is not False:
        raise RuntimeError("independent compliant production case must PASS without mutation authority")

def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 Inspector reference implementation")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--request-json")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("FA3 Inspector self-check: PASS")
        return 0
    if not args.request_json:
        parser.error("--request-json is required unless --self-check is used")
    print(json.dumps(classify_inspection(json.loads(args.request_json)), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
