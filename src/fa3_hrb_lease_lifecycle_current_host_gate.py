#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

GATE_ID = "FA3-GATE-HRB-LEASE-LIFECYCLE-CURRENT-HOST-001"
RECEIPT = "evidence/receipts/hrb-lease-lifecycle-current-host.json"
EVIDENCE_LEVEL = "CURRENT_HOST_HRB_LEASE_LIFECYCLE_DEDICATED_TTL_EVICTION_PASS"
CAPABILITY_COUNT = module_active_capability_count(__file__)
EXPECTED_STATES = ["ISSUED", "ACTIVE", "REVOKING", "EVICTING", "VERIFYING", "EVICTED"]


def validate_receipt(receipt: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def fail(code: str, message: str) -> None:
        findings.append({"code": code, "severity": "P0", "message": message})

    if (
        receipt.get("schema") != "fa3.hrb-lease-lifecycle-current-host-receipt.v1"
        or receipt.get("status") != "PASS"
        or receipt.get("evidence_level") != EVIDENCE_LEVEL
    ):
        fail("HRB-LEASE-HOST-001", "receipt identity/status/evidence level mismatch")

    if not (
        receipt.get("resource_authority_id") == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        and receipt.get("secret_authority_id") == "FA3-AUTH-SECRETS-001"
        and receipt.get("durable_evidence_authority_id") == "FA3-AUTH-OBS-EVIDENCE-001"
        and receipt.get("trust_profile_id") == "FA3-TRUST-PKI-001"
    ):
        fail("HRB-LEASE-HOST-002", "authority boundary mismatch")

    workload = receipt.get("workload", {})
    name = str(workload.get("name", ""))
    unit = str(workload.get("unit_scope", ""))
    if not (
        re.fullmatch(r"fa3-hrb-ttl-test-[0-9a-f]{12}", name)
        and unit == name + ".scope"
        and workload.get("dedicated") is True
        and workload.get("existing_fa3_workload_targeted") is False
        and workload.get("cpu_only") is True
        and workload.get("accelerator_assignments") == []
    ):
        fail("HRB-LEASE-HOST-003", "dedicated harmless TTL workload boundary invalid")

    crypto = receipt.get("crypto", {})
    if not (
        crypto.get("algorithm") == "HMAC-SHA256"
        and crypto.get("scope") == "HRB_INTERNAL_EPHEMERAL_LEASE_AUTH"
        and crypto.get("test_only_ephemeral_key") is True
        and crypto.get("production_hmac_master_key_read") is False
        and crypto.get("provider_agent_master_key_access") is False
        and crypto.get("hmac_used_for_durable_evidence_signature") is False
        and isinstance(crypto.get("key_id"), str)
        and crypto.get("key_id", "").startswith("current-host-test-")
    ):
        fail("HRB-LEASE-HOST-004", "cryptographic lease boundary invalid")

    binding = receipt.get("runtime_binding", {})
    required = {
        "lease_id", "generation", "workload_identity", "runtime_instance_identity",
        "host_attestation_digest", "cgroup_v2_identity", "pidfd_subject_reference",
        "systemd_unit_scope", "runtime_backend", "backend_instance_id",
        "accelerator_assignments", "execution_path", "issued_at_utc", "expires_at_utc", "ttl_seconds",
    }
    if not isinstance(binding, dict) or not required.issubset(binding):
        fail("HRB-LEASE-HOST-005", "trusted runtime binding incomplete")
    elif not (
        binding.get("workload_identity") == name
        and binding.get("systemd_unit_scope") == unit
        and binding.get("runtime_backend") == "SYSTEMD_CGROUPV2_SCOPE"
        and binding.get("backend_instance_id") == unit
        and binding.get("accelerator_assignments") == []
    ):
        fail("HRB-LEASE-HOST-006", "runtime binding is not bound to the dedicated scope")

    runtime = receipt.get("runtime", {})
    if not (
        runtime.get("systemd_user_transient_scope") is True
        and runtime.get("cgroup_v2") is True
        and runtime.get("pidfd") is True
        and runtime.get("group_kill_method") in {"CGROUP_V2_CGROUP_KILL", "SYSTEMD_KILL_ALL_CGROUP_SCOPE"}
        and runtime.get("final_state") == "EVICTED"
        and runtime.get("state_history") == EXPECTED_STATES
        and runtime.get("lease_record_deleted") is False
        and runtime.get("cleanup_verified") is True
        and runtime.get("gpu_global_reset_used") is False
        and runtime.get("cuda_device_reset_used") is False
    ):
        fail("HRB-LEASE-HOST-007", "physical eviction/death verification lifecycle incomplete")

    secret = receipt.get("secret_projection", {})
    if not (
        secret.get("test_projection_only") is True
        and secret.get("live_secret_broker_store_touched") is False
        and secret.get("zeroized") is True
        and secret.get("revoked") is True
    ):
        fail("HRB-LEASE-HOST-008", "test Secret Broker projection lifecycle incomplete")

    ev = receipt.get("evidence_handoff", {})
    if not (
        ev.get("typed_hash_chain_valid") is True
        and isinstance(ev.get("event_count"), int) and ev.get("event_count") >= 1
        and re.fullmatch(r"[0-9a-f]{64}", str(ev.get("final_event_sha256", "")))
        and ev.get("external_asymmetric_signature_required") is True
        and ev.get("durable_signing_authority") == "FA3-AUTH-OBS-EVIDENCE-001"
        and ev.get("trust_profile") == "FA3-TRUST-PKI-001"
    ):
        fail("HRB-LEASE-HOST-009", "typed evidence handoff invalid")

    safety = receipt.get("safety", {})
    if not (
        safety.get("target_derivation_from_client_identity") is False
        and safety.get("target_derivation_from_generated_container_name") is False
        and safety.get("test_prefix_enforced") is True
        and safety.get("preexisting_workload_kill_allowed") is False
        and safety.get("container_id_used") is False
    ):
        fail("HRB-LEASE-HOST-010", "current-host TTL safety boundary invalid")

    if not (
        receipt.get("capability_count_after") == CAPABILITY_COUNT
        and receipt.get("new_capabilities") == 0
        and receipt.get("new_architectural_authorities") == 0
        and receipt.get("global_promotion_claim") is False
    ):
        fail("HRB-LEASE-HOST-011", "capability/authority/global-promotion drift")

    return findings


def gate(root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (root / RECEIPT)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        findings = validate_receipt(receipt)
    except Exception as exc:
        receipt = {}
        findings = [{
            "code": "HRB-LEASE-HOST-000",
            "severity": "P0",
            "message": "current-host HRB lease lifecycle receipt missing or unreadable",
            "error": repr(exc),
        }]
    report = {
        "schema": "fa3.hrb-lease-lifecycle-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "evidence_level": receipt.get("evidence_level"),
        "promotion_effect": "ADDITIVE_HRB_COMPONENT_CURRENT_HOST_EVIDENCE_ONLY_GLOBAL_PROMOTION_UNCHANGED",
        "capability_count": CAPABILITY_COUNT,
    }
    out = root / "reports/hrb-lease-lifecycle-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = Path(args.receipt).resolve() if args.receipt else None
    result = gate(root, receipt)
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
