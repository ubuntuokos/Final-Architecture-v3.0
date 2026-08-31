#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CAPABILITY_COUNT = 143
BLOCKED = 2
INPUT_ERROR = 3
MANIFEST_REL = Path("fa3-current-host/manifest.json")
PROJECTION_REL = Path("canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json")


def loadj(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def finding(code: str, message: str, **extra):
    return {"code": code, "severity": "P0", "message": message, **extra}


def _capability_ids_from_matrix(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [row.get("capability_id") for row in rows]


def verify_projection(root: Path):
    root = Path(root).resolve()
    findings = []

    try:
        manifest = loadj(root / MANIFEST_REL)
    except Exception as exc:
        return {
            "schema": "fa3.current-host-projection-verification.v1",
            "result": "FAIL",
            "blocking_findings": 1,
            "findings": [finding("FA3-CH-001", "Current-host manifest unavailable", error=str(exc))],
        }

    if (
        manifest.get("schema") != "fa3.current-host-projection.v1"
        or manifest.get("id") != "FA3-CURRENT-HOST-PROJECTION-001"
        or manifest.get("status") != "IMPLEMENTATION_PROJECTION"
    ):
        findings.append(finding("FA3-CH-002", "Projection identity/schema/status mismatch"))

    if (
        manifest.get("capability_count") != CAPABILITY_COUNT
        or manifest.get("new_capabilities") != 0
        or manifest.get("new_architectural_authorities") != 0
        or manifest.get("architectural_authority") is not False
        or manifest.get("authority") != "NONE"
    ):
        findings.append(finding("FA3-CH-003", "Capability/authority invariant mismatch"))

    if (
        manifest.get("fail_closed") is not True
        or manifest.get("document_only_promotion_forbidden") is not True
        or manifest.get("automatic_promotion") is not False
        or manifest.get("promotion", {}).get("explicit_only") is not True
        or manifest.get("promotion", {}).get("global_promotion_claim_from_collection") is not False
    ):
        findings.append(finding("FA3-CH-004", "Fail-closed promotion semantics weakened"))

    required = manifest.get("required_repository_paths", [])
    missing = [rel for rel in required if not (root / rel).is_file()]
    if missing:
        findings.append(finding("FA3-CH-005", "Required current-host repository paths missing", paths=missing))

    try:
        policy = loadj(root / "canonical/enforcement-policy.json")
        if (
            policy.get("architecture_release") != manifest.get("architecture_release")
            or policy.get("canonical_capability_count") != CAPABILITY_COUNT
            or policy.get("canonical_release_projection") != manifest.get("canonical_release_projection")
            or policy.get("fail_closed") is not True
            or policy.get("document_only_promotion_forbidden") is not True
        ):
            findings.append(finding("FA3-CH-006", "Canonical enforcement policy binding mismatch"))
    except Exception as exc:
        findings.append(finding("FA3-CH-006", "Canonical enforcement policy unavailable", error=str(exc)))

    expected = [f"CAP-{i:03d}" for i in range(1, CAPABILITY_COUNT + 1)]
    try:
        ids = _capability_ids_from_matrix(root / "canonical/conformance-matrix.csv")
        if ids != expected:
            findings.append(
                finding("FA3-CH-007", "Conformance matrix is not exact CAP-001..CAP-143", count=len(ids))
            )
    except Exception as exc:
        findings.append(finding("FA3-CH-007", "Conformance matrix unavailable", error=str(exc)))

    try:
        evidence = loadj(root / "evidence/evidence-registry.json")
        records = evidence.get("records", [])
        record_ids = [r.get("subject_id") for r in records]
        if (
            evidence.get("canonical_capability_count") != CAPABILITY_COUNT
            or len(records) != CAPABILITY_COUNT
            or record_ids != expected
        ):
            findings.append(
                finding("FA3-CH-008", "Evidence Registry is not exact 143 capability set", count=len(records))
            )
    except Exception as exc:
        findings.append(finding("FA3-CH-008", "Evidence Registry unavailable", error=str(exc)))

    for surface in manifest.get("registered_current_host_surfaces", []):
        collector = surface.get("collector")
        if collector and not (root / collector).is_file():
            findings.append(
                finding(
                    "FA3-CH-009",
                    "Registered current-host collector missing",
                    surface=surface.get("name"),
                    collector=collector,
                )
            )

    try:
        projection = loadj(root / PROJECTION_REL)
        projection_paths = {entry.get("path") for entry in projection.get("manifest", [])}
        unbound = [
            rel for rel in required
            if rel != PROJECTION_REL.as_posix() and rel not in projection_paths
        ]
        if unbound:
            findings.append(
                finding("FA3-CH-010", "Current-host release-surface path missing from unified manifest", paths=unbound)
            )
    except Exception as exc:
        findings.append(finding("FA3-CH-010", "Unified release projection unavailable", error=str(exc)))

    result = "PASS" if not findings else "FAIL"
    return {
        "schema": "fa3.current-host-projection-verification.v1",
        "projection_id": manifest.get("id"),
        "architecture_release": manifest.get("architecture_release"),
        "result": result,
        "blocking_findings": len(findings),
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "findings": findings,
    }


def run_gate(root: Path, command: str):
    proc = subprocess.run(
        [str(root / "bin/fa3-enforce"), command],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
    }


def collect(root: Path, out: Path | None):
    check = verify_projection(root)
    if check["result"] != "PASS":
        print(json.dumps(check, indent=2))
        return BLOCKED

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (out or (root / ".fa3-current-host" / "runs" / stamp)).resolve()
    out.mkdir(parents=True, exist_ok=True)

    collector = root / "evidence/collect-current-host.sh"
    proc = subprocess.run([str(collector), str(out)], cwd=root, text=True, capture_output=True, check=False)
    fingerprint_path = out / "host-fingerprint.json"

    status_value = "ERROR"
    fingerprint = {}
    if proc.returncode == 0 and fingerprint_path.is_file():
        try:
            fingerprint = loadj(fingerprint_path)
            if (
                fingerprint.get("schema") == "fa3.host-fingerprint.evidence.v1"
                and fingerprint.get("status") == "COLLECTED_UNVALIDATED"
                and fingerprint.get("signed") is False
                and fingerprint.get("secret_collection") == "PROHIBITED"
            ):
                status_value = "COLLECTED_UNVALIDATED"
        except Exception:
            pass

    receipt = {
        "schema": "fa3.current-host-collection-receipt.v1",
        "status": status_value,
        "pass_claim": False,
        "global_promotion_claim": False,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(out),
        "collector_returncode": proc.returncode,
        "collector_stdout": proc.stdout[-4000:],
        "collector_stderr": proc.stderr[-4000:],
        "fingerprint_status": fingerprint.get("status"),
    }
    writej(out / "collection-receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    return 0 if status_value == "COLLECTED_UNVALIDATED" else BLOCKED


def gate(root: Path):
    verification = verify_projection(root)
    if verification["result"] != "PASS":
        print(json.dumps(verification, indent=2))
        return BLOCKED

    results = [run_gate(root, command) for command in ("static", "runtime", "acceptance")]
    unexpected = [r for r in results if r["returncode"] not in (0, BLOCKED)]
    static_ok = results[0]["returncode"] == 0
    runtime_ok = results[1]["returncode"] == 0
    acceptance_ok = results[2]["returncode"] == 0

    if unexpected:
        status_value = "ERROR"
    elif static_ok and runtime_ok and acceptance_ok:
        status_value = "PASS"
    elif static_ok:
        status_value = "PROMOTION_BLOCKED"
    else:
        status_value = "FAIL"

    report = {
        "schema": "fa3.current-host-global-gate-report.v1",
        "status": status_value,
        "fail_closed": True,
        "global_promotion_allowed": status_value == "PASS",
        "gate_results": results,
    }
    writej(root / ".fa3-current-host" / "reports" / "global-gate-report.json", report)
    print(json.dumps(report, indent=2))
    return 0 if status_value == "PASS" else BLOCKED


def status(root: Path):
    evidence = loadj(root / "evidence/evidence-registry.json")
    records = evidence.get("records", [])
    passed = sum(str(r.get("status", "")).upper() == "PASS" for r in records)
    promotion_path = root / "promotion/runtime-status.json"
    promotion = loadj(promotion_path) if promotion_path.is_file() else {"actual_state": "UNKNOWN"}
    obj = {
        "schema": "fa3.current-host-status.v1",
        "capability_count": CAPABILITY_COUNT,
        "evidence_records": len(records),
        "pass_count": passed,
        "pending_or_fail_count": len(records) - passed,
        "promotion_actual_state": promotion.get("actual_state", "UNKNOWN"),
        "promotion_allowed": promotion.get("promotion_allowed", False),
    }
    print(json.dumps(obj, indent=2))
    return 0


def promote(root: Path):
    proc = subprocess.run([str(root / "bin/fa3-enforce"), "promote"], cwd=root, check=False)
    return proc.returncode


def main():
    parser = argparse.ArgumentParser(description="FA3 unified current-host runtime/evidence projection")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verify")
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--out")
    sub.add_parser("gate")
    sub.add_parser("status")
    sub.add_parser("promote")
    all_parser = sub.add_parser("all")
    all_parser.add_argument("--out")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.command == "verify":
        report = verify_projection(root)
        writej(root / ".fa3-current-host" / "reports" / "projection-verification.json", report)
        print(json.dumps(report, indent=2))
        return 0 if report["result"] == "PASS" else BLOCKED
    if args.command == "collect":
        return collect(root, Path(args.out) if args.out else None)
    if args.command == "gate":
        return gate(root)
    if args.command == "status":
        return status(root)
    if args.command == "promote":
        return promote(root)
    if args.command == "all":
        report = verify_projection(root)
        if report["result"] != "PASS":
            print(json.dumps(report, indent=2))
            return BLOCKED
        rc = collect(root, Path(args.out) if args.out else None)
        if rc != 0:
            return rc
        return gate(root)
    return INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
