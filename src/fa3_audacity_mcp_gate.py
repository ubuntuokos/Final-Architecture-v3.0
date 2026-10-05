#!/usr/bin/env python3
"""Fail-closed P0 governance gate for CAP-124 Audacity MCP materialization."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fa3_release_baseline import load_active_release_baseline

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
GATESET_ID = "FA3-AUDACITY-MCP-GATESET-001"
EXECUTABLE_GATE_ID = "FA3-GATE-AUDACITY-MCP-001"
DECISION_ID = "FA3-DEC-AUDACITY-MCP-2026-09-28"

FILES = {
    "audacity": "canonical/providers/FA3-PROVIDER-AUDACITY-001.json",
    "mcp": "canonical/providers/FA3-PROVIDER-AUDACITY-MCP-001.json",
    "dsp": "canonical/providers/FA3-PROVIDER-AUDACITY-DSP-REFERENCE-001.json",
    "contract": "canonical/contracts/FA3-AUDACITY-MCP-CONTRACTS-001.json",
    "decision": "canonical/decisions/FA3-DEC-AUDACITY-MCP-2026-09-28.json",
    "gate_record": "canonical/FA3-GATE-AUDACITY-MCP-001.json",
    "gate_registry": "canonical/FA3-GATE-REGISTRY-001.json",
    "policy": "canonical/enforcement-policy.json",
    "evidence": "evidence/evidence-registry.json",
}

def load(root: Path, key: str) -> dict:
    return json.loads((root / FILES[key]).read_text(encoding="utf-8"))

def check(ok: bool, code: str, message: str) -> dict:
    return {"code": code, "result": "PASS" if ok else "FAIL", "message": message}

def gate(root: Path) -> dict:
    root = root.resolve()
    missing = [rel for rel in FILES.values() if not (root / rel).is_file()]
    if missing:
        return {
            "schema": "fa3.audacity-mcp-gate-report.v1",
            "gate_id": GATESET_ID,
            "executable_gate_id": EXECUTABLE_GATE_ID,
            "result": "FAIL",
            "findings": [{"code": "AUD-MCP-000", "message": "required files missing", "paths": missing}],
            "runtime_promotion_claim": False,
        }

    a, m, d, c, dec, grec, greg, pol, ev = (
        load(root, k)
        for k in (
            "audacity", "mcp", "dsp", "contract", "decision",
            "gate_record", "gate_registry", "policy", "evidence"
        )
    )
    inv = set(c["invariants"])
    baseline = load_active_release_baseline(root)
    capability_count = baseline.capability_count
    cap124 = next((x for x in ev.get("records", []) if x.get("subject_id") == "CAP-124"), {})
    provider_ids = [
        "FA3-PROVIDER-AUDACITY-001",
        "FA3-PROVIDER-AUDACITY-MCP-001",
        "FA3-PROVIDER-AUDACITY-DSP-REFERENCE-001",
    ]

    checks = [
        check(
            c["capability_id"] == "CAP-124" and c["capability_count"] == capability_count,
            "AUD-MCP-001",
            "CAP-124 / active release baseline preserved",
        ),
        check(c["new_capabilities"] == 0 and c["new_architectural_authorities"] == 0 and dec["capability_delta"] == 0 and dec["architectural_authority_delta"] == 0, "AUD-MCP-002", "zero capability/authority delta"),
        check(m["authority_boundaries"]["mcp"] == "FA3-AUTH-MCP-GATEWAY-001" and m["fa3_adapter_policy"]["direct_agent_to_provider_production_path"] == "DENY", "AUD-MCP-003", "Central MCP Gateway cannot be bypassed"),
        check(m["fa3_adapter_policy"]["upstream_installer_execution_in_fa3_managed_mode"] == "FORBIDDEN" and m["fa3_adapter_policy"]["host_config_mutation"] == "DENY", "AUD-MCP-004", "upstream installer/config mutation blocked"),
        check(m["software_coexistence"]["requires_upstream_uninstall"] is False and m["software_coexistence"]["global_environment_mutation"] is False and m["software_coexistence"]["claims_default_port"] is False, "AUD-MCP-005", "CAP-175 coexistence boundary"),
        check(m["runtime_activation"]["audacity_4"] == "NOT_ADMITTED_BY_THIS_PROVIDER" and m["fa3_adapter_policy"]["unsupported_interface_behavior"] == "FAIL_CLOSED_NO_GUI_CLICK_FALLBACK", "AUD-MCP-006", "unsupported Audacity interfaces fail closed"),
        check(m["mutation_policy"]["source_overwrite_default"] == "DENY" and m["mutation_policy"]["destructive_operation_checkpoint_required"] is True, "AUD-MCP-007", "non-destructive mutation defaults"),
        check(m["mutation_policy"]["recording_or_microphone_activation"] == "AUTHENTICATED_APPROVAL_REQUIRED" and m["mutation_policy"]["delete_or_irreversible_mutation"] == "AUTHENTICATED_APPROVAL_REQUIRED", "AUD-MCP-008", "sensitive mutations require approval"),
        check(c["hardware_audit"]["cpu_only_required"] is True and c["hardware_audit"]["accelerator_cardinality"] == "0..N" and c["hardware_audit"]["fixed_cpu_gpu_npu_numa_values"] == "FORBIDDEN", "AUD-MCP-009", "vendor-neutral Hardware Audit semantics"),
        check(d["execution_policy"]["model_router_required"] == "WHEN_OPERATION_USES_A_ROUTED_AI_MODEL" and d["execution_policy"]["deterministic_non_model_dsp_may_execute_without_model_router"] is True, "AUD-MCP-010", "Model Router used only for routed-model execution"),
        check(a["native_artifact_policy"]["preserve_native_project"] is True and a["native_artifact_policy"]["project_format"] == ".aup3", "AUD-MCP-011", "native project preservation"),
        check("FA3 managed integration SHALL NOT execute upstream installers that modify Audacity or third-party client configuration." in inv, "AUD-MCP-012", "non-interference invariant is normative"),
        check(dec["final_disposition"]["audacity_4_companion_fork"] == "NOT_BASELINE_ADMITTED", "AUD-MCP-013", "Audacity 4 companion fork is not baseline-admitted"),
        check(dec["final_disposition"]["openvino"] == "EXISTING_OPTIONAL_INFERENCE_PROVIDER_REMAINS_SEPARATE_NOT_AUDACITY_AUTHORITY", "AUD-MCP-014", "OpenVINO remains optional and non-authoritative"),
        check(
            grec.get("id") == EXECUTABLE_GATE_ID
            and grec.get("enforcement_id") == GATESET_ID
            and grec.get("priority") == "P0"
            and grec.get("fail_closed") is True
            and grec.get("static_pass_promotes_runtime") is False,
            "AUD-MCP-015",
            "canonical executable P0 gate record",
        ),
        check(
            GATESET_ID in greg.get("mandatory_reference_gates", [])
            and greg.get("mandatory_reference_gates") == pol.get("mandatory_reference_gates"),
            "AUD-MCP-016",
            "mandatory Gate Registry / enforcement-policy mirror binding",
        ),
        check(
            pol.get("audacity_mcp_gate_id") == GATESET_ID
            and pol.get("audacity_mcp_capability_id") == "CAP-124"
            and pol.get("audacity_mcp_provider_ids") == provider_ids
            and pol.get("audacity_mcp_current_host_runtime_promotion_claim") is False,
            "AUD-MCP-017",
            "global enforcement policy Audacity binding",
        ),
        check(
            cap124.get("status") == "PENDING_CURRENT_HOST"
            and DECISION_ID in cap124.get("source_decision_ids", [])
            and ev.get("audacity_mcp_reconciliation", {}).get("gate_id") == GATESET_ID
            and ev.get("audacity_mcp_reconciliation", {}).get("current_host_runtime_promotion_claim") is False,
            "AUD-MCP-018",
            "Evidence Registry decision binding without runtime overclaim",
        ),
    ]
    result = "PASS" if all(x["result"] == "PASS" for x in checks) else "FAIL"
    return {
        "schema": "fa3.audacity-mcp-gate-report.v1",
        "gate_id": GATESET_ID,
        "executable_gate_id": EXECUTABLE_GATE_ID,
        "result": result,
        "capability_id": "CAP-124",
        "active_release": baseline.release,
        "active_release_capability_count": capability_count,
        "checks": checks,
        "findings": [x for x in checks if x["result"] == "FAIL"],
        "runtime_promotion_claim": False,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(ROOT_DEFAULT))
    args = p.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
