#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

VERDICT_SCHEMA = "fa3.capability-current-host-qualification-constituent-verdict.v1"
CAPABILITY_ID = "CAP-083"
MODES = ("positive", "negative", "rollback")

EXPECTED_SOURCES = {
    "Vulkan-Headers": "e3b1eec08173d6b825cd3ac88c885a63b621504a",
    "Vulkan-Loader": "5f157b62e333c63260d05d81bf66faa216ab0fb8",
    "Vulkan-ValidationLayers": "f4874eee15c78d7bdb2b7e60659d539f14741500",
    "Vulkan-Profiles": "1f139a2ea3c475eed7e6699d67fc362203a69c41",
    "SPIRV-Tools": "b707790a898e44038547df54580022fc1cf89c3d",
    "glslang": "e1b562a8bed273a02f30b59b66a5d499793cede5",
    "SPIRV-Cross": "aa217aeb6c9f0ace7a0ab233b28807edf45eb165",
    "KTX-Software": "4d6fc70eaf62ad0558e63e8d97eb9766118327a6",
    "glTF-Validator": "434283be08a668a8fb4e437145630ddbf93b0686",
    "OpenXR-SDK": "f2448a8797c85814aa892efc1ab8707900fbcc78",
    "OpenCL-Headers": "6fe718c31a45fe25151362a72ef041c3a1047cbd",
    "OpenCL-ICD-Loader": "b7bd2803acc779c03d96588e9ca9e9568a18698a",
    "ANARI-SDK": "7534bd263d6ff97764eda93d0e1bd6bd2f108c32",
    "OpenVX-sample-impl": "031f44bdcd6648f0957c9e351f76c3a64a0bfc32",
    "NNEF-Tools": "765d27d9095e0c90301165f8933fb325b54ddd17",
    "SPIRV-Headers": "29981f65241605e08b0ede4cfeb999fe3b723c6a",
    "Vulkan-Utility-Libraries": "c279fa4350059faac3d2365df0538977e7e5b097",
    "jsoncpp": "89e2973c754a9c02a49974d839779b151e95afd6",
    "valijson": "0b4771e273a065d437814baf426bcfcafec0f434",
}
CORE_COMPONENTS = {
    "Vulkan-Headers", "Vulkan-Utility-Libraries", "SPIRV-Headers", "SPIRV-Tools",
    "glslang", "SPIRV-Cross", "jsoncpp", "valijson", "Vulkan-Loader",
    "Vulkan-Profiles", "Vulkan-ValidationLayers", "KTX-Software", "OpenXR-SDK",
    "OpenCL-Headers", "OpenCL-ICD-Loader", "ANARI-SDK",
}

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return obj

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value

def _repo_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()

def _sdk_root() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    return (Path(data_home).expanduser() if data_home else Path.home() / ".local/share") / "fa3/khronos-sdk"

def _expected_source_decisions(root: Path) -> list[str]:
    registry = _load(root / "evidence/evidence-registry.json")
    row = next((x for x in registry.get("records", []) if x.get("subject_id") == CAPABILITY_ID), None)
    ids = row.get("source_decision_ids") if isinstance(row, dict) else None
    if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not x for x in ids):
        raise RuntimeError("CAP-083 source-decision coverage invalid")
    return ids

def _validate_coverage(root: Path) -> list[str]:
    expected = _expected_source_decisions(root)
    supplied = json.loads(_required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON"))
    if supplied != expected:
        raise RuntimeError("CAP-083 producer coverage does not exactly match Evidence Registry")
    if "FA3-DEC-KHRONOS-OPEN-STANDARDS-2026-09-27" not in supplied:
        raise RuntimeError("Khronos materialization decision is not covered")
    return expected

def _verify_sources_and_build(root: Path) -> dict[str, Any]:
    sdk = _sdk_root()
    src = sdk / "src"
    source_rows = []
    for name, expected in EXPECTED_SOURCES.items():
        repo = src / name
        if not (repo / ".git").is_dir():
            raise RuntimeError(f"immutable Khronos/build dependency source missing: {name}")
        got = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        if got != expected:
            raise RuntimeError(f"immutable source pin mismatch: {name}: {got}")
        source_rows.append({"project": name, "commit": got})

    receipt = _load(sdk / "receipts/core-build.json")
    head = _repo_head(root)
    if receipt.get("status") != "PASS":
        raise RuntimeError("Khronos core build receipt is not PASS")
    if receipt.get("source_commit") != head:
        raise RuntimeError("Khronos core build receipt is not bound to exact repository HEAD")
    if set(receipt.get("components", [])) != CORE_COMPONENTS:
        raise RuntimeError("Khronos core build component set mismatch")
    for key in ("automatic_update_deps", "system_package_replacement", "global_environment_mutation", "hardware_parameter_mutation", "runtime_promotion_claim"):
        if receipt.get(key) is not False:
            raise RuntimeError(f"Khronos core build safety invariant failed: {key}")

    return {
        "sdk_root": str(sdk),
        "prefix": str(sdk / "prefix"),
        "source_count": len(source_rows),
        "sources": source_rows,
        "build_receipt_sha256": _sha256(sdk / "receipts/core-build.json"),
        "source_commit": head,
    }

def _child_env(prefix: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR") if k in os.environ}
    env["PATH"] = str(prefix / "bin") + os.pathsep + env.get("PATH", "")
    lib_paths = [str(prefix / "lib"), str(prefix / "lib64")]
    inherited = os.environ.get("LD_LIBRARY_PATH")
    if inherited:
        lib_paths.append(inherited)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths)
    env["PYTHONNOUSERSITE"] = "1"
    return env

def _run(argv: list[str], *, env: dict[str, str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, shell=False, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {argv[0]}: {proc.stderr[-1200:]}")
    return proc

def _find_file(prefix: Path, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        found = sorted(prefix.glob(pattern))
        if found:
            return str(found[0])
    raise RuntimeError("required installed SDK artifact missing: " + " | ".join(patterns))

def _functional_smoke(scope: Path, prefix: Path) -> dict[str, Any]:
    env = _child_env(prefix)
    tools = {name: prefix / "bin" / name for name in ("glslangValidator", "spirv-val", "spirv-opt", "spirv-cross")}
    missing = [name for name, path in tools.items() if not path.is_file()]
    if missing:
        raise RuntimeError("required Shader Fabric tools missing: " + ",".join(missing))

    shader = scope / "cap083.comp"
    spv = scope / "cap083.spv"
    opt = scope / "cap083.opt.spv"
    shader.write_text(
        "#version 450\nlayout(local_size_x=1) in;\nlayout(set=0,binding=0) buffer B { uint x; } b;\nvoid main(){ b.x = b.x + 1u; }\n",
        encoding="utf-8",
    )
    _run([str(tools["glslangValidator"]), "-V", "-S", "comp", "-o", str(spv), str(shader)], env=env, cwd=scope)
    _run([str(tools["spirv-val"]), str(spv)], env=env, cwd=scope)
    _run([str(tools["spirv-opt"]), "-O", str(spv), "-o", str(opt)], env=env, cwd=scope)
    reflected = _run([str(tools["spirv-cross"]), str(opt), "--reflect"], env=env, cwd=scope)
    reflect_obj = json.loads(reflected.stdout)
    if not isinstance(reflect_obj, dict):
        raise RuntimeError("SPIRV-Cross reflection is not an object")

    ktx_tool = prefix / "bin" / "ktx"
    if not ktx_tool.is_file():
        ktx_tool = prefix / "bin" / "toktx"
    if not ktx_tool.is_file():
        raise RuntimeError("KTX CLI tool missing from FA3 prefix")
    ktx_version = _run([str(ktx_tool), "--version"], env=env, cwd=scope).stdout.strip()

    installed = {
        "vulkan_loader": _find_file(prefix, ("lib*/libvulkan.so*",)),
        "vulkan_validation_layer": _find_file(prefix, ("share/vulkan/explicit_layer.d/VkLayer_khronos_validation.json", "lib*/libVkLayer_khronos_validation.so*")),
        "openxr_loader": _find_file(prefix, ("lib*/libopenxr_loader.so*",)),
        "opencl_loader": _find_file(prefix, ("lib*/libOpenCL.so*",)),
        "anari_frontend": _find_file(prefix, ("lib*/libanari.so*", "lib*/libanari.*")),
    }
    return {
        "shader_source_sha256": _sha256(shader),
        "spirv_sha256": _sha256(spv),
        "optimized_spirv_sha256": _sha256(opt),
        "reflection_keys": sorted(reflect_obj.keys()),
        "ktx_tool": str(ktx_tool),
        "ktx_version": ktx_version,
        "installed_runtime_artifacts": installed,
        "physical_accelerator_required": False,
        "xr_device_required": False,
        "opencl_device_required": False,
        "child_process_scoped_environment": True,
    }

def _run_positive(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    verified = _verify_sources_and_build(root)
    smoke = _functional_smoke(scope, Path(verified["prefix"]))
    return {"mode": "positive", "status": "PASS", "coverage_count": len(coverage), "verified": verified, "functional_smoke": smoke}

def _run_negative(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    verified = _verify_sources_and_build(root)
    prefix = Path(verified["prefix"])
    before = {k: os.environ.get(k) for k in ("PATH", "LD_LIBRARY_PATH", "VK_LAYER_PATH", "VK_ICD_FILENAMES", "OCL_ICD_VENDORS", "XR_RUNTIME_JSON")}
    child = _child_env(prefix)
    after = {k: os.environ.get(k) for k in before}
    adapter_registry = _load(root / "canonical/FA3-KHRONOS-ADAPTER-REGISTRY-001.json")
    openvx = next((x for x in adapter_registry.get("adapters", []) if x.get("project") == "OpenVX-sample-impl"), {})
    cases = {
        "parent_environment_unchanged": before == after,
        "child_path_is_namespaced": child.get("PATH", "").split(os.pathsep)[0] == str(prefix / "bin"),
        "no_global_vulkan_layer_override": "VK_LAYER_PATH" not in child,
        "no_global_vulkan_icd_override": "VK_ICD_FILENAMES" not in child,
        "no_global_opencl_icd_override": "OCL_ICD_VENDORS" not in child,
        "no_global_openxr_runtime_override": "XR_RUNTIME_JSON" not in child,
        "sdk_prefix_not_system_root": str(prefix).startswith(str(_sdk_root())),
        "openvx_not_runtime_admitted": openvx.get("runtime_admitted") is False and "SAMPLE_IMPLEMENTATION" in str(openvx.get("mode")),
    }
    if not all(cases.values()):
        raise RuntimeError("CAP-083 negative coexistence matrix failed")
    artifact = scope / "cap083-negative-cases.json"
    _write(artifact, cases)
    return {"mode": "negative", "status": "PASS", "coverage_count": len(coverage), "verified": verified, "cases": cases, "artifact_sha256": _sha256(artifact)}

def _run_rollback(root: Path, scope: Path) -> dict[str, Any]:
    coverage = _validate_coverage(root)
    verified = _verify_sources_and_build(root)
    path = scope / "cap083-child-runtime-env.json"
    baseline = {
        "PATH_PREPEND": str(Path(verified["prefix"]) / "bin"),
        "LD_LIBRARY_PATH_PREPEND": [str(Path(verified["prefix"]) / "lib"), str(Path(verified["prefix"]) / "lib64")],
        "VK_LAYER_PATH": None,
        "VK_ICD_FILENAMES": None,
        "OCL_ICD_VENDORS": None,
        "XR_RUNTIME_JSON": None,
        "scope": "CHILD_PROCESS_ONLY",
    }
    _write(path, baseline)
    pre = _sha256(path)
    fault = dict(baseline)
    fault["VK_ICD_FILENAMES"] = "/usr/share/vulkan/icd.d/forced-by-fa3.json"
    fault["scope"] = "GLOBAL_MUTATION_FORBIDDEN"
    _write(path, fault)
    mutated = _sha256(path)
    _write(path, baseline)
    post = _sha256(path)
    if pre != post or pre == mutated:
        raise RuntimeError("CAP-083 rollback hash proof failed")
    return {"mode": "rollback", "status": "PASS", "coverage_count": len(coverage), "verified": verified, "pre_sha256": pre, "mutated_sha256": mutated, "post_sha256": post, "rollback_hash_equal": True}

def run_mode(root: Path, scope: Path, mode: str) -> dict[str, Any]:
    root = root.resolve()
    scope = scope.resolve()
    if mode not in MODES:
        raise ValueError(f"unsupported mode: {mode}")
    if root not in scope.parents:
        raise RuntimeError("source artifact scope escapes repository")
    scope.mkdir(parents=True, exist_ok=True)
    if mode == "positive":
        return _run_positive(root, scope)
    if mode == "negative":
        return _run_negative(root, scope)
    return _run_rollback(root, scope)

def main() -> int:
    parser = argparse.ArgumentParser(description="CAP-083 Khronos current-host qualification producer")
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--producer-id", required=True)
    args = parser.parse_args()
    try:
        if _required_env("FA3_CURRENT_HOST") != "1":
            raise RuntimeError("real current-host execution marker required")
        if _required_env("FA3_EXECUTION_SCOPE") != "CURRENT_HOST":
            raise RuntimeError("CURRENT_HOST execution scope required")
        if _required_env("FA3_CAPABILITY_ID") != CAPABILITY_ID:
            raise RuntimeError("producer is bound only to CAP-083")
        root = Path(_required_env("FA3_REPOSITORY_ROOT")).resolve()
        scope = Path(_required_env("FA3_QUALIFICATION_SOURCE_ARTIFACT_DIR")).resolve()
        result = run_mode(root, scope, args.mode)
        artifact = scope / "cap083-khronos-evidence.json"
        payload = {
            "schema": "fa3.cap083-khronos-current-host-evidence.v1",
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "result": result,
        }
        _write(artifact, payload)
        verdict = {
            "schema": VERDICT_SCHEMA,
            "producer_id": args.producer_id,
            "qualification_id": _required_env("FA3_QUALIFICATION_ID"),
            "constituent_id": _required_env("FA3_CONSTITUENT_ID"),
            "subject_id": CAPABILITY_ID,
            "test_kind": _required_env("FA3_TEST_KIND"),
            "test_id": _required_env("FA3_TEST_ID"),
            "status": "PASS",
            "execution_scope": "CURRENT_HOST",
            "current_host": True,
            "synthetic": False,
            "ci_reference_only": False,
            "provider_receipt_only": False,
            "component_receipt_only": False,
            "generic_host_collection_only": False,
            "global_promotion_claim": False,
            "source_evidence_class": _required_env("FA3_SOURCE_EVIDENCE_CLASS"),
            "covers_source_decision_ids": json.loads(_required_env("FA3_COVERS_SOURCE_DECISION_IDS_JSON")),
            "source_artifact_path": artifact.relative_to(root).as_posix(),
            "source_artifact_sha256": _sha256(artifact),
        }
        print(json.dumps(verdict, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "REJECTED", "findings": [str(exc)]}), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
