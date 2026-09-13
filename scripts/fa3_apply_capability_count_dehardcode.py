#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def replace(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"expected migration anchor missing: {label}")
    return text.replace(old, new)


def patch(path: Path, transform) -> None:
    before = path.read_text(encoding="utf-8")
    after = transform(before)
    if after != before:
        path.write_text(after, encoding="utf-8")


def patch_enforce(text: str) -> str:
    text = replace(text, "from pathlib import Path\n", "from pathlib import Path\nfrom fa3_release_baseline import load_active_release_baseline\n", "enforce baseline import")
    text = text.replace('RELEASE="2026-08-23/v3.0.11"\nCAPS=143\n', "")
    text = text.replace('  3:"143 capability catalog validation PASS",', '  3:"active release capability catalog validation PASS",')
    text = replace(
        text,
        'def finding(code,msg,**kw):\n    return {"code":code,"severity":"P0","message":msg,**kw}\n\ndef static_check(root:Path):\n    fs=[]',
        'def finding(code,msg,**kw):\n    return {"code":code,"severity":"P0","message":msg,**kw}\n\ndef active_release_values(root:Path):\n    baseline=load_active_release_baseline(root)\n    return baseline.release,baseline.capability_count\n\ndef static_check(root:Path):\n    RELEASE,CAPS=active_release_values(root)\n    fs=[]',
        "enforce static baseline",
    )
    text = replace(text, 'def runtime_check(root:Path):\n    fs=[]', 'def runtime_check(root:Path):\n    RELEASE,CAPS=active_release_values(root)\n    fs=[]', "enforce runtime baseline")
    text = replace(text, 'def acceptance_check(root:Path):\n    s=static_check(root)', 'def acceptance_check(root:Path):\n    RELEASE,CAPS=active_release_values(root)\n    s=static_check(root)', "enforce acceptance baseline")
    text = replace(text, 'def promote(root:Path):\n    a=acceptance_check(root)', 'def promote(root:Path):\n    RELEASE,_=active_release_values(root)\n    a=acceptance_check(root)', "enforce promotion baseline")
    text = text.replace('range(1,144)', 'range(1,CAPS+1)')
    text = text.replace('"Capability catalog is not exact CAP-001..CAP-143"', 'f"Capability catalog is not exact CAP-001..CAP-{CAPS:03d}"')
    text = text.replace('"Evidence Registry is not exact 143 capability set"', 'f"Evidence Registry is not exact {CAPS} capability set"')
    text = text.replace('["143 capability validation not PASS"]', '[f"{CAPS} capability validation not PASS"]')
    return text


def patch_governance(text: str) -> str:
    text = replace(text, "from typing import Any\n", "from typing import Any\nfrom fa3_release_baseline import load_active_release_baseline\n", "governance baseline import")
    text = text.replace("EXPECTED_CAPABILITY_COUNT = 143\n", "")
    if '"baseline": "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"' not in text:
        text = text.replace('PATHS = {\n    "projection":', 'PATHS = {\n    "baseline": "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json",\n    "projection":')
    text = replace(text, '    projection = load_json(root, "projection")', '    expected_count = load_active_release_baseline(root).capability_count\n    projection = load_json(root, "projection")', "governance dynamic count")
    text = text.replace("EXPECTED_CAPABILITY_COUNT", "expected_count")
    return text


def patch_release_projection(text: str) -> str:
    text = replace(text, "from pathlib import Path\n", "from pathlib import Path\nfrom fa3_release_baseline import load_active_release_baseline\n", "release projection baseline import")
    text = text.replace('BASE_RELEASE = "2026-08-23/v3.0.11"\n', "")
    text = text.replace("CAPABILITY_COUNT = 143\n", "")
    text = replace(
        text,
        'def gate(root: Path):\n    root = Path(root).resolve()\n    findings = []',
        'def gate(root: Path):\n    root = Path(root).resolve()\n    active_baseline = load_active_release_baseline(root)\n    BASE_RELEASE = active_baseline.release\n    CAPABILITY_COUNT = active_baseline.capability_count\n    findings = []',
        "release projection dynamic baseline",
    )
    return text


def patch_release_scope(text: str) -> str:
    text = replace(text, "from typing import Any\n", "from typing import Any\nfrom fa3_release_baseline import BaselineError, load_active_release_baseline\n", "release scope baseline import")
    text = text.replace('CURRENT_RELEASE = "2026-08-23/v3.0.11"\nCURRENT_RELEASE_COUNT = 143\n', "")
    anchor = '    baseline = load_json(root, "baseline")'
    injected = '''    try:\n        active_baseline = load_active_release_baseline(root)\n    except BaselineError as exc:\n        return {\n            "schema": "fa3.release-evidence-scope-gate-report.v1",\n            "gate_set_id": GATESET_ID,\n            "baseline_id": BASELINE_ID,\n            "scope_id": SCOPE_ID,\n            "result": "FAIL",\n            "blocking_findings": 1,\n            "checks_passed": 0,\n            "checks_total": 18,\n            "findings": [finding("RESCOPE-003", str(exc))],\n        }\n    CURRENT_RELEASE = active_baseline.release\n    CURRENT_RELEASE_COUNT = active_baseline.capability_count\n    baseline = load_json(root, "baseline")'''
    text = replace(text, anchor, injected, "release scope dynamic baseline")
    return text


def patch_reconciler(text: str) -> str:
    text = replace(text, "import subprocess\nfrom pathlib import Path\n", "import subprocess\nimport sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parents[1] / \"src\"))\nfrom fa3_release_baseline import load_active_release_baseline\n", "reconciler baseline import")
    text = replace(
        text,
        'def reconcile(root: Path, projection_rel: str, policy_rel: str) -> dict:\n    projection_path = root / projection_rel',
        'def reconcile(root: Path, projection_rel: str, policy_rel: str) -> dict:\n    root = Path(root).resolve()\n    active_baseline = load_active_release_baseline(root)\n    capability_count = active_baseline.capability_count\n    projection_path = root / projection_rel',
        "reconciler dynamic baseline",
    )
    text = text.replace('    projection["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))', '    projection.setdefault("invariants", {})["canonical_capability_count"] = capability_count\n    projection["mandatory_reference_gates"] = list(policy.get("mandatory_reference_gates", []))')
    text = text.replace('"capability_count_after": 143,', '"capability_count_after": capability_count,')
    return text


def patch_governance_test(text: str) -> str:
    text = replace(text, "from fa3_governance_tiering_gate import PATHS, PROJECTION_ID, gate\n", "from fa3_governance_tiering_gate import PATHS, PROJECTION_ID, gate\nfrom fa3_release_baseline import load_active_release_baseline\n", "governance test baseline import")
    text = text.replace('self.assertEqual(result["canonical_capability_count"], 143)', 'self.assertEqual(result["canonical_capability_count"], load_active_release_baseline(self.repo_root).capability_count)')
    return text


def patch_release_scope_test(text: str) -> str:
    text = replace(text, "from fa3_release_evidence_scope_gate import BASELINE_ID, PATHS, SCOPE_ID, gate\n", "from fa3_release_evidence_scope_gate import BASELINE_ID, PATHS, SCOPE_ID, gate\nfrom fa3_release_baseline import load_active_release_baseline\n", "release scope test baseline import")
    text = text.replace('self.assertEqual(result["active_release_capability_count"], 143)', 'self.assertEqual(result["active_release_capability_count"], load_active_release_baseline(self.repo_root).capability_count)')
    text = text.replace('def test_143_cannot_be_reclassified_as_timeless(self)', 'def test_capability_count_cannot_be_reclassified_as_timeless(self)')
    return text


def apply(root: Path) -> None:
    root = Path(root).resolve()
    patches = {
        "src/fa3_enforce.py": patch_enforce,
        "src/fa3_governance_tiering_gate.py": patch_governance,
        "src/fa3_release_projection_gate.py": patch_release_projection,
        "src/fa3_release_evidence_scope_gate.py": patch_release_scope,
        "scripts/fa3_reconcile_release_projection.py": patch_reconciler,
        "tests/test_governance_tiering_gate.py": patch_governance_test,
        "tests/test_release_evidence_scope_gate.py": patch_release_scope_test,
    }
    for rel, transform in patches.items():
        patch(root / rel, transform)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply FA3 capability-count de-hardcode migration")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    apply(Path(args.root))
