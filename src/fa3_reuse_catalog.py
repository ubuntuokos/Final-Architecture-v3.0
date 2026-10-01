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


def _expanded_tokens(value: Any) -> list[str]:
    text = " ".join(_flatten_strings(value)).lower()
    whole = re.findall(r"[a-z0-9][a-z0-9_.:-]+", text)
    pieces = re.findall(r"[a-z0-9]+", text)
    return sorted(set(whole + pieces))


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
        if source.endswith("FA3-KHRONOS-ADAPTER-REGISTRY-001.json"):
            roles = list(obj.get("reuse_discovery_binding", {}).get("roles", []))
            for row in obj.get("adapters", []):
                if not isinstance(row, dict) or not row.get("id"):
                    continue
                add({
                    "candidate_id": str(row["id"]),
                    "candidate_class": "OPEN_STANDARD_ADAPTER",
                    "source_path": source,
                    "status": obj.get("status", "CANONICAL"),
                    "authority": False,
                    "capabilities": ["CAP-083"],
                    "tokens": _expanded_tokens({"source_family": "Khronos open standards", **row}),
                    "distribution_class": None,
                    "release_bundle_status": None,
                    "license": None,
                    "standard_family": "KHRONOS",
                    "project": row.get("project"),
                    "target": row.get("target"),
                    "mode": row.get("mode"),
                    "reuse_source_roles": roles,
                    "automatic_selection": False,
                })
        elif source.endswith("FA3-KHRONOS-OPEN-STANDARDS-INTEGRATION-001.json"):
            roles = list(obj.get("reuse_discovery_binding", {}).get("roles", []))
            capability = obj.get("capability")
            capabilities = [capability] if isinstance(capability, str) and capability else []
            for row in obj.get("bindings", []):
                if not isinstance(row, dict) or not row.get("layer"):
                    continue
                add({
                    "candidate_id": "FA3-KHRONOS-BINDING:" + str(row["layer"]),
                    "candidate_class": "OPEN_STANDARD_FABRIC_BINDING",
                    "source_path": source,
                    "status": "CANONICAL",
                    "authority": False,
                    "capabilities": capabilities,
                    "tokens": _expanded_tokens({"source_family": "Khronos open standards", **row}),
                    "distribution_class": None,
                    "release_bundle_status": None,
                    "license": None,
                    "standard_family": "KHRONOS",
                    "layer": row.get("layer"),
                    "projects": list(row.get("projects", [])) if isinstance(row.get("projects"), list) else [],
                    "mode": row.get("mode"),
                    "reuse_source_roles": roles,
                    "instruction_source": True,
                    "automatic_selection": False,
                })
        elif source.endswith("mcp-capability-registry.json"):
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
                expanded_tokens = set(_tokens(row))
                expanded_tokens.update(re.findall(r"[a-z0-9]+", " ".join(_flatten_strings(row)).lower()))
                add({
                    "candidate_id": f"EXTERNAL_SKILL_SOURCE:{repository}@{commit}",
                    "candidate_class": "EXTERNAL_SKILL_SOURCE",
                    "source_path": source,
                    "status": "REFERENCE_ONLY",
                    "authority": False,
                    "capabilities": [],
                    "tokens": sorted(expanded_tokens),
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

        elif source.endswith("FA3-DONOR-REFERENCE-REGISTRY-001.json"):
            for row in obj.get("entries", []):
                if not isinstance(row, dict) or not row.get("donor_id"):
                    continue
                status = str(row.get("status", "CANDIDATE"))
                if status == "SUPERSEDED" or row.get("discoverable_for_planning") is not True:
                    continue
                source_meta = row.get("source", {}) if isinstance(row.get("source"), dict) else {}
                license_meta = row.get("license", {}) if isinstance(row.get("license"), dict) else {}
                hints = list(row.get("capability_hints", [])) if isinstance(row.get("capability_hints"), list) else []
                canonical_caps = [str(x) for x in hints if isinstance(x, str) and re.fullmatch(r"CAP-[0-9]+", x)]
                add({
                    "candidate_id": str(row["donor_id"]),
                    "candidate_class": "DONOR_REFERENCE",
                    "source_path": source,
                    "status": status,
                    "authority": False,
                    "capabilities": sorted(set(canonical_caps)),
                    "tokens": _expanded_tokens({
                        "name": row.get("name"),
                        "source": source_meta,
                        "donor_modes": row.get("donor_modes", []),
                        "capability_hints": hints,
                        "domain_hints": row.get("domain_hints", []),
                        "problem_hints": row.get("problem_hints", []),
                        "target_hints": row.get("target_hints", []),
                        "tags": row.get("tags", []),
                        "notes": row.get("notes", []),
                    }),
                    "distribution_class": "REFERENCE_ONLY",
                    "release_bundle_status": "EXCLUDED",
                    "license": license_meta.get("declared"),
                    "donor_name": row.get("name"),
                    "source_kind": source_meta.get("kind"),
                    "source_locator": source_meta.get("locator"),
                    "source_normalized_key": source_meta.get("normalized_key"),
                    "donor_modes": list(row.get("donor_modes", [])) if isinstance(row.get("donor_modes"), list) else [],
                    "capability_hints": hints,
                    "domain_hints": list(row.get("domain_hints", [])) if isinstance(row.get("domain_hints"), list) else [],
                    "problem_hints": list(row.get("problem_hints", [])) if isinstance(row.get("problem_hints"), list) else [],
                    "target_hints": list(row.get("target_hints", [])) if isinstance(row.get("target_hints"), list) else [],
                    "code_reuse_policy": row.get("code_reuse_policy"),
                    "discoverable_for_planning": True,
                    "automatic_selection": False,
                    "automatic_fetch": False,
                    "automatic_install": False,
                    "automatic_activation": False,
                    "automatic_dependency": False,
                    "automatic_code_import": False,
                    "automatic_provider_admission": False,
                    "automatic_model_selection": False,
                })

    entries.sort(key=lambda row: (row["candidate_class"], row["candidate_id"], row["source_path"]))
    return {
        "schema": "fa3.reuse-catalog.snapshot.v1",
        "policy_id": policy.get("id"),
        "authority": False,
        "derived": True,
        "rebuildable": True,
        "entry_count": len(entries),
        "mandatory_source_reviews": list(policy.get("mandatory_source_reviews", [])),
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
