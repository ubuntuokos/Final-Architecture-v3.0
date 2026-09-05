#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_model_inventory_current_host_adapter import (
    CONFORMANCE_ID,
    EVIDENCE_LEVEL,
    GATE_ID,
    PROVIDER_IDS,
    STABILITY_MATRIX_PROVIDER_ID,
    collect_cross_provider_inventory,
    collect_stability_matrix_inventory,
    regression_check,
)
from fa3_model_manager_provider_adapter import sha256_bytes, sha256_file


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def host_fingerprint() -> dict[str, Any]:
    u = platform.uname()
    return {
        "system": u.system,
        "release": u.release,
        "machine": u.machine,
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "hostname_sha256": sha256_bytes(u.node.encode("utf-8")),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("current-host model inventory evidence requires Linux x86_64")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise RuntimeError("current-host model inventory evidence must not run as root")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runtime_dir = root / "evidence/runtime/model-inventory-current-host" / stamp
    runtime_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = runtime_dir / "cross-provider-inventory.json"
    receipt_path = root / "evidence/receipts/model-inventory-current-host.json"

    regressions = regression_check()
    if regressions.get("result") != "PASS":
        raise RuntimeError("model inventory adapter regression failed")

    receipt: dict[str, Any] = {
        "schema": "fa3.model-inventory-current-host-receipt.v1",
        "conformance_id": CONFORMANCE_ID,
        "gate_id": GATE_ID,
        "status": "FAIL",
        "evidence_level": "CURRENT_HOST_READ_ONLY_CROSS_PROVIDER_MODEL_INVENTORY_FAIL",
        "started_at": utc_now(),
        "host": host_fingerprint(),
        "adapter_regression": regressions,
        "execution_policy": {
            "read_only_provider_discovery": True,
            "model_store_mutation": False,
            "network_access": False,
            "model_download_or_pull": False,
            "canonical_admission": False,
            "physical_dedup": False,
            "absolute_model_store_paths_emitted": False,
        },
        "provider_ids": PROVIDER_IDS,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "capability_count_after": 143,
    }
    try:
        before = collect_stability_matrix_inventory()
        snapshot = collect_cross_provider_inventory()
        after = collect_stability_matrix_inventory()
        stability = snapshot["providers"][STABILITY_MATRIX_PROVIDER_ID]
        unchanged = (
            before.get("inventory_manifest_sha256") == after.get("inventory_manifest_sha256")
            and before.get("entry_count") == after.get("entry_count")
            and before.get("total_bytes") == after.get("total_bytes")
        )
        if not unchanged:
            raise RuntimeError("StabilityMatrix model-store structural inventory changed during read-only discovery run")
        if stability.get("status") != "PASS" or int(stability.get("entry_count", 0)) <= 0:
            raise RuntimeError("StabilityMatrix current-host inventory is empty or unavailable")
        if int(snapshot.get("available_provider_count", 0)) < 2:
            raise RuntimeError("cross-provider discovery requires StabilityMatrix plus at least one additional local provider with entries")

        writej(inventory_path, snapshot)
        receipt.update({
            "status": "PASS",
            "evidence_level": EVIDENCE_LEVEL,
            "completed_at": utc_now(),
            "stability_matrix": {
                "status": stability.get("status"),
                "entry_count": stability.get("entry_count"),
                "total_bytes": stability.get("total_bytes"),
                "symlink_file_count": stability.get("symlink_file_count"),
                "inventory_manifest_sha256": stability.get("inventory_manifest_sha256"),
                "representative": stability.get("representative"),
                "path_disclosure": stability.get("path_disclosure"),
            },
            "cross_provider": {
                "available_provider_ids": snapshot.get("available_provider_ids"),
                "available_provider_count": snapshot.get("available_provider_count"),
                "total_entries": snapshot.get("total_entries"),
                "inventory_snapshot_sha256": snapshot.get("inventory_snapshot_sha256"),
                "inventory_file": inventory_path.relative_to(root).as_posix(),
                "inventory_file_sha256": sha256_file(inventory_path),
            },
            "stability_matrix_before_after_equal": unchanged,
            "model_store_mutation_detected": False,
            "network_access_performed": False,
            "promotion_effect": "CURRENT_HOST_READ_ONLY_INVENTORY_EVIDENCE_ONLY_NO_MODEL_RUNTIME_OR_GLOBAL_PROMOTION",
        })
        writej(receipt_path, receipt)
        writej(runtime_dir / "summary.json", {
            "conformance_id": CONFORMANCE_ID,
            "status": "PASS",
            "evidence_level": EVIDENCE_LEVEL,
            "completed_at": receipt["completed_at"],
            "provider_statuses": {pid: item.get("status") for pid, item in snapshot["providers"].items()},
            "provider_entry_counts": {pid: item.get("entry_count", 0) for pid, item in snapshot["providers"].items()},
            "inventory_snapshot_sha256": snapshot.get("inventory_snapshot_sha256"),
            "receipt_sha256": sha256_file(receipt_path),
        })
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        receipt["completed_at"] = utc_now()
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
        writej(receipt_path, receipt)
        print(json.dumps(receipt, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
