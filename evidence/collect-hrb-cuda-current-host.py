#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_HOST = "horvath-precisiontower7910"
EVIDENCE_LEVEL = "SCOPED_CURRENT_HOST_HRB_V1_0_AUTHENTICATED_CUDA_V1_2_PRODUCTION_E2E_PASS"
SOURCES = {
    "HRB-CONFORMANCE": (
        "/var/lib/fa3/evidence/host-resource-broker/conformance-20260827T233036Z.json",
        "4249bde6a6312f5264d308ec222c72e9847fdf90dcf04be5392ab555d6ddf3f4",
    ),
    "CUDA-BROKER-REGRESSION": (
        "/var/lib/fa3/evidence/cuda-python/broker-regression-20260827T233617Z.json",
        "b94a1c083f8bd0f25fae358a8be84515a6c04e1f8a6f03152af4bef399ad4f5b",
    ),
    "CUDA-AUTH-E2E": (
        "/var/lib/fa3/evidence/cuda-python/e2e-20260827T233721Z.json",
        "c98a44673507f52d1c92dfff91e673fc84bb8963fef87c34c5cdc9105688f57c",
    ),
    "HRB-CUDA-EVIDENCE-INTEGRATION-GATE": (
        "/var/lib/fa3/evidence/integration/hrb-cuda/gate-20260827T234213Z.json",
        "5d42396b229cea0a371289a09f7a856955c961894666fadcb5aeb9457325cfee",
    ),
}
REGISTRY = {
    "HRB-CONFORMANCE": (
        "/var/lib/fa3/evidence-registry/current-host/HRB-CONFORMANCE.json",
        "FA3-HOST-RESOURCE-BROKER-001",
        "1.0.0",
    ),
    "CUDA-BROKER-REGRESSION": (
        "/var/lib/fa3/evidence-registry/current-host/CUDA-BROKER-REGRESSION.json",
        "FA3-CUDA-PY-001",
        "1.2.0",
    ),
    "CUDA-AUTH-E2E": (
        "/var/lib/fa3/evidence-registry/current-host/CUDA-AUTH-E2E.json",
        "FA3-CUDA-PY-001",
        "1.2.0",
    ),
}


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(source_root: Path, absolute: str) -> Path:
    return source_root / absolute.lstrip("/")


def collect(root: Path, source_root: Path) -> dict[str, Any]:
    host = os.uname().nodename
    if host != EXPECTED_HOST:
        raise RuntimeError(f"current-host mismatch: expected {EXPECTED_HOST}, got {host}")

    artifacts: list[dict[str, Any]] = []
    for evidence_id, (absolute, expected_digest) in SOURCES.items():
        path = _resolve(source_root, absolute)
        _json(path)
        actual_digest = _sha256(path)
        if actual_digest != expected_digest:
            raise RuntimeError(f"{evidence_id} sha256 mismatch: {actual_digest}")
        artifacts.append({
            "id": evidence_id,
            "path": absolute,
            "sha256": actual_digest,
            "status": "PASS",
            "byte_reverified": True,
        })

    registry_records: list[dict[str, Any]] = []
    for evidence_id, (absolute, expected_profile, expected_version) in REGISTRY.items():
        path = _resolve(source_root, absolute)
        record = _json(path)
        source_digest = dict((item["id"], item["sha256"]) for item in artifacts)[evidence_id]
        if not (
            record.get("id") == evidence_id
            and record.get("host") == EXPECTED_HOST
            and record.get("status") == "PASS"
            and record.get("profile") == expected_profile
            and record.get("version") == expected_version
            and record.get("sha256") == source_digest
        ):
            raise RuntimeError(f"{evidence_id} Evidence Registry record mismatch")
        registry_records.append({
            "id": evidence_id,
            "path": absolute,
            "host": record["host"],
            "status": record["status"],
            "profile": record["profile"],
            "version": record["version"],
            "sha256": record["sha256"],
        })

    receipt = {
        "schema": "fa3.hrb-cuda-current-host-receipt.v1",
        "status": "PASS",
        "evidence_level": EVIDENCE_LEVEL,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "live_source_reverified": True,
        "scope": {
            "hrb_implementation_version": "1.0.0",
            "cuda_python_version": "1.2.0",
            "canonical_hrb_profile_version": "1.4.0",
            "hrb_v1_4_full_runtime_claim": False,
            "cuda_component_promotion_eligible": True,
            "global_promotion_claim": False,
        },
        "artifacts": artifacts,
        "external_registry_records": registry_records,
        "authority_boundary": {
            "hrb": "ADMISSION_PLACEMENT_RESERVATION_LEASE_AUTHORITY",
            "cuda_python": "EXECUTION_PROVIDER_NOT_AUTHORITY",
        },
        "capability_count_after": 143,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_promotion_claim": False,
    }
    output = root / "evidence/receipts/hrb-cuda-current-host.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehydrate and verify immutable FA3 HRB/CUDA current-host evidence")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--source-root", default="/")
    args = parser.parse_args()
    receipt = collect(Path(args.root).resolve(), Path(args.source_root).resolve())
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
