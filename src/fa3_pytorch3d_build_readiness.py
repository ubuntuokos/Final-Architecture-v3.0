#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

SOURCE_REVISION = "0a7d4c1a171e8b768c63f15b17564f9ad495f49b"
SCHEMA = "fa3.pytorch3d-current-host-build-readiness.v1"


def _run(argv: list[str], timeout: int = 20, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        shell=False,
        check=False,
    )


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        try:
            absolute = Path(os.path.abspath(os.fspath(path.expanduser())))
        except Exception:
            continue
        key = str(absolute)
        if key not in seen:
            seen.add(key)
            out.append(absolute)
    return out


def _source_candidates() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("FA3_PYTORCH3D_SOURCE_DIR")
    if explicit:
        paths.append(Path(explicit))
    paths.extend(
        [
            Path("/opt/AI-modells/PyTorch3D"),
            Path("/opt/AI-modells/pytorch3d"),
            Path("/AI-modells/PyTorch3D"),
            Path("/AI-modells/pytorch3d"),
            Path("/opt/ai/pytorch3d/source"),
            Path.home() / ".local/share/fa3/pytorch3d/source",
        ]
    )
    return _dedupe(paths)


def _venv_candidates() -> list[Path]:
    paths: list[Path] = []
    explicit = os.environ.get("FA3_PYTORCH3D_VENV")
    if explicit:
        paths.append(Path(explicit))
    paths.extend(
        [
            Path("/opt/ai/pytorch3d/venv"),
            Path("/opt/AI-modells/PyTorch3D/.venv"),
            Path("/opt/AI-modells/pytorch3d/.venv"),
            Path("/AI-modells/PyTorch3D/.venv"),
            Path("/AI-modells/pytorch3d/.venv"),
            Path.home() / ".local/share/fa3/pytorch3d/venv",
        ]
    )
    return _dedupe(paths)


def _cuda_candidates() -> list[Path]:
    paths: list[Path] = []
    for name in ("FA3_CUDA_HOME", "CUDA_HOME"):
        value = os.environ.get(name)
        if value:
            paths.append(Path(value))
    for root in (Path("/usr/local"), Path("/opt")):
        paths.extend(root.glob("cuda-*"))
        paths.append(root / "cuda")
    return _dedupe(paths)


def _inspect_source(path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_dir(),
        "exact_revision": False,
        "tracked_tree_clean": False,
        "revision": None,
    }
    if not path.is_dir() or not (path / ".git").exists():
        return row
    try:
        rev = _run(["git", "rev-parse", "HEAD"], cwd=path, timeout=10)
        status = _run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=path, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        row["probe_error"] = str(exc)
        return row
    row["revision"] = rev.stdout.strip() if rev.returncode == 0 else None
    row["exact_revision"] = row["revision"] == SOURCE_REVISION
    row["tracked_tree_clean"] = status.returncode == 0 and not status.stdout.strip()
    return row


def _probe_build_venv(path: Path) -> dict[str, Any]:
    python = path / "bin/python"
    row: dict[str, Any] = {
        "path": str(path),
        "python": str(python),
        "exists": path.is_dir(),
        "isolated_pip_venv": (path / "pyvenv.cfg").is_file(),
        "probe_status": "MISSING",
        "torch_version": None,
        "torchvision_version": None,
        "torch_cuda": None,
        "pytorch3d_present": False,
    }
    if not python.is_file() or not os.access(python, os.X_OK):
        return row
    code = (
        "import importlib.util,json,sys;"
        "mods={n:(importlib.util.find_spec(n) is not None) for n in ('torch','torchvision','pytorch3d')};"
        "out={'python':sys.executable,'version':sys.version.split()[0],'modules':mods,"
        "'torch_version':None,'torchvision_version':None,'torch_cuda':None};"
        "\nif mods['torch']:\n import torch;out['torch_version']=getattr(torch,'__version__','unknown');out['torch_cuda']=getattr(torch.version,'cuda',None);"
        "\nif mods['torchvision']:\n import torchvision;out['torchvision_version']=getattr(torchvision,'__version__','unknown');"
        "\nprint(json.dumps(out))"
    )
    try:
        proc = _run([str(python), "-c", code], timeout=30)
    except subprocess.TimeoutExpired:
        row["probe_status"] = "TIMEOUT"
        return row
    except OSError as exc:
        row["probe_status"] = "ERROR"
        row["probe_error"] = str(exc)
        return row
    if proc.returncode != 0:
        row["probe_status"] = "ERROR"
        row["stderr_tail"] = proc.stderr[-1000:]
        return row
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as exc:
        row["probe_status"] = "ERROR"
        row["probe_error"] = f"invalid JSON probe: {exc}"
        return row
    modules = payload.get("modules", {})
    row.update(
        {
            "probe_status": "PASS",
            "python_version": payload.get("version"),
            "torch_version": payload.get("torch_version"),
            "torchvision_version": payload.get("torchvision_version"),
            "torch_cuda": payload.get("torch_cuda"),
            "torch_present": modules.get("torch") is True,
            "torchvision_present": modules.get("torchvision") is True,
            "pytorch3d_present": modules.get("pytorch3d") is True,
        }
    )
    return row


def _parse_nvcc_version(text: str) -> str | None:
    match = re.search(r"release\s+([0-9]+\.[0-9]+)", text)
    return match.group(1) if match else None


def _probe_cuda(path: Path) -> dict[str, Any]:
    nvcc = path / "bin/nvcc"
    row: dict[str, Any] = {
        "path": str(path),
        "nvcc": str(nvcc),
        "exists": path.is_dir(),
        "probe_status": "MISSING",
        "version": None,
    }
    if not nvcc.is_file() or not os.access(nvcc, os.X_OK):
        return row
    try:
        proc = _run([str(nvcc), "--version"], timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        row["probe_status"] = "ERROR"
        row["probe_error"] = str(exc)
        return row
    if proc.returncode != 0:
        row["probe_status"] = "ERROR"
        row["stderr_tail"] = proc.stderr[-1000:]
        return row
    row["version"] = _parse_nvcc_version(proc.stdout + "\n" + proc.stderr)
    row["probe_status"] = "PASS" if row["version"] else "ERROR"
    return row


def _tool(names: tuple[str, ...]) -> dict[str, Any]:
    for name in names:
        path = shutil.which(name)
        if path:
            return {"available": True, "name": name, "path": path}
    return {"available": False, "name": None, "path": None}


def collect(root: Path) -> dict[str, Any]:
    source_rows = [_inspect_source(path) for path in _source_candidates()]
    venv_rows = [_probe_build_venv(path) for path in _venv_candidates()]
    cuda_rows = [_probe_cuda(path) for path in _cuda_candidates()]
    compiler = _tool(("c++", "g++", "clang++"))
    syft = _tool(("syft",))

    sources = [
        row for row in source_rows
        if row.get("exact_revision") is True and row.get("tracked_tree_clean") is True
    ]
    build_envs = [
        row for row in venv_rows
        if row.get("probe_status") == "PASS"
        and row.get("isolated_pip_venv") is True
        and row.get("torch_present") is True
        and row.get("torchvision_present") is True
        and isinstance(row.get("torch_cuda"), str)
        and bool(row.get("torch_cuda"))
    ]
    toolkits = [
        row for row in cuda_rows
        if row.get("probe_status") == "PASS" and isinstance(row.get("version"), str)
    ]
    matches: list[dict[str, Any]] = []
    for env in build_envs:
        for toolkit in toolkits:
            if env.get("torch_cuda") == toolkit.get("version"):
                matches.append(
                    {
                        "venv": env["path"],
                        "python_version": env.get("python_version"),
                        "torch_version": env.get("torch_version"),
                        "torchvision_version": env.get("torchvision_version"),
                        "torch_cuda": env.get("torch_cuda"),
                        "cuda_home": toolkit["path"],
                        "nvcc_version": toolkit.get("version"),
                    }
                )

    findings: list[str] = []
    if not sources:
        findings.append(f"exact clean PyTorch3D source checkout missing for {SOURCE_REVISION}")
    if not build_envs:
        findings.append("isolated PyTorch3D build venv with torch + torchvision + CUDA tuple missing")
    if not toolkits:
        findings.append("local CUDA toolkit with executable nvcc not found in bounded approved roots")
    elif build_envs and not matches:
        findings.append("no isolated build venv has a Torch CUDA major.minor matching an installed nvcc toolkit")
    if not compiler["available"]:
        findings.append("C++ compiler missing")
    if not syft["available"]:
        findings.append("Syft missing for mandatory wheel SBOM generation")

    status = "READY_FOR_PINNED_SOURCE_BUILD" if not findings else "BLOCKED_BUILD_READINESS"
    return {
        "schema": SCHEMA,
        "capability_id": "CAP-032",
        "provider_id": "FA3-PROVIDER-PYTORCH3D-001",
        "execution_scope": "CURRENT_HOST",
        "diagnostic_only": True,
        "status": status,
        "source_revision_required": SOURCE_REVISION,
        "source_candidates": source_rows,
        "isolated_build_venv_candidates": venv_rows,
        "cuda_toolkit_candidates": cuda_rows,
        "matching_build_tuples": matches,
        "compiler": compiler,
        "syft": syft,
        "findings": findings,
        "global_promotion_claim": False,
        "runtime_pass_claim": False,
        "truth_constraints": {
            "shared_application_venv_admissible": False,
            "conda_or_mamba_admissible": False,
            "community_wheel_admissible": False,
            "network_install_performed": False,
            "host_mutation_performed": False,
            "readiness_is_capability_pass": False,
            "readiness_is_provider_promotion": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect read-only PyTorch3D current-host source-build readiness")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument(
        "--output",
        default=".fa3-current-host/pytorch3d/build-readiness.json",
        help="Repository-relative output path",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = (root / args.output).resolve()
    if root not in output.parents:
        raise SystemExit("output path escapes repository")
    report = collect(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
