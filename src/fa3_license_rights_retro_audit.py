#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from fa3_license_rights import evaluate_descriptor

JEV_PREFIX = "research/external-project-radar/jev/upstream/a27922ad457389775f4fe4eadcf688afc9d36d83/"
EXPECTED_JEV_LOCAL_FILES = {
    JEV_PREFIX + "README.md",
    JEV_PREFIX + "VERIFICATION.md",
    JEV_PREFIX + "manifest.json",
    JEV_PREFIX + "public/llms-full.txt",
    JEV_PREFIX + "public/llms.txt",
    JEV_PREFIX + "src/data/radar.json",
    JEV_PREFIX + "src/data/taxonomy.json",
}
MODEL_EXTENSIONS = {".gguf", ".safetensors", ".onnx", ".pt", ".pth", ".ckpt"}
FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2", ".eot"}
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".wav", ".mp3", ".ogg", ".flac", ".mp4", ".mov", ".mkv", ".webm"}


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def tracked_files(root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace"))
    return sorted(x for x in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if x)


def run_audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    policy = loadj(root / "canonical/license-rights-policy.json")
    status = loadj(root / "canonical/license-rights-audit-status.json")
    inventory = loadj(root / "canonical/license-rights-retro-audit-inventory.json")
    distribution = loadj(root / "canonical/distribution-manifest.json")
    descriptor = loadj(root / "canonical/descriptors/FA3-RIGHTS-JEV-RADAR-SNAPSHOT-001.json")

    findings: list[dict[str, Any]] = []
    files = tracked_files(root)
    file_set = set(files)

    descriptor_result = evaluate_descriptor(descriptor, policy)
    if descriptor_result["result"] != "PASS" or descriptor_result["admitted_for_release"] is not True:
        findings.append({"code": "RETRO-001", "message": "Jev snapshot rights descriptor is not release-admissible"})

    missing_snapshot = sorted(EXPECTED_JEV_LOCAL_FILES - file_set)
    extra_snapshot = sorted(
        x for x in file_set if x.startswith(JEV_PREFIX) and x not in EXPECTED_JEV_LOCAL_FILES
    )
    if missing_snapshot:
        findings.append({"code": "RETRO-002", "message": "Pinned Jev snapshot file missing", "paths": missing_snapshot})
    if extra_snapshot:
        findings.append({"code": "RETRO-003", "message": "Unreviewed Jev snapshot file appeared", "paths": extra_snapshot})

    for required in (
        "LICENSES/third-party/logicrw-awesome-jev-projects-MIT.txt",
        "THIRD_PARTY_NOTICES.md",
    ):
        if required not in file_set:
            findings.append({"code": "RETRO-004", "message": "Required third-party notice artifact missing", "path": required})

    if distribution.get("included_external_count") != 0:
        findings.append({
            "code": "RETRO-005",
            "message": "External distribution subject is included without this historical audit classifying it",
            "included_external_count": distribution.get("included_external_count"),
        })

    model_files = [x for x in files if Path(x).suffix.lower() in MODEL_EXTENSIONS]
    font_files = [x for x in files if Path(x).suffix.lower() in FONT_EXTENSIONS]
    media_files = [x for x in files if Path(x).suffix.lower() in MEDIA_EXTENSIONS]

    if model_files:
        findings.append({"code": "RETRO-006", "message": "Model binaries require dedicated ModelLicenseDescriptor review", "paths": model_files})
    if font_files:
        findings.append({"code": "RETRO-007", "message": "Font files require dedicated font embedding/redistribution review", "paths": font_files})

    remaining = inventory.get("remaining_review_classes", [])
    blockers = [
        row.get("id")
        for row in remaining
        if isinstance(row, dict) and row.get("status") != "PASS"
    ]
    complete = not findings and not blockers

    if status.get("status") == "PASS" and not complete:
        findings.append({"code": "RETRO-008", "message": "Canonical audit status claims PASS while unresolved classes remain"})
    if status.get("release_eligible") is True and not complete:
        findings.append({"code": "RETRO-009", "message": "Release eligibility cannot be true while historical rights audit is incomplete"})

    report = {
        "schema": "fa3.license-rights-retro-audit-report.v1",
        "audit_id": "FA3-LICENSE-RIGHTS-AUDIT-001",
        "control_result": "PASS" if not findings else "FAIL",
        "repository_audit_status": "PASS" if complete else "PENDING_RETROACTIVE_AUDIT",
        "repository_audit_complete": complete,
        "release_eligible": complete,
        "tracked_file_count_current": len(files),
        "anchored_snapshot_commit": inventory.get("snapshot_commit"),
        "anchored_snapshot_tree": inventory.get("snapshot_tree"),
        "physically_vendored_upstream_file_count": len([x for x in files if x.startswith(JEV_PREFIX)]),
        "model_binary_count": len(model_files),
        "font_count": len(font_files),
        "media_asset_count": len(media_files),
        "distribution_included_external_count": distribution.get("included_external_count"),
        "resolved_third_party_subjects": ["FA3-RIGHTS-JEV-RADAR-SNAPSHOT-001"],
        "remaining_review_classes": blockers,
        "findings": findings,
        "global_promotion_claim": False,
    }
    out = root / "reports/license-rights-retro-audit-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = run_audit(Path(args.root))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["control_result"] != "PASS":
        return 2
    if args.require_complete and not report["repository_audit_complete"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
