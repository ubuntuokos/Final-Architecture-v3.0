#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_model_router_runtime import AUTHORITY_ID, load_routes, regression_check

GATE_ID = "FA3-MODEL-ROUTER-GATESET-001"


def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"object required: {path}")
    return obj


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    fs: list[dict[str, Any]] = []
    try:
        profile = _load(root / "canonical/profiles/FA3-MODEL-ROUTER-001.json")
        contracts = _load(root / "canonical/contracts/FA3-MODEL-ROUTER-CONTRACTS-001.json")
        enforcement = _load(root / "canonical/model-router-enforcement.json")
        routes_path = root / "deployment/model-router/routes.json"
        routes = load_routes(routes_path)
        source = (root / "src/fa3_model_router_runtime.py").read_text(encoding="utf-8")

        if profile.get("id") != "FA3-MODEL-ROUTER-001" or profile.get("authority_id") != AUTHORITY_ID:
            fs.append(finding("MR-001", "Model Router profile/authority binding mismatch"))
        if profile.get("new_architectural_authority") is not False or profile.get("capability_count_delta") != 0:
            fs.append(finding("MR-002", "Model Router materialization must add zero authorities/capabilities"))
        if profile.get("data_plane", {}).get("reference_implementation") != "LiteLLM Proxy":
            fs.append(finding("MR-003", "LiteLLM must remain the reference data plane"))
        if profile.get("data_plane", {}).get("routing_authority") != AUTHORITY_ID:
            fs.append(finding("MR-004", "LiteLLM data plane must be authority-configured by the Model Router"))
        boundaries = profile.get("authority_boundaries", {})
        expected = {
            "inventory": "FA3-MODEL-MANAGER-001",
            "placement": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "security": "FA3-AUTH-SECURITY-GOV-001",
            "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
        }
        if any(boundaries.get(k) != v for k, v in expected.items()):
            fs.append(finding("MR-005", "Model Router authority boundaries drifted", actual=boundaries))
        if contracts.get("provider_neutral") is not True or contracts.get("routing_authority") != AUTHORITY_ID:
            fs.append(finding("MR-006", "Model Router contracts are not provider-neutral/authority-bound"))
        if enforcement.get("physical_provider_pin_in_canonical") != "DENY" or enforcement.get("physical_model_pin_in_canonical") != "DENY":
            fs.append(finding("MR-007", "Canonical physical provider/model pinning must be denied"))
        if enforcement.get("client_owned_model_selection") != "DENY" or enforcement.get("litellm_independent_route_authority") != "DENY":
            fs.append(finding("MR-008", "Clients and LiteLLM may not become independent routing authorities"))

        route_rows = routes.get("routes", [])
        aliases = {x.get("route") for x in route_rows if isinstance(x, dict)}
        required_aliases = {"fa3-text-primary", "fa3-text-secondary", "fa3-pageindex-index", "fa3-pageindex-reason"}
        if not required_aliases.issubset(aliases):
            fs.append(finding("MR-009", "Required logical route aliases are missing", missing=sorted(required_aliases-aliases)))

        text = routes_path.read_text(encoding="utf-8")
        forbidden_patterns = [
            r"127\.0\.0\.1:\d+",
            r"localhost:\d+",
            r"\bqwen[^\"\s]*",
            r"\bllama[^\"\s]*",
            r"\bgemma[^\"\s]*",
            r"\bollama/",
            r"\bopenai/",
            r"\bprovider_id\b",
            r"\bapi_base\b",
        ]
        hits = [p for p in forbidden_patterns if re.search(p, text, re.I)]
        if hits:
            fs.append(finding("MR-010", "Logical route manifest contains a physical provider/model binding", patterns=hits))

        if "FA3_LITELLM_MASTER_KEY" not in source or "CURRENT_HOST_PROVIDER_CATALOG" not in source:
            fs.append(finding("MR-011", "Runtime does not prove runtime secret injection and dynamic catalog selection"))
        if "allow_external" not in source or "locality" not in source:
            fs.append(finding("MR-012", "Runtime lacks explicit locality/external-route policy enforcement"))

        regression = regression_check()
        if regression.get("result") != "PASS":
            fs.append(finding("MR-013", "Executable Model Router regression failed", regression=regression))
    except Exception as exc:
        fs.append(finding("MR-000", "Model Router materialization unreadable", error=repr(exc)))

    return {
        "schema": "fa3.model-router-gate-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not fs else "FAIL",
        "findings": fs,
        "current_host_status": "PENDING_CURRENT_HOST",
        "global_promotion_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    report = gate(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
