#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from fa3_gui_current_host import collect as collect_gui
from fa3_model_router_materialize import canonical_provider_ok
from fa3_model_router_provider_execution import (
    CredentialCandidate,
    ExecutionDenied,
    rebind_action,
)
from fa3_terax_gate import resource_admission_valid

REPOSITORY = "ubuntuokos/Final-Architecture-v3.0"
RUNNER_CLASS = "fa3-current-host"
CONFORMANCE_ID = "FA3-GENERATIVE-MEDIA-MESH-CURRENT-HOST-CONFORMANCE-001"
PROBE_MARKER = "FA3_GMM_CURRENT_HOST_PROBE="
AFFECTED_CAPABILITIES = [
    "CAP-005", "CAP-014", "CAP-016", "CAP-041", "CAP-069",
    "CAP-095", "CAP-111", "CAP-112", "CAP-128", "CAP-135",
    "CAP-143", "CAP-148", "CAP-149", "CAP-154", "CAP-156",
    "CAP-159", "CAP-160", "CAP-163", "CAP-166", "CAP-167",
]
SCOPED_REQUALIFICATION_CAPABILITIES = [*AFFECTED_CAPABILITIES, "CAP-175"]

REQUIRED_CHECKS = [
    "AI_STUDIO_GENERATIVE_MEDIA_MESH_PANEL_LOADS_ON_CURRENT_HOST",
    "PANEL_LAYOUT_DOES_NOT_OVERLAP_ADJACENT_AI_STUDIO_CONTROLS",
    "RUNTIME_GATED_STATE_VISIBLE_BEFORE_PROVIDER_ADMISSION",
    "UNADMITTED_HIDREAM_CHILD_PROVIDER_EXECUTION_DENIED",
    "MODEL_ROUTER_REMAINS_SOLE_PROVIDER_MODEL_ROUTING_AUTHORITY",
    "HRB_REMAINS_SOLE_DEVICE_RESOURCE_PLACEMENT_AUTHORITY",
    "CPU_ONLY_OR_INELIGIBLE_PROVIDER_STATE_IS_EXPLICIT_WITHOUT_SILENT_FALLBACK",
    "DISPLAY_GPU_IS_NOT_AUTOMATICALLY_ENROLLED_FOR_AI",
    "ROLLBACK_REMOVES_MESH_UI_BINDING_WITHOUT_TOUCHING_UPSTREAM_APPLICATIONS_OR_USER_PROJECTS",
]


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _git_head(root: Path) -> str:
    import subprocess
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _parse_probe(output_dir: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for name in ("fa3-control-center.stdout.log", "fa3-control-center.stderr.log"):
        path = output_dir / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            pos = line.find(PROBE_MARKER)
            if pos < 0:
                continue
            raw = line[pos + len(PROBE_MARKER):].strip()
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"invalid GMM GUI probe JSON in {name}: {exc}") from exc
            if not isinstance(value, dict):
                raise RuntimeError("GMM GUI probe payload must be an object")
            matches.append(value)
    if len(matches) != 1:
        raise RuntimeError(f"exactly one GMM GUI probe payload required, got {len(matches)}")
    return matches[0]


def _ui_checks(probe: dict[str, Any]) -> dict[str, bool]:
    panel = probe.get("panel") if isinstance(probe.get("panel"), dict) else {}
    execution_policy = str(panel.get("executionPolicyText") or "")
    authority = str(panel.get("authorityText") or "")
    child = str(panel.get("childAdmissionText") or "")
    return {
        "panel_loads": (
            probe.get("pageVisible") is True
            and probe.get("pageMode") == 0
            and probe.get("selectedIndex") == 0
            and probe.get("selectedModule") == "Image"
            and panel.get("panelVisible") is True
            and float(panel.get("panelWidth") or 0) > 0
            and float(panel.get("panelHeight") or 0) > 0
        ),
        "panel_inside_page": probe.get("panelInsidePage") is True,
        "no_adjacent_overlap": probe.get("adjacentOverlap") is False,
        "runtime_gated_visible": (
            panel.get("runtimeGateVisible") is True
            and panel.get("runtimeGateText") == "RUNTIME GATED"
        ),
        "authority_text_visible": (
            panel.get("authorityVisible") is True
            and "Model Router" in authority
            and "HRB" in authority
        ),
        "child_denial_visible": (
            panel.get("childAdmissionVisible") is True
            and "HiDream child providers: not admitted" in child
        ),
        "execution_policy_visible": (
            panel.get("executionPolicyVisible") is True
            and "CPU reference/manual path" in execution_policy
            and "no silent fallback" in execution_policy
            and "display GPU is not auto-enrolled" in execution_policy
        ),
    }


def _runtime_provider_registry(root: Path) -> dict[str, Any]:
    configured = os.environ.get("FA3_MODEL_ROUTER_PROVIDERS", "").strip()
    path = Path(configured).expanduser() if configured else Path.home() / ".config/fa3/model-router/providers.json"
    if not path.is_file():
        return {
            "state": "ABSENT_NO_RUNTIME_PROVIDER_ADMISSION",
            "path": str(path),
            "enabled_provider_ids": [],
            "hidream_enabled": False,
            "all_enabled_bound_to_model_router": True,
        }

    registry = _load(path)
    if registry.get("schema") != "fa3.model-router-runtime-providers.v1":
        raise RuntimeError("current-host runtime provider registry schema mismatch")
    rows = registry.get("providers")
    if not isinstance(rows, list):
        raise RuntimeError("current-host runtime provider registry providers must be a list")
    enabled = []
    for row in rows:
        if not isinstance(row, dict) or row.get("enabled") is not True:
            continue
        provider_id = str(row.get("provider_id") or "").strip()
        if not provider_id:
            raise RuntimeError("enabled runtime provider lacks provider_id")
        enabled.append(provider_id)
    hidream = [provider_id for provider_id in enabled if "hidream" in provider_id.lower()]
    bound = [provider_id for provider_id in enabled if canonical_provider_ok(root, provider_id)]
    return {
        "state": "PRESENT",
        "path": str(path),
        "enabled_provider_ids": sorted(enabled),
        "hidream_enabled": bool(hidream),
        "hidream_provider_ids": sorted(hidream),
        "all_enabled_bound_to_model_router": sorted(bound) == sorted(enabled),
    }


def _boundary_checks(root: Path) -> tuple[dict[str, bool], dict[str, Any]]:
    contract = _load(root / "canonical/contracts/FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001.json")
    hardware = _load(root / "canonical/profiles/FA3-HW-001.json")
    hard_rules = contract.get("hard_rules") if isinstance(contract.get("hard_rules"), dict) else {}
    authorities = contract.get("authority_boundaries") if isinstance(contract.get("authority_boundaries"), dict) else {}

    denial_message = ""
    try:
        CredentialCandidate(
            provider_id="FA3-PROVIDER-HIDREAM-UNADMITTED-CURRENT-HOST-PROBE",
            credential_ref="secretref:gmm-current-host-unadmitted-probe",
            state="HEALTHY",
            admitted_provider=False,
        ).validate()
        unadmitted_denied = False
    except ExecutionDenied as exc:
        denial_message = str(exc)
        unadmitted_denied = "not admitted" in denial_message.lower()

    runtime_registry = _runtime_provider_registry(root)

    cpu_without_hrb_denied = not resource_admission_valid(
        workload_execution_requested=True,
        requested_resource_classes=["CPU"],
        hrb_authorization_present=False,
        accelerator_lease_present=False,
    )
    accelerator_without_lease_denied = not resource_admission_valid(
        workload_execution_requested=True,
        requested_resource_classes=["ACCELERATOR"],
        hrb_authorization_present=True,
        accelerator_lease_present=False,
    )
    display_renderer_does_not_force_compute_lease = resource_admission_valid(
        workload_execution_requested=True,
        requested_resource_classes=["CPU", "DISPLAY_RENDERER"],
        hrb_authorization_present=True,
        accelerator_lease_present=False,
    )

    checks = {
        "unadmitted_hidream_sentinel_denied": unadmitted_denied,
        "no_enabled_hidream_runtime_provider": runtime_registry["hidream_enabled"] is False,
        "model_router_contract_authority": authorities.get("provider_model_routing") == "FA3-AUTH-MODEL-ROUTER-001",
        "all_enabled_runtime_providers_model_router_bound": runtime_registry["all_enabled_bound_to_model_router"] is True,
        "hrb_contract_authority": authorities.get("host_resource_placement") == "FA3-AUTH-HOST-RESOURCE-BROKER-001",
        "hrb_hardware_profile_authority": (
            hardware.get("authority", {}).get("admission_placement_reservation")
            == "FA3-AUTH-HOST-RESOURCE-BROKER-001"
        ),
        "cpu_execution_without_hrb_denied": cpu_without_hrb_denied,
        "accelerator_execution_without_lease_denied": accelerator_without_lease_denied,
        "display_renderer_does_not_auto_create_compute_lease": display_renderer_does_not_force_compute_lease,
        "silent_policy_failure_is_fail_closed": rebind_action("POLICY_DENIED", False) == "FAIL_CLOSED",
        "model_unavailable_requires_router_reevaluation": (
            rebind_action("MODEL_UNAVAILABLE", False) == "MODEL_ROUTER_REEVALUATION_REQUIRED"
        ),
        "silent_provider_model_backend_fallback_forbidden": hard_rules.get("silent_provider_model_backend_fallback") is False,
        "automatic_display_gpu_enrollment_forbidden": hard_rules.get("automatic_display_gpu_enrollment") is False,
        "hidream_children_require_individual_admission": (
            hard_rules.get("child_repo_execution_requires_individual_admission") is True
            and hard_rules.get("org_level_donor_does_not_admit_children") is True
        ),
    }
    details = {
        "unadmitted_hidream_denial_message": denial_message,
        "runtime_provider_registry": runtime_registry,
        "hard_rules": {
            "silent_provider_model_backend_fallback": hard_rules.get("silent_provider_model_backend_fallback"),
            "automatic_display_gpu_enrollment": hard_rules.get("automatic_display_gpu_enrollment"),
            "child_repo_execution_requires_individual_admission": hard_rules.get("child_repo_execution_requires_individual_admission"),
            "org_level_donor_does_not_admit_children": hard_rules.get("org_level_donor_does_not_admit_children"),
        },
        "authority_boundaries": {
            "provider_model_routing": authorities.get("provider_model_routing"),
            "host_resource_placement": authorities.get("host_resource_placement"),
        },
    }
    return checks, details


def _remove_function_block(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise RuntimeError("rollback projection markers not found")
    return text[:start] + text[end:]


def _rollback_projection(root: Path, output_dir: Path) -> dict[str, Any]:
    ai_rel = Path("apps/fa3-control-center/qml/AiStudioPage.qml")
    cmake_rel = Path("apps/fa3-control-center/CMakeLists.txt")
    panel_rel = Path("apps/shared/generative-media/qml/GenerativeMediaMeshPanel.qml")
    ai_path = root / ai_rel
    cmake_path = root / cmake_rel
    panel_path = root / panel_rel
    originals = {str(path): _sha256(root / path) for path in (ai_rel, cmake_rel, panel_rel)}

    ai_text = ai_path.read_text(encoding="utf-8")
    ai_projected = _remove_function_block(
        ai_text,
        "    function _currentHostProbeRect(item) {",
        "    function stateLabel(state) {",
    )
    panel_block = re.compile(
        r"\n\s*GenerativeMediaMeshPanel\s*\{\s*\n"
        r"\s*id:\s*meshPanel\s*\n"
        r"\s*Layout\.fillWidth:\s*true\s*\n"
        r"\s*visible:\s*\[\"Image\",\s*\"Video\",\s*\"Animation\",\s*\"Story / Screenplay\"\]"
        r"\.indexOf\(root\.modules\[root\.selectedIndex\]\.title\)\s*>=\s*0\s*\n"
        r"\s*\}\s*\n",
        re.MULTILINE,
    )
    ai_projected, removed = panel_block.subn("\n", ai_projected, count=1)
    if removed != 1:
        raise RuntimeError("rollback projection failed to remove exactly one mesh UI binding")
    if "GenerativeMediaMeshPanel" in ai_projected or "meshPanel" in ai_projected:
        raise RuntimeError("rollback projection retained mesh UI binding")

    cmake_text = cmake_path.read_text(encoding="utf-8")
    cmake_projected = "\n".join(
        line for line in cmake_text.splitlines()
        if "FA3_GENERATIVE_MEDIA_MESH_PANEL_QML" not in line
    ) + "\n"
    if "GenerativeMediaMeshPanel.qml" in cmake_projected or "FA3_GENERATIVE_MEDIA_MESH_PANEL_QML" in cmake_projected:
        raise RuntimeError("rollback projection retained mesh QML resource registration")

    projected_root = output_dir / "rollback-projection"
    (projected_root / ai_rel.parent).mkdir(parents=True, exist_ok=True)
    (projected_root / cmake_rel.parent).mkdir(parents=True, exist_ok=True)
    (projected_root / ai_rel).write_text(ai_projected, encoding="utf-8")
    (projected_root / cmake_rel).write_text(cmake_projected, encoding="utf-8")

    post = {str(path): _sha256(root / path) for path in (ai_rel, cmake_rel, panel_rel)}
    original_unchanged = originals == post
    projected_files = sorted([str(ai_rel), str(cmake_rel)])
    return {
        "status": "PASS" if original_unchanged else "FAIL",
        "mode": "BOUNDED_NON_MUTATING_ROLLBACK_PROJECTION",
        "projected_files": projected_files,
        "mesh_ui_binding_removed": "GenerativeMediaMeshPanel" not in ai_projected,
        "mesh_resource_registration_removed": "GenerativeMediaMeshPanel.qml" not in cmake_projected,
        "repository_source_files_unchanged": original_unchanged,
        "upstream_applications_touched": False,
        "user_projects_touched": False,
        "source_sha256_before": originals,
        "source_sha256_after": post,
        "projected_ai_studio_sha256": _sha256(projected_root / ai_rel),
        "projected_cmake_sha256": _sha256(projected_root / cmake_rel),
    }


def collect(root: Path, executable: Path, output: Path, smoke_seconds: float) -> dict[str, Any]:
    root = root.resolve()
    executable = executable.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output_dir = output.parent

    expected_source = os.environ.get("FA3_EXPECTED_SOURCE_SHA", "").strip()
    source_commit = _git_head(root)
    if not expected_source or source_commit != expected_source:
        raise RuntimeError(
            f"exact source binding failed: expected={expected_source!r} actual={source_commit!r}"
        )
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise RuntimeError("physical GMM requalification requires exact GitHub repository binding")
    if os.environ.get("FA3_RUNNER_CLASS") != RUNNER_CLASS:
        raise RuntimeError("physical GMM requalification requires fa3-current-host runner class")

    gui_receipt = collect_gui(
        root,
        executable,
        output_dir=output_dir,
        smoke_seconds=smoke_seconds,
        executable_args=("--current-host-gmm-probe",),
    )
    probe = _parse_probe(output_dir)
    ui_checks = _ui_checks(probe)
    boundary_checks, boundary_details = _boundary_checks(root)
    rollback = _rollback_projection(root, output_dir)

    exact_gui_binding = (
        gui_receipt.get("result") == "PASS"
        and gui_receipt.get("source_binding", {}).get("repository_exact") is True
        and gui_receipt.get("source_binding", {}).get("source_commit_exact") is True
        and gui_receipt.get("source_binding", {}).get("source_commit") == source_commit
        and gui_receipt.get("host", {}).get("runner_class") == RUNNER_CLASS
        and gui_receipt.get("current_host_runtime_promotion_claimed") is True
        and gui_receipt.get("global_fa3_promotion_claim") is False
    )

    named_checks = {
        "AI_STUDIO_GENERATIVE_MEDIA_MESH_PANEL_LOADS_ON_CURRENT_HOST":
            exact_gui_binding and ui_checks["panel_loads"] and ui_checks["panel_inside_page"],
        "PANEL_LAYOUT_DOES_NOT_OVERLAP_ADJACENT_AI_STUDIO_CONTROLS":
            exact_gui_binding and ui_checks["no_adjacent_overlap"],
        "RUNTIME_GATED_STATE_VISIBLE_BEFORE_PROVIDER_ADMISSION":
            exact_gui_binding and ui_checks["runtime_gated_visible"] and ui_checks["child_denial_visible"],
        "UNADMITTED_HIDREAM_CHILD_PROVIDER_EXECUTION_DENIED":
            boundary_checks["unadmitted_hidream_sentinel_denied"]
            and boundary_checks["no_enabled_hidream_runtime_provider"]
            and boundary_checks["hidream_children_require_individual_admission"],
        "MODEL_ROUTER_REMAINS_SOLE_PROVIDER_MODEL_ROUTING_AUTHORITY":
            boundary_checks["model_router_contract_authority"]
            and boundary_checks["all_enabled_runtime_providers_model_router_bound"]
            and boundary_checks["model_unavailable_requires_router_reevaluation"],
        "HRB_REMAINS_SOLE_DEVICE_RESOURCE_PLACEMENT_AUTHORITY":
            boundary_checks["hrb_contract_authority"]
            and boundary_checks["hrb_hardware_profile_authority"]
            and boundary_checks["cpu_execution_without_hrb_denied"]
            and boundary_checks["accelerator_execution_without_lease_denied"],
        "CPU_ONLY_OR_INELIGIBLE_PROVIDER_STATE_IS_EXPLICIT_WITHOUT_SILENT_FALLBACK":
            ui_checks["execution_policy_visible"]
            and boundary_checks["silent_policy_failure_is_fail_closed"]
            and boundary_checks["silent_provider_model_backend_fallback_forbidden"],
        "DISPLAY_GPU_IS_NOT_AUTOMATICALLY_ENROLLED_FOR_AI":
            ui_checks["execution_policy_visible"]
            and boundary_checks["automatic_display_gpu_enrollment_forbidden"]
            and boundary_checks["display_renderer_does_not_auto_create_compute_lease"],
        "ROLLBACK_REMOVES_MESH_UI_BINDING_WITHOUT_TOUCHING_UPSTREAM_APPLICATIONS_OR_USER_PROJECTS":
            rollback["status"] == "PASS"
            and rollback["mesh_ui_binding_removed"] is True
            and rollback["mesh_resource_registration_removed"] is True
            and rollback["repository_source_files_unchanged"] is True
            and rollback["upstream_applications_touched"] is False
            and rollback["user_projects_touched"] is False,
    }
    if list(named_checks) != REQUIRED_CHECKS:
        raise RuntimeError("GMM physical check registry drift")

    positive_pass = all(named_checks[name] for name in REQUIRED_CHECKS[:3])
    negative_pass = all(named_checks[name] for name in REQUIRED_CHECKS[3:8])
    rollback_pass = named_checks[REQUIRED_CHECKS[8]]
    result = "PASS" if exact_gui_binding and positive_pass and negative_pass and rollback_pass else "FAIL"

    receipt = {
        "schema": "fa3.generative-media-mesh-current-host-receipt.v1",
        "id": "EVID-FA3-GENERATIVE-MEDIA-MESH-CURRENT-HOST-001",
        "conformance_id": CONFORMANCE_ID,
        "result": result,
        "fail_closed": True,
        "physical_current_host_execution": True,
        "synthetic": False,
        "historical_evidence_reused": False,
        "source_binding": {
            "repository": REPOSITORY,
            "repository_exact": os.environ.get("GITHUB_REPOSITORY") == REPOSITORY,
            "source_commit": source_commit,
            "expected_source_commit": expected_source,
            "source_commit_exact": source_commit == expected_source,
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
        },
        "host": {
            "runner_class": os.environ.get("FA3_RUNNER_CLASS"),
            "gui_host_fingerprint_sha256": gui_receipt.get("host", {}).get("fingerprint_sha256"),
            "session_type": gui_receipt.get("session", {}).get("type"),
            "qpa_platform": gui_receipt.get("session", {}).get("qpa_platform"),
        },
        "capability_scope": {
            "affected_capabilities": AFFECTED_CAPABILITIES,
            "scoped_requalification_capabilities": SCOPED_REQUALIFICATION_CAPABILITIES,
            "capability_baseline": 175,
            "capability_delta": 0,
            "authority_delta": 0,
        },
        "evidence_requirements": {
            "positive": "PASS" if positive_pass else "FAIL",
            "negative": "PASS" if negative_pass else "FAIL",
            "rollback": "PASS" if rollback_pass else "FAIL",
            "exact_head_binding": source_commit == expected_source,
            "physical_current_host": True,
            "synthetic_or_simulated_pass": False,
            "historical_evidence_reused": False,
        },
        "required_checks": named_checks,
        "required_check_count": len(REQUIRED_CHECKS),
        "required_check_pass_count": sum(value is True for value in named_checks.values()),
        "gui_probe": probe,
        "gui_current_host_receipt": gui_receipt,
        "ui_checks": ui_checks,
        "boundary_checks": boundary_checks,
        "boundary_details": boundary_details,
        "rollback": rollback,
        "claims": {
            "runtime_promotion_claim": False,
            "global_promotion_claim": False,
            "provider_admission_claim": False,
            "model_admission_claim": False,
            "hidream_child_admission_claim": False,
        },
    }
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Physical exact-head Current Host requalification for FA3 Generative Media Capability Mesh"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--executable", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--smoke-seconds", type=float, default=8.0)
    args = parser.parse_args()
    receipt = collect(
        Path(args.root),
        Path(args.executable),
        Path(args.output),
        args.smoke_seconds,
    )
    print(json.dumps({
        "result": receipt["result"],
        "source_commit": receipt["source_binding"]["source_commit"],
        "required_check_pass_count": receipt["required_check_pass_count"],
        "required_check_count": receipt["required_check_count"],
        "positive": receipt["evidence_requirements"]["positive"],
        "negative": receipt["evidence_requirements"]["negative"],
        "rollback": receipt["evidence_requirements"]["rollback"],
    }, ensure_ascii=False, indent=2))
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
