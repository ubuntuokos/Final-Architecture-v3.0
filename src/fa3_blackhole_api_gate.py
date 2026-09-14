#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from blackhole_api import BlackholeSubmitRequest, derive_server_policy


GATE_ID = "FA3-BLACKHOLE-REST-CONTROL-PLANE-GATE-001"


def check(root: Path) -> dict:
    required = [
        "src/blackhole_api.py",
        "src/fa3_blackhole_client.py",
        "deployment/containers/blackhole-api.Containerfile",
        "deployment/containers/blackhole-api.requirements.txt",
        "scripts/fa3_blackhole_zerocopy_probe.py",
        "tests/test_blackhole_api.py",
        "tests/test_fa3_blackhole_client.py",
        "canonical/contracts/FA3-BLACKHOLE-REST-CONTROL-PLANE-CONTRACTS-001.json",
        "canonical/decisions/FA3-DEC-BLACKHOLE-REST-CONTROL-DATA-PLANE-2026-09-14.json",
        "evidence/reference/blackhole-rest-control-plane-reference-2026-09-14.json",
    ]
    checks: list[tuple[str, bool, str]] = []
    for rel in required:
        checks.append((f"exists:{rel}", (root / rel).is_file(), rel))

    schema_text = json.dumps(BlackholeSubmitRequest.model_json_schema(), sort_keys=True)
    forbidden_request_fields = (
        "ffmpeg_binary_override",
        "runtime_environment",
        "environment_variables",
        "allowed_sm_architectures",
        "execution_priority",
        "neural_model_path",
        '"owner"',
    )
    for field in forbidden_request_fields:
        checks.append((f"request-forbids:{field}", field not in schema_text, field))

    sample = BlackholeSubmitRequest.model_validate(
        {
            "schema_version": "fa3.blackhole.request.v3",
            "request_id": "00000000-0000-4000-8000-000000000001",
            "lease_id": "ACC-LEASE-REFERENCE-001",
            "requirements": {
                "minimum_tu": 1.5,
                "required_features": ["cuda", "nvenc", "onnxruntime-gpu", "zero-copy"],
            },
            "pipeline": {
                "operation": "neural_media_enhance",
                "model_id": "FA3-MODEL-MEDIA-ENHANCER-V3",
                "input_asset_id": "FA3-ASSET-REFERENCE-001",
                "output_profile": "1080p-h264",
            },
        }
    )
    policy = derive_server_policy(sample)
    checks.extend(
        [
            ("policy:cuda-launch-blocking-off", policy["cuda_launch_blocking"] is False, ""),
            ("policy:ffmpeg-server-controlled", policy["ffmpeg_binary_source"] == "SERVER_CANONICAL_POLICY", ""),
            ("policy:env-server-controlled", policy["environment_source"] == "SERVER_CANONICAL_POLICY", ""),
            ("policy:hrb-worker-placement", policy["worker_gpu_assignment_source"] == "HRB_RUNTIME_LEASE", ""),
            ("policy:durable-queue", policy["dispatch_backend"] == "SQLITE_DURABLE_QUEUE", ""),
            ("policy:zc-scope", policy["zero_copy_claim_scope"] == "FRAME_TO_TENSOR_ONLY", ""),
            ("policy:no-e2e-overclaim", policy["end_to_end_gpu_resident_claim"] is False, ""),
        ]
    )

    container = (root / "deployment/containers/blackhole-api.Containerfile").read_text(encoding="utf-8")
    lower = container.lower()
    checks.extend(
        [
            ("container:no-nvidia-base", "nvcr.io" not in lower and "nvidia/cuda" not in lower, ""),
            ("container:no-ffmpeg", "ffmpeg" not in lower, ""),
            ("container:no-pytorch", "pytorch" not in lower and "torch" not in lower, ""),
            ("container:single-worker", re.search(r'"--workers",\s*"1"', container) is not None, ""),
            ("container:non-root", "USER fa3api:fa3api" in container, ""),
        ]
    )

    client = (root / "src/fa3_blackhole_client.py").read_text(encoding="utf-8")
    checks.extend(
        [
            ("client:no-sys-exit", "sys.exit" not in client, ""),
            ("client:no-utcnow", "utcnow(" not in client, ""),
            ("client:network-timeout", "timeout=self.timeout" in client, ""),
        ]
    )

    reqs = (root / "deployment/containers/blackhole-api.requirements.txt").read_text(encoding="utf-8")
    pinned = [line for line in reqs.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    checks.append(("dependencies:top-level-exact-pins", all("==" in line for line in pinned), ""))

    evidence = json.loads(
        (root / "evidence/reference/blackhole-rest-control-plane-reference-2026-09-14.json").read_text(encoding="utf-8")
    )
    checks.extend(
        [
            (
                "evidence:runtime-pending",
                evidence["runtime_promotion"]["status"] == "PENDING_EXECUTABLE_EVIDENCE",
                "",
            ),
            (
                "evidence:no-e2e-overclaim",
                evidence["claims"]["end_to_end_gpu_resident_claim"] is False,
                "",
            ),
        ]
    )

    failed = [{"check": name, "detail": detail} for name, ok, detail in checks if not ok]
    return {
        "gate_id": GATE_ID,
        "result": "PASS" if not failed else "FAIL",
        "total": len(checks),
        "passed": len(checks) - len(failed),
        "failed": failed,
        "current_host_runtime_claim": False,
        "runtime_zero_copy_status": "PENDING_EXECUTABLE_EVIDENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    report = check(args.root.resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
