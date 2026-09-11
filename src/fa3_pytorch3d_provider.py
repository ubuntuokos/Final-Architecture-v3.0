#!/usr/bin/env python3
from __future__ import annotations

import copy
import re
from typing import Any

SOURCE_REVISION = "0a7d4c1a171e8b768c63f15b17564f9ad495f49b"
ALLOWED_OPERATIONS = (
    "3d.mesh.fit",
    "3d.mesh.render",
    "3d.pointcloud.render",
    "3d.camera.optimize",
    "3d.volume.marching-cubes",
    "3d.geometry.convert",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PCI_BDF_RE = re.compile(r"^(?:[0-9a-fA-F]{4}:)?[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$")


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _cuda_major_minor(value: Any) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    compact = re.fullmatch(r"cu(\d{3})", normalized)
    if compact is not None:
        digits = compact.group(1)
        return int(digits[:2]), int(digits[2])
    match = re.search(r"(?:cu|cuda\s*)?(\d+)(?:[._]?(\d+))?", normalized)
    if match is None:
        return None
    major = int(match.group(1))
    minor_text = match.group(2)
    return major, int(minor_text or 0)


def validate_build_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    torch_cuda = _cuda_major_minor(candidate.get("torch_compiled_cuda_version"))
    build_cuda = _cuda_major_minor(candidate.get("build_toolkit_version"))
    checks = [
        _check("source-revision", candidate.get("source_revision") == SOURCE_REVISION, "exact accepted upstream revision"),
        _check("source-integrity", candidate.get("source_integrity_verified") is True, "source integrity verified"),
        _check("source-wheel", candidate.get("distribution") == "SOURCE_BUILT_WHEEL", "locally source-built wheel only"),
        _check("isolated-venv", candidate.get("environment_kind") == "ISOLATED_PIP_VENV", "isolated pip venv"),
        _check("no-shared-torch-env", candidate.get("shared_torch_environment") is False, "not a shared application Torch environment"),
        _check("no-conda", candidate.get("conda_prefix_present") is False, "Conda/mamba baseline absent"),
        _check("complete-python-torch-tuple", all(candidate.get(k) for k in ("python_version_and_abi", "torch_version", "torchvision_version")), "Python/Torch/torchvision identity complete"),
        _check("cuda-abi-match", torch_cuda is not None and torch_cuda == build_cuda, "Torch-compiled and build-toolkit CUDA major.minor match"),
        _check("compiler-abi", bool(candidate.get("compiler_id_and_version")) and candidate.get("cxx11_abi") in (0, 1), "compiler and C++ ABI recorded"),
        _check("hardware-derived-targets", bool(candidate.get("target_accelerator_architectures")) and candidate.get("target_architectures_source") == "HRB_DISCOVERY", "target architectures derive from admitted hardware"),
        _check("hrb-build-budget", candidate.get("build_parallelism_source") == "HRB_LEASE", "build parallelism derives from HRB"),
        _check("wheel-digest", _sha(candidate.get("wheel_sha256")), "wheel SHA-256 recorded"),
        _check("sbom", _sha(candidate.get("sbom_sha256")), "SBOM digest recorded"),
        _check("provenance", _sha(candidate.get("provenance_attestation_sha256")), "provenance attestation digest recorded"),
        _check("packaging-smoke", candidate.get("pep517_660_smoke_pass") is True, "modern local-build packaging regression passed"),
    ]
    return {
        "schema": "fa3.pytorch3d-build-admission.v1",
        "result": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks": checks,
    }


def _asset_list_valid(assets: Any) -> bool:
    return (
        isinstance(assets, list)
        and len(assets) > 0
        and all(
            isinstance(asset, dict)
            and isinstance(asset.get("asset_id"), str)
            and bool(asset["asset_id"])
            and _sha(asset.get("sha256"))
            for asset in assets
        )
    )


def admit_job(job: dict[str, Any]) -> dict[str, Any]:
    lease = job.get("accelerator_lease") if isinstance(job.get("accelerator_lease"), dict) else {}
    output = job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
    checks = [
        _check("schema", job.get("schema") == "fa3.differentiable-3d-job.v1", "typed job schema"),
        _check("job-id", isinstance(job.get("job_id"), str) and bool(job.get("job_id")), "non-empty job id"),
        _check("operation", job.get("operation") in ALLOWED_OPERATIONS, "operation is in the six-capability surface"),
        _check("content-addressed-input", _asset_list_valid(job.get("input_assets")), "all input assets have SHA-256 identities"),
        _check("content-addressed-output", _sha(output.get("expected_manifest_sha256")), "output manifest identity declared"),
        _check("compatibility-receipt", isinstance(job.get("runtime_compatibility_receipt_id"), str) and bool(job.get("runtime_compatibility_receipt_id")), "runtime compatibility receipt bound"),
        _check("cuda-explicit", job.get("execution_device") == "CUDA_EXPLICIT", "CUDA execution explicitly requested"),
        _check("no-fallback", job.get("fallback_policy") == "DENY", "fallback is denied"),
        _check("evidence-sink", job.get("evidence_sink") == "FA3-AUTH-OBS-EVIDENCE-001", "canonical evidence sink"),
        _check("no-runtime-fetch", job.get("runtime_network_fetch") is False, "runtime network fetch disabled"),
        _check("no-python-payload", job.get("arbitrary_python_payload") is False, "arbitrary Python payload disabled"),
        _check("hrb-lease", isinstance(lease.get("lease_id"), str) and bool(lease.get("lease_id")), "HRB lease id present"),
        _check("compute-role", lease.get("accelerator_role") == "COMPUTE", "compute accelerator role"),
        _check("stable-uuid", isinstance(lease.get("device_uuid"), str) and lease.get("device_uuid", "").startswith("GPU-"), "stable device UUID"),
        _check("stable-pci-bdf", isinstance(lease.get("pci_bdf"), str) and PCI_BDF_RE.fullmatch(lease.get("pci_bdf", "")) is not None, "stable PCI BDF"),
        _check("single-visible", lease.get("visible_accelerator_count") == 1, "one HRB-leased accelerator visible to worker"),
        _check("ordinal-ephemeral", isinstance(lease.get("runtime_ordinal"), int) and lease.get("runtime_ordinal_is_identity") is False, "runtime ordinal is an ephemeral mapping"),
    ]
    return {
        "schema": "fa3.pytorch3d-job-admission.v1",
        "result": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "checks": checks,
    }


def reference_build_candidate() -> dict[str, Any]:
    digest = "a" * 64
    return {
        "source_revision": SOURCE_REVISION,
        "source_integrity_verified": True,
        "distribution": "SOURCE_BUILT_WHEEL",
        "environment_kind": "ISOLATED_PIP_VENV",
        "shared_torch_environment": False,
        "conda_prefix_present": False,
        "python_version_and_abi": "3.14/cp314",
        "torch_version": "2.9.1+cu128",
        "torchvision_version": "ABI_MATCHED_TO_TORCH",
        "torch_compiled_cuda_version": "12.8",
        "build_toolkit_version": "12.8",
        "compiler_id_and_version": "DISCOVERED_CXX",
        "cxx11_abi": 1,
        "target_accelerator_architectures": ["DISCOVERED_BY_HRB"],
        "target_architectures_source": "HRB_DISCOVERY",
        "build_parallelism_source": "HRB_LEASE",
        "wheel_sha256": digest,
        "sbom_sha256": "b" * 64,
        "provenance_attestation_sha256": "c" * 64,
        "pep517_660_smoke_pass": True,
    }


def reference_job() -> dict[str, Any]:
    return {
        "schema": "fa3.differentiable-3d-job.v1",
        "job_id": "reference-job",
        "operation": "3d.mesh.render",
        "input_assets": [{"asset_id": "mesh-1", "sha256": "d" * 64}],
        "output_contract": {"expected_manifest_sha256": "e" * 64},
        "runtime_compatibility_receipt_id": "runtime-tuple-1",
        "execution_device": "CUDA_EXPLICIT",
        "fallback_policy": "DENY",
        "evidence_sink": "FA3-AUTH-OBS-EVIDENCE-001",
        "runtime_network_fetch": False,
        "arbitrary_python_payload": False,
        "accelerator_lease": {
            "lease_id": "hrb-lease-reference",
            "accelerator_role": "COMPUTE",
            "device_uuid": "GPU-reference-uuid",
            "pci_bdf": "0000:01:00.0",
            "visible_accelerator_count": 1,
            "runtime_ordinal": 0,
            "runtime_ordinal_is_identity": False,
        },
    }


def reference_policy_conformance() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def run(name: str, expected: str, actual: str) -> None:
        cases.append({"name": name, "expected": expected, "actual": actual, "status": "PASS" if actual == expected else "FAIL"})

    build = reference_build_candidate()
    run("source-build-positive", "PASS", validate_build_candidate(build)["result"])
    for name, field, value in (
        ("floating-source-rejected", "source_revision", "main"),
        ("shared-env-rejected", "shared_torch_environment", True),
        ("conda-rejected", "conda_prefix_present", True),
        ("binary-wheel-rejected", "distribution", "COMMUNITY_WHEEL"),
        ("cuda-mismatch-rejected", "build_toolkit_version", "13.2"),
        ("missing-wheel-hash-rejected", "wheel_sha256", ""),
        ("missing-sbom-rejected", "sbom_sha256", ""),
        ("missing-provenance-rejected", "provenance_attestation_sha256", ""),
        ("packaging-regression-rejected", "pep517_660_smoke_pass", False),
    ):
        candidate = copy.deepcopy(build)
        candidate[field] = value
        run(name, "FAIL", validate_build_candidate(candidate)["result"])

    job = reference_job()
    run("typed-job-positive", "PASS", admit_job(job)["result"])
    for name, mutation in (
        ("unknown-operation-rejected", lambda value: value.update(operation="3d.shell.exec")),
        ("unhashed-input-rejected", lambda value: value["input_assets"][0].update(sha256="latest")),
        ("cpu-fallback-rejected", lambda value: value.update(fallback_policy="CPU")),
        ("runtime-fetch-rejected", lambda value: value.update(runtime_network_fetch=True)),
        ("python-payload-rejected", lambda value: value.update(arbitrary_python_payload=True)),
        ("missing-hrb-lease-rejected", lambda value: value["accelerator_lease"].update(lease_id="")),
        ("display-gpu-rejected", lambda value: value["accelerator_lease"].update(accelerator_role="DISPLAY")),
        ("missing-stable-identity-rejected", lambda value: value["accelerator_lease"].update(device_uuid="")),
        ("ordinal-as-identity-rejected", lambda value: value["accelerator_lease"].update(runtime_ordinal_is_identity=True)),
        ("multi-visible-gpu-rejected", lambda value: value["accelerator_lease"].update(visible_accelerator_count=2)),
    ):
        candidate = copy.deepcopy(job)
        mutation(candidate)
        run(name, "FAIL", admit_job(candidate)["result"])

    return {
        "schema": "fa3.pytorch3d-reference-policy-conformance.v1",
        "result": "PASS" if all(item["status"] == "PASS" for item in cases) else "FAIL",
        "case_count": len(cases),
        "cases": cases,
        "current_host_runtime_promotion": False,
    }


if __name__ == "__main__":
    import json

    report = reference_policy_conformance()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
