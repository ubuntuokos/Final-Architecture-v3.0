#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from fa3_gtcrn_provider import reference_policy_conformance

PATHS = {
  "profile": "canonical/profiles/FA3-SPEECH-ENHANCEMENT-001.json",
  "contract": "canonical/contracts/FA3-SPEECH-ENHANCEMENT-CONTRACTS-001.json",
  "provider": "canonical/providers/FA3-PROVIDER-GTCRN-001.json",
  "decision": "canonical/decisions/FA3-DEC-GTCRN-SPEECH-ENHANCEMENT-2026-09-09.json",
  "reference": "canonical/references/FA3-GTCRN-UPSTREAM-REFERENCE-2026-09-09.json",
  "allowlist": "canonical/FA3-GTCRN-MODEL-ALLOWLIST-001.json",
  "runtime": "canonical/FA3-GTCRN-RUNTIME-CONFORMANCE-001.json",
  "gate": "canonical/FA3-GATE-GTCRN-001.json",
  "enforcement": "canonical/gtcrn-enforcement.json",
  "release": "canonical/releases/FA3-RELEASE-PROJECTION-GTCRN-2026-09-09.json"
}
EXPECTED_RULE_COUNT = 32

def load(root, key):
    return json.loads((root / PATHS[key]).read_text())

def finding(code, msg):
    return {"code": code, "severity": "P0", "message": msg}

def gate(root: Path) -> dict:
    root = Path(root)
    fs = []
    missing = [p for p in PATHS.values() if not (root / p).is_file()]
    if missing:
        return {"schema": "fa3.gtcrn-gate-report.v1", "result": "FAIL", "blocking_findings": len(missing), "findings": [finding("GTCRN-000", f"missing {p}") for p in missing]}
    p = load(root, "profile"); c = load(root, "contract"); v = load(root, "provider"); d = load(root, "decision"); r = load(root, "reference"); a = load(root, "allowlist"); rt = load(root, "runtime"); g = load(root, "gate"); e = load(root, "enforcement"); rel = load(root, "release")
    checks = [
      ("GTCRN-001", p.get("id") == "FA3-SPEECH-ENHANCEMENT-001", "profile id mismatch"),
      ("GTCRN-002", p.get("new_capability") is False and p.get("capability_count") == 143, "capability invariant failed"),
      ("GTCRN-003", p.get("new_architectural_authority") is False, "authority invariant failed"),
      ("GTCRN-004", p.get("capability_bindings") == ["CAP-017"], "CAP-017 projection required"),
      ("GTCRN-005", p.get("relationship", {}).get("parent") == "FA3-AUDIO-001", "audio parent mismatch"),
      ("GTCRN-006", c.get("provider_neutral") is True, "contract must be provider neutral"),
      ("GTCRN-007", c.get("model_admission", {}).get("overlay") == "FA3-MODEL-ARTIFACT-SECURITY-001", "model security overlay missing"),
      ("GTCRN-008", c.get("model_admission", {}).get("sha256_required_before_runtime_promotion") is True, "sha256 promotion gate missing"),
      ("GTCRN-009", c.get("execution_provider", {}).get("silent_cpu_fallback") is False, "silent CPU fallback forbidden"),
      ("GTCRN-010", c.get("execution_provider", {}).get("accelerator_requires_hrb_admission") is True, "HRB accelerator admission missing"),
      ("GTCRN-011", v.get("id") == "FA3-PROVIDER-GTCRN-001", "provider id mismatch"),
      ("GTCRN-012", v.get("upstream", {}).get("revision") == "502ebfab64da7c4a9af78dcb9c6ceef1ebb01c73", "upstream pin drift"),
      ("GTCRN-013", v.get("upstream", {}).get("license") == "MIT", "license reference drift"),
      ("GTCRN-014", v.get("runtime", {}).get("baseline_execution_provider") == "CPUExecutionProvider", "CPU baseline missing"),
      ("GTCRN-015", v.get("runtime", {}).get("gpu_required") is False, "GPU must not be mandatory"),
      ("GTCRN-016", v.get("runtime", {}).get("sample_rate_hz") == 16000, "16k baseline drift"),
      ("GTCRN-017", v.get("model_policy", {}).get("runtime_torch_checkpoint_loading") is False, "torch checkpoint direct runtime must be denied"),
      ("GTCRN-018", v.get("model_policy", {}).get("runtime_auto_download") is False, "runtime auto download forbidden"),
      ("GTCRN-019", all(not v.get("authority_boundaries", {}).get(k, False) for k in ["audio", "voice", "inference", "model_registry", "provider_routing", "device_routing", "workflow", "security", "host_resource", "evidence"]), "provider claimed authority"),
      ("GTCRN-020", r.get("revision") == v.get("upstream", {}).get("revision"), "reference/provider revision mismatch"),
      ("GTCRN-021", len(r.get("onnx_artifacts", [])) == 2, "ONNX reference inventory incomplete"),
      ("GTCRN-022", a.get("format_policy") == "ONNX_ONLY_FOR_DIRECT_RUNTIME", "allowlist must be ONNX-only"),
      ("GTCRN-023", ".tar" in a.get("denied_direct_runtime_extensions", []), "tar checkpoint deny missing"),
      ("GTCRN-024", all(m.get("sha256") == "REQUIRED_AT_QUARANTINE_ADMISSION" for m in a.get("models", [])), "quarantine sha256 requirement missing"),
      ("GTCRN-025", rt.get("production_admitted") is False and rt.get("status") == "PENDING_CURRENT_HOST", "runtime must remain pending"),
      ("GTCRN-026", g.get("rule_count") == EXPECTED_RULE_COUNT, "gate rule count mismatch"),
      ("GTCRN-027", g.get("fail_closed") is True, "gate not fail closed"),
      ("GTCRN-028", len(e.get("rules", [])) == EXPECTED_RULE_COUNT, "enforcement rule inventory mismatch"),
      ("GTCRN-029", d.get("baseline_effect", {}).get("new_architectural_authority") == 0, "decision added authority"),
      ("GTCRN-030", d.get("baseline_effect", {}).get("capability_count_after") == 143, "decision changed capability count"),
      ("GTCRN-031", rel.get("production_promotion_claimed") is False, "release projection falsely claims production"),
      ("GTCRN-032", rel.get("current_host_runtime_status") == "PENDING_CURRENT_HOST", "release projection current-host state drift")
    ]
    for code, ok, msg in checks:
        if not ok:
            fs.append(finding(code, msg))
    executable = reference_policy_conformance()
    if executable["result"] != "PASS":
        fs.append(finding("GTCRN-EXEC", "provider executable policy conformance failed"))
    result = "PASS" if not fs else "FAIL"
    report = {"schema": "fa3.gtcrn-gate-report.v1", "gate_set_id": "FA3-GTCRN-GATESET-001", "result": result, "blocking_findings": len(fs), "findings": fs, "rules_checked": EXPECTED_RULE_COUNT, "provider_executable_conformance": executable, "current_host_runtime_promoted": False}
    out = root / "reports/gtcrn-gate-report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    return report

if __name__ == "__main__":
    here = Path(__file__).resolve().parents[1]
    rep = gate(here)
    print(json.dumps(rep, indent=2))
    raise SystemExit(0 if rep["result"] == "PASS" else 2)
