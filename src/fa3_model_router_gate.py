#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
GATE_ID = "FA3-MODEL-ROUTER-GATESET-001"
REQUIRED_ROUTES = {
    "fa3-text-primary",
    "fa3-text-secondary",
    "fa3-pageindex-index",
    "fa3-pageindex-reason",
}
REQUIRED_RULES = {
    "ONE_CENTRAL_MODEL_ROUTER_AUTHORITY",
    "LITELLM_IS_DATA_PLANE_NOT_SECOND_ROUTING_AUTHORITY",
    "CANONICAL_ROUTES_MUST_NOT_PIN_PHYSICAL_PROVIDER",
    "CANONICAL_ROUTES_MUST_NOT_PIN_PHYSICAL_MODEL",
    "RUNTIME_PROVIDER_REQUIRES_CURRENT_HOST_ADMISSION_RECEIPT",
    "NO_SILENT_LOCAL_TO_CLOUD_FALLBACK",
    "CURRENT_HOST_ROUTER_RECEIPT_REQUIRED_FOR_CONSUMER_ADMISSION",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **extra}


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    paths = {
        "authority": root / "canonical/FA3-AUTH-MODEL-ROUTER-001.json",
        "routes": root / "deployment/model-router/routes.json",
        "enforcement": root / "canonical/model-router-enforcement.json",
        "gateway": root / "canonical/profiles/FA3-LLM-GATEWAY-001.json",
        "baseline": root / "deployment/litellm/config.yaml",
        "service": root / "deployment/model-router/fa3-model-router.service.in",
        "materializer": root / "src/fa3_model_router_materialize.py",
        "provider_discovery": root / "src/fa3_model_router_provider_discovery.py",
        "collector": root / "evidence/collect-model-router-current-host.py",
        "host_gate": root / "src/fa3_model_router_current_host_gate.py",
        "installer": root / "bin/fa3-model-router-install",
    }
    missing = [str(p.relative_to(root)) for p in paths.values() if not p.is_file()]
    if missing:
        findings.append(finding("MR-000", "required Model Router artifact missing", missing=missing))
        return {"schema":"fa3.model-router-gate.v1","gate_id":GATE_ID,"result":"FAIL","findings":findings}

    authority = loadj(paths["authority"])
    routes = loadj(paths["routes"])
    enforcement = loadj(paths["enforcement"])
    gateway = loadj(paths["gateway"])
    baseline = paths["baseline"].read_text(encoding="utf-8")
    service = paths["service"].read_text(encoding="utf-8")
    materializer = paths["materializer"].read_text(encoding="utf-8")
    provider_discovery = paths["provider_discovery"].read_text(encoding="utf-8")

    if authority.get("id") != AUTHORITY or authority.get("status") != "CANONICAL":
        findings.append(finding("MR-001", "central Model Router authority record mismatch"))
    if authority.get("materializes_existing_authority") is not True or authority.get("new_architectural_authority") is not False:
        findings.append(finding("MR-002", "Model Router must materialize the existing authority without authority delta"))
    data_plane = authority.get("data_plane", {})
    if data_plane.get("profile") != "FA3-LLM-GATEWAY-001" or data_plane.get("reference_runtime") != "LiteLLM Proxy" or data_plane.get("single_routing_plane") is not True:
        findings.append(finding("MR-003", "LiteLLM must be the single Model Router data plane"))
    if routes.get("authority") != AUTHORITY or routes.get("physical_provider_pins") is not False or routes.get("physical_model_pins") is not False:
        findings.append(finding("MR-004", "canonical routes must be authority-bound and physical-pin free"))
    route_rows = routes.get("routes", [])
    route_names = {str(x.get("route")) for x in route_rows if isinstance(x, dict)}
    if route_names != REQUIRED_ROUTES:
        findings.append(finding("MR-005", "required logical route set mismatch", routes=sorted(route_names)))
    for row in route_rows:
        if not isinstance(row, dict):
            findings.append(finding("MR-006", "route row is not an object"))
            continue
        if row.get("locality") != "LOCAL_ONLY" or row.get("external_fallback") != "DENY":
            findings.append(finding("MR-007", "baseline logical route must remain local-only without external fallback", route=row.get("route")))
        forbidden = {"provider_id","runtime_id","api_base","model","physical_model","physical_provider"}
        if forbidden.intersection(row):
            findings.append(finding("MR-008", "canonical logical route contains physical routing state", route=row.get("route")))
    if not REQUIRED_RULES.issubset(set(enforcement.get("rules", []))):
        findings.append(finding("MR-009", "Model Router enforcement rules incomplete"))
    bindings = gateway.get("authority_bindings", {})
    if bindings.get("provider_model_routing") != AUTHORITY:
        findings.append(finding("MR-010", "LLM Gateway is not bound to central Model Router authority"))
    if gateway.get("reference_implementation") != "LiteLLM Proxy":
        findings.append(finding("MR-011", "LiteLLM reference runtime drift"))
    if "model_list: []" not in baseline:
        findings.append(finding("MR-012", "committed LiteLLM baseline must not carry physical/runtime route materialization"))
    if "model:" in "\n".join(line for line in baseline.splitlines() if not line.lstrip().startswith("#")):
        findings.append(finding("MR-013", "committed LiteLLM baseline contains a model pin"))
    if "ExecStartPre=" not in service or "fa3_model_router_materialize.py" not in service or "fa3-model-router-serve" not in service:
        findings.append(finding("MR-014", "Model Router service does not materialize runtime selection before LiteLLM start"))
    if "IPAddressDeny=any" not in service or "IPAddressAllow=localhost" not in service:
        findings.append(finding("MR-015", "baseline Model Router service is not loopback-egress constrained"))
    required_materializer = (
        "receipt_proves_provider",
        "canonical_provider_ok",
        "fetch_models",
        "select_bindings",
        "physical_backend_pinned",
        "physical_model_pinned",
        "decision_fabric",
        "deterministic_admission_already_applied",
        "decision_advisory_changes_authority",
    )
    if any(token not in materializer for token in required_materializer):
        findings.append(finding("MR-016", "runtime materializer lacks provider admission/discovery/selection invariants"))
    required_discovery = (
        "FA3-PROVIDER-LM-STUDIO-MODEL-001",
        "FA3-PROVIDER-OLLAMA-MODEL-001",
        "CURRENT_HOST_LIVE_ENDPOINT_DISCOVERY",
        "provider_neutral",
        "physical_model_pins",
    )
    if any(token not in provider_discovery for token in required_discovery):
        findings.append(finding("MR-017", "current-host provider discovery does not preserve admitted/live/provider-neutral boundaries"))
    return {
        "schema": "fa3.model-router-gate.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "logical_routes": sorted(route_names),
        "capability_delta": 0,
        "authority_delta": 0,
        "current_host_claim": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
