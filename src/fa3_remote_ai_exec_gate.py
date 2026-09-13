#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "profile": ROOT / "canonical/profiles/FA3-REMOTE-AI-EXEC-001.json",
    "contract": ROOT / "canonical/contracts/FA3-REMOTE-AI-EXEC-CONTRACTS-001.json",
    "provider": ROOT / "canonical/providers/FA3-PROVIDER-HF-SPACES-001.json",
    "hf_model_store": ROOT / "canonical/providers/FA3-PROVIDER-HF-MODEL-STORE-001.json",
    "decision": ROOT / "canonical/decisions/FA3-DEC-REMOTE-AI-HF-SPACES-2026-09-13.json",
    "gate": ROOT / "canonical/FA3-GATE-REMOTE-AI-EXEC-001.json",
    "desktop_profile": ROOT / "canonical/profiles/FA3-DESKTOP-001.json",
    "desktop_contract": ROOT / "canonical/contracts/FA3-DESKTOP-CONTRACTS-001.json",
    "qml": ROOT / "apps/fa3-control-center/qml/Main.qml",
}

REQUIRED_ADAPTERS = {
    "GRADIO_PYTHON_CLIENT",
    "GRADIO_JAVASCRIPT_CLIENT",
    "QUEUE_BASED_REST_OPENAPI",
    "AGENTS_MD_AGENT_DISCOVERY",
    "MCP_COMPATIBLE_SPACE_TOOLS",
}

REQUIRED_ROUTING = {
    "LOCAL_REQUIRED",
    "LOCAL_PREFERRED_REMOTE_ALLOWED",
    "REMOTE_ALLOWED",
    "SPECIFIC_REMOTE_PROVIDER",
}

REQUIRED_OBJECTS = {
    "RemoteToolDescriptor",
    "EndpointSchema",
    "ToolCapability",
    "RemoteExecutionRequest",
    "RemoteExecutionJob",
    "RemoteExecutionResult",
    "ArtifactReference",
    "CredentialReference",
    "QuotaBudget",
    "ExecutionProvenance",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> list[str]:
    failures: list[str] = []
    for name, path in PATHS.items():
        if not path.exists():
            failures.append(f"missing:{name}:{path.relative_to(ROOT)}")
    if failures:
        return failures

    profile = load(PATHS["profile"])
    contract = load(PATHS["contract"])
    provider = load(PATHS["provider"])
    hf_model_store = load(PATHS["hf_model_store"])
    decision = load(PATHS["decision"])
    gate = load(PATHS["gate"])
    desktop_profile = load(PATHS["desktop_profile"])
    desktop_contract = load(PATHS["desktop_contract"])
    qml = PATHS["qml"].read_text(encoding="utf-8")

    checks = [
        (profile.get("id") == "FA3-REMOTE-AI-EXEC-001", "profile-id"),
        (profile.get("status") == "CANONICAL", "profile-canonical"),
        (profile.get("priority") == "P0" and profile.get("requirement") == "MUST", "profile-p0-must"),
        (profile.get("new_capability") is False, "profile-no-new-capability"),
        (profile.get("new_architectural_authority") is False, "profile-no-new-authority"),
        (profile.get("capability_count") == 143, "profile-capability-count"),
        (set(profile.get("capability_projection", [])) == {"CAP-005", "CAP-011"}, "profile-capability-projection"),
        (REQUIRED_OBJECTS.issubset(set(profile.get("canonical_objects", []))), "profile-canonical-objects"),
        (REQUIRED_ROUTING.issubset(set(profile.get("routing_policy_modes", []))), "profile-routing-modes"),
        (profile.get("mandatory_invariants", {}).get("silent_local_to_remote_fallback") == "FORBIDDEN", "profile-no-silent-fallback"),
        (contract.get("provider_neutral") is True, "contract-provider-neutral"),
        (contract.get("routing", {}).get("silent_local_to_remote_fallback") == "FORBIDDEN", "contract-no-silent-fallback"),
        (contract.get("discovery_and_trust", {}).get("agents_md_is_trust_authority") is False, "agents-md-not-trust-authority"),
        (contract.get("discovery_and_trust", {}).get("openapi_is_trust_authority") is False, "openapi-not-trust-authority"),
        (contract.get("credentials", {}).get("raw_secret_in_agent_prompt") == "FORBIDDEN", "no-secret-in-prompt"),
        (contract.get("credentials", {}).get("raw_secret_in_canonical_job") == "FORBIDDEN", "no-secret-in-job"),
        (provider.get("id") == "FA3-PROVIDER-HF-SPACES-001", "provider-id"),
        (provider.get("architectural_authority") is False, "provider-no-authority"),
        (provider.get("global_hard_dependency") is False, "provider-no-hard-dependency"),
        (provider.get("automatic_local_fallback_target") is False, "provider-no-auto-fallback"),
        (REQUIRED_ADAPTERS.issubset(set(provider.get("adapter_surfaces", []))), "provider-adapter-surfaces"),
        (provider.get("trust_and_security", {}).get("credential_reference_only") is True, "provider-credential-reference-only"),
        (provider.get("separation_from_hf_model_store", {}).get("must_not_be_collapsed") is True, "provider-model-store-separation"),
        (hf_model_store.get("category") == "model_store" and hf_model_store.get("integration_boundary") == "model_manager_only", "existing-hf-model-store-boundary"),
        (decision.get("new_capabilities") == 0 and decision.get("new_architectural_authorities") == 0 and decision.get("capability_count_after") == 143, "decision-no-authority-or-capability-drift"),
        (gate.get("fail_closed") is True, "gate-fail-closed"),
    ]
    failures.extend(name for ok, name in checks if not ok)

    navigation = desktop_contract.get("navigation_baseline", [])
    if len(navigation) < 2 or navigation[0:2] != ["Command Center", "Remote AI Hub"]:
        failures.append("desktop-navigation-remote-ai-not-featured-second")
    if "REMOTE_AI_HUB_FEATURED_PROJECTION" not in desktop_profile.get("scope", []):
        failures.append("desktop-profile-remote-ai-scope-missing")

    command_pos = qml.find('label: "Command Center"')
    hub_pos = qml.find('label: "Remote AI Hub"')
    projects_pos = qml.find('label: "Projects"')
    if min(command_pos, hub_pos, projects_pos) < 0 or not command_pos < hub_pos < projects_pos:
        failures.append("qml-remote-ai-navigation-not-featured-second")
    for token in [
        "Remote AI Hub",
        "FA3-PROVIDER-HF-SPACES-001",
        "PRIMARY REFERENCE",
        "No silent fallback",
        "CredentialReference",
        "agents.md",
        "OpenAPI",
        "MCP",
    ]:
        if token not in qml:
            failures.append(f"qml-remote-ai-token-missing:{token}")
    if "HF_TOKEN=" in qml or "hf_" in qml.lower():
        failures.append("qml-raw-hf-secret-pattern")

    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("FA3 Remote AI execution gate: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    print("FA3 Remote AI execution gate: PASS")
    print("profile=FA3-REMOTE-AI-EXEC-001 provider=FA3-PROVIDER-HF-SPACES-001 capabilities=143 new_authorities=0 gui=FEATURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
