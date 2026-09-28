#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILE = "canonical/profiles/FA3-GENERATIVE-MEDIA-STUDIO-001.json"
CONTRACT = "canonical/contracts/FA3-GENERATIVE-MEDIA-STUDIO-CONTRACTS-001.json"
DECISION = "canonical/decisions/FA3-DEC-GENERATIVE-MEDIA-STUDIO-2026-09-28.json"
REFERENCE = "canonical/references/FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28.json"
QML = "apps/fa3-generative-media-studio/qml/Main.qml"
BACKEND = "apps/fa3-generative-media-studio/src/StudioBackend.cpp"
CMAKE = "apps/fa3-generative-media-studio/CMakeLists.txt"


def load(root: Path, rel: str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def gate(root: Path) -> dict:
    findings: list[dict[str, str]] = []
    for rel in [PROFILE, CONTRACT, DECISION, REFERENCE, QML, BACKEND, CMAKE]:
        if not (root / rel).is_file():
            findings.append({"code": "GMS-001", "message": f"missing:{rel}"})
    if findings:
        return {"result": "FAIL", "findings": findings}

    p = load(root, PROFILE)
    c = load(root, CONTRACT)
    d = load(root, DECISION)
    r = load(root, REFERENCE)
    qml = (root / QML).read_text(encoding="utf-8")
    backend = (root / BACKEND).read_text(encoding="utf-8")
    cmake = (root / CMAKE).read_text(encoding="utf-8")

    checks = [
        (p.get("id") == "FA3-GENERATIVE-MEDIA-STUDIO-001", "GMS-002", "profile identity drift"),
        (p.get("capability_count") == 175 and p.get("new_capability") is False, "GMS-003", "capability baseline drift"),
        (p.get("new_architectural_authority") is False, "GMS-004", "authority delta"),
        (c.get("provider_neutral") is True, "GMS-005", "contract is not provider-neutral"),
        (c.get("request_compilation", {}).get("physical_provider_pin_allowed") is False, "GMS-006", "provider pin allowed"),
        (c.get("request_compilation", {}).get("physical_model_pin_allowed") is False, "GMS-007", "model pin allowed"),
        (c.get("authority_boundaries", {}).get("provider_routing") == "FA3-AUTH-MODEL-ROUTER-001", "GMS-008", "Model Router authority drift"),
        (c.get("authority_boundaries", {}).get("host_resources") == "FA3-AUTH-HOST-RESOURCE-BROKER-001", "GMS-009", "HRB authority drift"),
        (c.get("hardware_audit", {}).get("accelerator_cardinality") == "0..N", "GMS-010", "accelerator cardinality drift"),
        (c.get("hardware_audit", {}).get("cpu_only_architecture_supported") is True, "GMS-011", "CPU-only architecture lost"),
        (d.get("new_capabilities") == 0 and d.get("new_architectural_authorities") == 0, "GMS-012", "decision baseline delta"),
        (d.get("runtime_claims", {}).get("current_host_provider_execution_pass") is False, "GMS-013", "runtime overclaim"),
        (r.get("policy", {}).get("autom8ai_fork_is_canonical_source") is False, "GMS-014", "Autom8AI fork incorrectly authoritative"),
        (r.get("policy", {}).get("original_upstream_is_canonical_donor_source") is True, "GMS-015", "upstream provenance missing"),
        ("from: 6" in qml and "to: 20" in qml, "GMS-016", "6..20 second Studio control missing"),
        ("FA3 Model Router" in qml, "GMS-017", "Model Router projection missing"),
        ("PENDING_ADMISSION" in backend, "GMS-018", "request does not remain pending admission"),
        ("physical_provider_pin" in backend and "physical_model_pin" in backend, "GMS-019", "pin-denial fields missing"),
        ("Qt6::Qml" in cmake and "Qt6::Quick" in cmake, "GMS-020", "Qt6/QML build contract missing"),
    ]
    for ok, code, message in checks:
        if not ok:
            findings.append({"code": code, "message": message})

    for token in ["QProcess", "QNetworkAccessManager", "QTcpSocket", "curl ", "wget ", "system("]:
        if token in backend:
            findings.append({"code": "GMS-021", "message": f"direct execution/network token present:{token}"})

    return {
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "claims": ["STATIC_APPLICATION_CONTRACT_CONFORMANCE"] if not findings else [],
        "non_claims": ["CURRENT_HOST_BUILD_PASS", "PROVIDER_EXECUTION_PASS", "PRODUCTION_PROMOTION"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
