#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

CATALOG_POLICY = "canonical/FA3-REUSE-CATALOG-001.json"
DISTRIBUTION_REGISTRY = "canonical/distribution-registry.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def _classification(path: str) -> str:
    if path.startswith("canonical/profiles/"):
        return "PROFILE"
    if path.startswith("canonical/contracts/"):
        return "CONTRACT"
    if path.startswith("canonical/providers/"):
        return "PROVIDER"
    if path.startswith("canonical/actions/"):
        return "UAF_ACTION"
    if path.startswith("canonical/references/"):
        return "UPSTREAM_REFERENCE"
    if path.startswith("canonical/patterns/"):
        return "REUSABLE_PATTERN"
    if path.startswith("canonical/third-party/"):
        return "THIRD_PARTY_REFERENCE"
    if path.endswith("mcp-capability-registry.json"):
        return "CAPABILITY_REGISTRY"
    if path.endswith("FA3-GUI-SURFACE-REGISTRY-001.json"):
        return "GUI_PROJECTION_REGISTRY"
    return "DERIVED_IMPLEMENTATION"


def _tokens(obj: dict[str, Any]) -> list[str]:
    selected = {}
    for key in (
        "id", "name", "title", "description", "scope", "classification",
        "capability_projection", "capability_bindings", "contracts",
        "parent_profile", "parent_profiles", "provider_role",
        "problem_classes", "applicability", "invariants", "relationship",
        "skill_id", "package_id", "trigger", "eligibility",
        "repository", "role",
    ):
        if key in obj:
            selected[key] = obj[key]
    text = " ".join(_flatten_strings(selected))
    return sorted(set(re.findall(r"[a-z0-9][a-z0-9_.:-]+", text.lower())))


def _capabilities(obj: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("capability_projection", "capability_bindings", "capabilities"):
        value = obj.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    cid = item.get("capability_id") or item.get("id")
                    if isinstance(cid, str):
                        values.append(cid)
    return sorted(set(values))


def _distribution_map(root: Path) -> dict[str, dict[str, Any]]:
    path = root / DISTRIBUTION_REGISTRY
    if not path.is_file():
        return {}
    data = load_json(path)
    return {
        str(row.get("subject_id")): row
        for row in data.get("records", [])
        if isinstance(row, dict) and row.get("subject_id")
    }


def _generic_entry(root: Path, path: Path, obj: dict[str, Any], dist: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    rid = obj.get("id") or obj.get("x-fa3-contract-id") or path.stem
    distribution = dist.get(str(rid), {})
    return {
        "candidate_id": str(rid),
        "candidate_class": _classification(rel),
        "source_path": rel,
        "status": obj.get("status", "UNKNOWN"),
        "authority": bool(obj.get("architectural_authority", obj.get("authority", False))) if isinstance(obj.get("authority", False), bool) else False,
        "new_capability": obj.get("new_capability"),
        "new_architectural_authority": obj.get("new_architectural_authority"),
        "capabilities": _capabilities(obj),
        "tokens": _tokens(obj),
        "distribution_class": distribution.get("class"),
        "release_bundle_status": distribution.get("release_bundle_status"),
        "license": obj.get("license") or obj.get("upstream", {}).get("license") if isinstance(obj.get("upstream"), dict) else obj.get("license"),
    }


def build_catalog(root: Path) -> dict[str, Any]:
    root = root.resolve()
    policy = load_json(root / CATALOG_POLICY)
    dist = _distribution_map(root)
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(entry: dict[str, Any]) -> None:
        key = (str(entry.get("candidate_id")), str(entry.get("source_path")))
        if key not in seen:
            seen.add(key)
            entries.append(entry)

    for source in policy.get("source_roots", []):
        base = root / source
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                obj = load_json(path)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            add(_generic_entry(root, path, obj, dist))
            if path.as_posix().endswith("FA3-JEV-CODE-REUSE-001.json"):
                for row in obj.get("entries", []):
                    if not isinstance(row, dict):
                        continue
                    repo = row.get("source_repository")
                    commit = row.get("source_commit")
                    if not repo or not commit:
                        continue
                    add({
                        "candidate_id": f"THIRD_PARTY:{repo}@{commit}",
                        "candidate_class": "THIRD_PARTY_REFERENCE",
                        "source_path": path.relative_to(root).as_posix(),
                        "status": "REFERENCE",
                        "authority": False,
                        "capabilities": [],
                        "tokens": sorted(set(re.findall(r"[a-z0-9][a-z0-9_.:-]+", " ".join(_flatten_strings(row)).lower()))),
                        "distribution_class": row.get("distribution_class"),
                        "release_bundle_status": "EXCLUDED" if row.get("product_bundle_allowed") is False else None,
                        "license": row.get("license"),
                        "pattern_reimplementation_only": row.get("pattern_reimplementation_only") is True,
                    })

    for source in policy.get("explicit_sources", []):
        path = root / source
        if not path.is_file():
            continue
        obj = load_json(path)
        if not isinstance(obj, dict):
            continue
        if source.endswith("mcp-capability-registry.json"):
            for row in obj.get("capabilities", []):
                if not isinstance(row, dict) or not row.get("capability_id"):
                    continue
                add({
                    "candidate_id": row["capability_id"],
                    "candidate_class": "CAPABILITY",
                    "source_path": source,
                    "status": obj.get("status", "UNKNOWN"),
                    "authority": False,
                    "capabilities": [row["capability_id"]],
                    "tokens": _tokens(row),
                    "distribution_class": None,
                    "release_bundle_status": None,
                    "license": None,
                })
        elif source.endswith("FA3-GUI-SURFACE-REGISTRY-001.json"):
            for row in obj.get("surfaces", []):
                if not isinstance(row, dict) or not row.get("route_id"):
                    continue
                add({
                    "candidate_id": row["route_id"],
                    "candidate_class": "GUI_PROJECTION",
                    "source_path": source,
                    "status": obj.get("status", "UNKNOWN"),
                    "authority": False,
                    "capabilities": [],
                    "tokens": _tokens(row),
                    "distribution_class": None,
                    "release_bundle_status": None,
                    "license": None,
                })
        elif source.endswith("skill-registry.json"):
            for row in obj.get("entries", []):
                if not isinstance(row, dict) or not row.get("skill_id"):
                    continue
                admission_status = str(row.get("admission_status", "UNKNOWN"))
                entrypoint = row.get("entrypoint") if isinstance(row.get("entrypoint"), str) else source
                eligibility = row.get("eligibility", {}) if isinstance(row.get("eligibility"), dict) else {}
                add({
                    "candidate_id": str(row["skill_id"]),
                    "candidate_class": "SKILL",
                    "source_path": str(entrypoint),
                    "registry_source_path": source,
                    "status": admission_status,
                    "admission_status": admission_status,
                    "authority": bool(row.get("authority", False)),
                    "capabilities": [],
                    "tokens": _tokens(row),
                    "distribution_class": row.get("distribution_class"),
                    "release_bundle_status": None,
                    "license": None,
                    "package_id": row.get("package_id"),
                    "skill_version": row.get("version"),
                    "skill_trigger": row.get("trigger"),
                    "skill_task_classes": list(eligibility.get("task_classes", [])) if isinstance(eligibility.get("task_classes"), list) else [],
                    "task_scoped": row.get("task_scoped") is True,
                    "remote_fetch": row.get("remote_fetch") is True,
                    "skill_profile_id": row.get("profile_id"),
                    "admitted": admission_status == "ADMITTED",
                })
        elif source.endswith("FA3-EXTERNAL-SKILL-RADAR-001.json"):
            for row in obj.get("sources", []):
                if not isinstance(row, dict):
                    continue
                repository = row.get("repository")
                commit = row.get("commit")
                if not isinstance(repository, str) or not repository or not isinstance(commit, str) or not commit:
                    continue
                add({
                    "candidate_id": f"EXTERNAL_SKILL_SOURCE:{repository}@{commit}",
                    "candidate_class": "EXTERNAL_SKILL_SOURCE",
                    "source_path": source,
                    "status": "REFERENCE_ONLY",
                    "authority": False,
                    "capabilities": [],
                    "tokens": _tokens(row),
                    "distribution_class": row.get("classification"),
                    "release_bundle_status": "EXCLUDED",
                    "license": row.get("license"),
                    "repository": repository,
                    "source_commit": commit,
                    "reference_role": row.get("role"),
                    "admitted": False,
                    "automatic_fetch": False,
                    "automatic_install": False,
                    "automatic_activation": False,
                })

    entries.sort(key=lambda row: (row["candidate_class"], row["candidate_id"], row["source_path"]))
    return {
        "schema": "fa3.reuse-catalog.snapshot.v1",
        "policy_id": policy.get("id"),
        "authority": False,
        "derived": True,
        "rebuildable": True,
        "entry_count": len(entries),
        "entries": entries,
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Build the derived FA3 reuse catalog")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output")
    args = parser.parse_args()
    result = build_catalog(Path(args.root))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        if not path.is_absolute():
            path = Path(args.root) / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
