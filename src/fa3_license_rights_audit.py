#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

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

    if rel.startswith("canonical/providers/"):
        return "PROVIDER_OR_SERVICE"
    if rel.startswith("canonical/references/") or rel.startswith("research/"):
        return "THIRD_PARTY_REFERENCE"
    if "donor" in low and rel.startswith(("canonical/", "docs/", "research/")):
        return "DONOR_OR_REFERENCE"
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


def severity_for(category: str, rel: str, text: str) -> tuple[str, str]:
    if category in {"MODEL_OR_WEIGHT", "DATASET_OR_DATA", "FONT", "CREATIVE_ASSET", "SDK", "CODEC"}:
        return "HIGH", "NON_CODE_RIGHTS_DOMAIN_REQUIRES_SEPARATE_REVIEW"
    if category in {"PROVIDER_OR_SERVICE", "THIRD_PARTY_REFERENCE", "DONOR_OR_REFERENCE", "DEPENDENCY_MANIFEST"}:
        return "HIGH", "THIRD_PARTY_OR_DEPENDENCY_RIGHTS_REVIEW_REQUIRED"
    if category in {"SOURCE_CODE", "DOCUMENTATION"} and not explicit_license_metadata(text):
        return "MEDIUM", "FILE_OR_COMPONENT_LICENSE_PROVENANCE_TAGGING_REQUIRED"
    return "LOW", "CLASSIFICATION_RECORDED_NO_AUTOMATIC_CLEARANCE"


def build_inventory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    paths = tracked_files(root)
    patterns = reuse_patterns(root)

    distribution = loadj(root / "canonical/distribution-manifest.json")
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

        severity, reason = severity_for(category, rel, text)
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
    for subject_id in sorted(included_ids):
        queue.append({
            "subject_id": subject_id,
            "category": "RELEASE_INCLUDED_SUBJECT",
            "severity": "BLOCKING",
            "reason": "RELEASE_INCLUDED_SUBJECT_REQUIRES_EXPLICIT_RIGHTS_DESCRIPTOR",
            "required_action": "Bind an evidence-backed LicenseRightsDescriptor before release audit closure.",
        })
        severity_counts["BLOCKING"] += 1

    for subject_id in sorted(excluded_ids):
        queue.append({
            "subject_id": subject_id,
            "category": "EXCLUDED_EXTERNAL_OR_REFERENCE_SUBJECT",
            "severity": "HIGH",
            "reason": "EXCLUSION_DOES_NOT_REMOVE_PROVENANCE_OR_REFERENCE_LICENSE_RECORDING_REQUIREMENT",
            "required_action": "Record source revision, declared/detected license evidence and retained reference-only/excluded disposition.",
        })
        severity_counts["HIGH"] += 1

    queue.sort(key=lambda x: (
        {"BLOCKING": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(x.get("severity", "LOW"), 9),
        x.get("path", x.get("subject_id", "")),
    ))

    summary = {
        "tracked_files": len(paths),
        "subjects_scanned": len(subjects),
        "work_queue_items": len(queue),
        "release_included_subjects": len(included_ids),
        "unique_release_blockers": len(included_ids),
        "excluded_external_or_reference_subjects": len(excluded_ids),
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
