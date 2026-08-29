#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROVIDER_ID = "FA3-PROVIDER-DEMUCS-001"
PROFILE_ID = "FA3-AUDIO-SEPARATION-001"
GATE_ID = "FA3-DEMUCS-GATESET-001"
CAPABILITY_COUNT = 143
REFERENCE_RELEASE = "v4.1.0"
REFERENCE_COMMIT = "6a604bb002d12c4fbabb303ba64db40b5c5743f0"

P0_INVARIANTS = [
    "PROVIDER_NEUTRAL_SOURCE_SEPARATION_CONTRACT",
    "EXPLICIT_STEM_CAPABILITY_DECLARATION",
    "UNSUPPORTED_STEM_FAIL_CLOSED",
    "EXPERIMENTAL_STEM_NOT_PRODUCTION_PROMOTED",
    "MODEL_VARIANT_TYPED_ARTIFACT",
    "QUANTIZATION_CREATES_DISTINCT_ARTIFACT",
    "CHUNK_SEGMENT_POLICY_EXPLICIT",
    "OVERLAP_RECONSTRUCTION_POLICY_EXPLICIT",
    "RESOURCE_QUALITY_TRADEOFF_EVIDENCED",
    "PROVIDER_CANNOT_OWN_DEVICE_PLACEMENT",
    "HRB_LEASE_REQUIRED_FOR_ACCELERATOR",
    "AUDIO_NORMALIZATION_TYPED",
    "CLIPPING_POLICY_EXPLICIT",
    "DERIVED_TWO_STEM_LINEAGE_REQUIRED",
    "MODEL_BAG_FIRST_CLASS_ARTIFACT",
    "LONG_RUNNING_SEPARATION_CANCELLABLE",
    "INFERENCE_TRAINING_DEPENDENCY_SURFACES_SEPARATED",
    "STEM_OUTPUT_FIRST_CLASS_ARTIFACT_WITH_PROVENANCE",
    "MODEL_CONTAINER_SAFETY_NOT_EXECUTION_AUTHORIZATION",
    "EXTERNAL_MODEL_CLASS_ALLOWLIST",
]

SOURCE_BLOBS = {
    "README.md": "bf9e90e60122c13801cfabbcc94c3c9b51469121",
    "pyproject.toml": "267a8a5240baf8043095d4f931043324acf75032",
    "demucs/states.py": "3b1057a43201d69f73039715780423324bbd8657",
    "demucs/hf.py": "bbd7ab2449d630e57b914f5f613dea15155b3803",
    "docs/release.md": "1f3565cad88734e8d07919fd9b005804c84ae09c",
}

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}

def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}".encode() + bytes([0]) + data).hexdigest()

def provider_neutral_contract_valid(contract_identity: str, provider_name: str) -> bool:
    return bool(contract_identity and provider_name and provider_name.lower() not in contract_identity.lower())

def stem_request_valid(supported: set[str], requested: set[str]) -> bool:
    return bool(supported and requested and requested.issubset(supported))

def production_stem_valid(stem: str, maturity: dict[str, str], quality_pass: set[str]) -> bool:
    return maturity.get(stem) == "PRODUCTION" and stem in quality_pass

def distinct_artifact_identity_valid(*artifact_ids: str) -> bool:
    return bool(artifact_ids) and all(artifact_ids) and len(set(artifact_ids)) == len(artifact_ids)

def chunk_policy_valid(split: bool, segment_seconds: float | None) -> bool:
    return (not split) or (segment_seconds is not None and segment_seconds > 0)

def overlap_policy_valid(overlap: float | None) -> bool:
    return overlap is not None and 0 <= overlap < 1

def resource_quality_evidence_valid(resource_profile: str, quality_evidence: str) -> bool:
    return bool(resource_profile and quality_evidence)

def placement_authority_valid(accelerator: bool, hrb_lease: str | None, provider_self_placed: bool) -> bool:
    if provider_self_placed:
        return False
    return (not accelerator) or bool(hrb_lease)

def normalization_valid(samplerate: int, channels: int, bit_depth: str, codec: str) -> bool:
    return samplerate > 0 and channels > 0 and bool(bit_depth and codec)

def clipping_policy_valid(policy: str) -> bool:
    return policy in {"rescale", "clamp", "none", "tanh"}

def derived_lineage_valid(parent_id: str, derivation: str, output_id: str) -> bool:
    return bool(parent_id and derivation and output_id and output_id != parent_id)

def model_bag_valid(artifact_id: str, members: list[str], weights: list[float], segment: float | None) -> bool:
    return bool(artifact_id and members and len(members) == len(weights) and all(members) and segment is not None and segment > 0)

def cancellable_execution_valid(long_running: bool, cancellable: bool, bounded: bool) -> bool:
    return (not long_running) or (cancellable and bounded)

def dependency_surface_valid(inference: set[str], training_only: set[str]) -> bool:
    return bool(inference) and inference.isdisjoint(training_only)

def stem_artifact_valid(record: dict[str, Any]) -> bool:
    required = {"id", "parent_mixture", "stem", "output_hash", "model_id", "provider_id"}
    return required.issubset(record) and all(record[k] for k in required)

def model_loading_trust_valid(*, container_safe: bool, provenance_pass: bool, admitted: bool, legacy_pickle: bool, explicit_legacy_trust: bool) -> bool:
    if not (container_safe and provenance_pass and admitted):
        return False
    if legacy_pickle and not explicit_legacy_trust:
        return False
    return True

def class_allowlist_valid(metadata_class: str, implementation_map: dict[str, str]) -> bool:
    return bool(metadata_class and metadata_class in implementation_map)

def reference_check(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "decision": root / "canonical/decisions/FA3-DEC-DEMUCS-2026-08-29.json",
        "provider": root / "canonical/providers/FA3-PROVIDER-DEMUCS-001.json",
        "profile": root / "canonical/profiles/FA3-AUDIO-SEPARATION-001.json",
        "contracts": root / "canonical/contracts/FA3-AUDIO-SEPARATION-CONTRACTS-001.json",
        "enforcement": root / "canonical/demucs-enforcement.json",
        "evidence": root / "evidence/reference/demucs-v4.1.0.json",
        "model_allowlist": root / "canonical/FA3-DEMUCS-MODEL-ALLOWLIST-001.json",
        "runtime_conformance": root / "canonical/FA3-DEMUCS-RUNTIME-CONFORMANCE-001.json",
        "provider_ci_evidence": root / "evidence/reference/demucs-provider-ci-2026-08-30.json",
    }
    for idx, path in enumerate(paths.values(), 1):
        if not path.exists():
            findings.append(_finding(f"DEMUCS-REF-{idx:03d}", f"Missing Demucs canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    decision = _load(paths["decision"])
    provider = _load(paths["provider"])
    profile = _load(paths["profile"])
    contracts = _load(paths["contracts"])
    enforcement = _load(paths["enforcement"])
    evidence = _load(paths["evidence"])
    model_allowlist = _load(paths["model_allowlist"])
    runtime_conformance = _load(paths["runtime_conformance"])
    provider_ci_evidence = _load(paths["provider_ci_evidence"])

    if decision.get("status") != "CANONICAL_CLOSED" or decision.get("decision") != "ACCEPT":
        findings.append(_finding("DEMUCS-REF-010", "Demucs canonical decision is not closed ACCEPT"))
    if decision.get("new_capabilities") != 0 or decision.get("new_architectural_authorities") != 0 or decision.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("DEMUCS-REF-011", "Demucs decision changed capability/authority invariant"))

    if provider.get("id") != PROVIDER_ID or provider.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("DEMUCS-REF-012", "Demucs provider identity/capability-count mismatch"))
    if any(provider.get(k) is not False for k in ("canonical_root", "architectural_authority", "new_capability", "device_selection_authority", "model_routing_authority")):
        findings.append(_finding("DEMUCS-REF-013", "Demucs provider was promoted to forbidden authority/root/capability"))
    if provider.get("global_runtime_promotion_required_when_disabled") is not False:
        findings.append(_finding("DEMUCS-REF-014", "Disabled optional Demucs provider became mandatory for global promotion"))
    implementation = provider.get("implementation", {})
    if provider.get("status") != "IMPLEMENTED_OPTIONAL_PROVIDER" or implementation.get("adapter") != "src/fa3_demucs_provider.py":
        findings.append(_finding("DEMUCS-REF-029", "Demucs executable provider implementation binding drift"))

    if profile.get("id") != PROFILE_ID or profile.get("subprofile_of") != "FA3-AUDIO-001":
        findings.append(_finding("DEMUCS-REF-015", "Audio separation profile identity/parent drift"))
    if profile.get("capabilities") != ["CAP-017", "CAP-066"]:
        findings.append(_finding("DEMUCS-REF-016", "Audio separation profile capability projection drift"))
    if any(profile.get(k) is not False for k in ("canonical_root", "new_capability", "new_architectural_authority")):
        findings.append(_finding("DEMUCS-REF-017", "Audio separation profile became forbidden root/capability/authority"))

    if contracts.get("id") != "FA3-AUDIO-SEPARATION-CONTRACTS-001" or contracts.get("provider_neutral") is not True:
        findings.append(_finding("DEMUCS-REF-018", "Audio separation contract-set identity/provider-neutral invariant failed"))
    c_rules = contracts.get("rules", {})
    for key in (
        "provider_names_forbidden_in_contract_identity",
        "unsupported_stem_fail_closed",
        "experimental_stem_requires_explicit_nonproduction_status",
        "accelerator_execution_requires_host_resource_broker_lease",
        "legacy_pickle_checkpoint_requires_explicit_trust_admission",
        "external_model_metadata_arbitrary_class_import_forbidden",
    ):
        if c_rules.get(key) is not True:
            findings.append(_finding("DEMUCS-REF-019", f"Required contract invariant disabled: {key}"))

    if enforcement.get("gate_id") != GATE_ID or enforcement.get("provider_id") != PROVIDER_ID or enforcement.get("profile_id") != PROFILE_ID:
        findings.append(_finding("DEMUCS-REF-020", "Demucs gate/provider/profile identity mismatch"))
    if enforcement.get("demucs_rule_count") != 18 or enforcement.get("cross_cutting_model_trust_rule_count") != 2:
        findings.append(_finding("DEMUCS-REF-021", "Demucs canonical rule-count drift"))
    if enforcement.get("p0_invariants") != P0_INVARIANTS:
        findings.append(_finding("DEMUCS-REF-022", "Demucs P0 invariant set drift"))
    if enforcement.get("fail_closed") is not True or enforcement.get("floating_main_allowed_as_promotion_evidence") is not False:
        findings.append(_finding("DEMUCS-REF-023", "Demucs fail-closed/immutable-reference policy drift"))
    if enforcement.get("runtime_provider_required_for_global_promotion") is not False:
        findings.append(_finding("DEMUCS-REF-024", "Optional Demucs runtime became a global promotion dependency"))

    stable = evidence.get("stable_reference", {})
    if stable.get("release") != REFERENCE_RELEASE or stable.get("commit_sha") != REFERENCE_COMMIT:
        findings.append(_finding("DEMUCS-REF-025", "Stable Demucs immutable reference drift"))
    if stable.get("source_blobs") != SOURCE_BLOBS:
        findings.append(_finding("DEMUCS-REF-026", "Demucs source-blob reference drift"))
    if evidence.get("floating_main_allowed") is not False:
        findings.append(_finding("DEMUCS-REF-027", "Demucs evidence permits floating main"))
    if evidence.get("observed_security_boundary", {}).get("fa3_disposition") != "TRUST_GATED_ALLOWLISTED_ONLY":
        findings.append(_finding("DEMUCS-REF-028", "Demucs model-loading security disposition drift"))

    if model_allowlist.get("id") != "FA3-DEMUCS-MODEL-ALLOWLIST-001" or model_allowlist.get("policy") != "ALLOWLIST_ONLY_FAIL_CLOSED":
        findings.append(_finding("DEMUCS-REF-030", "Demucs model allowlist identity/fail-closed policy drift"))
    if model_allowlist.get("allowed_namespace") != "adefossez":
        findings.append(_finding("DEMUCS-REF-031", "Demucs model namespace allowlist widened or changed"))
    allowed_classes = set(model_allowlist.get("allowed_model_classes", []))
    if allowed_classes != {"demucs.htdemucs.HTDemucs", "demucs.hdemucs.HDemucs"}:
        findings.append(_finding("DEMUCS-REF-032", "Demucs model-class allowlist drift"))
    if runtime_conformance.get("id") != "FA3-DEMUCS-RUNTIME-CONFORMANCE-001" or runtime_conformance.get("fail_closed") is not True:
        findings.append(_finding("DEMUCS-REF-033", "Demucs runtime conformance contract identity/fail-closed drift"))
    if runtime_conformance.get("current_host_production_e2e", {}).get("synthetic_input_forbidden") is not True:
        findings.append(_finding("DEMUCS-REF-034", "Synthetic input was permitted to claim current-host production PASS"))
    if runtime_conformance.get("current_host_production_e2e", {}).get("cuda_requires_hrb_lease") is not True:
        findings.append(_finding("DEMUCS-REF-035", "Demucs CUDA current-host path no longer requires HRB lease"))

    if provider_ci_evidence.get("status") != "PASS" or provider_ci_evidence.get("evidence_scope") != "CI_NOT_CURRENT_HOST":
        findings.append(_finding("DEMUCS-REF-036", "Demucs executable provider CI evidence missing or scope drifted"))
    ci_result = provider_ci_evidence.get("results", {}).get("demucs_provider_conformance", {})
    if ci_result.get("status") != "PASS" or ci_result.get("passed") != 13 or ci_result.get("total") != 13:
        findings.append(_finding("DEMUCS-REF-037", "Demucs executable provider CI conformance is not pinned 13/13 PASS"))
    blob_expect = provider_ci_evidence.get("implementation_blobs", {})
    tracked = {
        "src/fa3_demucs_provider.py": root / "src/fa3_demucs_provider.py",
        "src/fa3_demucs_current_host_gate.py": root / "src/fa3_demucs_current_host_gate.py",
        "tests/test_demucs_provider_runtime.py": root / "tests/test_demucs_provider_runtime.py",
        "evidence/collect-demucs-current-host.py": root / "evidence/collect-demucs-current-host.py",
        "canonical/FA3-DEMUCS-MODEL-ALLOWLIST-001.json": root / "canonical/FA3-DEMUCS-MODEL-ALLOWLIST-001.json",
    }
    actual_blobs = {name: _git_blob_sha(path) for name, path in tracked.items()}
    stale = [name for name in tracked if blob_expect.get(name) != actual_blobs[name]]
    if stale:
        findings.append(_finding("DEMUCS-REF-038", "Demucs provider CI evidence is stale against implementation blobs", stale=stale, expected={name: blob_expect.get(name) for name in stale}, actual={name: actual_blobs[name] for name in stale}))
    host_state = provider_ci_evidence.get("current_host_production_e2e", {})
    if host_state.get("status") not in {"PENDING_REAL_HOST_EXECUTION", "PASS"}:
        findings.append(_finding("DEMUCS-REF-039", "Demucs current-host evidence state is invalid"))
    if host_state.get("synthetic_or_ci_evidence_accepted") is not False:
        findings.append(_finding("DEMUCS-REF-040", "Synthetic/CI evidence was enabled for current-host production claim"))

    return {"result": "PASS" if not findings else "FAIL", "findings": findings}

def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    def add(rule_id: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule_id, "name": name, "status": "PASS" if positive and negative else "FAIL", "positive_case": positive, "negative_case": negative})

    supported = {"vocals", "drums", "bass", "other"}
    add("FA3-DEMUCS-P0-001", "provider-neutral contract", provider_neutral_contract_valid("AudioSeparationRequest", "Demucs"), not provider_neutral_contract_valid("DemucsAudioSeparationRequest", "Demucs"))
    add("FA3-DEMUCS-P0-002", "explicit stem declaration", stem_request_valid(supported, {"vocals"}), not stem_request_valid(set(), {"vocals"}))
    add("FA3-DEMUCS-P0-003", "unsupported stem fail closed", stem_request_valid(supported, {"vocals", "drums"}), not stem_request_valid(supported, {"piano"}))
    maturity = {"vocals": "PRODUCTION", "piano": "EXPERIMENTAL"}
    add("FA3-DEMUCS-P0-004", "experimental stem promotion gate", production_stem_valid("vocals", maturity, {"vocals"}), not production_stem_valid("piano", maturity, {"vocals"}))
    add("FA3-DEMUCS-P0-005", "typed model variant identity", distinct_artifact_identity_valid("htdemucs@shaA", "htdemucs_ft@shaB"), not distinct_artifact_identity_valid("same", "same"))
    add("FA3-DEMUCS-P0-006", "quantization distinct artifact", distinct_artifact_identity_valid("mdx@base", "mdx_q@quant"), not distinct_artifact_identity_valid("mdx@base", "mdx@base"))
    add("FA3-DEMUCS-P0-007", "explicit chunk policy", chunk_policy_valid(True, 7.0), not chunk_policy_valid(True, None))
    add("FA3-DEMUCS-P0-008", "explicit overlap policy", overlap_policy_valid(0.25), not overlap_policy_valid(None))
    add("FA3-DEMUCS-P0-009", "resource-quality evidence", resource_quality_evidence_valid("VRAM<=8GiB segment=7", "quality-pass-001"), not resource_quality_evidence_valid("VRAM<=8GiB", ""))
    add("FA3-DEMUCS-P0-010", "provider cannot self-place", placement_authority_valid(False, None, False), not placement_authority_valid(False, None, True))
    add("FA3-DEMUCS-P0-011", "HRB lease for accelerator", placement_authority_valid(True, "HRB-LEASE-123", False), not placement_authority_valid(True, None, False))
    add("FA3-DEMUCS-P0-012", "typed audio normalization", normalization_valid(44100, 2, "float32", "wav"), not normalization_valid(0, 2, "", ""))
    add("FA3-DEMUCS-P0-013", "explicit clipping policy", clipping_policy_valid("rescale"), not clipping_policy_valid("implicit-default"))
    add("FA3-DEMUCS-P0-014", "derived two-stem lineage", derived_lineage_valid("stemset-1", "sum(other_stems)", "no_vocals-1"), not derived_lineage_valid("", "", "no_vocals-1"))
    add("FA3-DEMUCS-P0-015", "model bag artifact identity", model_bag_valid("bag-1", ["m1", "m2"], [0.5, 0.5], 7.0), not model_bag_valid("", ["m1"], [], None))
    add("FA3-DEMUCS-P0-016", "cancellable long-running execution", cancellable_execution_valid(True, True, True), not cancellable_execution_valid(True, False, True))
    add("FA3-DEMUCS-P0-017", "separated dependency surfaces", dependency_surface_valid({"torch", "safetensors"}, {"musdb", "museval"}), not dependency_surface_valid({"torch", "musdb"}, {"musdb"}))
    good_stem = {"id":"stem-1","parent_mixture":"mix-1","stem":"vocals","output_hash":"abc","model_id":"m1","provider_id":PROVIDER_ID}
    add("FA3-DEMUCS-P0-018", "stem first-class artifact", stem_artifact_valid(good_stem), not stem_artifact_valid({"id":"stem-1","stem":"vocals"}))
    add("FA3-MODEL-LOAD-TRUST", "container safety is not execution authorization",
        model_loading_trust_valid(container_safe=True, provenance_pass=True, admitted=True, legacy_pickle=False, explicit_legacy_trust=False),
        not model_loading_trust_valid(container_safe=True, provenance_pass=False, admitted=False, legacy_pickle=False, explicit_legacy_trust=False))
    add("FA3-MODEL-CLASS-ALLOWLIST", "external model class allowlist",
        class_allowlist_valid("HTDemucs", {"HTDemucs":"fa3.impl.htdemucs"}),
        not class_allowlist_valid("evil.module.Class", {"HTDemucs":"fa3.impl.htdemucs"}))
    passed = sum(case["status"] == "PASS" for case in cases)
    return {"schema":"fa3.demucs-regression-report.v1","result":"PASS" if passed == len(cases) else "FAIL","passed":passed,"total":len(cases),"cases":cases}

def gate(root: Path) -> dict[str, Any]:
    reference = reference_check(root)
    regressions = run_regressions()
    ok = reference["result"] == "PASS" and regressions["result"] == "PASS"
    report = {"schema":"fa3.demucs-gate-report.v1","gate_id":GATE_ID,"provider_id":PROVIDER_ID,"profile_id":PROFILE_ID,
              "capability_count":CAPABILITY_COUNT,"result":"PASS" if ok else "FAIL","mode":"CANONICAL_REFERENCE_AND_EXECUTABLE_INVARIANTS",
              "reference":reference,"regressions":regressions,"runtime_provider_required":False,
              "promotion_effect":"MANDATORY_CANONICAL_RULE_PASS_PROVIDER_RUNTIME_OPTIONAL"}
    _write(root / "reports/demucs-gate-report.json", report)
    return report

def main() -> int:
    ap = argparse.ArgumentParser(description="FA3 Demucs canonical audio-separation invariant gate")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args()
    result = gate(Path(args.root).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
