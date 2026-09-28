#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "intent": ROOT / "canonical/intents/FA3-STRATA-TIERED-MOE-APPLICATION-INTENT-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-STRATA-001.json",
    "contracts": ROOT / "canonical/contracts/FA3-TIERED-MOE-EXECUTION-CONTRACTS-001.json",
    "assessment": ROOT / "canonical/assessments/FA3-STRATA-REUSE-ASSESSMENT-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-STRATA-TIERED-MOE-2026-09-28.json",
    "decision_assessment": ROOT / "canonical/assessments/FA3-STRATA-TIERED-MOE-DECISION-ASSESSMENT-2026-09-28.json",
    "distribution_registry": ROOT / "canonical/distribution-registry.json",
    "distribution_manifest": ROOT / "canonical/distribution-manifest.json",
    "planner": ROOT / "src/fa3_tiered_moe_plan.py",
    "provider_adapter": ROOT / "src/fa3_strata_provider_adapter.py",
}

PIN = "b742ff998704638903461a2d7d6c1e03b8032509"
ROUTER = "FA3-AUTH-MODEL-ROUTER-001"
HRB = "FA3-AUTH-HOST-RESOURCE-BROKER-001"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check() -> None:
    missing = [str(p.relative_to(ROOT)) for p in FILES.values() if not p.is_file()]
    assert not missing, f"missing files: {missing}"

    intent, provider, contracts, assessment, decision, decision_assessment, distribution_registry, distribution_manifest = [
        load(FILES[k]) for k in ("intent", "provider", "contracts", "assessment", "decision", "decision_assessment", "distribution_registry", "distribution_manifest")
    ]

    assert provider["id"] == "FA3-PROVIDER-STRATA-001"
    assert provider["upstream_snapshot_commit"] == PIN
    assert provider["capability_count"] == 175
    assert provider["new_capability"] is False
    assert provider["new_architectural_authority"] is False
    assert provider["authority_boundaries"]["model_routing"] == ROUTER
    assert provider["authority_boundaries"]["host_resource_admission_placement"] == HRB
    assert provider["provider_constraints"]["application_direct_endpoint_use"] == "FORBIDDEN"
    assert provider["provider_constraints"]["canonical_fixed_model"] == "FORBIDDEN"
    assert provider["provider_constraints"]["silent_provider_or_model_fallback"] == "FORBIDDEN"
    assert provider["reuse_license"]["source_copy_into_fa3"] == "FORBIDDEN"
    assert provider["current_host_production_evidence"] == "NOT_CLAIMED"
    assert provider["global_promotion_claim"] is False
    assert provider["current_host_probe"]["mode"] == "READ_ONLY_LOOPBACK_API_CONFORMANCE"
    assert provider["current_host_probe"]["fixed_default_port"] is False
    assert provider["current_host_probe"]["network_egress"] is False
    assert provider["current_host_probe"]["static_or_probe_pass_promotes_runtime"] is False
    assert provider["distribution"]["class"] == "REFERENCE_ONLY"
    assert provider["distribution"]["release_bundle_status"] == "EXCLUDED"
    assert provider["product_bundle_allowed"] is False

    assert intent["constraints"]["capability_count"] == 175
    assert intent["constraints"]["capability_delta"] == 0
    assert intent["constraints"]["authority_delta"] == 0
    assert intent["upstream_reference"]["commit"] == PIN
    assert intent["upstream_reference"]["direct_source_reuse"].startswith("FORBIDDEN")

    assert contracts["provider_neutral"] is True
    assert contracts["new_capabilities"] == 0
    assert contracts["new_architectural_authorities"] == 0
    assert contracts["authorities"]["model_router"] == ROUTER
    assert contracts["authorities"]["host_resource_broker"] == HRB
    inv = set(contracts["invariants"])
    assert "CPU_ONLY_EXECUTION_REMAINS_VALID_FOR_THE_GLOBAL_FA3_BASELINE" in inv
    assert "STORAGE_IS_NOT_SILENTLY_TREATED_AS_EXECUTABLE_EXPERT_MEMORY" in inv
    assert "NO_SILENT_LOCAL_TO_CLOUD_OR_PROVIDER_FALLBACK" in inv

    assert assessment["source_reuse"]["upstream_original_code_copied"] is False
    assert assessment["hardware_audit"]["global_vendor_neutral"] is True
    assert assessment["hardware_audit"]["global_cpu_only_viable"] is True
    assert assessment["hardware_audit"]["global_accelerator_cardinality"] == "0..N"
    assert assessment["current_host_runtime_promotion_claim"] is False

    assert decision["capability_count_before"] == 175
    assert decision["capability_count_after"] == 175
    assert decision["capability_delta"] == 0
    assert decision["authority_delta"] == 0
    assert decision["runtime_promotion"] == "PENDING_CURRENT_HOST_EVIDENCE"

    assert decision_assessment["assessment"] == "NOT_APPLICABLE"
    assert decision_assessment["project_radar_checked"] is True
    assert decision_assessment["security_boundary"]["may_admit_provider"] is False

    reg = [x for x in distribution_registry["records"] if x.get("subject_id") == "FA3-PROVIDER-STRATA-001"]
    assert reg == [{"subject_id": "FA3-PROVIDER-STRATA-001", "class": "REFERENCE_ONLY", "release_bundle_status": "EXCLUDED"}]
    manifest = [x for x in distribution_manifest["excluded"] if x.get("subject_id") == "FA3-PROVIDER-STRATA-001"]
    assert manifest == reg

    adapter_text = FILES["provider_adapter"].read_text(encoding="utf-8")
    assert "NO_UPSTREAM_STRATA_SOURCE_COPIED" in adapter_text
    assert "LOOPBACK_HOSTS" in adapter_text
    assert "current_host_runtime_promotion_claim" in adapter_text

    planner_text = FILES["planner"].read_text(encoding="utf-8")
    assert "NO_UPSTREAM_STRATA_SOURCE_COPIED" in planner_text
    assert "HRB admission" in planner_text


if __name__ == "__main__":
    check()
    print("FA3 Strata tiered-MoE static gate: PASS")
