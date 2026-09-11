#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_pytorch3d_provider import SOURCE_REVISION, validate_build_candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip()}")
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect real current-host PyTorch3D source-build and GPU E2E evidence")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--venv", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--build-receipt", type=Path, required=True)
    parser.add_argument("--hrb-receipt", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, default=ROOT / "evidence/receipts/pytorch3d-current-host.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.time()
    receipt: dict[str, Any] = {
        "schema": "fa3.pytorch3d-current-host-receipt.v1",
        "provider_id": "FA3-PROVIDER-PYTORCH3D-001",
        "profile_id": "FA3-DIFFERENTIABLE-3D-001",
        "capability_id": "CAP-032",
        "status": "FAIL",
        "production_admitted": False,
        "global_143_capability_promotion": False,
    }
    try:
        source = args.source_dir.resolve()
        python = (args.venv / "bin/python").resolve()
        for path in (source, python, args.wheel, args.sbom, args.provenance, args.build_receipt, args.hrb_receipt):
            if not path.exists():
                raise RuntimeError(f"required path missing: {path}")
        source_revision = run(["git", "rev-parse", "HEAD"], cwd=source).stdout.strip()
        if source_revision != SOURCE_REVISION:
            raise RuntimeError(f"source revision mismatch: {source_revision}")
        if os.environ.get("CONDA_PREFIX"):
            raise RuntimeError("Conda environment is active; isolated pip venv is required")

        build = load_json(args.build_receipt)
        hrb = load_json(args.hrb_receipt)
        if build.get("source_revision") != SOURCE_REVISION:
            raise RuntimeError("build receipt source revision mismatch")
        if build.get("wheel_sha256") != sha256_file(args.wheel):
            raise RuntimeError("wheel SHA-256 does not match build receipt")
        if build.get("sbom_sha256") != sha256_file(args.sbom):
            raise RuntimeError("SBOM SHA-256 does not match build receipt")
        if build.get("provenance_attestation_sha256") != sha256_file(args.provenance):
            raise RuntimeError("provenance SHA-256 does not match build receipt")
        build_admission = validate_build_candidate(build)
        if build_admission["result"] != "PASS":
            raise RuntimeError(f"build candidate admission failed: {build_admission}")
        if not hrb.get("lease_id") or hrb.get("accelerator_role") != "COMPUTE":
            raise RuntimeError("valid HRB compute lease receipt required")
        if not hrb.get("device_uuid") or not hrb.get("pci_bdf"):
            raise RuntimeError("HRB receipt requires UUID and PCI BDF stable identity")

        probe = run([str(python), str(ROOT / "src/fa3_pytorch3d_runtime_probe.py")], cwd=Path("/tmp"))
        probe_report = json.loads(probe.stdout.strip().splitlines()[-1])
        if probe_report.get("result") != "PASS":
            raise RuntimeError("runtime probe did not pass")
        if probe_report.get("accelerator", {}).get("visible_count") != 1:
            raise RuntimeError("runtime probe did not observe exactly one HRB-leased accelerator")

        child_pid = probe_report.get("pid")
        lifecycle = run(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            check=False,
        )
        residual_pids = {line.strip() for line in lifecycle.stdout.splitlines() if line.strip()}
        if str(child_pid) in residual_pids:
            raise RuntimeError("PyTorch3D probe process retained a GPU compute context after exit")

        receipt.update(
            {
                "status": "PASS",
                "production_admitted": True,
                "source_revision": source_revision,
                "wheel_sha256": sha256_file(args.wheel),
                "sbom_sha256": sha256_file(args.sbom),
                "provenance_attestation_sha256": sha256_file(args.provenance),
                "hrb_lease": {
                    "lease_id": hrb["lease_id"],
                    "accelerator_role": hrb["accelerator_role"],
                    "device_uuid": hrb["device_uuid"],
                    "pci_bdf": hrb["pci_bdf"],
                },
                "build_admission": build_admission,
                "runtime_probe": probe_report,
                "lifecycle": {
                    "probe_process_exited": True,
                    "gpu_context_released": True,
                    "rollback_target": "DISABLED_PROVIDER_NO_LONG_LIVED_DAEMON",
                },
            }
        )
    except Exception as exc:
        receipt["error"] = str(exc)
    finally:
        receipt["duration_seconds"] = round(time.time() - started, 3)
        write_json(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
