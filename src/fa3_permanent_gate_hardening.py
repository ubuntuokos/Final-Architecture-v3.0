#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable

from fa3_release_baseline import load_active_release_baseline

GATE_ID = "FA3-PERMANENT-GATE-HARDENING-GATESET-001"
CONFIG_REL = Path("canonical/FA3-PERMANENT-GATE-HARDENING-001.json")
GATE_REGISTRY_REL = Path("canonical/FA3-GATE-REGISTRY-001.json")
POLICY_REL = Path("canonical/enforcement-policy.json")
REPORT_REL = Path("reports/permanent-gate-hardening-report.json")
AUTHORITY_MANIFEST_REL = Path("reports/fa3-permanent-gate-authority-manifest.json")
BINDING_REL = Path("reports/fa3-permanent-gate-provenance-binding.json")
PRESERVATION_REL = Path("reports/fa3-permanent-gate-preservation.zip")
AUTHORITY_SNAPSHOT_REL = Path("reports/fa3-permanent-gate-authority-input-snapshot.json")

ACTION_USE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^#\s]+)(?:\s+#.*)?$")
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")
DEFAULT_CURRENT_HOST_WORKFLOW_MARKERS = ("current-host", "current_host", "fa3-current-host")
ALLOWED_PASS = "PASS"


def loadj(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def writej(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def explicit_gate_pass(value: Any) -> bool:
    return isinstance(value, str) and value == ALLOWED_PASS


def discover_current_host_workflows(
    root: Path, markers: Iterable[str]
) -> list[str]:
    workflow_root = root / ".github/workflows"
    normalized_markers = tuple(
        sorted({str(marker).strip().lower() for marker in markers if str(marker).strip()})
    )
    if not normalized_markers or not workflow_root.is_dir():
        return []
    discovered: list[str] = []
    for path in sorted(workflow_root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml"}:
            continue
        rel = path.relative_to(root).as_posix()
        name = path.name.lower()
        body = path.read_text(encoding="utf-8").lower()
        if any(marker in name or marker in body for marker in normalized_markers):
            discovered.append(rel)
    return discovered


def protected_action_pin_workflows(root: Path, config: dict[str, Any]) -> list[str]:
    paths = set(config.get("sha_pinned_workflows", []))
    if config.get("sha_pin_current_host_linked_workflows") is True:
        markers = config.get(
            "current_host_workflow_markers", DEFAULT_CURRENT_HOST_WORKFLOW_MARKERS
        )
        paths.update(discover_current_host_workflows(root, markers))
    return sorted(paths)


def scan_workflow_action_pins(
    root: Path, paths: Iterable[str]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for rel in paths:
        path = root / rel
        if not path.is_file():
            findings.append(
                {
                    "code": "PGH-020",
                    "path": rel,
                    "message": "protected workflow missing",
                }
            )
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            match = ACTION_USE.match(line)
            if not match:
                continue
            target = match.group(1)
            if target.startswith("./"):
                continue
            if not PINNED_ACTION.fullmatch(target):
                findings.append(
                    {
                        "code": "PGH-021",
                        "path": rel,
                        "line": lineno,
                        "target": target,
                        "message": (
                            "external GitHub Action is not immutable "
                            "40-hex SHA pinned"
                        ),
                    }
                )
    return findings


def validate_config(
    root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    config = loadj(root / CONFIG_REL)
    baseline = load_active_release_baseline(root)
    roles = config.get("carrier_roles", {})
    non_authorizing = set(config.get("non_authorizing_carriers", []))
    required_non_authorizing = {
        "EVIDENCE",
        "BINDING",
        "TRACE",
        "AUDIT",
        "READER",
        "DIAGNOSTIC",
        "PUBLICATION",
    }

    if config.get("id") != "FA3-PERMANENT-GATE-HARDENING-001":
        findings.append(
            {"code": "PGH-001", "message": "hardening config identity drift"}
        )
    if config.get("gate_id") != GATE_ID:
        findings.append(
            {"code": "PGH-002", "message": "hardening gate identity drift"}
        )
    if config.get("capability_count") != baseline.capability_count:
        findings.append(
            {
                "code": "PGH-003",
                "message": (
                    "hardening baseline does not follow active release baseline"
                ),
            }
        )
    if (
        config.get("new_capabilities") != 0
        or config.get("new_architectural_authorities") != 0
    ):
        findings.append(
            {
                "code": "PGH-004",
                "message": (
                    "hardening must not create capability or "
                    "architectural authority"
                ),
            }
        )
    if config.get("sha_pin_current_host_linked_workflows") is not True:
        findings.append(
            {
                "code": "PGH-012",
                "message": "Current Host-linked workflow immutable Action pin scope disabled",
            }
        )
    markers = config.get("current_host_workflow_markers")
    if not isinstance(markers, list) or not markers or any(
        not isinstance(marker, str) or not marker.strip() for marker in markers
    ):
        findings.append(
            {
                "code": "PGH-013",
                "message": "Current Host workflow marker configuration invalid",
            }
        )
    if config.get("current_host_runtime_promotion_claim") is not False:
        findings.append(
            {
                "code": "PGH-005",
                "message": "hardening may not claim Current Host promotion",
            }
        )
    if (
        roles.get("AUTHORITY")
        != "EXISTING_FA3_CANONICAL_AND_PROMOTION_PATH"
    ):
        findings.append(
            {
                "code": "PGH-006",
                "message": (
                    "authority carrier must remain the existing FA3 path"
                ),
            }
        )
    if (
        not required_non_authorizing.issubset(non_authorizing)
        or "AUTHORITY" in non_authorizing
    ):
        findings.append(
            {
                "code": "PGH-007",
                "message": "carrier authority separation drift",
            }
        )
    if config.get("manifest_role") != "TRACE_NOT_AUTHORITY":
        findings.append(
            {
                "code": "PGH-008",
                "message": "authority manifest gained decision authority",
            }
        )
    if (
        config.get("provenance_binding_role")
        != "BINDING_NOT_AUTHORITY"
    ):
        findings.append(
            {
                "code": "PGH-009",
                "message": "provenance binding gained decision authority",
            }
        )
    if config.get("preservation_role") != "AUDIT_COPY_NOT_AUTHORITY":
        findings.append(
            {
                "code": "PGH-010",
                "message": "preservation artifact gained decision authority",
            }
        )
    return config, findings


def gate(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, Any]] = []
    try:
        config, config_findings = validate_config(root)
        findings.extend(config_findings)
        registry = loadj(root / GATE_REGISTRY_REL)
        policy = loadj(root / POLICY_REL)
    except Exception as exc:
        report = {
            "schema": "fa3.permanent-gate-hardening-report.v1",
            "gate_id": GATE_ID,
            "result": "FAIL",
            "findings": [{"code": "PGH-000", "message": str(exc)}],
            "current_host_runtime_promotion_claim": False,
        }
        writej(root / REPORT_REL, report)
        return report

    mandatory = registry.get("mandatory_reference_gates", [])
    if (
        GATE_ID not in mandatory
        or policy.get("mandatory_reference_gates") != mandatory
    ):
        findings.append(
            {
                "code": "PGH-011",
                "message": (
                    "hardening gate is not mirrored through Gate Registry "
                    "and enforcement policy"
                ),
            }
        )

    findings.extend(
        scan_workflow_action_pins(
            root, protected_action_pin_workflows(root, config)
        )
    )

    rejected = [
        None,
        False,
        True,
        0,
        1,
        "",
        "pass",
        "Pass",
        "BLOCKED",
        "PENDING",
        "ERROR",
        {},
        [],
    ]
    if (
        not explicit_gate_pass("PASS")
        or any(explicit_gate_pass(x) for x in rejected)
    ):
        findings.append(
            {
                "code": "PGH-030",
                "message": "no-implicit-PASS semantics weakened",
            }
        )

    report = {
        "schema": "fa3.permanent-gate-hardening-report.v1",
        "gate_id": GATE_ID,
        "result": "PASS" if not findings else "FAIL",
        "capability_count": load_active_release_baseline(root).capability_count,
        "authority_delta": 0,
        "capability_delta": 0,
        "current_host_runtime_promotion_claim": False,
        "checks": {
            "carrier_authority_separation": not any(
                f["code"]
                in {"PGH-006", "PGH-007", "PGH-008", "PGH-009", "PGH-010"}
                for f in findings
            ),
            "immutable_action_pins": not any(
                f["code"] in {"PGH-012", "PGH-013", "PGH-020", "PGH-021"}
                for f in findings
            ),
            "no_implicit_pass": not any(
                f["code"] == "PGH-030" for f in findings
            ),
            "gate_registry_binding": not any(
                f["code"] == "PGH-011" for f in findings
            ),
        },
        "findings": findings,
    }
    writej(root / REPORT_REL, report)
    return report


def _subject(path: Path, root: Path, role: str) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "role": role,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def materialize(
    root: Path,
    *,
    base_sha: str,
    head_sha: str,
    published_main_sha: str,
    primary_result: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    hardening = gate(root)
    if hardening["result"] != "PASS":
        raise ValueError(
            "hardening gate must PASS before trace materialization"
        )
    if not explicit_gate_pass(primary_result):
        raise ValueError("primary result must be explicit PASS")

    baseline = load_active_release_baseline(root)
    registry = loadj(root / GATE_REGISTRY_REL)
    policy = loadj(root / POLICY_REL)

    inputs = []
    for rel, role in [
        (CONFIG_REL, "POLICY"),
        (GATE_REGISTRY_REL, "GATE_REGISTRY"),
        (POLICY_REL, "ENFORCEMENT_POLICY"),
        (
            Path("canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"),
            "RELEASE_BASELINE",
        ),
    ]:
        inputs.append(_subject(root / rel, root, role))

    report_subjects = []
    for rel in [
        REPORT_REL,
        Path("reports/static-gate-report.json"),
        Path("reports/gate-registry-gate-report.json"),
        Path("reports/governance-status-gate-report.json"),
        Path("reports/release-projection-gate-report.json"),
        Path("reports/reuse-discovery-gate-report.json"),
    ]:
        path = root / rel
        if path.is_file():
            report_subjects.append(_subject(path, root, "GATE_REPORT"))

    manifest = {
        "schema": "fa3.permanent-gate-authority-manifest.v1",
        "role": "TRACE_CARRIER",
        "creates_authority": False,
        "recomputes_primary_decision": False,
        "run_identity": {
            "base_sha": base_sha,
            "candidate_head_sha": head_sha,
            "published_main_sha": published_main_sha,
            "architecture_release": baseline.release,
            "capability_count": baseline.capability_count,
        },
        "authority": {
            "authority_path": "EXISTING_FA3_CANONICAL_AND_PROMOTION_PATH",
            "effective_mandatory_gate_ids": registry.get(
                "mandatory_reference_gates", []
            ),
            "fail_closed": policy.get("fail_closed") is True,
            "primary_result_recorded": primary_result,
        },
        "inputs": inputs,
        "gate_reports": report_subjects,
        "diagnostic_and_reader_outputs_are_non_authorizing": True,
    }
    writej(root / AUTHORITY_MANIFEST_REL, manifest)

    binding_subjects = (
        inputs
        + report_subjects
        + [
            _subject(
                root / AUTHORITY_MANIFEST_REL,
                root,
                "TRACE_CARRIER",
            )
        ]
    )
    binding = {
        "schema": "fa3.permanent-gate-provenance-binding.v1",
        "role": "BINDING_CARRIER",
        "creates_authority": False,
        "run_identity": manifest["run_identity"],
        "subjects": binding_subjects,
    }
    binding["binding_hash"] = sha256_bytes(canonical_json_bytes(binding))
    writej(root / BINDING_REL, binding)
    return manifest, binding


def verify_binding(
    root: Path, binding_path: Path | None = None
) -> dict[str, Any]:
    root = Path(root).resolve()
    path = binding_path or (root / BINDING_REL)
    binding = loadj(path)
    findings: list[dict[str, Any]] = []
    recorded_hash = binding.get("binding_hash")
    body = dict(binding)
    body.pop("binding_hash", None)
    if recorded_hash != sha256_bytes(canonical_json_bytes(body)):
        findings.append(
            {"code": "PGB-001", "message": "binding hash mismatch"}
        )
    for subject in binding.get("subjects", []):
        rel = subject.get("path")
        if (
            not isinstance(rel, str)
            or rel.startswith("/")
            or ".." in Path(rel).parts
        ):
            findings.append(
                {
                    "code": "PGB-002",
                    "message": "invalid subject path",
                    "path": rel,
                }
            )
            continue
        target = root / rel
        if not target.is_file():
            findings.append(
                {
                    "code": "PGB-003",
                    "message": "bound subject missing",
                    "path": rel,
                }
            )
            continue
        if (
            sha256_file(target) != subject.get("sha256")
            or target.stat().st_size != subject.get("size_bytes")
        ):
            findings.append(
                {
                    "code": "PGB-004",
                    "message": "bound subject digest/size mismatch",
                    "path": rel,
                }
            )
    return {
        "schema": "fa3.permanent-gate-provenance-verification.v1",
        "result": "PASS" if not findings else "FAIL",
        "binding_path": (
            path.relative_to(root).as_posix()
            if path.is_relative_to(root)
            else str(path)
        ),
        "findings": findings,
    }



def authority_input_snapshot(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    paths = sorted(
        [
            path
            for path in (root / "canonical").rglob("*")
            if path.is_file()
        ]
        + [
            root / ".github/workflows/fa3-permanent-enforcement.yml",
            root / ".github/workflows/fa3-permanent-control-plane.yml",
            root / ".github/workflows/fa3-donor-serialization.yml",
            root / "src/fa3_enforce.py",
            root / "src/fa3_gate_registry.py",
            root / "src/fa3_release_baseline.py",
            root / "src/fa3_permanent_gate_hardening.py",
            root / "src/fa3_trusted_control_plane_gate.py",
        ],
        key=lambda path: path.relative_to(root).as_posix(),
    )
    missing = [
        path.relative_to(root).as_posix()
        for path in paths
        if not path.is_file()
    ]
    if missing:
        raise ValueError(f"authority input snapshot missing files: {missing}")
    return {
        "schema": "fa3.permanent-gate-authority-input-snapshot.v1",
        "files": [
            _subject(path, root, "AUTHORITY_OR_CONTROL_PLANE_INPUT")
            for path in paths
        ],
    }


def verify_non_interference(
    root: Path, snapshot_path: Path | None = None
) -> dict[str, Any]:
    root = Path(root).resolve()
    path = snapshot_path or (root / AUTHORITY_SNAPSHOT_REL)
    before = loadj(path)
    after = authority_input_snapshot(root)
    before_map = {
        row["path"]: (row["sha256"], row["size_bytes"])
        for row in before.get("files", [])
    }
    after_map = {
        row["path"]: (row["sha256"], row["size_bytes"])
        for row in after.get("files", [])
    }
    changed = sorted(
        set(before_map).symmetric_difference(after_map)
        | {
            key
            for key in set(before_map).intersection(after_map)
            if before_map[key] != after_map[key]
        }
    )
    return {
        "schema": "fa3.permanent-gate-non-interference-report.v1",
        "result": "PASS" if not changed else "FAIL",
        "authority_inputs_unchanged": not changed,
        "changed_paths": changed,
        "creates_authority": False,
    }


def verify_preservation(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    path = root / PRESERVATION_REL
    findings: list[dict[str, Any]] = []
    if not path.is_file():
        return {
            "schema": "fa3.permanent-gate-preservation-verification.v1",
            "result": "FAIL",
            "findings": [{"code": "PGP-000", "message": "package missing"}],
        }
    with zipfile.ZipFile(path, "r") as zf:
        infos = zf.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            findings.append(
                {"code": "PGP-001", "message": "duplicate ZIP member"}
            )
        for info in infos:
            member = Path(info.filename)
            if (
                not info.filename
                or "\\" in info.filename
                or member.is_absolute()
                or ".." in member.parts
                or info.is_dir()
            ):
                findings.append(
                    {
                        "code": "PGP-002",
                        "message": "unsafe ZIP member",
                        "path": info.filename,
                    }
                )
        if "PRESERVATION_MANIFEST.json" not in names:
            findings.append(
                {"code": "PGP-003", "message": "manifest missing"}
            )
        else:
            manifest = json.loads(
                zf.read("PRESERVATION_MANIFEST.json").decode("utf-8")
            )
            if (
                manifest.get("preservation_only") is not True
                or manifest.get("creates_authority") is not False
                or manifest.get("replaces_primary_decision") is not False
            ):
                findings.append(
                    {
                        "code": "PGP-004",
                        "message": "preservation authority boundary drift",
                    }
                )
            for row in manifest.get("members", []):
                rel = row.get("path")
                if rel not in names:
                    findings.append(
                        {
                            "code": "PGP-005",
                            "message": "declared member missing",
                            "path": rel,
                        }
                    )
                    continue
                payload = zf.read(rel)
                if (
                    len(payload) != row.get("size_bytes")
                    or sha256_bytes(payload) != row.get("sha256")
                ):
                    findings.append(
                        {
                            "code": "PGP-006",
                            "message": "member digest/size mismatch",
                            "path": rel,
                        }
                    )
    return {
        "schema": "fa3.permanent-gate-preservation-verification.v1",
        "result": "PASS" if not findings else "FAIL",
        "findings": findings,
        "creates_authority": False,
    }


def preserve(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    required = [AUTHORITY_MANIFEST_REL, BINDING_REL, REPORT_REL]
    missing = [
        p.as_posix() for p in required if not (root / p).is_file()
    ]
    if missing:
        raise ValueError(f"preservation inputs missing: {missing}")

    members = []
    for rel in required + [
        Path("reports/static-gate-report.json"),
        Path("reports/gate-registry-gate-report.json"),
        Path("reports/governance-status-gate-report.json"),
        Path("reports/release-projection-gate-report.json"),
        Path("reports/reuse-discovery-gate-report.json"),
    ]:
        path = root / rel
        if path.is_file():
            members.append(rel)
    members = sorted(set(members), key=lambda p: p.as_posix())

    package_manifest = {
        "schema": "fa3.permanent-gate-preservation-manifest.v1",
        "role": "AUDIT_PRESERVATION_CARRIER",
        "preservation_only": True,
        "creates_authority": False,
        "replaces_primary_decision": False,
        "members": [
            {
                "path": p.as_posix(),
                "size_bytes": (root / p).stat().st_size,
                "sha256": sha256_file(root / p),
            }
            for p in members
        ],
    }
    manifest_bytes = (
        json.dumps(package_manifest, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    sums = "".join(
        f'{row["sha256"]}  {row["path"]}\n'
        for row in package_manifest["members"]
    ).encode("utf-8")

    out = root / PRESERVATION_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    fixed = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(
        out, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for name, data in [
            ("PRESERVATION_MANIFEST.json", manifest_bytes),
            ("SHA256SUMS", sums),
        ]:
            info = zipfile.ZipInfo(name, fixed)
            info.external_attr = 0o100644 << 16
            zf.writestr(info, data)
        for rel in members:
            info = zipfile.ZipInfo(rel.as_posix(), fixed)
            info.external_attr = 0o100644 << 16
            zf.writestr(info, (root / rel).read_bytes())

    return {
        "schema": "fa3.permanent-gate-preservation-result.v1",
        "result": "PASS",
        "path": PRESERVATION_REL.as_posix(),
        "sha256": sha256_file(out),
        "member_count": len(members) + 2,
        "creates_authority": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root", default=str(Path(__file__).resolve().parents[1])
    )
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    mat = sub.add_parser("materialize")
    mat.add_argument("--base-sha", required=True)
    mat.add_argument("--head-sha", required=True)
    mat.add_argument("--published-main-sha", required=True)
    mat.add_argument("--primary-result", default="PASS")
    sub.add_parser("verify")
    snap = sub.add_parser("snapshot-authority-inputs")
    snap.add_argument(
        "--output",
        default=AUTHORITY_SNAPSHOT_REL.as_posix(),
    )
    ni = sub.add_parser("verify-non-interference")
    ni.add_argument(
        "--snapshot",
        default=AUTHORITY_SNAPSHOT_REL.as_posix(),
    )
    sub.add_parser("preserve")
    sub.add_parser("verify-preservation")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.command == "check":
        result = gate(root)
    elif args.command == "materialize":
        manifest, binding = materialize(
            root,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            published_main_sha=args.published_main_sha,
            primary_result=args.primary_result,
        )
        result = {
            "result": "PASS",
            "manifest": manifest,
            "binding": binding,
        }
    elif args.command == "verify":
        result = verify_binding(root)
    elif args.command == "snapshot-authority-inputs":
        result = authority_input_snapshot(root)
        writej(root / args.output, result)
        result = {"result": "PASS", "snapshot": args.output}
    elif args.command == "verify-non-interference":
        result = verify_non_interference(root, root / args.snapshot)
    elif args.command == "preserve":
        result = preserve(root)
    else:
        result = verify_preservation(root)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("result") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
