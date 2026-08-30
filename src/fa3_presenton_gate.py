#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-PRESENTON-001"
CONTRACT_ID = "FA3-PRESENTON-CONTRACTS-001"
GATE_ID = "FA3-PRESENTON-GATESET-001"
DECISION_ID = "FA3-DEC-PRESENTON-2026-08-30"
REFERENCE_ID = "FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30"
CAPABILITY_COUNT = 143
RELEASE = "v0.9.8-beta"
SOURCE_COMMIT = "88c28f18a63e29742e4922facdba6b95c67959cd"
OCI_INDEX_DIGEST = "sha256:e6866086f2dbdf9f6c50c8f217123cada2a84f4dd03131ad78f397d6fb11b3d1"
OCI_AMD64_DIGEST = "sha256:2db3979c90d70952de075e301f6ba8cac207e5d06fe89e698d5b22101f9074dd"
EVIDENCE_LEVEL = "CURRENT_HOST_PRODUCTION_E2E_PASS"
RECEIPT_PATH = "evidence/receipts/presenton-current-host.json"
MANDATORY_CONSTRAINT = (
    "Presenton SHALL NOT become an FA3 identity, authorization, MCP, workflow, event, "
    "model-routing, host-resource, image-generation, memory, evidence, secrets, "
    "network-egress or artifact-trust authority."
)

P0_INVARIANTS = [
    "PRESENTON_IMMUTABLE_SOURCE_AND_OCI_PIN_REQUIRED",
    "PRESENTON_ROOTLESS_LOOPBACK_ONLY",
    "PRESENTON_AUTHENTICATED_GATEWAY_MEDIATION_REQUIRED",
    "PRESENTON_LITELLM_ONLY_MODEL_ROUTE",
    "PRESENTON_DIRECT_GPU_ACCESS_FORBIDDEN",
    "PRESENTON_COMFYUI_SEPARATE_ADMISSION_REQUIRED",
    "PRESENTON_POSTGRESQL_REQUIRED_SQLITE_FALLBACK_FORBIDDEN",
    "PRESENTON_MEMORY_PRESENTATION_SCOPED_NON_AUTHORITATIVE",
    "PRESENTON_WEB_GROUNDING_AND_TELEMETRY_DISABLED_BY_DEFAULT",
    "PRESENTON_PARALLEL_IMAGE_GENERATION_DISABLED",
    "PRESENTON_UPLOAD_POLICY_AND_LOCAL_REFERENCE_REQUIRED",
    "PRESENTON_ASYNC_EXECUTION_BOUNDED_AND_FAIL_CLOSED",
    "PRESENTON_PPTX_PDF_ARTIFACT_INTEGRITY_AND_LINEAGE_REQUIRED",
    "PRESENTON_SECRETS_EXTERNALIZED",
    "PRESENTON_DISABLED_PROVIDER_ZERO_NEAR_ZERO_RUNTIME_COST",
    "PRESENTON_PROVIDER_NOT_ARCHITECTURAL_AUTHORITY",
]

EXPECTED_BOUNDARIES = {
    "identity": "EXISTING_FA3_IDENTITY_AUTHORITY_ONLY",
    "authorization_policy": "FA3-AUTH-SECURITY-GOV-001",
    "mcp_tool_mediation": "FA3-AUTH-MCP-GATEWAY-001",
    "workflow": "EXISTING_FA3_WORKFLOW_AUTHORITY_ONLY",
    "event": "EXISTING_FA3_EVENT_AUTHORITY_ONLY",
    "model_routing": "EXISTING_FA3_MODEL_ROUTING_AUTHORITY_ONLY",
    "host_resource": "FA3-AUTH-HOST-RESOURCE-BROKER-001",
    "image_generation": "EXISTING_FA3_IMAGE_GENERATION_AUTHORITY_ONLY",
    "memory": "EXISTING_FA3_MEMORY_AUTHORITY_ONLY",
    "evidence": "FA3-AUTH-OBS-EVIDENCE-001",
    "secrets": "EXISTING_FA3_SECRETS_AUTHORITY_ONLY",
    "network_egress": "EXISTING_FA3_NETWORK_EGRESS_AUTHORITY_ONLY",
    "artifact_trust": "FA3-REG-ARTIFACT-MODEL-001",
    "registry": "FA3-REGISTRY-001",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def generation_request_allowed(request: dict[str, Any]) -> bool:
    authorization = request.get("authorization_decision", {})
    references = request.get("file_references", [])
    formats = request.get("export_formats", [])
    return bool(
        request.get("schema") == "fa3.presenton-generation-request.v1"
        and request.get("request_id")
        and request.get("caller_identity")
        and request.get("workspace_id")
        and authorization.get("authority") == "FA3-AUTH-SECURITY-GOV-001"
        and authorization.get("decision") == "ALLOW"
        and "presentation.generate" in authorization.get("capabilities", [])
        and isinstance(request.get("content"), str)
        and request.get("content", "").strip()
        and isinstance(request.get("n_slides"), int)
        and 1 <= request["n_slides"] <= 40
        and request.get("language")
        and set(formats) == {"pptx", "pdf"}
        and request.get("web_search") is False
        and request.get("trigger_webhook") is False
        and all(isinstance(x, str) and x.startswith("artifact://") for x in references)
        and 0 <= int(request.get("source_bytes", 0)) <= 67_108_864
        and request.get("execution_mode") == "ASYNC_BOUNDED"
        and 1 <= int(request.get("timeout_seconds", 0)) <= 3600
    )


def gateway_access_allowed(*, authenticated: bool, via_central_gateway: bool,
                           access_key_scope: str, browser_cookie_used: bool) -> bool:
    return bool(
        authenticated
        and via_central_gateway
        and access_key_scope == "presenton.presentation.generate"
        and not browser_cookie_used
    )


def runtime_config_valid(config: dict[str, Any]) -> bool:
    return bool(
        config.get("rootless") is True
        and config.get("bind") == "127.0.0.1:5001"
        and config.get("image") == f"ghcr.io/presenton/presenton@{OCI_INDEX_DIGEST}"
        and config.get("llm") == "litellm"
        and str(config.get("litellm_base_url", "")).startswith("http://host.containers.internal:4000/")
        and config.get("image_provider") == "comfyui"
        and str(config.get("comfyui_url", "")).startswith("http://host.containers.internal:9876")
        and str(config.get("database_url", "")).startswith("postgresql://")
        and config.get("gpu_devices", []) == []
        and config.get("web_grounding") is False
        and config.get("anonymous_tracking") is False
        and config.get("parallel_image_generation") is False
        and config.get("start_ollama") is False
        and config.get("can_change_keys") is False
        and config.get("memory_scope") == "PRESENTATION_LOCAL_NON_AUTHORITATIVE"
        and config.get("secrets_externalized") is True
    )


def disabled_zero_cost(state: dict[str, Any]) -> bool:
    return bool(
        state.get("resident_process_count") == 0
        and state.get("background_worker_count") == 0
        and state.get("network_session_count") == 0
        and state.get("accelerator_reservation_count") == 0
        and state.get("active_polling") is False
        and state.get("background_fetch") is False
    )


def artifact_bytes_valid(kind: str, data: bytes, *, page_count: int | None = None,
                         rendered_page_count: int | None = None) -> bool:
    if kind == "pptx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as package:
                names = set(package.namelist())
            return "[Content_Types].xml" in names and "ppt/presentation.xml" in names
        except (zipfile.BadZipFile, OSError):
            return False
    if kind == "pdf":
        return bool(
            data.startswith(b"%PDF-")
            and page_count is not None
            and page_count > 0
            and rendered_page_count == page_count
        )
    return False


def provider_shape_valid(provider: dict[str, Any]) -> bool:
    runtime = provider.get("runtime_projection", {})
    return bool(
        provider.get("id") == PROVIDER_ID
        and provider.get("status") == "ACCEPTED_OPTIONAL_PRODUCTION_CANDIDATE"
        and provider.get("canonical_root") is False
        and provider.get("architectural_authority") is False
        and provider.get("new_capability") is False
        and provider.get("capability_count") == CAPABILITY_COUNT
        and provider.get("activation_mode") == "OPTIONAL_DISABLED_BY_DEFAULT"
        and provider.get("global_runtime_promotion_required_when_disabled") is False
        and provider.get("authority_boundaries") == EXPECTED_BOUNDARIES
        and provider.get("normative_constraint") == MANDATORY_CONSTRAINT
        and runtime.get("release") == RELEASE
        and runtime.get("source_commit") == SOURCE_COMMIT
        and runtime.get("linux_amd64_manifest") == OCI_AMD64_DIGEST
        and runtime.get("gpu_access") == "DENIED"
    )


def scan_canonical_authority_assignments(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned = 0

    def walk(obj: Any, field: str, source: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                here = f"{field}.{key}" if field else key
                if isinstance(value, str) and value == PROVIDER_ID and (
                    key == "authority" or key.endswith("_authority")
                ):
                    findings.append(_finding(
                        "PRESENTON-AUTH-001",
                        "Presenton was assigned a prohibited canonical authority role",
                        source=source,
                        field=here,
                    ))
                walk(value, here, source)
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                walk(value, f"{field}[{index}]", source)

    for path in sorted((root / "canonical").rglob("*.json")):
        scanned += 1
        try:
            walk(_load(path), "", str(path.relative_to(root)))
        except Exception as exc:
            findings.append(_finding(
                "PRESENTON-AUTH-002", "Unreadable canonical JSON during authority scan",
                source=str(path.relative_to(root)), error=str(exc),
            ))

    return {
        "result": "PASS" if not findings else "FAIL",
        "scanned_canonical_json_files": scanned,
        "findings": findings,
    }


def reference_check(root: Path) -> dict[str, Any]:
    paths = {
        "provider": root / "canonical/providers/FA3-PROVIDER-PRESENTON-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-PRESENTON-2026-08-30.json",
        "reference": root / "canonical/references/FA3-PRESENTON-UPSTREAM-REFERENCE-2026-08-30.json",
        "contract": root / "canonical/contracts/FA3-PRESENTON-CONTRACTS-001.json",
        "enforcement": root / "canonical/presenton-enforcement.json",
        "policy": root / "canonical/enforcement-policy.json",
        "evidence": root / "evidence/reference/presenton-provider-ci-2026-08-30.json",
        "registry": root / "evidence/evidence-registry.json",
    }
    findings = [
        _finding("PRESENTON-REF-001", f"Missing Presenton artifact: {name}", path=str(path.relative_to(root)))
        for name, path in paths.items() if not path.is_file()
    ]
    if findings:
        return {"result": "FAIL", "findings": findings}

    provider = _load(paths["provider"])
    decision = _load(paths["decision"])
    reference = _load(paths["reference"])
    contract = _load(paths["contract"])
    enforcement = _load(paths["enforcement"])
    policy = _load(paths["policy"])
    evidence = _load(paths["evidence"])
    registry = _load(paths["registry"])

    if not provider_shape_valid(provider):
        findings.append(_finding("PRESENTON-REF-002", "Provider shape, pin or authority boundary drift"))
    if not {"CAP-018", "CAP-030", "CAP-033"}.issubset(set(provider.get("projects_existing_capabilities", []))):
        findings.append(_finding("PRESENTON-REF-003", "Existing capability projection is incomplete"))
    if (
        decision.get("id") != DECISION_ID
        or decision.get("provider_id") != PROVIDER_ID
        or decision.get("gate_id") != GATE_ID
        or decision.get("contract_id") != CONTRACT_ID
        or decision.get("new_capabilities") != 0
        or decision.get("new_architectural_authorities") != 0
        or decision.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(_finding("PRESENTON-REF-004", "Decision invariant mismatch"))
    stable = reference.get("stable_reference", {})
    oci = reference.get("oci_reference", {})
    if (
        reference.get("id") != REFERENCE_ID
        or reference.get("provider_id") != PROVIDER_ID
        or stable.get("release") != RELEASE
        or stable.get("commit_sha") != SOURCE_COMMIT
        or oci.get("index_digest") != OCI_INDEX_DIGEST
        or oci.get("linux_amd64_manifest_digest") != OCI_AMD64_DIGEST
    ):
        findings.append(_finding("PRESENTON-REF-005", "Upstream source or OCI identity drift"))
    if contract.get("id") != CONTRACT_ID or contract.get("canonical_capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("PRESENTON-REF-006", "Typed contract identity/cardinality mismatch"))
    if (
        enforcement.get("gate_id") != GATE_ID
        or enforcement.get("provider_id") != PROVIDER_ID
        or enforcement.get("fail_closed") is not True
        or enforcement.get("mandatory_rule_count") != len(P0_INVARIANTS)
        or enforcement.get("p0_invariants") != P0_INVARIANTS
    ):
        findings.append(_finding("PRESENTON-REF-007", "Enforcement rule set drift"))
    if (
        policy.get("presenton_provider_id") != PROVIDER_ID
        or policy.get("presenton_mandatory_p0_rules") != P0_INVARIANTS
        or GATE_ID not in policy.get("mandatory_reference_gates", [])
    ):
        findings.append(_finding("PRESENTON-REF-008", "Global enforcement policy is not bound to Presenton"))
    cap033 = next((item for item in registry.get("records", []) if item.get("subject_id") == "CAP-033"), {})
    if (
        evidence.get("provider_id") != PROVIDER_ID
        or evidence.get("gate_id") != GATE_ID
        or evidence.get("status") != "PASS"
        or evidence.get("evidence_scope") != "LOCAL_EXECUTABLE_CONFORMANCE_NOT_CURRENT_HOST_PRODUCTION"
        or evidence.get("current_host_production_e2e", {}).get("status") != "PENDING_REAL_CURRENT_HOST_EXECUTION"
        or evidence.get("new_capabilities") != 0
        or evidence.get("new_architectural_authorities") != 0
        or evidence.get("capability_count_after") != CAPABILITY_COUNT
    ):
        findings.append(_finding("PRESENTON-REF-009", "Reference evidence scope or capability invariant mismatch"))
    if (
        "FA3-DEC-PRESENTON-2026-08-30" not in cap033.get("source_decision_ids", [])
        or "evidence/reference/presenton-provider-ci-2026-08-30.json" not in cap033.get("evidence_artifacts", [])
        or cap033.get("status") != "PENDING_CURRENT_HOST"
    ):
        findings.append(_finding("PRESENTON-REF-010", "CAP-033 Evidence Registry projection mismatch"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def deployment_check(root: Path) -> dict[str, Any]:
    paths = {
        "quadlet": root / "deployment/presenton/presenton.container",
        "caddy": root / "deployment/presenton/presenton.caddy",
        "postgres": root / "deployment/presenton/postgresql-bootstrap.sql",
        "runbook": root / "deployment/presenton/README.md",
        "target": root / "deployment/presenton/ai-creative.target",
        "collector": root / "evidence/collect-presenton-current-host.py",
        "wrapper": root / "bin/fa3-presenton-current-host.sh",
    }
    findings = [
        _finding("PRESENTON-DEPLOY-001", f"Missing deployment artifact: {name}")
        for name, path in paths.items() if not path.is_file()
    ]
    if findings:
        return {"result": "FAIL", "findings": findings}

    quadlet = paths["quadlet"].read_text(encoding="utf-8")
    caddy = paths["caddy"].read_text(encoding="utf-8")
    required_quadlet = [
        f"Image=ghcr.io/presenton/presenton@{OCI_INDEX_DIGEST}",
        "PublishPort=127.0.0.1:5001:80",
        "Environment=LLM=litellm",
        "Environment=LITELLM_BASE_URL=http://host.containers.internal:4000/v1",
        "Environment=IMAGE_PROVIDER=comfyui",
        "Environment=COMFYUI_URL=http://host.containers.internal:9876",
        "Environment=MIGRATE_DATABASE_ON_STARTUP=true",
        "Environment=CAN_CHANGE_KEYS=false",
        "Environment=DISABLE_ANONYMOUS_TRACKING=true",
        "Environment=WEB_GROUNDING=false",
        "Environment=START_OLLAMA=false",
        "Environment=ENABLE_PARALLEL_IMAGE_GENERATION=false",
        "Secret=presenton-database-url,type=env,target=DATABASE_URL",
        "NoNewPrivileges=true",
        "DropCapability=ALL",
        "--cpus=8",
        "--memory=16g",
        "--memory-reservation=12g",
        "--pids-limit=2048",
    ]
    missing = [item for item in required_quadlet if item not in quadlet]
    forbidden = [
        item for item in ("Image=ghcr.io/presenton/presenton:latest", "0.0.0.0:5001", "--gpus", "NVIDIA_VISIBLE_DEVICES", "OPENAI_API_KEY=")
        if item in quadlet
    ]
    if missing or forbidden:
        findings.append(_finding(
            "PRESENTON-DEPLOY-002", "Quadlet security/runtime invariant mismatch",
            missing=missing, forbidden=forbidden,
        ))
    if "bind 127.0.0.1" not in caddy or "max_size 64MB" not in caddy or "reverse_proxy 127.0.0.1:5001" not in caddy:
        findings.append(_finding("PRESENTON-DEPLOY-003", "Caddy loopback/upload boundary mismatch"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def executable_regressions() -> dict[str, Any]:
    good_request = {
        "schema": "fa3.presenton-generation-request.v1",
        "request_id": "req-1",
        "caller_identity": "user-1",
        "workspace_id": "workspace-1",
        "authorization_decision": {
            "authority": "FA3-AUTH-SECURITY-GOV-001",
            "decision": "ALLOW",
            "capabilities": ["presentation.generate"],
        },
        "content": "FA3 Presenton conformance",
        "n_slides": 3,
        "language": "hu",
        "export_formats": ["pptx", "pdf"],
        "file_references": ["artifact://source/1"],
        "source_bytes": 1024,
        "web_search": False,
        "trigger_webhook": False,
        "execution_mode": "ASYNC_BOUNDED",
        "timeout_seconds": 600,
    }
    good_runtime = {
        "rootless": True,
        "bind": "127.0.0.1:5001",
        "image": f"ghcr.io/presenton/presenton@{OCI_INDEX_DIGEST}",
        "llm": "litellm",
        "litellm_base_url": "http://host.containers.internal:4000/v1",
        "image_provider": "comfyui",
        "comfyui_url": "http://host.containers.internal:9876",
        "database_url": "postgresql://presenton:redacted@host.containers.internal:5432/presenton",
        "gpu_devices": [],
        "web_grounding": False,
        "anonymous_tracking": False,
        "parallel_image_generation": False,
        "start_ollama": False,
        "can_change_keys": False,
        "memory_scope": "PRESENTATION_LOCAL_NON_AUTHORITATIVE",
        "secrets_externalized": True,
    }
    pptx = io.BytesIO()
    with zipfile.ZipFile(pptx, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("ppt/presentation.xml", "<p:presentation/>")
    cases = [
        ("authorized request", generation_request_allowed(good_request)),
        ("authorization denied", not generation_request_allowed({**good_request, "authorization_decision": {"authority": "FA3-AUTH-SECURITY-GOV-001", "decision": "DENY", "capabilities": ["presentation.generate"]}})),
        ("web search denied", not generation_request_allowed({**good_request, "web_search": True})),
        ("remote file denied", not generation_request_allowed({**good_request, "file_references": ["https://example.invalid/x.pdf"]})),
        ("oversize upload denied", not generation_request_allowed({**good_request, "source_bytes": 67_108_865})),
        ("unbounded timeout denied", not generation_request_allowed({**good_request, "timeout_seconds": 3601})),
        ("gateway auth accepted", gateway_access_allowed(authenticated=True, via_central_gateway=True, access_key_scope="presenton.presentation.generate", browser_cookie_used=False)),
        ("direct access denied", not gateway_access_allowed(authenticated=True, via_central_gateway=False, access_key_scope="presenton.presentation.generate", browser_cookie_used=False)),
        ("runtime accepted", runtime_config_valid(good_runtime)),
        ("sqlite denied", not runtime_config_valid({**good_runtime, "database_url": "sqlite:///app.db"})),
        ("gpu denied", not runtime_config_valid({**good_runtime, "gpu_devices": ["/dev/nvidia0"]})),
        ("direct model route denied", not runtime_config_valid({**good_runtime, "llm": "ollama"})),
        ("pptx package accepted", artifact_bytes_valid("pptx", pptx.getvalue())),
        ("invalid pptx denied", not artifact_bytes_valid("pptx", b"not-a-package")),
        ("pdf render accepted", artifact_bytes_valid("pdf", b"%PDF-1.7\n", page_count=3, rendered_page_count=3)),
        ("disabled zero cost", disabled_zero_cost({"resident_process_count": 0, "background_worker_count": 0, "network_session_count": 0, "accelerator_reservation_count": 0, "active_polling": False, "background_fetch": False})),
    ]
    failed = [name for name, passed in cases if not passed]
    return {
        "result": "PASS" if not failed else "FAIL",
        "passed": len(cases) - len(failed),
        "total": len(cases),
        "failed": failed,
    }


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    reference = reference_check(root)
    deployment = deployment_check(root)
    authority = scan_canonical_authority_assignments(root)
    regressions = executable_regressions()
    findings = reference["findings"] + deployment["findings"] + authority["findings"]
    if regressions["result"] != "PASS":
        findings.append(_finding("PRESENTON-REG-001", "Executable regression case failed", failed=regressions["failed"]))
    report = {
        "schema": "fa3.presenton-gate-report.v1",
        "provider_id": PROVIDER_ID,
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
        "details": {
            "reference": reference["result"],
            "deployment": deployment["result"],
            "authority_scan": authority["result"],
            "executable_regressions": regressions,
            "canonical_capability_count": CAPABILITY_COUNT,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "current_host_production_e2e": "NOT_CLAIMED_BY_STATIC_GATE",
        },
    }
    _write(root / "reports/presenton-gate-report.json", report)
    return report


def current_host_gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    path = root / RECEIPT_PATH
    findings: list[dict[str, Any]] = []
    if not path.is_file():
        findings.append(_finding("PRESENTON-HOST-001", "Presenton current-host receipt is missing"))
        receipt: dict[str, Any] = {}
    else:
        try:
            receipt = _load(path)
        except Exception as exc:
            receipt = {}
            findings.append(_finding("PRESENTON-HOST-002", "Presenton receipt is unreadable", error=str(exc)))

    if receipt:
        if (
            receipt.get("schema") != "fa3.presenton-current-host-receipt.v1"
            or receipt.get("provider_id") != PROVIDER_ID
            or receipt.get("status") != "PASS"
            or receipt.get("evidence_level") != EVIDENCE_LEVEL
            or receipt.get("synthetic") is not False
            or receipt.get("collector_mode") != "REAL_CURRENT_HOST_SERVICE"
        ):
            findings.append(_finding("PRESENTON-HOST-003", "Receipt identity or production evidence level mismatch"))
        deployment = receipt.get("deployment", {})
        required_deployment = (
            "rootless_quadlet_active", "pinned_oci_digest", "loopback_only_bind", "no_gpu_devices",
            "postgresql_backend", "litellm_route", "comfyui_route", "telemetry_disabled",
            "web_grounding_disabled", "parallel_images_disabled", "secrets_externalized",
        )
        if not all(deployment.get(key) is True for key in required_deployment):
            findings.append(_finding("PRESENTON-HOST-004", "Runtime deployment evidence is incomplete"))
        if receipt.get("authentication", {}).get("unauthenticated_request_denied") is not True:
            findings.append(_finding("PRESENTON-HOST-005", "Unauthenticated negative-path evidence missing"))
        generation = receipt.get("generation", {})
        if generation.get("async_status") != "completed" or not generation.get("presentation_id"):
            findings.append(_finding("PRESENTON-HOST-006", "Real asynchronous generation evidence missing"))
        artifacts = receipt.get("artifacts", {})
        for kind in ("pptx", "pdf"):
            ref = artifacts.get(kind, {})
            artifact_path = Path(ref.get("path", ""))
            if not artifact_path.is_file():
                findings.append(_finding("PRESENTON-HOST-007", f"{kind.upper()} artifact missing"))
            elif ref.get("sha256") != _sha256(artifact_path):
                findings.append(_finding("PRESENTON-HOST-008", f"{kind.upper()} artifact digest mismatch"))
            elif ref.get("integrity") != "PASS":
                findings.append(_finding("PRESENTON-HOST-009", f"{kind.upper()} integrity evidence missing"))
        pdf = artifacts.get("pdf", {})
        if not (isinstance(pdf.get("page_count"), int) and pdf.get("page_count", 0) > 0 and pdf.get("rendered_page_count") == pdf.get("page_count") and pdf.get("render_qa") == "PASS"):
            findings.append(_finding("PRESENTON-HOST-010", "PDF render QA evidence mismatch"))

    report = {
        "schema": "fa3.presenton-current-host-gate-report.v1",
        "provider_id": PROVIDER_ID,
        "result": "PASS" if not findings else "FAIL",
        "evidence_level": receipt.get("evidence_level"),
        "blocking_findings": len(findings),
        "findings": findings,
        "promotion_effect": "PROVIDER_SPECIFIC_PRODUCTION_E2E_EVIDENCE_ONLY_GLOBAL_143_CAPABILITY_PROMOTION_UNCHANGED",
    }
    _write(root / "reports/presenton-current-host-gate-report.json", report)
    return report
