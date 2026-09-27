#!/usr/bin/env python3
from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from fa3_release_baseline import module_active_capability_count

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_COUNT = module_active_capability_count(__file__)
CANONICAL = "canonical/FA3-REPRODUCIBILITY-FABRIC-001.json"
ENFORCEMENT_ID = "FA3-REPRODUCIBILITY-GATESET-001"


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def evaluate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    canonical = json.loads((root / CANONICAL).read_text(encoding="utf-8"))
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    pytest_cfg = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})
    permanent = (root / ".github/workflows/fa3-permanent-enforcement.yml").read_text(encoding="utf-8")
    reconcile = (root / ".github/workflows/fa3-release-projection-reconcile.yml").read_text(encoding="utf-8")
    reuse = (root / ".github/workflows/fa3-reuse-discovery.yml").read_text(encoding="utf-8")
    requirements = (root / "requirements-test.txt").read_text(encoding="utf-8").splitlines()

    from fa3_python_namespace_audit import audit
    namespace = audit(root)

    checks = [
        _check("baseline-175", canonical.get("capability_count") == CAPABILITY_COUNT == 175, "active capability baseline remains 175"),
        _check("zero-capability-delta", canonical.get("new_capabilities") == 0, "reproducibility fabric adds no capability"),
        _check("zero-authority-delta", canonical.get("new_architectural_authorities") == 0, "reproducibility fabric adds no authority"),
        _check("pytest-pinned", requirements == ["pytest==9.1.1"], "canonical full-suite runner is exactly pinned"),
        _check("pytest-source-root", pytest_cfg.get("pythonpath") == ["src"], "pytest exposes src as the only FA3 module source root"),
        _check("pytest-test-root", pytest_cfg.get("testpaths") == ["tests"], "pytest canonical test root is tests"),
        _check("namespace-audit", namespace.get("result") == "PASS", "no package-style src.fa3_* or relative FA3 imports remain"),
        _check("test-entrypoint", (root / "bin/fa3-test").is_file(), "canonical venv-backed test entrypoint exists"),
        _check("repo-entrypoint", (root / "bin/fa3-prepare-repository").is_file(), "canonical repository history bootstrap exists"),
        _check("repo-module", (root / "src/fa3_repository_prepare.py").is_file(), "repository bootstrap implementation exists"),
        _check("permanent-uses-test", "bash bin/fa3-test -v" in permanent, "Permanent Enforcement uses canonical full-suite entrypoint"),
        _check("permanent-prepares-history", "bash bin/fa3-prepare-repository" in permanent, "Permanent Enforcement prepares required Git history"),
        _check("reconcile-uses-test", "bash bin/fa3-test -v" in reconcile, "release reconciliation uses canonical full-suite entrypoint"),
        _check("reconcile-prepares-history", "bash bin/fa3-prepare-repository" in reconcile, "release reconciliation prepares required Git history"),
        _check("reuse-uses-test", "bash bin/fa3-test -v" in reuse, "Reuse Discovery full regression uses canonical test entrypoint"),
        _check("physical-marker-declared", any(str(x).startswith("physical_current_host:") for x in pytest_cfg.get("markers", [])), "physical current-host tests have a dedicated marker"),
        _check("bootstrap-regression", (root / "tests/test_reproducibility_bootstrap.py").is_file(), "shallow-clone recovery and namespace regression are covered"),
        _check("no-current-host-overclaim", canonical.get("current_host_runtime_promotion_claim") is False, "reproducibility PASS never creates runtime promotion"),
    ]
    result = "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL"
    return {
        "schema": "fa3.reproducibility-gate-report.v1",
        "gate_id": ENFORCEMENT_ID,
        "result": result,
        "summary": {"passed": sum(x["status"] == "PASS" for x in checks), "total": len(checks)},
        "namespace_audit": namespace,
        "checks": checks,
        "current_host_runtime_promotion_claim": False,
    }


def gate(root: Path) -> dict[str, Any]:
    result = evaluate(root)
    report = root / "reports/reproducibility-gate-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
