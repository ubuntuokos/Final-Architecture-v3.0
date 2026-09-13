#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASELINE_PATH = "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
BASELINE_ID = "FA3-RELEASE-CAPABILITY-BASELINE-001"
BASELINE_SCHEMA = "fa3.release-capability-baseline.v1"


class BaselineError(RuntimeError):
    """Raised when the active FA3 release baseline is missing, ambiguous or inconsistent."""


@dataclass(frozen=True)
class ActiveReleaseBaseline:
    release: str
    capability_count: int
    record: dict[str, Any]
    document: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BaselineError(f"missing active release baseline: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise BaselineError(f"unreadable active release baseline: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BaselineError("active release baseline must be a JSON object")
    return data


def load_active_release_baseline(root: Path) -> ActiveReleaseBaseline:
    root = Path(root).resolve()
    data = _load_json(root / BASELINE_PATH)

    if data.get("schema") != BASELINE_SCHEMA or data.get("id") != BASELINE_ID:
        raise BaselineError("release baseline schema/id drift")
    if data.get("baseline_semantics") != "RELEASE_SCOPED":
        raise BaselineError("release baseline is not RELEASE_SCOPED")

    release = data.get("current_release")
    count = data.get("current_release_capability_count")
    if not isinstance(release, str) or not release.strip():
        raise BaselineError("current_release is missing")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise BaselineError("current_release_capability_count must be a positive integer")

    records = data.get("release_baselines")
    if not isinstance(records, list):
        raise BaselineError("release_baselines must be a list")
    active = [r for r in records if isinstance(r, dict) and r.get("status") == "ACTIVE_BASELINE"]
    if len(active) != 1:
        raise BaselineError(f"expected exactly one ACTIVE_BASELINE, found {len(active)}")
    record = active[0]
    if record.get("release") != release:
        raise BaselineError("ACTIVE_BASELINE release does not match current_release")
    if record.get("capability_count") != count:
        raise BaselineError("ACTIVE_BASELINE capability_count does not match current release count")

    return ActiveReleaseBaseline(release=release, capability_count=count, record=record, document=data)


def repository_root_from_module(module_file: str | Path) -> Path:
    module_path = Path(module_file).resolve()
    for parent in module_path.parents:
        if (parent / BASELINE_PATH).is_file():
            return parent
    raise BaselineError(f"cannot locate FA3 repository root from module path: {module_path}")


def module_active_release_baseline(module_file: str | Path) -> ActiveReleaseBaseline:
    return load_active_release_baseline(repository_root_from_module(module_file))


def module_active_capability_count(module_file: str | Path) -> int:
    return module_active_release_baseline(module_file).capability_count


def module_active_release(module_file: str | Path) -> str:
    return module_active_release_baseline(module_file).release


def active_release(root: Path) -> str:
    return load_active_release_baseline(root).release


def active_capability_count(root: Path) -> int:
    return load_active_release_baseline(root).capability_count
