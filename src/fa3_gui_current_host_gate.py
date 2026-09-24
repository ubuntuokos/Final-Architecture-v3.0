#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count
from fa3_gui_current_host import runtime_surface_git_blobs

GATESET_ID = "FA3-GUI-CURRENT-HOST-GATESET-001"
GATE_RECORD_ID = "FA3-GATE-GUI-CURRENT-HOST-001"
CONFORMANCE_ID = "FA3-GUI-RUNTIME-CONFORMANCE-001"
PROFILE_ID = "FA3-DESKTOP-001"
REPOSITORY = "ubuntuokos/Final-Architecture-v3.0"
CAPABILITY_COUNT = module_active_capability_count(__file__)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")

P0 = [
    "GUI_CURRENT_HOST_EXACT_SELF_HOSTED_RUNNER_LABELS",
    "GUI_CURRENT_HOST_SOURCE_COMMIT_BOUND",
    "GUI_CURRENT_HOST_RUNTIME_SURFACE_GIT_BLOBS_EXACT",
    "GUI_CURRENT_HOST_NON_ROOT_EXECUTION",
    "GUI_CURRENT_HOST_ACTIVE_LOCAL_GRAPHICAL_SESSION_REQUIRED",
    "GUI_CURRENT_HOST_WAYLAND_OR_X11_ONLY",
    "GUI_CURRENT_HOST_DISPLAY_ENDPOINT_PROVEN",
    "GUI_CURRENT_HOST_DESKTOP_RUNTIME_SCOPE_ADMISSION_REQUIRED",
    "GUI_CURRENT_HOST_SAME_SOURCE_QT6_BUILD_REQUIRED",
    "GUI_CURRENT_HOST_NETWORK_FETCH_AND_PACKAGE_INSTALL_FORBIDDEN",
    "GUI_CURRENT_HOST_BINARY_SHA256_REQUIRED",
    "GUI_CURRENT_HOST_NATIVE_QPA_MATCHES_SESSION",
    "GUI_CURRENT_HOST_OFFSCREEN_AND_MINIMAL_FORBIDDEN",
    "GUI_CURRENT_HOST_WEBENGINE_SANDBOX_DISABLE_FORBIDDEN",
    "GUI_CURRENT_HOST_REAL_PROCESS_SURVIVES_SMOKE_WINDOW",
    "GUI_CURRENT_HOST_MINIMUM_SMOKE_WINDOW_5_SECONDS",
    "GUI_CURRENT_HOST_PROCESS_CLEANUP_REQUIRED",
    "GUI_CURRENT_HOST_RECEIPT_SECRET_FREE",
    "GUI_CURRENT_HOST_SECRET_BACKEND_SEPARATE_AUTHORITY_NOT_PROMOTED",
    "GUI_CURRENT_HOST_TESTED_PATH_SECRET_INDEPENDENCE_EXPLICIT",
    "GUI_CURRENT_HOST_PASS_NOT_GLOBAL_FA3_PROMOTION",
    "GUI_CURRENT_HOST_CAPABILITY_AND_AUTHORITY_COUNT_INVARIANT",
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_receipt(receipt: dict[str, Any], *, root: Path | None = None) -> list[str]:
    errors: list[str] = []
    source = receipt.get("source_binding", {})
    host = receipt.get("host", {})
    session = receipt.get("session", {})
    desktop = receipt.get("desktop_admission", {})
    desktop_scope = receipt.get("desktop_runtime_scope", {})
    tested_path = receipt.get("tested_path", {})
    build = receipt.get("build", {})
    launch = receipt.get("launch", {})
    security = receipt.get("security", {})
    checks = receipt.get("checks", {})
    session_type = session.get("type")
    expected_qpa = (
        "wayland" if session_type == "wayland"
        else "xcb" if session_type == "x11"
        else None
    )

    required = [
        (receipt.get("schema") == "fa3.gui-current-host-receipt.v1", "receipt schema drift"),
        (receipt.get("evidence_id") == "EVID-FA3-GUI-CURRENT-HOST-001", "evidence id drift"),
        (receipt.get("gate_id") == GATESET_ID, "receipt gate binding drift"),
        (receipt.get("conformance_id") == CONFORMANCE_ID, "receipt conformance binding drift"),
        (receipt.get("result") == "PASS", "receipt result is not PASS"),
        (receipt.get("fail_closed") is True, "receipt not fail-closed"),
        (source.get("github_actions") is True, "receipt is not GitHub Actions current-host evidence"),
        (
            source.get("repository") == REPOSITORY
            and source.get("repository_exact") is True,
            "repository binding drift",
        ),
        (SHA40.fullmatch(str(source.get("source_commit", ""))) is not None, "source commit invalid"),
        (source.get("source_commit_exact") is True, "source commit not exact"),
        (
            source.get("runtime_surface_policy") == "EXACT_TRACKED_GIT_BLOBS",
            "runtime surface policy drift",
        ),
        (
            isinstance(source.get("runtime_surface_git_blobs"), dict)
            and bool(source.get("runtime_surface_git_blobs")),
            "runtime surface Git-blob map missing",
        ),
        (host.get("runner_class") == "fa3-current-host", "runner class drift"),
        (
            str(host.get("fingerprint_sha256", "")).startswith("sha256:"),
            "hashed host fingerprint missing",
        ),
        (session_type in {"wayland", "x11"}, "unsupported graphical session"),
        (
            session.get("active_local_graphical_session_proven") is True,
            "active local graphical session not proven",
        ),
        (session.get("runtime_dir_proven") is True, "owned XDG runtime not proven"),
        (session.get("user_bus_socket_proven") is True, "user D-Bus not proven"),
        (session.get("display_endpoint_proven") is True, "display endpoint not proven"),
        (session.get("qpa_platform") == expected_qpa, "Qt QPA does not match session"),
        (
            desktop.get("mode") == "LOCAL_GUI",
            "desktop admission is not local GUI observation",
        ),
        (
            desktop_scope.get("result") == "PASS",
            "GUI desktop runtime scoped admission not PASS",
        ),
        (
            desktop_scope.get("secret_backend_used_for_gui_runtime_admission") is False,
            "GUI runtime scope improperly depends on Secret Backend",
        ),
        (
            desktop_scope.get("secret_backend_required_for_tested_path") is False
            and receipt.get("secret_backend_required_for_tested_path") is False,
            "tested GUI path unexpectedly requires Secret Backend",
        ),
        (
            desktop_scope.get("secret_backend_authority") == "AUTH-SECRETS"
            and receipt.get("secret_backend_authority") == "AUTH-SECRETS",
            "Secret Backend authority ownership drift",
        ),
        (
            desktop_scope.get("secret_backend_capability") == "CAP-003"
            and receipt.get("secret_backend_capability") == "CAP-003"
            and desktop_scope.get("secrets_authority_owner") == "CAP-003",
            "Secret Backend capability ownership drift",
        ),
        (
            desktop_scope.get("secret_backend_pass_claimed") is False
            and receipt.get("secret_backend_pass_claimed") is False,
            "GUI receipt falsely claims Secret Backend PASS",
        ),
        (
            receipt.get("secret_backend_status")
            == desktop_scope.get("secret_backend_status")
            == desktop.get("capabilities", {}).get("secret_backend"),
            "Secret Backend status is not faithfully projected",
        ),
        (
            tested_path.get("id") == "CONTROL_CENTER_STARTUP_SESSION_VAULT_UNCONFIGURED"
            and tested_path.get("secret_dependency") == "NONE"
            and tested_path.get("session_vault_configuration") == "NOT_CONFIGURED"
            and tested_path.get("session_vault_image_present_before_launch") is False
            and tested_path.get("session_vault_image_present_after_launch") is False
            and tested_path.get("secret_lookup_required") is False,
            "tested GUI path is not proven secret-independent",
        ),
        (
            not (
                desktop.get("result") == "FAIL"
                and desktop_scope.get("full_desktop_required_failures") != ["secret_backend"]
            ),
            "full desktop failure exceeds separately-owned Secret Backend scope",
        ),
        (build.get("status") == "PASS", "same-source Qt build not PASS"),
        (
            SHA64.fullmatch(str(build.get("binary_sha256", ""))) is not None,
            "binary SHA-256 missing",
        ),
        (launch.get("attempted") is True, "GUI process not launched"),
        (launch.get("qpa_platform") == expected_qpa, "launch QPA mismatch"),
        (
            launch.get("process_alive_after_smoke") is True,
            "GUI process did not survive smoke window",
        ),
        (
            float(launch.get("observed_runtime_seconds", 0.0)) >= 5.0,
            "smoke window below five seconds",
        ),
        (
            launch.get("terminated_by_probe") is True
            and launch.get("cleanup_completed") is True,
            "probe cleanup incomplete",
        ),
        (
            launch.get("fatal_qt_startup_marker_absent") is True,
            "fatal Qt/QML startup marker observed",
        ),
        (security.get("root_execution") is False, "root GUI execution claimed"),
        (security.get("sudo_or_pkexec_used") is False, "privilege bypass used"),
        (
            security.get("package_install_or_network_fetch_used") is False,
            "current-host job installed/fetched dependencies",
        ),
        (
            security.get("webengine_sandbox_disabled") is False,
            "WebEngine sandbox disabled",
        ),
        (
            security.get("offscreen_or_minimal_platform_used") is False,
            "synthetic Qt platform used",
        ),
        (
            security.get("secret_material_recorded") is False,
            "receipt may contain secret material",
        ),
        (
            security.get("secret_backend_promoted_by_gui_receipt") is False,
            "GUI receipt falsely promotes Secret Backend",
        ),
        (
            checks.get("secret_independent_tested_path") is True,
            "secret-independent tested-path check not PASS",
        ),
        (bool(checks) and all(checks.values()), "receipt P0 check set not all PASS"),
        (receipt.get("capability_count") == CAPABILITY_COUNT, "capability count drift"),
        (receipt.get("new_capabilities") == 0, "new capability introduced"),
        (
            receipt.get("new_architectural_authorities") == 0,
            "new authority introduced",
        ),
        (
            receipt.get("gui_runtime_promotion_eligible") is True,
            "GUI runtime promotion not eligible",
        ),
        (
            receipt.get("current_host_runtime_promotion_claimed") is True,
            "GUI current-host runtime PASS not claimed",
        ),
        (
            receipt.get("global_fa3_promotion_claim") is False,
            "GUI receipt falsely claims global FA3 promotion",
        ),
    ]
    for ok, message in required:
        if not ok:
            errors.append(message)
    if root is not None:
        current_surface = runtime_surface_git_blobs(root.resolve())
        if not current_surface:
            errors.append("current runtime surface could not be enumerated")
        elif source.get("runtime_surface_git_blobs") != current_surface:
            errors.append("runtime surface Git-blob map is stale or mismatched")
    return errors


def report(root: Path, errors: list[str], evidence_state: str) -> dict[str, Any]:
    value = {
        "schema": "fa3.gui-current-host-gate-report.v1",
        "gate_id": GATESET_ID,
        "result": "PASS" if not errors else "FAIL",
        "finding_count": len(errors),
        "findings": errors,
        "runtime_evidence_status": evidence_state,
        "capability_count": CAPABILITY_COUNT,
        "new_capabilities": 0,
        "new_architectural_authorities": 0,
        "global_fa3_promotion_claim": False,
    }
    out = root / "reports/gui-current-host-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return value


def gate(
    root: Path,
    *,
    receipt_path: Path | None = None,
    require_evidence: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    paths = {
        "conformance": root / "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
        "gate": root / "canonical/FA3-GATE-GUI-CURRENT-HOST-001.json",
        "enforcement": root / "canonical/gui-current-host-enforcement.json",
        "workflow": root / ".github/workflows/fa3-gui-current-host.yml",
        "runtime": root / "src/fa3_gui_current_host.py",
        "collector": root / "evidence/collect-gui-current-host.py",
        "current_host_manifest": root / "fa3-current-host/manifest.json",
    }
    errors: list[str] = []
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"missing {name}: {path.relative_to(root)}")
    if errors:
        return report(root, errors, "MATERIALIZATION_INCOMPLETE")

    conformance = load(paths["conformance"])
    gate_record = load(paths["gate"])
    enforcement = load(paths["enforcement"])
    workflow = paths["workflow"].read_text(encoding="utf-8")
    runtime_text = paths["runtime"].read_text(encoding="utf-8")
    collector_text = paths["collector"].read_text(encoding="utf-8")
    current_host_manifest = load(paths["current_host_manifest"])

    if not (
        conformance.get("id") == CONFORMANCE_ID
        and conformance.get("profile_id") == PROFILE_ID
        and conformance.get("required_evidence_level")
        == "CURRENT_HOST_ADMITTED_DESKTOP_SESSION_RUNTIME_PASS"
        and conformance.get("current_host_gate_id") == GATESET_ID
        and conformance.get("current_host_workflow")
        == ".github/workflows/fa3-gui-current-host.yml"
        and conformance.get("current_host_collector")
        == "evidence/collect-gui-current-host.py"
        and conformance.get("new_capabilities") == 0
        and conformance.get("new_architectural_authorities") == 0
        and conformance.get("capability_count_after") == CAPABILITY_COUNT
    ):
        errors.append("GUI current-host conformance governance drift")

    pending = (
        conformance.get("status")
        == "EXECUTABLE_CURRENT_HOST_CLOSURE_MATERIALIZED_PENDING_RUN"
        and conformance.get("production_admitted") is False
        and conformance.get("current_host_receipt_present") is False
        and set(conformance.get("promotion_blockers", []))
        == {
            "CURRENT_HOST_QT6_BUILD_RECEIPT_MISSING",
            "CURRENT_HOST_ADMITTED_WAYLAND_OR_X11_INTERACTIVE_SMOKE_RECEIPT_MISSING",
        }
    )
    promoted = (
        conformance.get("status") == "CURRENT_HOST_PASS"
        and conformance.get("production_admitted") is True
        and conformance.get("current_host_receipt_present") is True
        and conformance.get("promotion_blockers") == []
        and SHA40.fullmatch(str(conformance.get("tested_source_commit", ""))) is not None
        and conformance.get("admission_scope") == "GUI_CONTROL_CENTER_PROCESS_RUNTIME_ONLY"
        and conformance.get("secret_backend_admission") == "FAIL_SEPARATE_AUTHORITY_NOT_PROMOTED"
    )
    if not (pending or promoted):
        errors.append(
            "GUI current-host state is neither fail-closed pending nor evidence-promoted PASS"
        )

    session_vault_cpp_path = root / "apps/fa3-control-center/src/SessionVaultService.cpp"
    main_cpp_path = root / "apps/fa3-control-center/src/main.cpp"
    if not session_vault_cpp_path.is_file() or not main_cpp_path.is_file():
        errors.append("Control Center Session Vault startup source missing")
    else:
        session_vault_cpp = session_vault_cpp_path.read_text(encoding="utf-8")
        main_cpp = main_cpp_path.read_text(encoding="utf-8")
        guard = "if (!configured() || m_unlocked)"
        secret_lookup = 'p.start(QStringLiteral("secret-tool")'
        if not (
            "SessionVaultService sessionVault;" in main_cpp
            and "QTimer::singleShot(0, this, [this]() { tryAutoUnlock(); });" in session_vault_cpp
            and guard in session_vault_cpp
            and secret_lookup in session_vault_cpp
            and session_vault_cpp.index(guard) < session_vault_cpp.index(secret_lookup)
        ):
            errors.append("secret-independent Session Vault startup guard drift")

    required_manifest_paths = {
        ".github/workflows/fa3-gui-current-host.yml",
        "canonical/FA3-GUI-RUNTIME-CONFORMANCE-001.json",
        "canonical/FA3-GATE-GUI-CURRENT-HOST-001.json",
        "canonical/gui-current-host-enforcement.json",
        "docs/FA3-GUI-CURRENT-HOST-CLOSURE-001.md",
        "evidence/collect-gui-current-host.py",
        "src/fa3_gui_current_host.py",
        "src/fa3_gui_current_host_gate.py",
        "tests/test_fa3_gui_current_host.py",
    }
    manifest_required = set(current_host_manifest.get("required_repository_paths", []))
    gui_surface = next(
        (
            item
            for item in current_host_manifest.get("registered_current_host_surfaces", [])
            if item.get("name") == "gui-control-center"
        ),
        {},
    )
    expected_collection_status = (
        "REAL_CURRENT_HOST_PASS_GUI_PROCESS_RUNTIME_ONLY"
        if promoted
        else "EXECUTABLE_CLOSURE_MATERIALIZED_REAL_EXECUTION_PENDING"
    )
    if not required_manifest_paths.issubset(manifest_required):
        errors.append(
            "current-host manifest missing GUI closure repository paths: "
            + ",".join(sorted(required_manifest_paths - manifest_required))
        )
    if not (
        gui_surface.get("collector") == "evidence/collect-gui-current-host.py"
        and gui_surface.get("gate") == "gui-current-host"
        and gui_surface.get("workflow") == ".github/workflows/fa3-gui-current-host.yml"
        and gui_surface.get("receipt") == "evidence/receipts/fa3-gui-current-host.json"
        and gui_surface.get("collection_status") == expected_collection_status
        and gui_surface.get("production_runtime_promoted") is promoted
        and gui_surface.get("global_promotion_claim") is False
        and gui_surface.get("secret_backend_authority_owner") == "CAP-003"
    ):
        errors.append("current-host manifest GUI surface binding drift")

    if not (
        gate_record.get("id") == GATE_RECORD_ID
        and gate_record.get("gateset_id") == GATESET_ID
        and gate_record.get("conformance_id") == CONFORMANCE_ID
        and gate_record.get("profile_id") == PROFILE_ID
        and gate_record.get("priority") == "P0"
        and gate_record.get("fail_closed") is True
        and gate_record.get("mandatory_rule_count") == len(P0)
        and gate_record.get("p0_invariants") == P0
        and gate_record.get("new_capabilities") == 0
        and gate_record.get("new_architectural_authorities") == 0
        and gate_record.get("capability_count_after") == CAPABILITY_COUNT
    ):
        errors.append("GUI current-host gate record drift")

    if not (
        enforcement.get("id") == GATESET_ID
        and enforcement.get("gate_record_id") == GATE_RECORD_ID
        and enforcement.get("conformance_id") == CONFORMANCE_ID
        and enforcement.get("fail_closed") is True
        and enforcement.get("mandatory_rule_count") == len(P0)
        and enforcement.get("p0_invariants") == P0
    ):
        errors.append("GUI current-host enforcement drift")

    workflow_tokens = [
        "workflow_dispatch:",
        "pull_request:",
        "runs-on: [self-hosted, linux, x64, fa3-current-host]",
        "github.event.pull_request.head.repo.full_name == github.repository",
        "FA3_RUNNER_CLASS: fa3-current-host",
        "FA3_EXPECTED_SOURCE_SHA:",
        "cmake -S apps/fa3-control-center",
        "cmake --build",
        "evidence/collect-gui-current-host.py",
        "--require-evidence",
        "fa3-gui-current-host-evidence",
    ]
    for token in workflow_tokens:
        if token not in workflow:
            errors.append(f"current-host workflow missing: {token}")
    for forbidden in (
        "sudo ",
        "pkexec ",
        "apt-get ",
        "dnf ",
        "pacman ",
        "zypper ",
        "curl ",
        "wget ",
    ):
        if forbidden in workflow:
            errors.append(
                f"current-host workflow contains forbidden mutation/fetch token: {forbidden.strip()}"
            )

    for token in (
        "discover_current_user_session_environment",
        "evaluate_desktop",
        "gui_desktop_runtime_scoped_admission",
        "GUI_PROCESS_RUNTIME_PROOF_NOT_SECRET_BACKEND_ADMISSION",
        "QT_QPA_PLATFORM",
        '"wayland"',
        '"xcb"',
        '"offscreen"',
        '"minimal"',
        "QTWEBENGINE_DISABLE_SANDBOX",
        "process_alive_after_smoke",
        "global_fa3_promotion_claim",
    ):
        if token not in runtime_text:
            errors.append(f"runtime collector contract missing: {token}")
    if "collect(" not in collector_text or "fa3_gui_current_host" not in collector_text:
        errors.append("collector entrypoint drift")

    evidence_state = "PENDING_CURRENT_HOST"
    candidate = receipt_path
    if candidate is None and promoted:
        candidate = root / str(conformance.get("current_host_receipt"))

    if candidate is not None:
        if not candidate.is_absolute():
            candidate = root / candidate
        if not candidate.is_file():
            errors.append(f"current-host receipt missing: {candidate}")
        else:
            receipt = load(candidate)
            receipt_errors = validate_receipt(receipt, root=root)
            errors.extend(f"receipt: {item}" for item in receipt_errors)
            evidence_state = "PASS" if not receipt_errors else "FAIL"
            if promoted and receipt_path is None and not receipt_errors:
                if (
                    conformance.get("tested_source_commit")
                    != receipt.get("source_binding", {}).get("source_commit")
                ):
                    errors.append(
                        "promoted conformance source commit does not match canonical receipt"
                    )
    elif require_evidence:
        errors.append("current-host evidence required but no receipt was supplied")

    return report(root, errors, evidence_state)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="FA3 GUI current-host materialization and evidence gate"
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--receipt")
    parser.add_argument("--require-evidence", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    receipt = Path(args.receipt) if args.receipt else None
    result = gate(root, receipt_path=receipt, require_evidence=args.require_evidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
