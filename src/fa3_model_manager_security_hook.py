#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fa3_model_artifact_security_gate import admission_valid

HOOK_ID = "FA3-MODEL-MANAGER-SECURITY-HOOK-001"


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(receipt: dict[str, Any], artifact_sha256: str) -> dict[str, Any]:
    same_artifact = receipt.get("artifact", {}).get("sha256") == artifact_sha256
    admitted = same_artifact and admission_valid(receipt)
    return {
        "schema": "fa3.model-manager-security-hook-result.v1",
        "hook_id": HOOK_ID,
        "artifact_sha256": artifact_sha256,
        "receipt_artifact_sha256": receipt.get("artifact", {}).get("sha256"),
        "security_state": "SECURITY_ADMITTED" if admitted else "SECURITY_BLOCKED",
        "model_manager_promotion_eligible": admitted,
        "direct_runtime_store_download_bypass": False,
        "scanner_output_is_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--artifact-sha256", required=True)
    args = ap.parse_args()
    result = evaluate(loadj(Path(args.receipt)), args.artifact_sha256)
    print(json.dumps(result, indent=2))
    return 0 if result["model_manager_promotion_eligible"] else 2


if __name__ == "__main__": raise SystemExit(main())
