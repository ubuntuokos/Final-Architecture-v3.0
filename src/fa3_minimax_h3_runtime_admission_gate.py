#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from fa3_minimax_h3_provider_adapter import PROVIDER_ID, adapter_conformance, admit_local_execution

GATE_ID = "FA3-MINIMAX-H3-RUNTIME-ADMISSION-GATESET-001"
RECEIPT = "evidence/receipts/minimax-h3-current-host.json"
REPORT = "reports/minimax-h3-current-host-gate-report.json"
PRODUCTION_LEVEL = "CURRENT_HOST_REMOTE_E2E_PASS"
INTEGRATION_INDEX_REFERENCE = "FA3-MINIMAX-H3-INTEGRATION-INDEX-REFERENCE-2026-09-12"
INTEGRATION_INDEX_PATH = "canonical/references/FA3-MINIMAX-H3-INTEGRATION-INDEX-REFERENCE-2026-09-12.json"
INTEGRATION_INDEX_COMMIT = "41872e10b49d112c543775ef2341e2006644cb75"
REQUIRED_PASS_KEYS = [
    "service_terms",
    "credential_class",
    "entitlement_discovery",
    "adapter_conformance",
    "real_video_e2e",
    "qc",
    "provenance",
]


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def static_gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    required = {
        "canonical/contracts/FA3-MINIMAX-H3-ADAPTER-CONTRACTS-001.json",
        "canonical/FA3-MINIMAX-H3-RUNTIME-ADMISSION-001.json",
        "canonical/minimax-h3-runtime-admission-enforcement.json",
        "canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json",
        INTEGRATION_INDEX_PATH,
        "src/fa3_minimax_h3_provider_adapter.py",
        "evidence/collect-minimax-h3-current-host.py",
        "bin/fa3-minimax-h3-current-host.sh",
        ".github/workflows/fa3-minimax-h3-current-host.yml",
    }
    for rel in sorted(required):
        if not (root / rel).is_file():
            fail("H3-ADM-001", f"Required runtime-admission artifact missing: {rel}")

    if not findings:
        contract = _load(root / "canonical/contracts/FA3-MINIMAX-H3-ADAPTER-CONTRACTS-001.json")
        runtime = _load(root / "canonical/FA3-MINIMAX-H3-RUNTIME-ADMISSION-001.json")
        enforcement = _load(root / "canonical/minimax-h3-runtime-admission-enforcement.json")
        provider = _load(root / "canonical/providers/FA3-PROVIDER-MINIMAX-H3-001.json")
        integration_index = _load(root / INTEGRATION_INDEX_PATH)
        if contract.get("new_capability") is not False or contract.get("new_architectural_authority") is not False:
            fail("H3-ADM-002", "H3 adapter contract cannot create capability or authority")
        if runtime.get("capability_count") != 143 or enforcement.get("capability_count") != 143:
            fail("H3-ADM-003", "H3 runtime admission changed the 143-capability invariant")
        if runtime.get("runtime_promotion_claim") is not False or enforcement.get("runtime_promotion_claim") is not False:
            fail("H3-ADM-004", "Static materialization must not claim runtime promotion")
        service = provider.get("service_access_policy", {})
        if service.get("fallback_policy", {}).get("credential_class_auto_substitution_forbidden") is not True:
            fail("H3-ADM-005", "Credential-class auto substitution is not fail-closed")
        hosted = service.get("hosted_open_platform", {})
        modes = hosted.get("credential_modes", {})
        if modes.get("payg_api_key", {}).get("interchangeable_with_subscription_key") is not False:
            fail("H3-ADM-006", "PAYG credential must not be interchangeable with Subscription Key")
        if modes.get("token_plan_subscription_key", {}).get("interchangeable_with_payg_api_key") is not False:
            fail("H3-ADM-007", "Subscription Key must not be interchangeable with PAYG")
        if admit_local_execution(None).get("state") != "LOCAL_DENIED_WITHOUT_LICENSE_EVIDENCE":
            fail("H3-ADM-008", "Local H3 execution is not denied without license evidence")
        conf = adapter_conformance()
        if conf.get("result") != "PASS" or conf.get("passed") != conf.get("total"):
            fail("H3-ADM-009", "MiniMax H3 adapter executable conformance failed")

        if provider.get("integration_index_reference") != INTEGRATION_INDEX_REFERENCE:
            fail("H3-ADM-010", "Provider projection is not bound to the pinned H3 integration index reference")
        upstream = integration_index.get("upstream", {})
        if upstream.get("commit") != INTEGRATION_INDEX_COMMIT or integration_index.get("runtime_promotion_claim") is not False:
            fail("H3-ADM-011", "H3 integration index must be immutable-pinned reference-only evidence")

        targets = provider.get("integration_targets", {})
        vllm = targets.get("vllm", {})
        if vllm.get("status") != "RESTRICTED_NOT_END_TO_END_H3_TARGET" or vllm.get("end_to_end_h3_dit_serving") is not False or vllm.get("production_h3_target") is not False:
            fail("H3-ADM-012", "Plain vLLM must not be projected as end-to-end MiniMax H3 DiT serving")
        vllm_omni = targets.get("vllm_omni", {})
        if vllm_omni.get("status") != "DISCOVERED_NOT_ADMITTED" or vllm_omni.get("automatic_promotion") is not False or vllm_omni.get("current_host_e2e_required") is not True:
            fail("H3-ADM-013", "vLLM-Omni must remain discovered-not-admitted until real current-host admission")

        candidates = provider.get("discovered_local_execution_candidates", {})
        for name in ("diffsynth_studio", "lightx2v", "nvidia_sol_attn", "vdn_h3"):
            candidate = candidates.get(name, {})
            if candidate.get("status") != "DISCOVERED_NOT_ADMITTED" or candidate.get("automatic_promotion") is not False:
                fail("H3-ADM-014", f"H3 integration candidate is not fail-closed: {name}")
        if candidates.get("nvidia_sol_attn", {}).get("governing_contract") != "FA3-GPU-KERNEL-RUNTIME-CONTRACTS-001":
            fail("H3-ADM-015", "Sol-Attn must remain governed by the canonical GPU kernel runtime contract")
        if candidates.get("vdn_h3", {}).get("separate_model_artifact_admission_required") is not True:
            fail("H3-ADM-016", "VDN-H3 must require separate model-variant artifact admission")

        barrier = enforcement.get("integration_index_promotion_barrier", {})
        invariant = "H3_INTEGRATION_INDEX_DISCOVERY_MUST_NOT_AUTO_PROMOTE_OR_SILENTLY_SUBSTITUTE_RUNTIME_KERNEL_QUANTIZATION_OR_MODEL_VARIANT"
        if enforcement.get("mandatory_rule_count") != 13 or invariant not in enforcement.get("p0_invariants", []):
            fail("H3-ADM-017", "H3 integration-index P0 promotion barrier is missing")
        if barrier.get("reference_id") != INTEGRATION_INDEX_REFERENCE or barrier.get("discovered_candidate_automatic_promotion_forbidden") is not True or barrier.get("discovered_candidate_silent_substitution_forbidden") is not True:
            fail("H3-ADM-018", "H3 integration-index promotion barrier is not fail-closed")
        if "DISCOVERED_NOT_ADMITTED" not in enforcement.get("pending_states_are_not_pass", []):
            fail("H3-ADM-019", "DISCOVERED_NOT_ADMITTED must be a non-pass runtime state")

    report = {
        "schema": "fa3.minimax-h3-runtime-admission-gate-report.v1",
        "gate_id": GATE_ID,
        "mode": "STATIC_CONFORMANCE",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "runtime_promotion_claim": False,
    }
    _write(root / "reports/minimax-h3-runtime-admission-gate-report.json", report)
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    path = root / RECEIPT
    if not path.is_file():
        receipt: dict[str, Any] = {}
        fail("H3-HOST-001", "MiniMax H3 current-host receipt is missing")
    else:
        try:
            receipt = _load(path)
        except Exception:
            receipt = {}
            fail("H3-HOST-002", "MiniMax H3 current-host receipt is unreadable")

    if receipt:
        if receipt.get("status") != "PASS":
            fail("H3-HOST-003", "Current-host receipt status is not PASS")
        if receipt.get("provider_id") != PROVIDER_ID:
            fail("H3-HOST-004", "Provider identity mismatch")
        if receipt.get("evidence_level") != PRODUCTION_LEVEL:
            fail("H3-HOST-005", "Evidence level is not CURRENT_HOST_REMOTE_E2E_PASS")
        gates = receipt.get("promotion_criteria", {})
        for key in REQUIRED_PASS_KEYS:
            if gates.get(key) != "PASS":
                fail("H3-HOST-006", f"Required promotion criterion is not PASS: {key}")
        if receipt.get("secret_persisted") is not False:
            fail("H3-HOST-007", "Credential secret persistence is not disproven")
        if receipt.get("execution_topology") != "HOSTED_REMOTE_FROM_CURRENT_HOST":
            fail("H3-HOST-008", "Receipt does not prove hosted remote execution from current host")
        artifact = receipt.get("artifact", {})
        artifact_path = Path(str(artifact.get("path", "")))
        if not artifact_path.is_file():
            fail("H3-HOST-009", "Generated video artifact is missing on collecting host")
        elif artifact.get("sha256") != _sha256(artifact_path):
            fail("H3-HOST-010", "Generated video SHA-256 mismatch")
        qc = receipt.get("quality_evidence", {})
        if qc.get("result") != "PASS" or qc.get("video_stream") is not True or qc.get("audio_stream") is not True:
            fail("H3-HOST-011", "H3 AV quality evidence is incomplete")
        prov = receipt.get("provenance", {})
        if prov.get("provider_task_id") != receipt.get("task_id") or not prov.get("request_sha256"):
            fail("H3-HOST-012", "Provider task/request provenance is incomplete")
        if receipt.get("local_h3_execution_claimed") is not False:
            fail("H3-HOST-013", "Hosted E2E receipt must not imply local H3 license admission")

    report = {
        "schema": "fa3.minimax-h3-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "provider_id": PROVIDER_ID,
        "mode": "CURRENT_HOST_REMOTE_E2E",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "evidence_level": receipt.get("evidence_level") if receipt else None,
        "promotion_effect": "PROVIDER_SPECIFIC_REMOTE_E2E_ONLY_LOCAL_H3_AND_GLOBAL_PROMOTION_UNCHANGED",
    }
    _write(root / REPORT, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 MiniMax H3 runtime admission gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--current-host", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = current_host_gate(root) if args.current_host else static_gate(root)
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
