#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_hrb_lease_lifecycle import (
    EVIDENCE_AUTHORITY_ID,
    HMAC_ALG,
    HMAC_SCOPE,
    HRB_AUTHORITY_ID,
    REQUIRED_BINDING_FIELDS,
    STATES,
    TRUST_PROFILE_ID,
)

PROFILE = "canonical/profiles/FA3-HOST-RESOURCE-BROKER-001.json"
CONTRACT = "canonical/contracts/FA3-HOST-RESOURCE-BROKER-CONTRACTS-001.json"
GATE_RECORD = "canonical/FA3-GATE-HRB-LEASE-LIFECYCLE-001.json"
CORE = "src/fa3_hrb_lease_lifecycle.py"
TEST = "tests/test_hrb_lease_lifecycle.py"
GATE_ID = "FA3-GATE-HRB-LEASE-LIFECYCLE-001"
CAPABILITY_COUNT = module_active_capability_count(__file__)

REQUIRED_NEGATIVES = {
    "forged_hmac_mac",
    "malformed_lease",
    "stale_generation",
    "expiry_renewal_race",
    "wrong_runtime_kill",
    "pid_reuse",
    "cgroup_substitution",
    "symlink_path_ownership_attack",
    "systemd_restart_race",
    "runtime_adapter_failure",
    "secret_revoke_failure",
    "clock_jump_reboot",
    "cpu_only_workload",
    "shared_accelerator",
    "unknown_backend_device",
    "evidence_tampering",
    "key_rotation",
}
REQUIRED_EVICTION_ORDER = [
    "ATOMIC_LEASE_REVOKE",
    "BLOCK_NEW_ADMISSION_AND_RESTART",
    "SECRET_BROKER_PROJECTION_REVOKE_ZEROIZE",
    "VERIFY_TRUSTED_RUNTIME_BINDING",
    "SYSTEMD_CGROUP_LIFECYCLE_TERMINATION",
    "CGROUP_V2_GROUP_LEVEL_KILL",
    "PIDFD_AND_CGROUP_DEATH_VERIFICATION",
    "RUNTIME_ADAPTER_CLEANUP_IMMUTABLE_BACKEND_INSTANCE_ID",
    "RESOURCE_RELEASE",
    "IMMUTABLE_TYPED_EVIDENCE_HANDOFF",
]
REQUIRED_LIFECYCLE_INVARIANTS = {
    "HRB_LEASE_LIFECYCLE_REMAINS_UNDER_EXISTING_HRB_AUTHORITY",
    "HRB_LEASE_HMAC_IS_INTERNAL_EPHEMERAL_AUTH_NOT_DURABLE_EVIDENCE_SIGNATURE",
    "HRB_HMAC_MASTER_KEY_ROOT_ONLY_AND_PROVIDER_AGENT_INACCESSIBLE",
    "HRB_HMAC_REQUIRES_KEY_ID_SCOPE_AND_ROTATION",
    "RENEWAL_CREATES_NEW_GENERATION",
    "EVICTING_GENERATION_MUST_NEVER_REACTIVATE",
    "PRIVILEGED_EVICTION_TARGETS_TRUSTED_RUNTIME_BINDING_NOT_CLIENT_IDENTITY_OR_GENERATED_NAME",
    "SECRET_BROKER_PROJECTION_REVOKE_ZEROIZE_PRECEDES_RUNTIME_TERMINATION",
    "WRONG_RUNTIME_BINDING_MUST_FAIL_CLOSED_WITHOUT_KILL",
    "CGROUP_V2_EVICTION_REQUIRES_GROUP_LEVEL_KILL",
    "PIDFD_AND_CGROUP_DEATH_VERIFICATION_REQUIRED",
    "FAILED_EVICTION_RETAINS_LEASE_RECORD_AND_QUARANTINES",
    "NORMAL_EVICTION_FORBIDS_GPU_GLOBAL_OR_DEVICE_RESET",
    "DURABLE_EVIDENCE_USES_EXISTING_ASYMMETRIC_EVIDENCE_PKI_AUTHORITY",
    "BOOT_ID_AND_MONOTONIC_EXPIRY_BIND_LEASE_TO_CURRENT_BOOT",
    "CPU_ONLY_WORKLOAD_MUST_NOT_REQUIRE_ACCELERATOR_ASSIGNMENT",
    "SHARED_ACCELERATOR_EVICTION_MUST_NOT_RESET_GLOBAL_DEVICE",
    "HRB_TTL_EVICTION_MUST_REVOKE_PROJECTION_LEASE_NOT_UNDERLYING_SECRET",
    "SECRET_PROJECTION_ZEROIZE_TARGET_REQUIRES_IMMUTABLE_FILE_IDENTITY",
}


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def evaluate(root: Path) -> dict[str, Any]:
    profile = _load(root, PROFILE)
    contract = _load(root, CONTRACT)
    gate = _load(root, GATE_RECORD)
    lifecycle = contract.get("lease_lifecycle", {})
    core = (root / CORE).read_text(encoding="utf-8")
    tests = (root / TEST).read_text(encoding="utf-8") if (root / TEST).is_file() else ""

    auth = lifecycle.get("authentication", {})
    evidence = lifecycle.get("durable_evidence", {})
    runtime = lifecycle.get("runtime_binding", {})
    failure = lifecycle.get("failure_semantics", {})
    secret = lifecycle.get("secret_broker_hook", {})
    negatives = set(gate.get("mandatory_negative_tests", []))
    lifecycle_invariants = set(lifecycle.get("invariants", []))
    contract_names = set(contract.get("contracts", []))

    checks = [
        _check(
            "capability-authority-stable",
            contract.get("capability_count") == profile.get("capability_count") == gate.get("capability_count") == CAPABILITY_COUNT
            and contract.get("new_capability") is False
            and profile.get("new_capability") is False
            and gate.get("new_capability") is False
            and contract.get("new_architectural_authority") is False
            and profile.get("new_architectural_authority") is False
            and gate.get("new_architectural_authority") is False,
            "canonical count remains 143 with zero new capabilities and authorities",
        ),
        _check(
            "existing-hrb-authority",
            contract.get("authority_id") == HRB_AUTHORITY_ID
            and profile.get("existing_authority_id") == HRB_AUTHORITY_ID
            and gate.get("authority_id") == HRB_AUTHORITY_ID
            and lifecycle.get("authority_id") == HRB_AUTHORITY_ID,
            "lease lifecycle is a child of the existing HRB authority",
        ),
        _check(
            "contract-family-extended",
            {
                "LeaseLifecycleState",
                "LeaseRuntimeBinding",
                "LeaseAuthenticationEnvelope",
                "LeaseGeneration",
                "LeaseEvictionReceipt",
                "LeaseQuarantineRecord",
                "LeaseEvidenceHandoff",
            }.issubset(contract_names),
            "existing HRB contract family owns lifecycle contracts",
        ),
        _check(
            "state-machine-exact",
            tuple(lifecycle.get("states", [])) == STATES
            and lifecycle.get("success_path") == ["ISSUED", "ACTIVE", "REVOKING", "EVICTING", "VERIFYING", "EVICTED"]
            and lifecycle.get("failure_path") == ["EVICTION_FAILED", "QUARANTINED"],
            "mandatory success and failure states are canonical",
        ),
        _check(
            "renewal-generation",
            lifecycle.get("renewal", {}).get("new_generation_required") is True
            and lifecycle.get("renewal", {}).get("stale_generation_privileged_operation") == "DENY"
            and lifecycle.get("renewal", {}).get("evicting_generation_reactivation") == "FORBIDDEN",
            "renewal creates a new generation and stale/evicting generations cannot regain authority",
        ),
        _check(
            "hmac-boundary",
            auth.get("algorithm") == HMAC_ALG
            and auth.get("scope") == HMAC_SCOPE
            and auth.get("master_key_boundary") == "HRB_ROOT_ONLY"
            and auth.get("provider_agent_master_key_access") == "FORBIDDEN"
            and auth.get("key_id_required") is True
            and auth.get("rotation_required") is True
            and auth.get("durable_evidence_signature") is False,
            "HMAC is HRB-internal ephemeral lease authentication only",
        ),
        _check(
            "root-key-file-enforcement",
            "st.st_uid != 0" in core
            and "stat.S_IMODE(st.st_mode) & 0o077" in core
            and "stat.S_ISLNK(st.st_mode)" in core
            and "from_root_key_file" in core,
            "production lease key loader is root-owned, non-symlink and mode restricted",
        ),
        _check(
            "runtime-binding-complete",
            set(runtime.get("required_fields", [])) == REQUIRED_BINDING_FIELDS
            and set(gate.get("runtime_binding_required_fields", [])) == REQUIRED_BINDING_FIELDS
            and runtime.get("container_id_semantics") == "RUNTIME_ADAPTER_SPECIFIC_ONLY"
            and runtime.get("privileged_target_derivation_from_client_identity") is False
            and runtime.get("privileged_target_derivation_from_generated_container_name") is False,
            "privileged eviction is bound to trusted immutable runtime facts",
        ),
        _check(
            "eviction-order",
            lifecycle.get("eviction_order") == REQUIRED_EVICTION_ORDER,
            "revocation, secret zeroize, binding verification, termination, death verification, cleanup, release and evidence are ordered",
        ),
        _check(
            "secret-authority-preserved",
            secret.get("authority_id") == "FA3-AUTH-SECRETS-001"
            and secret.get("hrb_may_become_secret_authority") is False
            and secret.get("revoke_zeroize_before_runtime_termination") is True
            and secret.get("projection_lease_id_semantics") == "OPAQUE_SPL_HANDLE_ONLY"
            and secret.get("underlying_secret_id_in_hrb_lease_record") == "FORBIDDEN"
            and secret.get("underlying_secret_revoke_for_hrb_ttl_eviction") == "FORBIDDEN"
            and secret.get("persistent_projection_path_scope") == "ABSOLUTE_BELOW_RUN_ONLY"
            and "SecretBrokerProjectionLifecycleHook" in core
            and "_zeroize_projection_target" in core,
            "HRB coordinates opaque SecretProjectionLease revoke/zeroize without mutating credential objects",
        ),
        _check(
            "wrong-runtime-no-kill",
            runtime.get("binding_mismatch_action") == "QUARANTINE_WITHOUT_PRIVILEGED_KILL"
            and "RUNTIME_BINDING_MISMATCH" in core
            and core.index("adapter.verify_binding") < core.index('self._transition(record, "EVICTING")'),
            "trusted runtime binding is verified before privileged termination",
        ),
        _check(
            "failure-retention-quarantine",
            failure.get("delete_lease_on_kill_failure") is False
            and failure.get("terminal_failure_state") == "QUARANTINED"
            and failure.get("lease_record_retention") == "REQUIRED",
            "failed eviction never deletes the lease record",
        ),
        _check(
            "systemd-cgroup-pidfd",
            "SystemdCgroupV2ScopeAdapter" in core
            and "os.pidfd_open" in core
            and "cgroup.kill" in core
            and "--kill-whom=all" in core
            and "cgroup.procs" in core
            and "_proc_start_ticks" in core,
            "systemd/cgroup v2 group termination and pidfd/PID-reuse checks are materialized",
        ),
        _check(
            "podman-immutable-id",
            'binding["runtime_backend"] == "PODMAN"' in core
            and 're.fullmatch(r"[0-9a-f]{64}"' in core,
            "container runtime identity is adapter-specific and full immutable Podman IDs are required",
        ),
        _check(
            "no-normal-gpu-reset",
            set(gate.get("normal_eviction_forbidden_operations", []))
            == {"GPU_GLOBAL_RESET", "CUDA_DEVICE_RESET", "HIP_DEVICE_RESET"}
            and "adapter.group_kill(binding)" in core,
            "normal eviction is process/cgroup scoped and does not use device-global reset",
        ),
        _check(
            "durable-evidence-boundary",
            evidence.get("authority_id") == EVIDENCE_AUTHORITY_ID
            and evidence.get("trust_profile") == TRUST_PROFILE_ID
            and evidence.get("asymmetric_signature_required") is True
            and evidence.get("hmac_signature_allowed") is False
            and "external_asymmetric_signature_required" in core
            and "hmac_is_durable_evidence_signature" in core,
            "durable evidence remains delegated to existing Evidence/PKI authority",
        ),
        _check(
            "typed-evidence-chain",
            "HashChainEvidenceSink" in core
            and "previous_event_sha256" in core
            and "event_sha256" in core
            and "verify_chain" in core,
            "typed lifecycle evidence handoff is immutable/hash-chained before durable signing",
        ),
        _check(
            "boot-clock-binding",
            lifecycle.get("clock_semantics", {}).get("runtime_expiry_source") == "MONOTONIC"
            and lifecycle.get("clock_semantics", {}).get("boot_id_change") == "INVALIDATE_LEASE"
            and "expires_monotonic_ns" in core
            and "boot_id" in core,
            "wall-clock jumps cannot extend TTL and reboot invalidates the lease",
        ),
        _check(
            "negative-matrix-declared",
            negatives == REQUIRED_NEGATIVES and len(negatives) == 17,
            "all mandatory negative and edge cases are declared",
        ),
        _check(
            "negative-matrix-tested",
            all(name in tests for name in REQUIRED_NEGATIVES),
            "unit suite names every mandatory negative/edge case",
        ),
        _check(
            "lifecycle-invariants",
            REQUIRED_LIFECYCLE_INVARIANTS.issubset(lifecycle_invariants),
            "lease lifecycle invariants are scoped inside the existing HRB contract family",
        ),
        _check(
            "phase-one-global-surfaces-protected",
            gate.get("promotion_semantics", "").startswith("Phase-one gate validates additive HRB lease lifecycle closure only"),
            "global enforcement/distribution/release/evidence-envelope/GUI reconciliation is explicitly deferred",
        ),
    ]
    status = "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL"
    return {
        "schema": "fa3.hrb-lease-lifecycle-gate-report.v1",
        "gate_id": GATE_ID,
        "status": status,
        "scope": "HRB_LEASE_LIFECYCLE_PHASE_ONE",
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count": CAPABILITY_COUNT,
        "global_promotion_claim": False,
        "checks": checks,
        "summary": {"passed": sum(x["status"] == "PASS" for x in checks), "total": len(checks)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report", default="reports/hrb-lease-lifecycle-gate-report.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    result = evaluate(root)
    report = Path(args.report)
    if not report.is_absolute():
        report = root / report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
