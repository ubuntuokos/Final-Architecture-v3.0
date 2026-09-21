#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "fa3.secret-broker-current-host-receipt.v1"

REQUIRED_CHECKS = [
    "current_host_privileged_bridge_source_binding_pass",
    "non_root_admin_authorization_pass",
    "ephemeral_admin_probe_removed_pass",
    "authorized_single_secret_get",
    "systemd_loadcredential_projection_pass",
    "encrypted_systemd_unlock_runtime_pass",
    "systemd_target_lifecycle_pass",
    "secrets_target_inactive_pass",
    "hardware_neutral_systemd_credential_host_key_mode_pass",
    "luks_unlock_key_rotation_pass",
    "old_unlock_key_rejected_after_rekey",
    "new_unlock_key_accepted_after_rekey",
    "rekey_final_closed_state_pass",
    "systemd_e2e_artifact_cleanup_pass",
    "policy_preflight_pass",
    "policy_install_remove_pass",
    "rotation_pass",
    "revocation_pass",
    "metadata_only_list_pass",
    "unauthorized_consumer_denied",
    "raw_vault_access_denied",
    "bulk_export_absent",
    "credential_scope_enforced",
    "audit_contains_no_raw_secret",
    "secret_absent_from_argv",
    "secret_absent_from_environment",
    "broker_health_pass",
    "explicit_unmount_pass",
    "luks_close_pass",
    "fa3_exit_closed_state_pass",
    "opaque_backup_copy_pass",
    "restore_unlock_pass",
    "restore_mount_pass",
    "restore_broker_health_pass",
    "restore_secret_read_pass",
]


def validate(x: dict) -> list[str]:
    findings: list[str] = []

    def req(ok: bool, code: str) -> None:
        if not ok:
            findings.append(code)

    req(x.get("schema") == SCHEMA, "SBH-001")
    req(
        x.get("status") == "PASS"
        and x.get("real_execution") is True
        and x.get("synthetic") is False,
        "SBH-002",
    )
    req(
        x.get("luks2") is True
        and x.get("filesystem") == "ext4"
        and set(x.get("mount_options", [])) == {"nodev", "nosuid", "noexec"},
        "SBH-003",
    )
    req(
        x.get("broker_unprivileged") is True
        and x.get("broker_user") == "fa3-secret-broker",
        "SBH-004",
    )

    bridge = str(x.get("bridge_source_commit", ""))
    req(
        len(bridge) == 40
        and all(ch in "0123456789abcdef" for ch in bridge),
        "SBH-004A",
    )

    checks = x.get("checks", {})
    for key in REQUIRED_CHECKS:
        req(checks.get(key) is True, "SBH-" + key)

    req(
        x.get("secret_values_collected") is False
        and x.get("runtime_promotion_eligible") is True
        and x.get("global_promotion_claim") is False,
        "SBH-005",
    )
    req(
        x.get("new_capabilities") == 0
        and x.get("new_architectural_authorities") == 0
        and x.get("capability_count_after") == 143,
        "SBH-006",
    )
    return findings


def gate(root: Path, receipt: Path | None, require: bool) -> dict:
    path = receipt or root / "evidence/receipts/secret-broker-current-host.json"
    if not path.is_file():
        return {
            "schema": "fa3.secret-broker-current-host-gate-report.v1",
            "gate_id": "FA3-GATE-SECRET-BROKER-CURRENT-HOST-001",
            "result": "FAIL" if require else "PASS",
            "status": (
                "BLOCKED_CURRENT_HOST_EVIDENCE_REQUIRED"
                if require
                else "PENDING_CURRENT_HOST"
            ),
            "findings": ["MISSING_RECEIPT"] if require else [],
            "global_promotion_claim": False,
        }

    try:
        receipt_obj = json.loads(path.read_text())
        findings = validate(receipt_obj)
    except Exception as exc:
        findings = ["UNREADABLE:" + type(exc).__name__]

    return {
        "schema": "fa3.secret-broker-current-host-gate-report.v1",
        "gate_id": "FA3-GATE-SECRET-BROKER-CURRENT-HOST-001",
        "result": "PASS" if not findings else "FAIL",
        "status": "CURRENT_HOST_PASS" if not findings else "BLOCKED_INVALID_EVIDENCE",
        "findings": findings,
        "global_promotion_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    receipt = Path(args.receipt).resolve() if args.receipt else None
    output = gate(root, receipt, args.require_evidence)

    report = root / "reports/secret-broker-current-host-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return 0 if output["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
