#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from fa3_lavasr_provider import MODEL_ASSETS, RUNTIME_REVISION, SOURCE_REVISION, reference_policy_conformance

PATHS = {
    "profile": "canonical/profiles/FA3-SPEECH-ENHANCEMENT-001.json",
    "contract": "canonical/contracts/FA3-AUDIO-RESTORATION-BWE-CONTRACTS-001.json",
    "provider": "canonical/providers/FA3-PROVIDER-LAVASR-001.json",
    "decision": "canonical/decisions/FA3-DEC-LAVASR-2026-09-09.json",
    "reference": "canonical/references/FA3-LAVASR-UPSTREAM-REFERENCE-2026-09-09.json",
    "allowlist": "canonical/FA3-LAVASR-MODEL-ALLOWLIST-001.json",
    "runtime": "canonical/FA3-LAVASR-RUNTIME-CONFORMANCE-001.json",
    "gate": "canonical/FA3-GATE-LAVASR-001.json",
    "enforcement": "canonical/lavasr-enforcement.json",
    "release": "canonical/releases/FA3-RELEASE-PROJECTION-LAVASR-2026-09-09.json",
}
EXPECTED_RULE_COUNT = 40


def load(root: Path, key: str) -> dict:
    return json.loads((root / PATHS[key]).read_text())


def finding(code: str, message: str) -> dict:
    return {"code": code, "severity": "P0", "message": message}


def gate(root: Path) -> dict:
    root = Path(root)
    findings: list[dict] = []
    missing = [path for path in PATHS.values() if not (root / path).is_file()]
    if missing:
        return {
            "schema": "fa3.lavasr-gate-report.v1",
            "result": "FAIL",
            "blocking_findings": len(missing),
            "findings": [finding("LAVASR-000", f"missing {path}") for path in missing],
        }

    p = load(root, "profile")
    c = load(root, "contract")
    v = load(root, "provider")
    d = load(root, "decision")
    r = load(root, "reference")
    a = load(root, "allowlist")
    rt = load(root, "runtime")
    g = load(root, "gate")
    e = load(root, "enforcement")
    rel = load(root, "release")

    all_authorities_false = all(
        not v.get("authority_boundaries", {}).get(key, False)
        for key in [
            "audio", "voice", "inference", "model_registry", "provider_routing",
            "device_routing", "workflow", "security", "host_resource", "evidence",
        ]
    )
    allow_assets = {item["filename"]: item for item in a.get("bundle", {}).get("assets", [])}
    reference_assets = {item["name"]: item for item in r.get("runtime_model_assets", [])}
    asset_hash_closure = (
        set(allow_assets) == set(MODEL_ASSETS)
        and set(reference_assets) == set(MODEL_ASSETS)
        and all(
            allow_assets[name].get("sha256") == expected_hash
            and allow_assets[name].get("size_bytes") == expected_size
            and reference_assets[name].get("sha256") == expected_hash
            and reference_assets[name].get("size_bytes") == expected_size
            for name, (expected_size, expected_hash) in MODEL_ASSETS.items()
        )
    )

    checks = [
        ("LAVASR-001", p.get("id") == "FA3-SPEECH-ENHANCEMENT-001", "profile id mismatch"),
        ("LAVASR-002", p.get("new_capability") is False and p.get("capability_count") == 143, "capability invariant failed"),
        ("LAVASR-003", p.get("new_architectural_authority") is False, "profile authority invariant failed"),
        ("LAVASR-004", p.get("capability_bindings") == ["CAP-017"], "CAP-017 projection required"),
        ("LAVASR-005", p.get("relationship", {}).get("parent") == "FA3-AUDIO-001", "audio parent mismatch"),
        ("LAVASR-006", "FA3-PROVIDER-LAVASR-001" in p.get("providers", []), "LavaSR provider missing from profile"),
        ("LAVASR-007", "FA3-AUDIO-RESTORATION-BWE-CONTRACTS-001" in p.get("contracts", []), "restoration contract missing from profile"),
        ("LAVASR-008", c.get("provider_neutral") is True, "restoration contract must be provider neutral"),
        ("LAVASR-009", c.get("new_capability") is False and c.get("capability_count") == 143, "contract capability invariant failed"),
        ("LAVASR-010", c.get("model_admission", {}).get("overlay") == "FA3-MODEL-ARTIFACT-SECURITY-001", "model security overlay missing"),
        ("LAVASR-011", c.get("model_admission", {}).get("dangerous_serialization_direct_runtime_load") == "FORBIDDEN", "dangerous serialization direct runtime must be forbidden"),
        ("LAVASR-012", c.get("execution_provider", {}).get("silent_cpu_fallback") is False, "silent CPU fallback forbidden"),
        ("LAVASR-013", c.get("execution_provider", {}).get("accelerator_requires_hrb_admission") is True, "HRB accelerator admission missing"),
        ("LAVASR-014", c.get("denoise", {}).get("implicit_double_denoise") == "FORBIDDEN", "implicit double denoise must be forbidden"),
        ("LAVASR-015", c.get("audio_integrity", {}).get("batch_padding_must_not_leak_to_output") is True, "padding-tail integrity rule missing"),
        ("LAVASR-016", v.get("id") == "FA3-PROVIDER-LAVASR-001", "provider id mismatch"),
        ("LAVASR-017", v.get("upstream", {}).get("revision") == SOURCE_REVISION, "upstream source pin drift"),
        ("LAVASR-018", v.get("upstream", {}).get("effective_license") == "Apache-2.0", "effective license reference drift"),
        ("LAVASR-019", v.get("upstream", {}).get("license_metadata_conflict") is True, "license metadata conflict must remain recorded"),
        ("LAVASR-020", v.get("runtime_reference", {}).get("revision") == RUNTIME_REVISION, "ONNX runtime source pin drift"),
        ("LAVASR-021", v.get("model_policy", {}).get("preferred_format") == "ONNX_BUNDLE", "ONNX-first policy missing"),
        ("LAVASR-022", v.get("model_policy", {}).get("direct_runtime_pytorch_bin_loading") is False, "PyTorch bin direct runtime must be denied"),
        ("LAVASR-023", v.get("model_policy", {}).get("runtime_auto_download") is False, "runtime auto-download forbidden"),
        ("LAVASR-024", v.get("runtime", {}).get("baseline_execution_provider") == "CPUExecutionProvider" and v.get("runtime", {}).get("gpu_required") is False, "CPU baseline/GPU optional invariant failed"),
        ("LAVASR-025", v.get("runtime", {}).get("provider_native_input_sample_rate_hz") == 16000, "native 16 kHz processing rate drift"),
        ("LAVASR-026", v.get("runtime", {}).get("output_sample_rate_hz") == 48000, "48 kHz output rate drift"),
        ("LAVASR-027", v.get("runtime", {}).get("default_denoise") is False, "denoise default must be disabled"),
        ("LAVASR-028", all_authorities_false, "provider claimed architectural authority"),
        ("LAVASR-029", r.get("source", {}).get("revision") == SOURCE_REVISION and r.get("runtime_reference", {}).get("revision") == RUNTIME_REVISION, "reference pin closure failed"),
        ("LAVASR-030", r.get("runtime_reference", {}).get("release_immutable") is False, "mutable release fact must remain explicit"),
        ("LAVASR-031", a.get("format_policy") == "ONNX_BUNDLE_ONLY_FOR_DIRECT_RUNTIME", "allowlist must be ONNX-bundle only"),
        ("LAVASR-032", a.get("runtime_network_fetch") is False and a.get("release_tag_is_sufficient_identity") is False, "runtime fetch/release identity policy drift"),
        ("LAVASR-033", asset_hash_closure, "ONNX asset SHA-256/size closure failed"),
        ("LAVASR-034", rt.get("production_admitted") is False and rt.get("status") == "PENDING_CURRENT_HOST", "runtime must remain pending before real host evidence"),
        ("LAVASR-035", g.get("rule_count") == EXPECTED_RULE_COUNT and g.get("fail_closed") is True, "gate descriptor drift"),
        ("LAVASR-036", len(e.get("rules", [])) == EXPECTED_RULE_COUNT and e.get("rule_count") == EXPECTED_RULE_COUNT, "enforcement rule inventory mismatch"),
        ("LAVASR-037", d.get("baseline_effect", {}).get("new_architectural_authority") == 0 and d.get("baseline_effect", {}).get("capability_count_after") == 143, "decision baseline invariant failed"),
        ("LAVASR-038", rel.get("production_promotion_claimed") is False, "release projection falsely claims production"),
        ("LAVASR-039", rel.get("current_host_runtime_status") == "PENDING_CURRENT_HOST", "release projection current-host state drift"),
        ("LAVASR-040", rel.get("post_merge_unified_projection_reconciliation_required") is True, "post-merge unified projection reconciliation must remain explicit"),
    ]

    for code, ok, message in checks:
        if not ok:
            findings.append(finding(code, message))

    executable = reference_policy_conformance()
    if executable.get("result") != "PASS":
        findings.append(finding("LAVASR-EXEC", "provider executable policy conformance failed"))

    result = "PASS" if not findings else "FAIL"
    report = {
        "schema": "fa3.lavasr-gate-report.v1",
        "gate_set_id": "FA3-LAVASR-GATESET-001",
        "result": result,
        "blocking_findings": len(findings),
        "findings": findings,
        "rules_checked": EXPECTED_RULE_COUNT,
        "provider_executable_conformance": executable,
        "current_host_runtime_promoted": False,
    }
    out = root / "reports/lavasr-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    report = gate(here)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["result"] == "PASS" else 2)
