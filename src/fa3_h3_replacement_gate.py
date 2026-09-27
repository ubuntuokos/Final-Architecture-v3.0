#!/usr/bin/env python3
import json
from pathlib import Path

FORBIDDEN_RUNTIME_PATHS = [
    "bin/fa3-minimax-h3-current-host.sh",
    "evidence/collect-minimax-h3-current-host.py",
    "src/fa3_minimax_h3_provider_adapter.py",
    "src/fa3_minimax_h3_runtime_admission_gate.py",
    ".github/workflows/fa3-minimax-h3-current-host.yml",
]

def load(root: Path, rel: str):
    return json.loads((root / rel).read_text(encoding="utf-8"))

def gate(root: Path):
    errors = []
    policy = load(root, "canonical/h3-replacement-enforcement.json")
    profile = load(root, "canonical/profiles/FA3-VIDEO-001.json")
    provider = load(root, "canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
    video = load(root, "canonical/video-enforcement.json")

    if not policy.get("mandatory") or not policy.get("fail_closed"):
        errors.append("replacement policy must be mandatory and fail-closed")
    if policy.get("capability_delta") != 0 or policy.get("authority_delta") != 0:
        errors.append("replacement must not add capability or authority")
    if policy.get("capability_count") != 143:
        errors.append("capability count must remain 143")
    if "FA3-PROVIDER-MINIMAX-H3-001" in profile.get("providers", []):
        errors.append("H3 must not be an active FA3-VIDEO-001 provider")
    if "FA3-PROVIDER-MINIMAX-H3-001" in video.get("provider_ids", []):
        errors.append("H3 must not be an active video enforcement provider")
    if provider.get("status") != "RETIRED_REFERENCE_ONLY":
        errors.append("H3 provider record must be retired reference only")
    if provider.get("activation_mode") != "DISABLED_FORBIDDEN":
        errors.append("H3 activation must be disabled and forbidden")
    if not provider.get("runtime_execution_forbidden"):
        errors.append("H3 runtime execution must be forbidden")
    if not provider.get("provider_selection_forbidden"):
        errors.append("H3 provider selection must be forbidden")

    repl = policy.get("replacement", {})
    chain = repl.get("mandatory_execution_chain", [])
    for required in ("FA3-AUTH-MODEL-ROUTER-001", "FA3-AUTH-HOST-RESOURCE-BROKER-001", "provider_admission"):
        if required not in chain:
            errors.append(f"replacement chain missing {required}")
    if not repl.get("silent_fallback_forbidden"):
        errors.append("silent fallback must be forbidden")

    hw = policy.get("hardware_audit", {})
    if not hw.get("vendor_neutral") or not hw.get("accelerator_neutral"):
        errors.append("hardware policy must be vendor/accelerator neutral")
    if not hw.get("cpu_only_architecture_supported"):
        errors.append("CPU-only architecture must remain supported")
    if hw.get("accelerator_cardinality") != "0..N":
        errors.append("accelerator cardinality must be 0..N")

    for rel in FORBIDDEN_RUNTIME_PATHS:
        if (root / rel).exists():
            errors.append(f"forbidden H3 runtime path still exists: {rel}")

    result = {
        "schema": "fa3.h3-replacement-gate-report.v1",
        "gate_id": "FA3-H3-REPLACEMENT-GATESET-001",
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "capability_count": 143,
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_runtime_claim": False,
        "provider_runtime_promotion_claim": False,
    }
    out = root / "reports/h3-replacement-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

def main():
    root = Path(__file__).resolve().parents[1]
    result = gate(root)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
