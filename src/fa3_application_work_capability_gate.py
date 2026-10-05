#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = {
    "owner_map": "canonical/FA3-APPLICATION-WORK-CAPABILITY-OWNER-MAP-001.json",
    "platform_reconciliation": "canonical/FA3-PLATFORM-BINDING-RECONCILIATION-001.json",
    "consumer_reconciliation": "canonical/FA3-APPLICATION-WORK-CAPABILITY-CONSUMER-RECONCILIATION-001.json",
    "work_semantics": "canonical/contracts/FA3-WORK-MANAGEMENT-SEMANTIC-CONTRACTS-001.json",
    "runtime_lifecycle": "canonical/contracts/FA3-APPLICATION-RUNTIME-LIFECYCLE-CONTRACTS-001.json",
    "grant_scope": "canonical/contracts/FA3-CAPABILITY-GRANT-SCOPE-CONTRACTS-001.json",
    "work_context": "canonical/contracts/FA3-WORK-CONTEXT-CONTRACTS-001.json",
    "blueprint_extension": "canonical/contracts/FA3-AGENT-APPLICATION-BLUEPRINT-EXTENSION-CONTRACTS-001.json",
    "task_capsule": "canonical/contracts/FA3-TASK-CAPSULE-CONTRACTS-001.json",
    "application_handoff": "canonical/contracts/FA3-APPLICATION-OPERATION-HANDOFF-CONTRACTS-001.json",
}
PARENTS = {
    "work_projection": "canonical/FA3-WORK-MANAGEMENT-PROJECTION-001.json",
    "work_item_contract": "canonical/contracts/FA3-WORK-ITEM-PROJECTION-CONTRACTS-001.json",
    "app_lifecycle": "canonical/FA3-APP-LIFECYCLE-001.json",
    "agent_exec": "canonical/contracts/FA3-AGENT-EXEC-CONTRACTS-001.json",
    "blueprint": "canonical/contracts/FA3-AGENT-APPLICATION-BLUEPRINT-CONTRACTS-001.json",
    "agent_workload": "canonical/profiles/FA3-AGENT-WORKLOAD-RUNTIME-001.json",
    "fa3_os": "canonical/profiles/FA3-OS-001.json",
    "uaf": "canonical/profiles/FA3-UNIFIED-ACTION-FABRIC-001.json",
}


SOURCE_INVENTORIES = {
    "application_donor_links": "canonical/FA3-APPLICATION-DONOR-LINKS-001.json",
    "ai_studio_catalog": "canonical/FA3-AI-STUDIO-APP-CATALOG-001.json",
    "application_installation_registry": "canonical/FA3-APPLICATION-INSTALLATION-REGISTRY-001.json",
    "product_family_registry": "canonical/FA3-PRODUCT-FAMILY-REGISTRY-001.json",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path))
    return value


def gate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, str]] = []
    docs: dict[str, dict[str, Any]] = {}

    for name, rel in {**NEW_FILES, **PARENTS, **SOURCE_INVENTORIES}.items():
        path = root / rel
        if not path.is_file():
            findings.append({"code": "AWC-001", "detail": f"missing:{rel}"})
            continue
        try:
            docs[name] = load(path)
        except Exception as exc:
            findings.append({"code": "AWC-002", "detail": f"invalid-json:{rel}:{exc}"})

    for name in NEW_FILES:
        value = docs.get(name)
        if not value:
            continue
        count = value.get("capability_count")
        if count != 175:
            findings.append({"code": "AWC-003", "detail": f"{name}:capability_count={count}"})
        if value.get("new_capability") is not False:
            findings.append({"code": "AWC-004", "detail": f"{name}:new_capability"})
        if value.get("new_architectural_authority") is not False:
            findings.append({"code": "AWC-005", "detail": f"{name}:new_architectural_authority"})
        if value.get("authority") not in (False, None):
            findings.append({"code": "AWC-006", "detail": f"{name}:authority"})

    owner = docs.get("owner_map", {})
    owners = owner.get("owners", {})
    expected = {
        "application_effectful_operation": "FA3-UNIFIED-ACTION-FABRIC-001",
        "work_goal_project_task_truth": "FA3-WORK-MANAGEMENT-PROJECTION-001",
        "work_context_projection": "FA3-OS-001",
        "application_provisioning_lifecycle": "FA3-APP-LIFECYCLE-001",
        "agent_task_local_execution": "FA3-AGENT-WORKLOAD-RUNTIME-001",
        "authorization_and_capability_grant": "FA3-AUTH-SECURITY-GOV-001",
        "model_provider_routing": "FA3-AUTH-MODEL-ROUTER-001",
        "host_resource_admission": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "tool_mcp_mediation": "FA3-AUTH-MCP-GATEWAY-001",
        "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
        "history_activity": "FA3-JOURNAL-001",
        "inter_application_operation_handoff": "FA3-UNIFIED-ACTION-FABRIC-001",
    }
    for key, expected_owner in expected.items():
        actual = owners.get(key, {}).get("owner")
        if actual != expected_owner:
            findings.append({"code": "AWC-007", "detail": f"{key}:{actual}"})

    platform = docs.get("platform_reconciliation", {})
    if platform.get("platform_registry") != "FA3-PLATFORM-001":
        findings.append({"code": "AWC-011", "detail": "platform-registry-binding-drift"})
    for row in platform.get("bindings", []):
        if row.get("service_id") in {"COLLABORATION_FABRIC", "PLUGIN_EXTENSION_FABRIC"} and row.get("state") == "BOUND" and not row.get("canonical_owners") and not row.get("target_owner"):
            findings.append({"code": "AWC-012", "detail": "bound-platform-service-without-owner:" + str(row.get("service_id"))})

    consumer_reconciliation = docs.get("consumer_reconciliation", {})
    source_inventory = consumer_reconciliation.get("source_inventory", {})
    consumers = consumer_reconciliation.get("consumers", [])
    if source_inventory.get("current_scope_count") != len(consumers):
        findings.append({"code": "AWC-013", "detail": "consumer-reconciliation-count-drift"})
    if consumer_reconciliation.get("closure", {}).get("published_main_consumers_without_disposition") != 0:
        findings.append({"code": "AWC-014", "detail": "unreconciled-published-main-consumers"})
    allowed_dispositions = {
        "NO_CHANGE", "GUI_PROJECTION", "CONTRACT_ADAPTER", "SHARED_CAPABILITY_BINDING",
        "LOCAL_TO_SHARED_MIGRATION", "RUNTIME_REQUALIFICATION",
    }
    for row in consumers:
        if row.get("disposition") not in allowed_dispositions:
            findings.append({"code": "AWC-015", "detail": "invalid-consumer-disposition:" + str(row.get("application_id"))})

    consumer_ids = [row.get("application_id") for row in consumers if row.get("application_id")]
    consumer_id_set = set(consumer_ids)
    if len(consumer_ids) != len(consumers) or len(consumer_id_set) != len(consumers):
        findings.append({"code": "AWC-016", "detail": "consumer-identity-missing-or-duplicate"})

    expected_source_ids = {
        "FA3-APPLICATION-DONOR-LINKS-001": {
            row.get("application_id")
            for row in docs.get("application_donor_links", {}).get("applications", [])
            if row.get("application_id")
        },
        "FA3-AI-STUDIO-APP-CATALOG-001": {
            row.get("id")
            for row in docs.get("ai_studio_catalog", {}).get("applications", [])
            if row.get("id")
        },
        "FA3-APPLICATION-INSTALLATION-REGISTRY-001": {
            row.get("application_id")
            for row in docs.get("application_installation_registry", {}).get("applications", [])
            if row.get("application_id")
        },
        "FA3-PRODUCT-FAMILY-REGISTRY-001": {
            row.get("application_id")
            for row in docs.get("product_family_registry", {}).get("application_placements", [])
            if row.get("application_id")
        },
        "REPOSITORY_APPS_DIRECTORY": {
            path.name
            for path in (root / "apps").iterdir()
            if path.is_dir() and path.name != "shared"
        } if (root / "apps").is_dir() else set(),
    }
    source_inventory_bindings = {
        "FA3-APPLICATION-DONOR-LINKS-001": source_inventory.get("application_links"),
        "FA3-AI-STUDIO-APP-CATALOG-001": source_inventory.get("ai_studio_catalog"),
        "FA3-APPLICATION-INSTALLATION-REGISTRY-001": source_inventory.get("application_installation_registry"),
        "FA3-PRODUCT-FAMILY-REGISTRY-001": source_inventory.get("product_family_registry"),
        "REPOSITORY_APPS_DIRECTORY": source_inventory.get("repository_app_directory"),
    }
    coverage_map = consumer_reconciliation.get("source_coverage", {})
    coverage_consumer_ids: set[str] = set()
    if source_inventory.get("repository_app_directory_root") != "apps":
        findings.append({"code": "AWC-027", "detail": "repository-app-root-drift"})
    if source_inventory.get("repository_app_directory_exclusions") != ["shared"]:
        findings.append({"code": "AWC-028", "detail": "repository-app-exclusion-drift"})
    source_inventory_record_count = sum(len(values) for values in expected_source_ids.values())
    for source_id, expected_ids in expected_source_ids.items():
        if source_inventory_bindings.get(source_id) != source_id:
            findings.append({"code": "AWC-017", "detail": "source-inventory-binding-drift:" + source_id})
        rows = coverage_map.get(source_id, [])
        if not isinstance(rows, list):
            findings.append({"code": "AWC-018", "detail": "source-coverage-not-list:" + source_id})
            continue
        actual_source_ids = {
            row.get("source_id")
            for row in rows
            if isinstance(row, dict) and row.get("source_id")
        }
        missing_source_ids = sorted(expected_ids - actual_source_ids)
        extra_source_ids = sorted(actual_source_ids - expected_ids)
        if missing_source_ids or extra_source_ids:
            findings.append({
                "code": "AWC-019",
                "detail": source_id + ":coverage-drift:missing=" + ",".join(missing_source_ids) + ":extra=" + ",".join(extra_source_ids),
            })
        for row in rows:
            if not isinstance(row, dict):
                findings.append({"code": "AWC-020", "detail": "invalid-source-coverage-row:" + source_id})
                continue
            consumer_id = row.get("consumer_id")
            if consumer_id not in consumer_id_set:
                findings.append({"code": "AWC-021", "detail": source_id + ":unknown-consumer:" + str(consumer_id)})
            elif consumer_id:
                coverage_consumer_ids.add(consumer_id)

    if coverage_consumer_ids != consumer_id_set:
        findings.append({
            "code": "AWC-022",
            "detail": "consumer-source-coverage-drift:missing=" + ",".join(sorted(consumer_id_set - coverage_consumer_ids)),
        })
    if source_inventory.get("source_record_count") != source_inventory_record_count:
        findings.append({"code": "AWC-023", "detail": "source-record-count-drift"})
    if source_inventory.get("normalized_consumer_count") != len(consumers):
        findings.append({"code": "AWC-024", "detail": "normalized-consumer-count-drift"})
    if consumer_reconciliation.get("closure", {}).get("source_inventory_records_without_consumer_coverage") != 0:
        findings.append({"code": "AWC-025", "detail": "source-inventory-coverage-not-closed"})
    if consumer_reconciliation.get("closure", {}).get("installation_registry_apps_without_disposition") != 0:
        findings.append({"code": "AWC-026", "detail": "installation-registry-consumer-coverage-not-closed"})

    if consumer_reconciliation.get("closure", {}).get("repository_app_directories_without_disposition") != 0:
        findings.append({"code": "AWC-029", "detail": "repository-app-consumer-coverage-not-closed"})

    if consumer_reconciliation.get("closure", {}).get("product_family_placements_without_disposition") != 0:
        findings.append({"code": "AWC-030", "detail": "product-family-consumer-coverage-not-closed"})

    rules = set(owner.get("anti_cross_layer_rules", []))
    required_rules = {
        "WORK_CONTEXT_REFERENCES_WORK_TRUTH_BUT_DOES_NOT_DUPLICATE_IT",
        "TASK_CAPSULE_COMPOSES_EXISTING_OWNERS_BUT_OWNS_NONE_OF_THEM",
        "NO_SECOND_PERMISSION_AUTHORITY",
        "NO_SECOND_WORKFLOW_AUTHORITY",
    }
    for rule in sorted(required_rules - rules):
        findings.append({"code": "AWC-008", "detail": "missing-rule:" + rule})

    gui_checks = {
        "apps/fa3-control-center/qml/WorkManagementPage.qml": (
            "Goals / Projects / Milestones / Tasks",
            "Check-ins / Risks",
            "New goal",
            "New check-in",
        ),
        "apps/fa3-control-center/qml/AgentActionCenterPage.qml": (
            "Scoped delegation",
            "CapabilityGrant = actor + operation + resource + project/workspace + expiry + approval + budget.",
            "Task Capsule = Agent Workload + Workspace + Blueprint + CapabilityGrant + Work Context.",
        ),
        "apps/fa3-control-center/qml/Fa3OsPage.qml": (
            "Shared Work Context",
            "Reference-only context projection.",
            "Work Context",
        ),
        "apps/fa3-control-center/qml/AiStudioPage.qml": (
            "Application Runtime Lifecycle v2",
            "Runtime control: ADAPTER-GATED",
            "RUNNING",
            "SUSPENDED",
        ),
    }
    for rel, tokens in gui_checks.items():
        path = root / rel
        if not path.is_file():
            findings.append({"code": "AWC-009", "detail": "missing-gui:" + rel})
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                findings.append({"code": "AWC-010", "detail": rel + ":missing-token:" + token})

    return {
        "schema": "fa3.application-work-capability-gate-report.v1",
        "id": "FA3-APPLICATION-WORK-CAPABILITY-GATE-001",
        "result": "PASS" if not findings else "FAIL",
        "fail_closed": True,
        "capability_count": 175,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "current_host_promotion_claim": False,
        "source_inventory_record_count": source_inventory_record_count,
        "normalized_consumer_count": len(consumers),
        "findings": findings,
    }


if __name__ == "__main__":
    report = gate()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
