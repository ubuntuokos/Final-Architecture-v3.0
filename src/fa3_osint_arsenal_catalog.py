#!/usr/bin/env python3
"""Offline, non-executing normalization of a pinned OSINT donor catalog.

This module only projects metadata for Reuse Discovery. It never downloads,
installs, imports, executes, probes, or activates any listed downstream tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

SOURCE_ROOT = Path("research/external-project-radar/osint/awesome-osint-arsenal")
PIN_PATH = SOURCE_ROOT / "pin.json"
SNAPSHOT_PATH = SOURCE_ROOT / "upstream/tools.json"
METHODS = frozenset({"web", "manual", "git", "apt", "pip", "go", "docker"})
RISK_REVIEW = frozenset({
    "red-team-offensive", "data-breach", "people-identity", "image-facial",
    "dark-web", "iot-devices", "hardware-hacking", "vpn-privacy",
    "bug-bounty", "search-dorking", "crypto-blockchain",
})
# A category hint is not an authorization or an executable provider binding.
CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "username-social": ("CAP-053",),
    "email-phone": ("CAP-053",),
    "domain-ip-network": ("CAP-054",),
    "geolocation": ("CAP-053",),
    "image-facial": ("CAP-035", "CAP-053"),
    "document-metadata": ("CAP-035", "CAP-053"),
    "company-business": ("CAP-053",),
    "vehicle-aviation-maritime": ("CAP-053",),
    "blue-team-defensive": ("CAP-051",),
    "malware-threat-intel": ("CAP-051",),
    "threat-intel-platforms": ("CAP-051",),
    "digital-forensics": ("CAP-035", "CAP-053"),
    "learning-resources": ("CAP-094",),
    "training-ctf": ("CAP-094",),
}
NO_AUTHORITY = {
    "authority": False,
    "automatic_fetch": False,
    "automatic_install": False,
    "automatic_activation": False,
    "automatic_provider_admission": False,
    "automatic_code_import": False,
    "runtime_promotion": False,
}


class CatalogError(ValueError):
    """Fail closed when provenance or source identity cannot be established."""


def git_blob_sha1(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def load_pin(path: Path) -> dict[str, Any]:
    pin = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(pin, dict)
            or pin.get("schema") != "fa3.osint-arsenal-source-pin.v1"
            or not re.fullmatch(r"[0-9a-f]{40}", pin.get("upstream_commit", ""))
            or not re.fullmatch(r"[0-9a-f]{40}", pin.get("upstream_catalog_git_blob_sha1", ""))
            or pin.get("snapshot_policy") != "IMMUTABLE_OFFLINE_REFERENCE_ONLY"
            or pin.get("authority") is not False
            or any(pin.get(k) is not False for k in (
                "automatic_fetch", "automatic_install", "automatic_provider_admission"
            ))):
        raise CatalogError("invalid or unsafe source pin")
    return pin


def safe_source_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname:
            return None
        if url.username or url.password or any(c.isspace() for c in value):
            return None
        return value
    except ValueError:
        return None


def normalize(content: bytes, pin: dict[str, Any]) -> dict[str, Any]:
    observed_blob = git_blob_sha1(content)
    if observed_blob != pin["upstream_catalog_git_blob_sha1"]:
        raise CatalogError("source blob does not match the immutable upstream pin")
    raw = json.loads(content.decode("utf-8"))
    if not isinstance(raw, list):
        raise CatalogError("tools.json root must be an array")
    rows: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    missing_url = 0
    categories: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise CatalogError("non-object tool at source position " + str(index))
        tool_id, name, category = item.get("id"), item.get("name"), item.get("category")
        if (not isinstance(tool_id, str)
                or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", tool_id)
                or not isinstance(name, str) or not name.strip()
                or not isinstance(category, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", category)):
            raise CatalogError("invalid required metadata at source position " + str(index))
        installation = item.get("install")
        method = installation.get("method") if isinstance(installation, dict) else None
        if method not in METHODS:
            raise CatalogError("unknown install method at source position " + str(index))
        original_url = item.get("url", "")
        if not isinstance(original_url, str):
            raise CatalogError("non-text source URL at position " + str(index))
        if not original_url:
            missing_url += 1
        validated_url = safe_source_url(original_url)
        categories.add(category)
        existing = rows.get(tool_id)
        if existing:
            if existing["category"] != category:
                raise CatalogError("conflicting duplicate tool category: " + tool_id)
            if existing["url"] and validated_url and existing["url"] != validated_url:
                raise CatalogError("conflicting duplicate source URLs: " + tool_id)
            if validated_url and not existing["url"]:
                existing["url"] = validated_url
                existing["url_status"] = "UNVERIFIED_EXTERNAL_LINK"
            existing["names"] = sorted(set(existing["names"] + [name]))
            existing["source_positions"].append(index)
            existing["install_method_hints"] = sorted(set(existing["install_method_hints"] + [method]))
            existing["review_class"] = "RESTRICTED_REVIEW" if category in RISK_REVIEW else "STANDARD_REVIEW"
            duplicates.append({"id": tool_id, "source_position": index, "merged_metadata_only": True})
            continue
        rows[tool_id] = {
            "id": tool_id,
            "name": name,
            "names": [name],
            "category": category,
            "url": validated_url,
            "url_status": (
                "MISSING" if not original_url else
                "UNVERIFIED_EXTERNAL_LINK" if validated_url else "INVALID_QUARANTINED"
            ),
            "source_positions": [index],
            "install_method_hints": [method],
            "capability_hints": list(CATEGORY_HINTS.get(category, ())),
            "review_class": "RESTRICTED_REVIEW" if category in RISK_REVIEW else "STANDARD_REVIEW",
            "status": "DISCOVERED_METADATA_ONLY",
            "downstream_license": "UNVERIFIED_PER_TOOL",
            **NO_AUTHORITY,
        }
    expected = {
        "snapshot_records": len(raw),
        "unique_tool_ids": len(rows),
        "normalized_categories": len(categories),
        "records_without_direct_url": missing_url,
    }
    for key, actual in expected.items():
        if pin.get(key) != actual:
            raise CatalogError("upstream pin/count mismatch: " + key)
    if pin.get("duplicate_id") != (duplicates[0]["id"] if len(duplicates) == 1 else None):
        raise CatalogError("unexpected duplicate source identity")
    if any(row["url_status"] == "INVALID_QUARANTINED" for row in rows.values()):
        raise CatalogError("unsafe source URLs require manual source repair")
    return {
        "schema": "fa3.osint-arsenal-catalog-projection.v1",
        "source": pin["source"],
        "upstream_commit": pin["upstream_commit"],
        "upstream_catalog_git_blob_sha1": observed_blob,
        "role": "NON_AUTHORITATIVE_OFFLINE_REUSE_DISCOVERY",
        "counts": {**expected, "duplicate_records": len(duplicates)},
        "duplicate_merges": duplicates,
        "categories": sorted(categories),
        "records": [rows[key] for key in sorted(rows)],
        **NO_AUTHORITY,
    }


def read_catalog(root: Path, *, source: Path | None = None, pin_file: Path | None = None) -> dict[str, Any]:
    pin = load_pin(pin_file or (root / PIN_PATH))
    catalog = source or (root / SNAPSHOT_PATH)
    return normalize(catalog.read_bytes(), pin)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".osint-catalog-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a pinned, offline, non-executing OSINT donor snapshot")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source", type=Path, help="Explicit local source; still checked against the supplied pin")
    parser.add_argument("--pin", type=Path, help="Explicit reviewed immutable pin")
    parser.add_argument("--check", action="store_true", help="Validate without writing")
    parser.add_argument("--summary", action="store_true", help="Show counts only")
    parser.add_argument("--output", type=Path, help="Materialize an untrusted metadata projection")
    args = parser.parse_args()
    try:
        catalog = read_catalog(args.root.resolve(), source=args.source, pin_file=args.pin)
        if args.output and not args.check:
            atomic_json(args.output, catalog)
        if args.summary or not args.output:
            print(json.dumps({"result": "PASS", **catalog["counts"], "role": catalog["role"]}, sort_keys=True))
        return 0
    except (CatalogError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"result": "FAIL", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
