#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from fa3_runtime_hardening import shadow_execution_valid
from fa3_runtime_hardening_current_host import (
    load_json,
    repo_head,
    sha256_file,
    utcnow,
    validate_runtime_sandbox_receipt,
    write_json,
)


def collect(root: Path, *, sandbox_receipt_path: Path, output: Path) -> dict:
    receipt = {
        "schema": "fa3.promotion-shadow-current-host-receipt.v1",
        "surface": "PROMOTION_SHADOW",
        "repository_head": repo_head(root),
        "captured_at": utcnow(),
        "synthetic": False,
        "global_promotion_claim": False,
        "promotion_authority": False,
        "may_assign_promoted": False,
        "authoritative_output": False,
        "external_side_effects": False,
        "output_quarantined": False,
        "workspace_destroyed": False,
    }
    workspace_path = None
    try:
        if not sandbox_receipt_path.is_file():
            raise RuntimeError(f"sandbox receipt missing: {sandbox_receipt_path}")
        sandbox = load_json(sandbox_receipt_path)
        sandbox_ok, sandbox_reasons = validate_runtime_sandbox_receipt(sandbox, root=root)
        receipt["sandbox_receipt_sha256"] = sha256_file(sandbox_receipt_path)
        receipt["sandbox_dependency_status"] = "PASS" if sandbox_ok else "PENDING"
        receipt["sandbox_dependency_reasons"] = sandbox_reasons
        if not sandbox_ok:
            raise RuntimeError("sandbox dependency is not CURRENT_HOST_PASS")

        state_root = root / ".fa3-current-host"
        state_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="shadow-", dir=state_root) as td:
            workspace = Path(td)
            workspace_path = workspace
            inp = workspace / "input"
            quarantine = workspace / "quarantine"
            inp.mkdir()
            quarantine.mkdir()
            source = inp / "synthetic.json"
            source.write_text('{"class":"synthetic-shadow-fixture","value":7}\n', encoding="utf-8")
            allowed = shadow_execution_valid(
                current_host_evidence="PENDING_CURRENT_HOST",
                execution_mode="SHADOW",
                input_mode="SYNTHETIC",
                production_data=False,
                data_governance_admitted=False,
                authoritative_output=False,
                external_side_effects=False,
                output_quarantined=True,
                evidence_collection=True,
                workspace_ephemeral=True,
                network_mode="DENY",
            )
            if not allowed:
                raise RuntimeError("canonical Shadow policy denied conformant synthetic plan")
            result = quarantine / "result.json"
            result.write_text(
                json.dumps({"input_sha256": sha256_file(source), "authoritative": False}) + "\n",
                encoding="utf-8",
            )
            receipt["execution_allowed"] = True
            receipt["input_mode"] = "SYNTHETIC"
            receipt["network_mode"] = "DENY"
            receipt["output_quarantined"] = result.is_file() and result.parent == quarantine
            receipt["output_sha256"] = sha256_file(result)
        receipt["workspace_destroyed"] = workspace_path is not None and not workspace_path.exists()
        if not receipt["workspace_destroyed"]:
            raise RuntimeError("ephemeral Shadow workspace cleanup failed")
        receipt["result"] = "PASS"
        receipt["status"] = "CURRENT_HOST_PASS"
    except Exception as exc:
        receipt.setdefault("execution_allowed", False)
        receipt["result"] = "PENDING"
        receipt["status"] = "PENDING_CURRENT_HOST"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)
    receipt["completed_at"] = utcnow()
    write_json(output, receipt)
    return receipt


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--sandbox-receipt", required=True)
    p.add_argument("--output", default="evidence/receipts/promotion-shadow-current-host.json")
    a = p.parse_args()
    root = Path(a.root).resolve()
    output = Path(a.output)
    if not output.is_absolute():
        output = root / output
    receipt = collect(
        root,
        sandbox_receipt_path=Path(a.sandbox_receipt).resolve(),
        output=output,
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
