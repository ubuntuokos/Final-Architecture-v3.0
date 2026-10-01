#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

from fa3_license_rights import evaluate_descriptor

AUDIT_ID = "FA3-LICENSE-RIGHTS-AUDIT-001"
SCHEMA = "fa3.license-rights-audit-inventory.v1"

TEXT_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".fish", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".jsx", ".java", ".kt", ".kts", ".go", ".rs", ".c", ".cc", ".cpp", ".cxx", ".h",
    ".hh", ".hpp", ".hxx", ".cs", ".rb", ".php", ".lua", ".pl", ".pm", ".swift",
    ".qml", ".xml", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".md", ".rst",
    ".txt", ".json", ".jsonl", ".csv",
}
CODE_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".fish", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".jsx", ".java", ".kt", ".kts", ".go", ".rs", ".c", ".cc", ".cpp", ".cxx", ".h",
    ".hh", ".hpp", ".hxx", ".cs", ".rb", ".php", ".lua", ".pl", ".pm", ".swift", ".qml",
}
MODEL_SUFFIXES = {".gguf", ".safetensors", ".onnx", ".pt", ".pth", ".ckpt", ".tflite", ".engine"}
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".wav", ".mp3", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm"}
DATASET_SUFFIXES = {".parquet", ".arrow", ".feather"}
DEPENDENCY_NAMES = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock", "pdm.lock",
    "uv.lock", "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "Cargo.toml", "Cargo.lock", "go.mod", "go.sum", "Gemfile", "Gemfile.lock",
    "composer.json", "composer.lock",
}
DISTRIBUTION_SCOPE_DIRS = ("canonical/providers", "canonical/references", "canonical/third-party")
UNKNOWN_LICENSE_MARKERS = {"", "UNKNOWN", "UNVERIFIED", "PENDING", "NOASSERTION", "NONE", "UNCLASSIFIED"}
IMMUTABLE_REVISION = re.compile(r"^[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?$")

LICENSE_NAMES = {
    "license", "license.txt", "license.md", "copying", "copying.txt", "notice",
    "third-party.md", "third_party.md", "third-party-notices.txt", "licenses",
}


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        return sorted(
            p for p in proc.stdout.decode("utf-8", "surrogateescape").split("\0")
            if p and not p.startswith(("reports/", "acceptance/", "promotion/"))
        )
    return sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    )


def reuse_patterns(root: Path) -> list[str]:
    path = root / "REUSE.toml"
    if not path.is_file():
        return []
    obj = tomllib.loads(path.read_text(encoding="utf-8"))
    out: list[str] = []
    for annotation in obj.get("annotations", []):
        if annotation.get("SPDX-License-Identifier"):
            out.extend(str(x) for x in annotation.get("path", []))
    return out


def reuse_covered(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in patterns)


def read_text_if_small(path: Path, max_bytes: int = 512_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def classify(rel: str) -> str:
    p = Path(rel)
    low = rel.lower()
    suffix = p.suffix.lower()
    name = p.name.lower()

    if rel.startswith(tuple(scope + "/" for scope in DISTRIBUTION_SCOPE_DIRS)):
        return "FA3_CANONICAL_METADATA"
    if rel.startswith("research/"):
        return "THIRD_PARTY_REFERENCE"
    if suffix in MODEL_SUFFIXES or "/models/" in low or low.startswith("models/"):
        return "MODEL_OR_WEIGHT"
    if suffix in FONT_SUFFIXES or "/fonts/" in low:
        return "FONT"
    if suffix in MEDIA_SUFFIXES or any(x in low for x in ("/assets/", "/media/", "/images/", "/audio/", "/video/")):
        return "CREATIVE_ASSET"
    if suffix in DATASET_SUFFIXES or any(x in low for x in ("/datasets/", "/dataset/", "/corpus/", "/data/")):
        return "DATASET_OR_DATA"
    if name in DEPENDENCY_NAMES or name.startswith("requirements-"):
        return "DEPENDENCY_MANIFEST"
    if "sdk" in low:
        return "SDK"
    if "codec" in low:
        return "CODEC"
    if suffix in CODE_SUFFIXES:
        return "SOURCE_CODE"
    if suffix in {".md", ".rst", ".txt"} or rel.startswith("docs/"):
        return "DOCUMENTATION"
    return "OTHER_TRACKED_FILE"


def explicit_license_metadata(text: str) -> bool:
    low = text.lower()
    return (
        "spdx-license-identifier:" in low
        or '"license"' in low
        or '"license_status"' in low
        or '"license_and_rights"' in low
        or '"distribution_class"' in low
        or '"rights"' in low
    )


def severity_for(category: str, rel: str, text: str, *, has_spdx: bool, has_reuse: bool) -> tuple[str, str]:
    if category in {"MODEL_OR_WEIGHT", "DATASET_OR_DATA", "FONT", "CREATIVE_ASSET", "SDK", "CODEC"}:
        return "HIGH", "NON_CODE_RIGHTS_DOMAIN_REQUIRES_SEPARATE_REVIEW"
    if category in {"THIRD_PARTY_REFERENCE", "DEPENDENCY_MANIFEST"}:
        return "HIGH", "THIRD_PARTY_OR_DEPENDENCY_RIGHTS_REVIEW_REQUIRED"
    if category in {"SOURCE_CODE", "DOCUMENTATION", "FA3_CANONICAL_METADATA"}:
        if has_spdx or has_reuse or explicit_license_metadata(text):
            return "LOW", "EXPLICIT_FILE_OR_REUSE_LICENSE_EVIDENCE_PRESENT"
        return "MEDIUM", "FILE_OR_COMPONENT_LICENSE_PROVENANCE_TAGGING_REQUIRED"
    return "LOW", "CLASSIFICATION_RECORDED_NO_AUTOMATIC_CLEARANCE"


def _known_license(value: Any) -> str | None:
    if isinstance(value, str):
        token = value.strip()
        if token and token.upper() not in UNKNOWN_LICENSE_MARKERS:
            return token
        return None
    if isinstance(value, dict):
        for key in ("effective", "concluded", "spdx_expression", "spdx", "declared", "id", "license"):
            token = _known_license(value.get(key))
            if token:
                return token
    return None


def _immutable_revision(value: Any) -> str | None:
    if isinstance(value, dict):
        preferred = (
            "commit", "revision", "upstream_commit", "source_commit", "immutable_commit",
            "git_commit", "repository_commit", "sha", "sha256",
        )
        for key in preferred:
            raw = value.get(key)
            if isinstance(raw, str) and IMMUTABLE_REVISION.fullmatch(raw.strip()):
                return raw.strip().lower()
        for child in value.values():
            found = _immutable_revision(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _immutable_revision(child)
            if found:
                return found
    return None


def _distribution_fields(row: dict[str, Any]) -> tuple[str | None, str | None]:
    dist = row.get("distribution") if isinstance(row.get("distribution"), dict) else {}
    cls = dist.get("class") or row.get("distribution_class")
    status = dist.get("release_bundle_status")
    if status not in {"INCLUDED", "EXCLUDED"}:
        allowed = dist.get("product_bundle_allowed")
        if allowed is None:
            allowed = row.get("product_bundle_allowed")
        if allowed is not None:
            status = "INCLUDED" if allowed is True else "EXCLUDED"
    return (str(cls) if cls else None, str(status) if status else None)


def canonical_subject_records(root: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for scope in DISTRIBUTION_SCOPE_DIRS:
        base = root / scope
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                row = loadj(path)
            except Exception:
                continue
            subject_id = row.get("id") or row.get("subject_id")
            if not isinstance(subject_id, str) or not subject_id.strip():
                continue
            cls, status = _distribution_fields(row)
            license_value = _known_license(row.get("license"))
            if not license_value:
                license_value = _known_license(row.get("license_and_rights"))
            if not license_value:
                license_value = _known_license(row.get("license_status"))
            records[subject_id] = {
                "subject_id": subject_id,
                "record_path": path.relative_to(root).as_posix(),
                "class": cls,
                "release_bundle_status": status,
                "license": license_value,
                "immutable_revision": _immutable_revision(row),
            }
    return records


def build_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    paths = tracked_files(root)
    patterns = reuse_patterns(root)

    distribution = loadj(root / "canonical/distribution-manifest.json")
    distribution_registry = loadj(root / "canonical/distribution-registry.json")
    included_ids = {
        str(row.get("subject_id"))
        for row in distribution.get("included", [])
        if row.get("release_bundle_status") == "INCLUDED"
    }
    excluded_ids = {
        str(row.get("subject_id"))
        for row in distribution.get("excluded", [])
        if row.get("release_bundle_status") == "EXCLUDED"
    }

    distribution_by_id = {
        str(row.get("subject_id")): row
        for row in distribution_registry.get("records", [])
        if isinstance(row, dict) and row.get("subject_id")
    }
    canonical_records = canonical_subject_records(root)

    descriptor_registry_path = root / "canonical/license-rights-descriptor-registry.json"
    descriptor_registry = loadj(descriptor_registry_path) if descriptor_registry_path.is_file() else {"entries": []}
    rights_policy_path = root / "canonical/license-rights-policy.json"
    rights_policy = loadj(rights_policy_path) if rights_policy_path.is_file() else {"id": "FA3-LICENSE-RIGHTS-POLICY-001"}
    descriptor_rows = {
        str(row.get("subject_id")): row
        for row in descriptor_registry.get("entries", [])
        if isinstance(row, dict) and row.get("subject_id")
    }
    cleared_release_ids: set[str] = set()
    descriptor_results: dict[str, dict[str, Any]] = {}
    for subject_id in sorted(included_ids):
        row = descriptor_rows.get(subject_id, {})
        descriptor_rel = row.get("descriptor")
        if not isinstance(descriptor_rel, str) or not descriptor_rel:
            continue
        descriptor_path = root / descriptor_rel
        if not descriptor_path.is_file():
            continue
        descriptor = loadj(descriptor_path)
        decision = evaluate_descriptor(descriptor, rights_policy)
        descriptor_results[subject_id] = {
            "descriptor": descriptor_rel,
            "result": decision.get("result"),
            "admitted_for_release": decision.get("admitted_for_release"),
            "disposition": decision.get("disposition"),
            "findings": decision.get("findings", []),
        }
        if decision.get("result") == "PASS" and decision.get("admitted_for_release") is True:
            cleared_release_ids.add(subject_id)

    unresolved_release_ids = included_ids - cleared_release_ids

    subjects: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    category_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    spdx_tagged = 0
    reuse_tagged = 0

    for rel in paths:
        path = root / rel
        category = classify(rel)
        category_counts[category] += 1
        text = read_text_if_small(path) if path.suffix.lower() in TEXT_SUFFIXES or path.name.lower() in LICENSE_NAMES else ""
        has_spdx = "SPDX-License-Identifier:" in text
        has_reuse = reuse_covered(rel, patterns)
        has_license_meta = explicit_license_metadata(text)

        if has_spdx:
            spdx_tagged += 1
        if has_reuse:
            reuse_tagged += 1

        severity, reason = severity_for(category, rel, text, has_spdx=has_spdx, has_reuse=has_reuse)
        severity_counts[severity] += 1

        subject = {
            "path": rel,
            "category": category,
            "spdx_file_tag": has_spdx,
            "reuse_annotation": has_reuse,
            "explicit_license_or_rights_metadata": has_license_meta,
            "automatic_legal_clearance": False,
        }
        subjects.append(subject)

        if severity != "LOW":
            queue.append({
                "path": rel,
                "category": category,
                "severity": severity,
                "reason": reason,
                "required_action": (
                    "Collect immutable source/license/right evidence, conclude the effective rights disposition, "
                    "materialize obligations, and bind a LicenseRightsDescriptor or an explicit reference-only/excluded decision."
                ),
            })

    # Distribution subjects are rights subjects even if their IDs do not map 1:1 to filenames.
    for subject_id in sorted(unresolved_release_ids):
        queue.append({
            "subject_id": subject_id,
            "category": "RELEASE_INCLUDED_SUBJECT",
            "severity": "BLOCKING",
            "reason": "RELEASE_INCLUDED_SUBJECT_REQUIRES_EXPLICIT_RIGHTS_DESCRIPTOR",
            "required_action": "Bind an evidence-backed LicenseRightsDescriptor before release audit closure.",
        })
        severity_counts["BLOCKING"] += 1

    external_subjects: list[dict[str, Any]] = []
    resolved_reference_only_ids: set[str] = set()
    for subject_id in sorted(excluded_ids):
        registry_row = distribution_by_id.get(subject_id, {})
        record = canonical_records.get(subject_id, {})
        cls = registry_row.get("class") or record.get("class")
        release_status = registry_row.get("release_bundle_status") or record.get("release_bundle_status") or "EXCLUDED"
        license_value = record.get("license")
        immutable_revision = record.get("immutable_revision")
        reference_resolved = (
            cls == "REFERENCE_ONLY"
            and release_status == "EXCLUDED"
            and isinstance(license_value, str)
            and bool(license_value.strip())
            and isinstance(immutable_revision, str)
            and bool(immutable_revision.strip())
        )
        resolution = "REFERENCE_ONLY_EVIDENCE_BACKED" if reference_resolved else "REVIEW_REQUIRED"
        external_subjects.append({
            "subject_id": subject_id,
            "record_path": record.get("record_path"),
            "distribution_class": cls,
            "release_bundle_status": release_status,
            "license": license_value,
            "immutable_revision": immutable_revision,
            "resolution": resolution,
            "automatic_legal_clearance": False,
        })
        if reference_resolved:
            resolved_reference_only_ids.add(subject_id)
            continue
        severity = "MEDIUM" if cls == "FA3_NATIVE" else "HIGH"
        queue.append({
            "subject_id": subject_id,
            "category": "EXCLUDED_EXTERNAL_OR_REFERENCE_SUBJECT",
            "severity": severity,
            "reason": "EXCLUDED_SUBJECT_REQUIRES_PROVENANCE_LICENSE_OR_RIGHTS_COMPLETION",
            "distribution_class": cls,
            "record_path": record.get("record_path"),
            "required_action": (
                "Record immutable source revision and license/right evidence. REFERENCE_ONLY may be resolved "
                "without bundle admission only when immutable provenance and a known license are both present."
            ),
        })
        severity_counts[severity] += 1

    queue.sort(key=lambda x: (
        {"BLOCKING": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.get("severity", "LOW"), 9),
        x.get("path", x.get("subject_id", "")),
    ))

    summary = {
        "tracked_files": len(paths),
        "subjects_scanned": len(subjects),
        "work_queue_items": len(queue),
        "release_included_subjects": len(included_ids),
        "rights_descriptor_cleared_release_subjects": len(cleared_release_ids),
        "unique_release_blockers": len(unresolved_release_ids),
        "excluded_external_or_reference_subjects": len(excluded_ids),
        "external_subjects_scanned": len(external_subjects),
        "evidence_backed_reference_only_subjects": len(resolved_reference_only_ids),
        "unresolved_excluded_subjects": len(excluded_ids - resolved_reference_only_ids),
        "spdx_file_tagged": spdx_tagged,
        "reuse_annotated": reuse_tagged,
        "category_counts": dict(sorted(category_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
    }
    return {
        "schema": SCHEMA,
        "audit_id": AUDIT_ID,
        "result": "PASS",
        "audit_closure_status": "BLOCKED",
        "audit_state": "IN_PROGRESS_RETROACTIVE_AUDIT",
        "summary": summary,
        "work_queue": queue,
        "subjects": subjects,
        "release_descriptor_results": descriptor_results,
        "external_subjects": external_subjects,
        "invariants": {
            "automatic_inventory_is_not_legal_clearance": True,
            "third_party_relicense_forbidden": True,
            "historical_evidence_overwrite_forbidden": True,
            "release_eligible": False,
        },
    }


def gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    try:
        plan = loadj(root / "canonical/license-rights-audit-plan.json")
        status = loadj(root / "canonical/license-rights-audit-status.json")
        gate_record = loadj(root / "canonical/FA3-GATE-LICENSE-RIGHTS-AUDIT-001.json")
        inventory = build_inventory(root)
    except Exception as exc:
        return {
            "schema": "fa3.license-rights-audit-gate-report.v1",
            "gate_id": "FA3-GATE-LICENSE-RIGHTS-AUDIT-001",
            "result": "FAIL",
            "audit_closure_status": "BLOCKED",
            "findings": [{"code": "LRA-000", "message": "audit inventory unreadable", "error": repr(exc)}],
        }

    if plan.get("id") != "FA3-LICENSE-RIGHTS-AUDIT-PLAN-001":
        findings.append({"code": "LRA-010", "message": "audit plan identity drift"})
    if gate_record.get("fail_closed") is not True:
        findings.append({"code": "LRA-011", "message": "audit gate must remain fail-closed"})
    if status.get("status") not in {"PENDING_RETROACTIVE_AUDIT", "IN_PROGRESS_RETROACTIVE_AUDIT", "PASS"}:
        findings.append({"code": "LRA-012", "message": "unknown retroactive audit state"})
    if status.get("status") != "PASS":
        if status.get("release_eligible") is not False or status.get("global_runtime_promotion_claim") is not False:
            findings.append({"code": "LRA-013", "message": "unfinished audit must block release and global promotion"})
        if inventory.get("audit_closure_status") != "BLOCKED":
            findings.append({"code": "LRA-014", "message": "unfinished audit inventory must remain BLOCKED"})
    if not inventory.get("work_queue"):
        findings.append({"code": "LRA-015", "message": "retroactive audit work queue unexpectedly empty"})
    if inventory.get("invariants", {}).get("automatic_inventory_is_not_legal_clearance") is not True:
        findings.append({"code": "LRA-016", "message": "inventory may not claim automatic legal clearance"})
    if status.get("release_included_subject_rights_status") == "PASS":
        blockers = int(inventory.get("summary", {}).get("unique_release_blockers", -1))
        if blockers != 0:
            findings.append({"code": "LRA-017", "message": "release-included rights phase marked PASS but unresolved release blockers remain", "blockers": blockers})
        cleared = int(inventory.get("summary", {}).get("rights_descriptor_cleared_release_subjects", -1))
        included = int(inventory.get("summary", {}).get("release_included_subjects", -1))
        if cleared != included:
            findings.append({"code": "LRA-018", "message": "release-included rights phase marked PASS but descriptor coverage is incomplete", "cleared": cleared, "included": included})

    result = {
        "schema": "fa3.license-rights-audit-gate-report.v1",
        "gate_id": "FA3-GATE-LICENSE-RIGHTS-AUDIT-001",
        "result": "PASS" if not findings else "FAIL",
        "audit_closure_status": "PASS" if status.get("status") == "PASS" and not findings else "BLOCKED",
        "findings": findings,
        "summary": inventory.get("summary", {}),
        "release_eligible": status.get("release_eligible", False),
    }
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "license-rights-retroactive-audit-inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (reports / "license-rights-retroactive-audit-gate-report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    result = gate(Path(args.root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
