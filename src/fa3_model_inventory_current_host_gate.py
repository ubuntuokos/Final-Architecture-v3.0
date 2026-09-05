#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_model_inventory_current_host_adapter import (
    CONFORMANCE_ID,
    EVIDENCE_LEVEL,
    GATE_ID,
    PROVIDER_IDS,
    STABILITY_MATRIX_PROVIDER_ID,
)
from fa3_model_manager_provider_adapter import sha256_file

RECEIPT = "evidence/receipts/model-inventory-current-host.json"
DECISION_ID = "FA3-DEC-MODEL-MANAGER-INVENTORY-CURRENT-HOST-2026-09-05"
ENFORCEMENT_PATH = "canonical/model-manager-inventory-current-host-enforcement.json"
CONFORMANCE_PATH = "canonical/FA3-MODEL-INVENTORY-CURRENT-HOST-CONFORMANCE-001.json"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def digest64(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def reference_check(root: Path) -> dict[str, Any]:
    fs: list[dict[str, Any]] = []
    conformance_path = root / CONFORMANCE_PATH
    enforcement_path = root / ENFORCEMENT_PATH
    decision_path = root / "canonical/decisions" / f"{DECISION_ID}.json"
    provider_path = root / "canonical/providers/FA3-PROVIDER-STABILITY-MATRIX-MODEL-STORE-001.json"
    contract_path = root / "canonical/contracts/FA3-MODEL-MANAGER-CONTRACTS-001.json"
    for name, path in {
        "conformance": conformance_path,
        "enforcement": enforcement_path,
        "decision": decision_path,
        "provider": provider_path,
        "contract": contract_path,
    }.items():
        if not path.is_file():
            fs.append(finding("MODEL-INV-REF-001", "required canonical artifact missing", artifact=name, path=str(path.relative_to(root))))
    if fs:
        return {"result": "FAIL", "findings": fs}
    conf = loadj(conformance_path)
    enf = loadj(enforcement_path)
    dec = loadj(decision_path)
    provider = loadj(provider_path)
    contract = loadj(contract_path)
    if not (
        conf.get("id") == CONFORMANCE_ID
        and conf.get("profile_id") == "FA3-MODEL-MANAGER-001"
        and conf.get("provider_ids") == PROVIDER_IDS
        and conf.get("required_evidence_level") == EVIDENCE_LEVEL
        and conf.get("new_capability") is False
        and conf.get("new_architectural_authority") is False
        and conf.get("capability_count") == 143
    ):
        fs.append(finding("MODEL-INV-REF-010", "current-host inventory conformance drift"))
    if not (
        enf.get("gate_id") == GATE_ID
        and enf.get("conformance_id") == CONFORMANCE_ID
        and enf.get("provider_ids") == PROVIDER_IDS
        and enf.get("fail_closed") is True
        and enf.get("read_only_required") is True
        and enf.get("network_access_forbidden") is True
        and enf.get("model_store_mutation_forbidden") is True
    ):
        fs.append(finding("MODEL-INV-REF-011", "inventory enforcement drift"))
    if not (
        dec.get("id") == DECISION_ID
        and dec.get("status") == "CANONICAL_CLOSED"
        and dec.get("conformance_id") == CONFORMANCE_ID
        and dec.get("gate_id") == GATE_ID
        and dec.get("provider_ids") == PROVIDER_IDS
        and dec.get("new_capabilities") == 0
        and dec.get("new_architectural_authorities") == 0
        and dec.get("capability_count_after") == 143
    ):
        fs.append(finding("MODEL-INV-REF-012", "inventory decision drift"))
    if not (
        provider.get("id") == STABILITY_MATRIX_PROVIDER_ID
        and provider.get("architectural_authority") is False
        and provider.get("fa3_usage_policy", {}).get("automatic_physical_dedup") == "FORBIDDEN"
    ):
        fs.append(finding("MODEL-INV-REF-013", "StabilityMatrix authority/dedup boundary drift"))
    contracts = contract.get("contracts", [])
    semantics = contract.get("additional_required_semantics", {})
    if not (
        "ReadOnlyProviderInventoryScan" in contracts
        and "CrossProviderInventorySnapshot" in contracts
        and "CurrentHostInventoryEvidenceReceipt" in contracts
        and semantics.get("read_only_cross_provider_inventory") == "DISCOVERY_ONLY_NO_MUTATION_NO_ROUTING_NO_ADMISSION"
    ):
        fs.append(finding("MODEL-INV-REF-014", "Model Manager inventory contract extension missing"))
    return {"result": "PASS" if not fs else "FAIL", "findings": fs}


def gate(root: Path) -> dict[str, Any]:
    fs: list[dict[str, Any]] = []
    ref = reference_check(root)
    if ref["result"] != "PASS":
        fs.extend(ref["findings"])
    path = root / RECEIPT
    receipt: dict[str, Any] = {}
    if not path.is_file():
        fs.append(finding("MODEL-INV-HOST-001", "current-host cross-provider inventory receipt missing"))
    else:
        try:
            receipt = loadj(path)
        except Exception as exc:
            fs.append(finding("MODEL-INV-HOST-002", "current-host inventory receipt unreadable", error=repr(exc)))
    if receipt:
        if not (
            receipt.get("conformance_id") == CONFORMANCE_ID
            and receipt.get("gate_id") == GATE_ID
            and receipt.get("status") == "PASS"
            and receipt.get("evidence_level") == EVIDENCE_LEVEL
        ):
            fs.append(finding("MODEL-INV-HOST-003", "receipt identity/evidence level missing"))
        policy = receipt.get("execution_policy", {})
        if not (
            policy.get("read_only_provider_discovery") is True
            and policy.get("model_store_mutation") is False
            and policy.get("network_access") is False
            and policy.get("model_download_or_pull") is False
            and policy.get("canonical_admission") is False
            and policy.get("physical_dedup") is False
            and policy.get("absolute_model_store_paths_emitted") is False
        ):
            fs.append(finding("MODEL-INV-HOST-004", "read-only execution policy drift"))
        if receipt.get("provider_ids") != PROVIDER_IDS:
            fs.append(finding("MODEL-INV-HOST-005", "provider set mismatch", provider_ids=receipt.get("provider_ids")))
        sm = receipt.get("stability_matrix", {})
        rep = sm.get("representative", {})
        if not (
            sm.get("status") == "PASS"
            and int(sm.get("entry_count", 0)) > 0
            and int(sm.get("total_bytes", 0)) > 0
            and digest64(sm.get("inventory_manifest_sha256"))
            and int(rep.get("size_bytes", 0)) > 0
            and digest64(rep.get("sha256"))
            and sm.get("path_disclosure") == "ABSOLUTE_PATHS_NOT_EMITTED"
        ):
            fs.append(finding("MODEL-INV-HOST-006", "StabilityMatrix real read-only inventory evidence incomplete"))
        cross = receipt.get("cross_provider", {})
        inv_rel = cross.get("inventory_file")
        inv_path = root / str(inv_rel) if isinstance(inv_rel, str) else None
        if not (
            int(cross.get("available_provider_count", 0)) >= 2
            and isinstance(cross.get("available_provider_ids"), list)
            and STABILITY_MATRIX_PROVIDER_ID in cross.get("available_provider_ids", [])
            and int(cross.get("total_entries", 0)) >= int(sm.get("entry_count", 0))
            and digest64(cross.get("inventory_snapshot_sha256"))
            and digest64(cross.get("inventory_file_sha256"))
            and inv_path is not None
            and inv_path.is_file()
            and sha256_file(inv_path) == cross.get("inventory_file_sha256")
        ):
            fs.append(finding("MODEL-INV-HOST-007", "cross-provider inventory evidence incomplete or inventory artifact hash mismatch"))
        if not (
            receipt.get("stability_matrix_before_after_equal") is True
            and receipt.get("model_store_mutation_detected") is False
            and receipt.get("network_access_performed") is False
        ):
            fs.append(finding("MODEL-INV-HOST-008", "read-only/no-network proof failed"))
        if receipt.get("new_capabilities") != 0 or receipt.get("new_architectural_authorities") != 0 or receipt.get("capability_count_after") != 143:
            fs.append(finding("MODEL-INV-HOST-009", "capability/authority invariant drift"))
    report = {
        "schema": "fa3.model-inventory-current-host-gate-report.v1",
        "gate_id": GATE_ID,
        "conformance_id": CONFORMANCE_ID,
        "provider_ids": PROVIDER_IDS,
        "result": "PASS" if not fs else "FAIL",
        "evidence_level": receipt.get("evidence_level") if receipt else None,
        "reference": ref,
        "findings": fs,
        "promotion_effect": "CURRENT_HOST_READ_ONLY_INVENTORY_PASS_DOES_NOT_GRANT_ROUTING_RUNTIME_OR_GLOBAL_PROMOTION",
    }
    out = root / "reports/model-inventory-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root).resolve())
    print(json.dumps(report, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
