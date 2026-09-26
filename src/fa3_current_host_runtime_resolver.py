#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


def run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
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
            resolved = path.expanduser().resolve()
        except Exception:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        out.append(resolved)
    return out


def _dedupe_launchers(paths: Iterable[Path]) -> list[Path]:
    """Deduplicate executable launch paths without resolving venv symlinks.

    Resolving venv/bin/python to its base interpreter discards pyvenv.cfg based
    environment discovery and therefore hides the venv's site-packages.
    """
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        try:
            expanded = path.expanduser()
            absolute = Path(os.path.abspath(os.fspath(expanded)))
        except Exception:
            continue
        key = str(absolute)
        if key in seen:
            continue
        seen.add(key)
        out.append(absolute)
    return out


def approved_python_roots() -> list[Path]:
    roots = [
        Path("/AI-modells"),
        Path("/opt/AI-modells"),
        Path("/opt/ai"),
        Path.home() / ".local/share/fa3",
    ]
    override = os.environ.get("FA3_AI_PYTHON_ROOT")
    if override:
        roots.insert(0, Path(override))
    return _dedupe(roots)


def candidate_python_interpreters() -> list[Path]:
    candidates: list[Path] = [Path(sys.executable)]
    override = os.environ.get("FA3_AI_PYTHON")
    if override:
        candidates.insert(0, Path(override))

    common = [
        Path("/opt/ai/venv"),
        Path.home() / ".local/share/fa3",
    ]
    for root in _dedupe(common + approved_python_roots()):
        if not root.exists():
            continue
        direct = (
            root / "bin/python",
            root / "bin/python3",
            root / ".venv/bin/python",
            root / "venv/bin/python",
        )
        candidates.extend(direct)
        # Deliberately bounded: only inspect a few levels below approved AI roots.
        try:
            for pattern in (
                "*/bin/python",
                "*/bin/python3",
                "*/*/bin/python",
                "*/*/bin/python3",
                "*/*/*/bin/python",
            ):
                candidates.extend(root.glob(pattern))
        except OSError:
            pass
    return [p for p in _dedupe_launchers(candidates) if p.is_file() and os.access(p, os.X_OK)]


def probe_python(path: Path) -> dict[str, Any]:
    code = (
        "import importlib.util,json,sys;"
        "mods={n:(importlib.util.find_spec(n) is not None) for n in ('torch','pytorch3d')};"
        "out={'python':sys.executable,'version':sys.version.split()[0],'modules':mods,"
        "'torch_version':None,'pytorch3d_version':None,'cuda_available':False,'cuda_count':0};"
        "\nif mods['torch']:\n"
        " import torch;out['torch_version']=getattr(torch,'__version__','unknown');"
        "out['cuda_available']=bool(torch.cuda.is_available());out['cuda_count']=int(torch.cuda.device_count());"
        "\nif mods['pytorch3d']:\n"
        " import pytorch3d;out['pytorch3d_version']=getattr(pytorch3d,'__version__','unknown');"
        "\nprint(json.dumps(out))"
    )
    timeout_seconds = 30
    try:
        proc = run([str(path), "-c", code], timeout_seconds)
    except subprocess.TimeoutExpired:
        return {
            "path": str(path),
            "probe_status": "TIMEOUT",
            "timeout_seconds": timeout_seconds,
        }
    if proc.returncode != 0:
        return {
            "path": str(path),
            "probe_status": "ERROR",
            "returncode": proc.returncode,
            "stderr_tail": proc.stderr[-1000:],
        }
    try:
        value = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as exc:
        return {
            "path": str(path),
            "probe_status": "ERROR",
            "returncode": proc.returncode,
            "parse_error": str(exc),
        }
    value["path"] = str(path)
    value["probe_status"] = "PASS"
    return value


def resolve_python_runtime(*, require_torch: bool, require_pytorch3d: bool, require_cuda: bool) -> dict[str, Any]:
    probes = [probe_python(path) for path in candidate_python_interpreters()]
    selected: dict[str, Any] | None = None
    for row in probes:
        if row.get("probe_status") != "PASS":
            continue
        mods = row.get("modules", {})
        if require_torch and mods.get("torch") is not True:
            continue
        if require_pytorch3d and mods.get("pytorch3d") is not True:
            continue
        if require_cuda and (row.get("cuda_available") is not True or int(row.get("cuda_count", 0)) < 1):
            continue
        selected = row
        break
    return {
        "selected": selected,
        "candidates": probes,
        "requirements": {
            "torch": require_torch,
            "pytorch3d": require_pytorch3d,
            "cuda": require_cuda,
        },
    }


if __name__ == "__main__":
    payload = {
        "gpu_python": resolve_python_runtime(require_torch=True, require_pytorch3d=False, require_cuda=True),
        "pytorch3d_python": resolve_python_runtime(require_torch=True, require_pytorch3d=True, require_cuda=False),
    }
    print(json.dumps(payload, indent=2))
