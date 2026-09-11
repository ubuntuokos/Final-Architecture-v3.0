#!/usr/bin/env python3
"""Executable reference policy for FA3 OpenFX host/plugin admission.

This module validates typed execution and provenance receipts.  It does not
load native OFX binaries and therefore cannot create current-host evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Callable


ALLOWED_BACKENDS = ("CPU", "CUDA", "OPENCL", "METAL")
REFERENCE_STANDARD_VERSION = "1.5.1"
REFERENCE_STANDARD_COMMIT = "ab779510b2655b4d11a7e01e5c521f9aa8c88976"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PCI_BDF_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _version(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError):
        return ()


def reference_execution() -> dict[str, Any]:
    input_sha = _sha("fa3-openfx-golden-input-v1")
    plugin_sha = _sha("fa3-openfx-admitted-plugin-v1")
    ocio_sha = _sha("fa3-openfx-ocio-config-v1")
    output_sha = _sha("fa3-openfx-golden-output-v1")
    return {
        "schema": "fa3.openfx-execution-receipt.v1",
        "host": {
            "provider_id": "FA3-PROVIDER-REFERENCE-OPENFX-HOST-TEST-ONLY",
            "version": "1.0.0",
            "observed_openfx_api_version": "1.5.1",
            "observed_suites": [
                "core",
                "property",
                "image_effect",
                "parameter",
                "memory",
                "message",
                "multithread",
                "colour_management",
                "cuda_render",
            ],
            "admitted": True,
            "worker_isolation": "DEDICATED_PROCESS",
            "network_policy": "DENY",
            "plugin_search_path_policy": "ADMITTED_DIRECTORIES_ONLY",
        },
        "plugin": {
            "plugin_id": "org.fa3.reference.invert",
            "version": "1.0.0",
            "binary_sha256": plugin_sha,
            "allowlisted": True,
            "source_identity": "reference-fixture://openfx/invert/1.0.0",
            "release_identity": "reference-fixture-v1",
            "license_spdx": "BSD-3-Clause",
            "dependency_inventory_present": True,
            "sbom_present": True,
            "malware_behavior_scan": "PASS",
            "signature_or_exception_receipt": "VERIFIED",
            "automatic_install_or_update": False,
            "execution_class": "UNTRUSTED_NATIVE_CODE",
        },
        "effect": {
            "identifier": "org.fa3.reference.invert",
            "required_openfx_api_version": "1.5.1",
            "required_suites": ["core", "property", "image_effect", "parameter", "cuda_render"],
            "parameter_digest": _sha("amount=1.0"),
        },
        "job": {
            "input_sha256": input_sha,
            "frame_range": {"start": 1, "end": 1},
            "timebase": "24/1",
            "output_format": "EXR_RGBA_F32",
            "workspace_policy": "CONTENT_ADDRESSED_INPUT_READONLY_OUTPUT_STAGING_WRITEONLY",
            "direct_host_project_mutation": False,
        },
        "color": {
            "input_space": "ACEScg",
            "working_space": "ACEScg",
            "output_space": "ACEScg",
            "management": "OCIO",
            "ocio_config_sha256": ocio_sha,
        },
        "resource": {
            "requested_backend": "CUDA",
            "observed_backend": "CUDA",
            "fallback_policy": "FAIL_CLOSED",
            "hrb_lease": {
                "lease_id": "lease-reference-openfx-001",
                "device_uuid": "GPU-reference-uuid",
                "pci_bdf": "0000:05:00.0",
                "role": "COMPUTE",
                "runtime_ordinal": 0,
                "runtime_ordinal_is_canonical": False,
            },
        },
        "result": {
            "status": "PASS",
            "effect_identifier": "org.fa3.reference.invert",
            "input_sha256": input_sha,
            "plugin_binary_sha256": plugin_sha,
            "requested_backend": "CUDA",
            "observed_backend": "CUDA",
            "color_binding_sha256": _sha(f"ACEScg:ACEScg:ACEScg:{ocio_sha}"),
            "output_sha256": output_sha,
            "frame_checksums": {"1": output_sha},
            "finite_pixel_qc": "PASS",
            "alpha_qc": "PASS",
            "worker_crashed": False,
            "partial_output_promoted": False,
            "source_project_unchanged": True,
            "rollback_and_unload_receipt": "PASS",
            "lineage_complete": True,
        },
        "claim_scope": {
            "reference_policy_execution": True,
            "real_openfx_binary_executed": False,
            "current_host_runtime_evidence": False,
            "production_promotion": False,
        },
    }


def validate_execution(candidate: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def require(code: str, condition: bool, message: str) -> None:
        if not condition:
            findings.append({"code": code, "message": message})

    host = candidate.get("host", {})
    plugin = candidate.get("plugin", {})
    effect = candidate.get("effect", {})
    job = candidate.get("job", {})
    color = candidate.get("color", {})
    resource = candidate.get("resource", {})
    result = candidate.get("result", {})
    scope = candidate.get("claim_scope", {})
    host_version = _version(host.get("observed_openfx_api_version", ""))
    required_version = _version(effect.get("required_openfx_api_version", ""))
    host_suites = set(host.get("observed_suites", []))
    required_suites = set(effect.get("required_suites", []))

    require("OFX-R-001", candidate.get("schema") == "fa3.openfx-execution-receipt.v1", "typed receipt schema mismatch")
    require("OFX-R-002", host.get("admitted") is True, "host is not admitted")
    require("OFX-R-003", host.get("worker_isolation") == "DEDICATED_PROCESS", "dedicated worker isolation missing")
    require("OFX-R-004", host.get("network_policy") == "DENY", "worker network policy is not deny")
    require("OFX-R-005", host.get("plugin_search_path_policy") == "ADMITTED_DIRECTORIES_ONLY", "plugin discovery is not allowlist-scoped")
    require("OFX-R-006", bool(host_version) and bool(required_version) and host_version >= required_version, "host API version does not satisfy effect requirement")
    require("OFX-R-007", required_suites.issubset(host_suites), "required OpenFX suite is unavailable")

    require("OFX-R-008", plugin.get("execution_class") == "UNTRUSTED_NATIVE_CODE", "plugin is not classified as untrusted native code")
    require("OFX-R-009", bool(SHA256_RE.fullmatch(plugin.get("binary_sha256", ""))), "plugin digest is not immutable SHA-256")
    require("OFX-R-010", plugin.get("allowlisted") is True, "plugin digest is not allowlisted")
    require("OFX-R-011", bool(plugin.get("source_identity")) and bool(plugin.get("release_identity")), "source or release identity missing")
    require("OFX-R-012", bool(plugin.get("license_spdx")) and plugin.get("dependency_inventory_present") is True and plugin.get("sbom_present") is True, "license/dependency/SBOM inventory incomplete")
    require("OFX-R-013", plugin.get("malware_behavior_scan") == "PASS", "plugin security scan did not pass")
    require("OFX-R-014", plugin.get("signature_or_exception_receipt") in {"VERIFIED", "APPROVED_EXCEPTION"}, "signature or explicit exception receipt missing")
    require("OFX-R-015", plugin.get("automatic_install_or_update") is False, "automatic plugin install/update is forbidden")

    require("OFX-R-016", bool(SHA256_RE.fullmatch(job.get("input_sha256", ""))), "content-addressed input missing")
    frame_range = job.get("frame_range", {})
    require("OFX-R-017", isinstance(frame_range.get("start"), int) and isinstance(frame_range.get("end"), int) and frame_range.get("start", 1) <= frame_range.get("end", 0) and bool(job.get("timebase")), "frame range or timebase invalid")
    require("OFX-R-018", job.get("workspace_policy") == "CONTENT_ADDRESSED_INPUT_READONLY_OUTPUT_STAGING_WRITEONLY", "workspace is not read-only-input/staged-output")
    require("OFX-R-019", job.get("direct_host_project_mutation") is False, "direct host-project mutation is forbidden")

    require("OFX-R-020", all(bool(color.get(key)) for key in ("input_space", "working_space", "output_space")), "explicit color spaces missing")
    require("OFX-R-021", color.get("management") != "OCIO" or bool(SHA256_RE.fullmatch(color.get("ocio_config_sha256", ""))), "OCIO configuration digest missing")

    requested = resource.get("requested_backend")
    observed = resource.get("observed_backend")
    require("OFX-R-022", requested in ALLOWED_BACKENDS, "requested backend is unsupported")
    require("OFX-R-023", requested == observed, "requested and observed backend differ")
    require("OFX-R-024", resource.get("fallback_policy") == "FAIL_CLOSED", "silent backend fallback is enabled")
    if requested != "CPU":
        lease = resource.get("hrb_lease", {})
        require("OFX-R-025", bool(lease.get("lease_id")) and bool(lease.get("device_uuid")) and bool(PCI_BDF_RE.fullmatch(lease.get("pci_bdf", ""))), "accelerator execution lacks stable HRB lease identity")
        require("OFX-R-026", lease.get("role") == "COMPUTE", "display or non-compute accelerator lease is forbidden")
        require("OFX-R-027", lease.get("runtime_ordinal_is_canonical") is False, "runtime ordinal became canonical accelerator identity")

    expected_color_sha = _sha(
        f"{color.get('input_space', '')}:{color.get('working_space', '')}:"
        f"{color.get('output_space', '')}:{color.get('ocio_config_sha256', '')}"
    )
    require("OFX-R-028", result.get("status") == "PASS" and result.get("effect_identifier") == effect.get("identifier"), "render result identity/status mismatch")
    require("OFX-R-029", result.get("input_sha256") == job.get("input_sha256") and result.get("plugin_binary_sha256") == plugin.get("binary_sha256"), "render input/plugin lineage mismatch")
    require("OFX-R-030", result.get("requested_backend") == requested and result.get("observed_backend") == observed, "render backend receipt mismatch")
    require("OFX-R-031", result.get("color_binding_sha256") == expected_color_sha, "render color binding mismatch")
    require("OFX-R-032", bool(SHA256_RE.fullmatch(result.get("output_sha256", ""))) and bool(result.get("frame_checksums")), "output or frame checksums missing")
    require("OFX-R-033", result.get("finite_pixel_qc") == "PASS" and result.get("alpha_qc") == "PASS", "pixel or alpha QC failed")
    require("OFX-R-034", result.get("worker_crashed") is False and result.get("partial_output_promoted") is False, "crash containment or partial-output rule failed")
    require("OFX-R-035", result.get("source_project_unchanged") is True and result.get("rollback_and_unload_receipt") == "PASS" and result.get("lineage_complete") is True, "project safety, rollback or lineage receipt missing")
    require("OFX-R-036", scope.get("reference_policy_execution") is True and scope.get("real_openfx_binary_executed") is False and scope.get("current_host_runtime_evidence") is False and scope.get("production_promotion") is False, "reference policy overclaims runtime evidence")

    return {
        "schema": "fa3.openfx-execution-validation.v1",
        "result": "PASS" if not findings else "FAIL",
        "blocking_findings": len(findings),
        "findings": findings,
    }


def _mutate(path: tuple[str, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(candidate: dict[str, Any]) -> None:
        node = candidate
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return apply


def _make_cpu_case(candidate: dict[str, Any]) -> None:
    candidate["resource"].update(
        requested_backend="CPU",
        observed_backend="CPU",
        hrb_lease=None,
    )
    candidate["result"].update(
        requested_backend="CPU",
        observed_backend="CPU",
    )


def run_reference_conformance() -> dict[str, Any]:
    cases: list[tuple[str, str, Callable[[dict[str, Any]], None] | None]] = [
        ("valid_cuda", "PASS", None),
        ("valid_cpu", "PASS", _make_cpu_case),
        ("schema_mismatch", "FAIL", _mutate(("schema",), "invalid")),
        ("host_unadmitted", "FAIL", _mutate(("host", "admitted"), False)),
        ("worker_not_isolated", "FAIL", _mutate(("host", "worker_isolation"), "IN_PROCESS")),
        ("network_enabled", "FAIL", _mutate(("host", "network_policy"), "ALLOW")),
        ("plugin_digest_missing", "FAIL", _mutate(("plugin", "binary_sha256"), "")),
        ("plugin_not_allowlisted", "FAIL", _mutate(("plugin", "allowlisted"), False)),
        ("sbom_missing", "FAIL", _mutate(("plugin", "sbom_present"), False)),
        ("security_scan_failed", "FAIL", _mutate(("plugin", "malware_behavior_scan"), "FAIL")),
        ("signature_unverified", "FAIL", _mutate(("plugin", "signature_or_exception_receipt"), "MISSING")),
        ("automatic_update", "FAIL", _mutate(("plugin", "automatic_install_or_update"), True)),
        ("host_api_too_old", "FAIL", _mutate(("host", "observed_openfx_api_version"), "1.4")),
        ("required_suite_missing", "FAIL", _mutate(("host", "observed_suites"), ["core", "property", "image_effect", "parameter"])),
        ("silent_backend_fallback", "FAIL", _mutate(("resource", "observed_backend"), "CPU")),
        ("accelerator_lease_missing", "FAIL", _mutate(("resource", "hrb_lease"), {})),
        ("display_gpu_selected", "FAIL", _mutate(("resource", "hrb_lease", "role"), "DISPLAY")),
        ("ocio_identity_missing", "FAIL", _mutate(("color", "ocio_config_sha256"), "")),
        ("output_hash_missing", "FAIL", _mutate(("result", "output_sha256"), "")),
        ("plugin_lineage_mismatch", "FAIL", _mutate(("result", "plugin_binary_sha256"), "0" * 64)),
        ("source_project_mutated", "FAIL", _mutate(("result", "source_project_unchanged"), False)),
    ]
    results = []
    for name, expected, mutation in cases:
        candidate = reference_execution()
        if mutation is not None:
            mutation(candidate)
        report = validate_execution(candidate)
        results.append({"name": name, "expected": expected, "actual": report["result"], "pass": report["result"] == expected})
    passed = sum(item["pass"] for item in results)
    return {
        "schema": "fa3.openfx-reference-conformance.v1",
        "result": "PASS" if passed == len(results) else "FAIL",
        "case_count": len(results),
        "cases_passed": passed,
        "cases": results,
        "real_openfx_binary_executed": False,
        "current_host_runtime_promotion": False,
    }


if __name__ == "__main__":
    report = run_reference_conformance()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
