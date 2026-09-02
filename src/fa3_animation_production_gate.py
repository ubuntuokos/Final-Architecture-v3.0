#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

PROFILE_ID = "FA3-ANIMATION-PRODUCTION-001"
CONTRACT_ID = "FA3-ANIMATION-PRODUCTION-CONTRACTS-001"
GATESET_ID = "FA3-ANIMATION-PRODUCTION-GATESET-001"
GATE_ID = "FA3-GATE-ANIMATION-PRODUCTION-001"
DECISION_ID = "FA3-DEC-ANIMATION-PRODUCTION-2026-09-02"
HARDWARE_REFERENCE_ID = "FA3-T7910-ANIMATION-HARDWARE-REFERENCE-2026-09-02"
CAPABILITY_COUNT = 143
CAPABILITIES = ["CAP-014", "CAP-015", "CAP-016", "CAP-017", "CAP-041", "CAP-071", "CAP-114", "CAP-121", "CAP-126"]
PROVIDERS = [
    "FA3-PROVIDER-BFORARTISTS-001",
    "FA3-PROVIDER-BLENDER-001",
    "FA3-PROVIDER-OPENTOONZ-001",
    "FA3-PROVIDER-MUSETALK-001",
]
PINNED_REFS = {
    "bforartists": "0a1ca45552dba1006ae0fb5c4dd36657622a4e66",
    "opentoonz": "065cc1404ba43019b22a2577d529134c3e01931b",
    "musetalk": "0a89dec45a0192b824e3cf4daf96c239440c5ed8",
    "opentimelineio": "44236713c1db295a6ffc66189ae98dbdfd0cb9c4",
    "opencolorio": "c52966a6677723d5bd2dbef0ccec3fed9cbc3790",
    "openexr": "e71cdd5d30a146dcb56c5e4c576d9e9d3c45f4fb",
}
NEGATIVE_REFERENCE_PINS = {
    "Wav2Lip": "bac9a81e63ecc153202353372e5724b83d9e6322",
    "AudioCraft_MusicGen": "896ec7c47f5e5d1e5aa1e4b260c4405328bf009d",
    "F5_TTS": "9c614e9657089213efc6a7421b30630be138a3f5",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _finding(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "severity": "P0", "message": message, **details}


def immutable_pin_valid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{40}", value or ""))


def catalog_projection_valid(*, capability_count: int, new_capability: bool, new_authority: bool) -> bool:
    return capability_count == CAPABILITY_COUNT and not new_capability and not new_authority


def provider_contract_valid(*, provider_neutral: bool, provider_local_formats_are_roots: bool) -> bool:
    return provider_neutral and not provider_local_formats_are_roots


def delegation_valid(dependencies: set[str]) -> bool:
    required = {"FA3-VOICE-001", "FA3-STT-MEDIA-001", "FA3-MUSIC-001", "FA3-DCC-RT3D-001", "FA3-KDENLIVE-EDITORIAL-001", "FA3-HOST-RESOURCE-BROKER-001"}
    return required.issubset(dependencies)


def opentoonz_admission_valid(*, role: str, core_license: str, component_audit: bool) -> bool:
    return role == "PRIMARY_TRADITIONAL_2D_REFERENCE" and core_license == "BSD-3-Clause" and component_audit


def musetalk_runtime_valid(*, typed_adapter: bool, isolated: bool, shared_comfyui_env: bool, hrb_lease: bool) -> bool:
    return typed_adapter and isolated and not shared_comfyui_env and hrb_lease


def hardware_roles_valid(*, compute_model: str, compute_vram_gib: int, display_model: str, display_vram_gib: int, display_implicit_fallback: bool) -> bool:
    return compute_model == "NVIDIA GeForce RTX 3090" and compute_vram_gib == 24 and display_model == "NVIDIA RTX A1000" and display_vram_gib == 8 and not display_implicit_fallback


def human_finishing_valid(*, editorial: str, audio: str, picture_lock_human: bool) -> bool:
    return editorial == "Kdenlive" and audio == "Ardour" and picture_lock_human


def final_master_valid(checks: set[str]) -> bool:
    required = {"picture_lock", "audio_lock", "color_qc", "caption_qc", "av_sync_qc", "delivery_qc", "provenance"}
    return required.issubset(checks)


def immutable_runtime_policy_valid(*, runtime_pin: str, model_pin: str, runtime_download: bool, floating_ref: bool) -> bool:
    return immutable_pin_valid(runtime_pin) and immutable_pin_valid(model_pin) and not runtime_download and not floating_ref


def promotion_claim_valid(*, ci_reference_pass: bool, current_host_claimed: bool, real_e2e: bool) -> bool:
    return not current_host_claimed or (real_e2e and not ci_reference_pass)


def disabled_provider_valid(*, enabled: bool, runtime_cost: int, blocks_global_promotion: bool) -> bool:
    return enabled or (runtime_cost == 0 and not blocks_global_promotion)


def stage_transition_valid(record: dict[str, Any]) -> bool:
    required = {
        "source_artifact_ids", "source_content_hashes", "provider_id", "operation_or_intent",
        "frame_rate_and_timebase", "color_space_and_alpha_mode", "result_artifact_id",
        "result_content_hash", "policy_and_license_decisions", "review_or_qc_evidence",
    }
    return required.issubset(record) and all(record.get(key) for key in required)


def license_admission_valid(dimensions: dict[str, bool], *, commercial: bool, noncommercial_component: bool) -> bool:
    required = {"code", "runtime_dependencies", "model_weights", "training_datasets", "input_assets_and_likeness", "output_usage_rights"}
    return required.issubset(dimensions) and all(dimensions[key] for key in required) and not (commercial and noncommercial_component)


def lipsync_request_valid(request: dict[str, Any]) -> bool:
    required = {"video_artifact", "audio_artifact", "character_identity", "frame_rate", "timebase", "consent", "synthetic_disclosure"}
    return required.issubset(request) and all(request.get(key) for key in required)


def accelerator_identity_valid(*, device_uuid: str, pci_bdf: str, runtime_index_only: bool) -> bool:
    return bool(device_uuid and re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]", pci_bdf or "")) and not runtime_index_only


def hrb_execution_valid(*, accelerator: bool, lease_valid: bool, provider_self_placed: bool) -> bool:
    return not provider_self_placed and ((not accelerator) or lease_valid)


def display_fallback_valid(*, selected_role: str, heavy_job: bool, explicit_policy: bool) -> bool:
    return not (heavy_job and selected_role == "DISPLAY_UI_MEDIA_IO" and not explicit_policy)


def vram_admission_valid(*, requested_gib: float, capacity_gib: float, reserve_gib: float, concurrent_heavy: int, max_heavy: int) -> bool:
    return requested_gib > 0 and reserve_gib >= 0 and requested_gib <= capacity_gib - reserve_gib and 0 < concurrent_heavy <= max_heavy


def oom_policy_valid(*, action: str, explicit: bool, silent_device_or_provider_fallback: bool) -> bool:
    return explicit and action in {"FAIL", "QUEUE", "RETRY_SAME_ROUTE", "DEGRADE_EXPLICIT"} and not silent_device_or_provider_fallback


def cpu_topology_admission_valid(*, live_discovered: bool, lscpu_or_sysfs: bool, static_cpu_ids: bool, global_threads: int | None) -> bool:
    return live_discovered and lscpu_or_sysfs and not static_cpu_ids and global_threads not in {44, 88}


def interchange_valid(*, timeline: str, color: str, hdr: str, provider_local_root: bool) -> bool:
    return timeline == "OpenTimelineIO" and color == "OpenColorIO" and hdr == "OpenEXR" and not provider_local_root


def dcc_route_valid(*, primary: str, fallback: str, explicit: bool, compatibility_evidence: bool) -> bool:
    return primary == "Bforartists" and fallback == "Blender" and explicit and compatibility_evidence


def reference_check(root: Path, *, require_evidence: bool = True) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    paths = {
        "profile": root / "canonical/profiles/FA3-ANIMATION-PRODUCTION-001.json",
        "contracts": root / "canonical/contracts/FA3-ANIMATION-PRODUCTION-CONTRACTS-001.json",
        "decision": root / "canonical/decisions/FA3-DEC-ANIMATION-PRODUCTION-2026-09-02.json",
        "enforcement": root / "canonical/animation-production-enforcement.json",
        "gate": root / "canonical/FA3-GATE-ANIMATION-PRODUCTION-001.json",
        "upstream": root / "canonical/references/FA3-ANIMATION-UPSTREAM-REFERENCE-2026-09-02.json",
        "hardware": root / "canonical/references/FA3-T7910-ANIMATION-HARDWARE-REFERENCE-2026-09-02.json",
        "cpu": root / "canonical/references/FA3-T7910-CPU-NUMA-REFERENCE-2026-09-02.json",
        "policy": root / "canonical/enforcement-policy.json",
    }
    for provider_id in PROVIDERS:
        paths[provider_id] = root / f"canonical/providers/{provider_id}.json"
    if require_evidence:
        paths["evidence"] = root / "evidence/reference/animation-production-ci-2026-09-02.json"
    for idx, path in enumerate(paths.values(), 1):
        if not path.exists():
            findings.append(_finding(f"ANIM-REF-{idx:03d}", f"Missing animation canonical artifact: {path.relative_to(root)}"))
    if findings:
        return {"result": "FAIL", "findings": findings}

    profile, contracts = _load(paths["profile"]), _load(paths["contracts"])
    decision, enforcement = _load(paths["decision"]), _load(paths["enforcement"])
    gate_record, upstream, hardware, cpu = _load(paths["gate"]), _load(paths["upstream"]), _load(paths["hardware"]), _load(paths["cpu"])
    policy = _load(paths["policy"])
    provider_records = {provider_id: _load(paths[provider_id]) for provider_id in PROVIDERS}

    if profile.get("id") != PROFILE_ID or profile.get("status") != "CANONICAL" or profile.get("requirement") != "MUST":
        findings.append(_finding("ANIM-REF-020", "Animation profile identity/status/requirement drift"))
    if profile.get("capabilities") != CAPABILITIES:
        findings.append(_finding("ANIM-REF-021", "Animation capability projection drift"))
    if any(profile.get(key) is not False for key in ("canonical_root", "new_capability", "new_architectural_authority")) or profile.get("capability_count") != CAPABILITY_COUNT:
        findings.append(_finding("ANIM-REF-022", "Animation profile changed root/capability/authority invariant"))
    if contracts.get("id") != CONTRACT_ID or contracts.get("provider_neutral") is not True:
        findings.append(_finding("ANIM-REF-023", "Animation provider-neutral contract invariant failed"))
    expected_interchange = {"editorial": "OpenTimelineIO", "color_management": "OpenColorIO", "hdr_intermediate": "OpenEXR"}
    if any(contracts.get("canonical_interchange", {}).get(key) != value for key, value in expected_interchange.items()):
        findings.append(_finding("ANIM-REF-024", "OTIO/OCIO/OpenEXR canonical interchange drift"))
    resource = contracts.get("resource_contract", {})
    if not all(resource.get(key) is True for key in ("accelerator_execution_requires_hrb_lease", "vram_headroom_required", "heavy_job_concurrency_bounded", "oom_fallback_requires_explicit_policy", "static_cpu_or_numa_ids_forbidden")):
        findings.append(_finding("ANIM-REF-025", "Animation HRB/VRAM/CPU resource contract weakened"))
    if resource.get("accelerator_identity") != ["device_uuid", "pci_bdf"] or resource.get("display_gpu_implicit_compute_fallback") is not False:
        findings.append(_finding("ANIM-REF-026", "Stable GPU identity/display isolation contract drift"))

    expected_status = {
        "FA3-PROVIDER-BFORARTISTS-001": "CANONICAL_PRIMARY_DCC_FRONTEND_PROVIDER",
        "FA3-PROVIDER-BLENDER-001": "REQUIRED_VALIDATED_COMPATIBILITY_FALLBACK",
        "FA3-PROVIDER-OPENTOONZ-001": "ACCEPTED_REQUIRED_PRIMARY_REFERENCE",
        "FA3-PROVIDER-MUSETALK-001": "ACCEPTED_REQUIRED_PRIMARY_REFERENCE",
    }
    for provider_id, record in provider_records.items():
        if record.get("id") != provider_id or record.get("status") != expected_status[provider_id] or record.get("architectural_authority") is not False or record.get("capability_count") != CAPABILITY_COUNT:
            findings.append(_finding("ANIM-REF-027", f"Animation provider role/authority drift: {provider_id}"))
    musetalk = provider_records["FA3-PROVIDER-MUSETALK-001"]
    if musetalk.get("runtime_isolation", {}).get("shared_comfyui_environment_forbidden") is not True or musetalk.get("execution_policy", {}).get("hrb_lease_required_for_cuda") is not True:
        findings.append(_finding("ANIM-REF-028", "MuseTalk isolation/HRB policy drift"))

    refs = upstream.get("references", {})
    observed = {
        "bforartists": refs.get("bforartists", {}).get("tag_commit"),
        "opentoonz": refs.get("opentoonz", {}).get("tag_commit"),
        "musetalk": refs.get("musetalk", {}).get("observed_main_commit"),
        "opentimelineio": refs.get("opentimelineio", {}).get("tag_commit"),
        "opencolorio": refs.get("opencolorio", {}).get("tag_commit"),
        "openexr": refs.get("openexr", {}).get("tag_commit"),
    }
    if observed != PINNED_REFS or not all(immutable_pin_valid(value) for value in observed.values()):
        findings.append(_finding("ANIM-REF-029", "Animation upstream immutable reference drift", observed=observed))
    negative = upstream.get("negative_or_conditional_dispositions", {})
    if not all("DENIED" in negative.get(name, "") for name in ("Wav2Lip", "AudioCraft_MusicGen_released_weights", "F5_TTS_pretrained_models")):
        findings.append(_finding("ANIM-REF-030", "Noncommercial production exclusion drift"))
    negative_snapshots = upstream.get("negative_upstream_snapshots", {})
    negative_observed = {name: negative_snapshots.get(name, {}).get("observed_main_commit") for name in NEGATIVE_REFERENCE_PINS}
    if negative_observed != NEGATIVE_REFERENCE_PINS or not all(immutable_pin_valid(value) for value in negative_observed.values()):
        findings.append(_finding("ANIM-REF-030A", "Noncommercial upstream immutable reference drift", observed=negative_observed))

    roles = hardware.get("declared_accelerator_roles", {})
    if roles.get("primary_ai_render_compute") != {"model": "NVIDIA GeForce RTX 3090", "vram_gib": 24, "display_role": False}:
        findings.append(_finding("ANIM-REF-031", "RTX 3090 compute reference drift"))
    if roles.get("display_ui_media_io") != {"model": "NVIDIA RTX A1000", "vram_gib": 8, "display_role": True, "implicit_heavy_ai_fallback": False}:
        findings.append(_finding("ANIM-REF-032", "RTX A1000 display reference drift"))
    declared_cpu = cpu.get("declared_cpu_configuration", {})
    if declared_cpu.get("model") != "Intel Xeon E5-2696 v4" or declared_cpu.get("physical_cores_total") != 44 or declared_cpu.get("logical_cpus_total") != 88:
        findings.append(_finding("ANIM-REF-033", "T7910 E5-2696 v4 44C/88T CPU reference drift"))

    if decision.get("id") != DECISION_ID or decision.get("new_capability") is not False or decision.get("new_architectural_authority") is not False or decision.get("capability_count_after") != CAPABILITY_COUNT:
        findings.append(_finding("ANIM-REF-034", "Animation decision capability/authority invariant drift"))
    if enforcement.get("gate_id") != GATESET_ID or enforcement.get("mandatory_rule_count") != 26 or len(enforcement.get("rules", [])) != 26 or enforcement.get("fail_closed") is not True:
        findings.append(_finding("ANIM-REF-035", "Animation enforcement ruleset drift"))
    rule_names = [rule.get("name") for rule in enforcement.get("rules", [])]
    if policy.get("animation_production_mandatory_p0_rules") != rule_names or GATESET_ID not in policy.get("mandatory_reference_gates", []):
        findings.append(_finding("ANIM-REF-035A", "Animation global enforcement-policy linkage drift"))
    if gate_record.get("id") != GATE_ID or gate_record.get("mandatory_checks") != 26 or gate_record.get("current_host_runtime_promotion_claim") is not False:
        findings.append(_finding("ANIM-REF-036", "Animation executable gate record drift"))
    if require_evidence:
        evidence = _load(paths["evidence"])
        if evidence.get("result") != "PASS" or evidence.get("regression_case_count") != 26 or evidence.get("current_host_runtime_promotion_claim") is not False:
            findings.append(_finding("ANIM-REF-037", "Animation CI/reference evidence invalid or overclaims runtime"))
    return {"result": "PASS" if not findings else "FAIL", "findings": findings}


def run_regressions() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    def add(rule_id: str, name: str, positive: bool, negative: bool) -> None:
        cases.append({"rule_id": rule_id, "name": name, "status": "PASS" if positive and negative else "FAIL", "positive_case": positive, "negative_case": negative})

    good_stage = {key: "x" for key in ("source_artifact_ids", "source_content_hashes", "provider_id", "operation_or_intent", "frame_rate_and_timebase", "color_space_and_alpha_mode", "result_artifact_id", "result_content_hash", "policy_and_license_decisions", "review_or_qc_evidence")}
    dims = {key: True for key in ("code", "runtime_dependencies", "model_weights", "training_datasets", "input_assets_and_likeness", "output_usage_rights")}
    good_lipsync = {key: "x" for key in ("video_artifact", "audio_artifact", "character_identity", "frame_rate", "timebase", "consent", "synthetic_disclosure")}
    add("FA3-ANIM-P0-001", "capability and authority invariant", catalog_projection_valid(capability_count=143, new_capability=False, new_authority=False), not catalog_projection_valid(capability_count=144, new_capability=True, new_authority=True))
    add("FA3-ANIM-P0-002", "provider-neutral contract", provider_contract_valid(provider_neutral=True, provider_local_formats_are_roots=False), not provider_contract_valid(provider_neutral=False, provider_local_formats_are_roots=True))
    add("FA3-ANIM-P0-003", "stage transition evidence", stage_transition_valid(good_stage), not stage_transition_valid({**good_stage, "result_content_hash": ""}))
    add("FA3-ANIM-P0-004", "DCC explicit compatibility fallback", dcc_route_valid(primary="Bforartists", fallback="Blender", explicit=True, compatibility_evidence=True), not dcc_route_valid(primary="Blender", fallback="Bforartists", explicit=False, compatibility_evidence=False))
    add("FA3-ANIM-P0-005", "OpenToonz separate component admission", opentoonz_admission_valid(role="PRIMARY_TRADITIONAL_2D_REFERENCE", core_license="BSD-3-Clause", component_audit=True), not opentoonz_admission_valid(role="EXCLUSIVE_AUTHORITY", core_license="BSD-3-Clause", component_audit=False))
    add("FA3-ANIM-P0-006", "MuseTalk isolated typed adapter", musetalk_runtime_valid(typed_adapter=True, isolated=True, shared_comfyui_env=False, hrb_lease=True), not musetalk_runtime_valid(typed_adapter=False, isolated=False, shared_comfyui_env=True, hrb_lease=False))
    required_deps = {"FA3-VOICE-001", "FA3-STT-MEDIA-001", "FA3-MUSIC-001", "FA3-DCC-RT3D-001", "FA3-KDENLIVE-EDITORIAL-001", "FA3-HOST-RESOURCE-BROKER-001"}
    add("FA3-ANIM-P0-007", "existing fabric delegation", delegation_valid(required_deps), not delegation_valid({"FA3-ANIMATION-PRODUCTION-001"}))
    add("FA3-ANIM-P0-008", "OTIO canonical timeline", interchange_valid(timeline="OpenTimelineIO", color="OpenColorIO", hdr="OpenEXR", provider_local_root=False), not interchange_valid(timeline=".kdenlive", color="OpenColorIO", hdr="OpenEXR", provider_local_root=True))
    add("FA3-ANIM-P0-009", "OCIO canonical color boundary", interchange_valid(timeline="OpenTimelineIO", color="OpenColorIO", hdr="OpenEXR", provider_local_root=False), not interchange_valid(timeline="OpenTimelineIO", color="provider LUT", hdr="OpenEXR", provider_local_root=False))
    add("FA3-ANIM-P0-010", "OpenEXR HDR intermediate", interchange_valid(timeline="OpenTimelineIO", color="OpenColorIO", hdr="OpenEXR", provider_local_root=False), not interchange_valid(timeline="OpenTimelineIO", color="OpenColorIO", hdr="JPEG", provider_local_root=False))
    add("FA3-ANIM-P0-011", "separate license dimensions", license_admission_valid(dims, commercial=True, noncommercial_component=False), not license_admission_valid({**dims, "model_weights": False}, commercial=True, noncommercial_component=False))
    add("FA3-ANIM-P0-012", "noncommercial production denial", not license_admission_valid(dims, commercial=True, noncommercial_component=True), not license_admission_valid(dims, commercial=True, noncommercial_component=True))
    add("FA3-ANIM-P0-013", "voice face performance consent", lipsync_request_valid(good_lipsync), not lipsync_request_valid({**good_lipsync, "consent": ""}))
    add("FA3-ANIM-P0-014", "HRB accelerator lease", hrb_execution_valid(accelerator=True, lease_valid=True, provider_self_placed=False), not hrb_execution_valid(accelerator=True, lease_valid=False, provider_self_placed=False))
    add("FA3-ANIM-P0-015", "stable GPU UUID and PCI BDF", accelerator_identity_valid(device_uuid="GPU-deadbeef", pci_bdf="0000:05:00.0", runtime_index_only=False), not accelerator_identity_valid(device_uuid="", pci_bdf="GPU0", runtime_index_only=True))
    add("FA3-ANIM-P0-016", "T7910 accelerator roles", hardware_roles_valid(compute_model="NVIDIA GeForce RTX 3090", compute_vram_gib=24, display_model="NVIDIA RTX A1000", display_vram_gib=8, display_implicit_fallback=False), not hardware_roles_valid(compute_model="NVIDIA GeForce RTX 3080", compute_vram_gib=12, display_model="NVIDIA Quadro RTX 4000", display_vram_gib=8, display_implicit_fallback=True))
    add("FA3-ANIM-P0-017", "display GPU isolation", display_fallback_valid(selected_role="PRIMARY_AI_RENDER_COMPUTE", heavy_job=True, explicit_policy=False), not display_fallback_valid(selected_role="DISPLAY_UI_MEDIA_IO", heavy_job=True, explicit_policy=False))
    add("FA3-ANIM-P0-018", "VRAM headroom and concurrency", vram_admission_valid(requested_gib=18, capacity_gib=24, reserve_gib=4, concurrent_heavy=1, max_heavy=1), not vram_admission_valid(requested_gib=23, capacity_gib=24, reserve_gib=4, concurrent_heavy=2, max_heavy=1))
    add("FA3-ANIM-P0-019", "explicit OOM handling", oom_policy_valid(action="QUEUE", explicit=True, silent_device_or_provider_fallback=False), not oom_policy_valid(action="FALLBACK_OTHER_GPU", explicit=False, silent_device_or_provider_fallback=True))
    add("FA3-ANIM-P0-020", "live CPU NUMA topology", cpu_topology_admission_valid(live_discovered=True, lscpu_or_sysfs=True, static_cpu_ids=False, global_threads=None), not cpu_topology_admission_valid(live_discovered=False, lscpu_or_sysfs=False, static_cpu_ids=True, global_threads=88))
    add("FA3-ANIM-P0-021", "physical-core-first thread budget", cpu_topology_admission_valid(live_discovered=True, lscpu_or_sysfs=True, static_cpu_ids=False, global_threads=8), not cpu_topology_admission_valid(live_discovered=True, lscpu_or_sysfs=True, static_cpu_ids=False, global_threads=44))
    add("FA3-ANIM-P0-022", "human finishing boundaries", human_finishing_valid(editorial="Kdenlive", audio="Ardour", picture_lock_human=True), not human_finishing_valid(editorial="provider bot", audio="generated-only", picture_lock_human=False))
    final_checks = {"picture_lock", "audio_lock", "color_qc", "caption_qc", "av_sync_qc", "delivery_qc", "provenance"}
    add("FA3-ANIM-P0-023", "final lock QC provenance", final_master_valid(final_checks), not final_master_valid(final_checks - {"provenance"}))
    first_pin, second_pin = PINNED_REFS["musetalk"], PINNED_REFS["opentoonz"]
    add("FA3-ANIM-P0-024", "immutable provider/model identity", immutable_runtime_policy_valid(runtime_pin=first_pin, model_pin=second_pin, runtime_download=False, floating_ref=False), not immutable_runtime_policy_valid(runtime_pin="main", model_pin="latest", runtime_download=True, floating_ref=True))
    add("FA3-ANIM-P0-025", "no document-only current-host PASS", promotion_claim_valid(ci_reference_pass=True, current_host_claimed=False, real_e2e=False), not promotion_claim_valid(ci_reference_pass=True, current_host_claimed=True, real_e2e=False))
    add("FA3-ANIM-P0-026", "disabled optional provider zero cost", disabled_provider_valid(enabled=False, runtime_cost=0, blocks_global_promotion=False), not disabled_provider_valid(enabled=False, runtime_cost=1, blocks_global_promotion=True))
    passed = sum(case["status"] == "PASS" for case in cases)
    return {"result": "PASS" if passed == len(cases) else "FAIL", "total": len(cases), "passed": passed, "cases": cases}


def gate(root: Path, *, require_evidence: bool = True) -> dict[str, Any]:
    reference = reference_check(root, require_evidence=require_evidence)
    regressions = run_regressions()
    result = "PASS" if reference["result"] == regressions["result"] == "PASS" else "FAIL"
    return {
        "schema": "fa3.animation-production-gate-report.v1",
        "gate_id": GATESET_ID,
        "result": result,
        "reference": reference,
        "regressions": regressions,
        "current_host_runtime_promotion_claim": False,
        "promotion_semantics": "CI_REFERENCE_CONFORMANCE_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="FA3 animation production canonical and regression gate")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--report")
    parser.add_argument("--write-reference-evidence", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = gate(root, require_evidence=not args.write_reference_evidence)
    if args.write_reference_evidence and report["result"] == "PASS":
        evidence = {
            "schema": "fa3.animation-production-reference-evidence.v1",
            "evidence_id": "FA3-EVID-ANIMATION-PRODUCTION-CI-2026-09-02",
            "observed_at": date.today().isoformat(),
            "gate_id": GATESET_ID,
            "result": "PASS",
            "reference_result": report["reference"]["result"],
            "regression_result": report["regressions"]["result"],
            "regression_case_count": report["regressions"]["total"],
            "regression_pass_count": report["regressions"]["passed"],
            "hardware_reference_id": HARDWARE_REFERENCE_ID,
            "capability_count": CAPABILITY_COUNT,
            "new_capabilities": 0,
            "new_architectural_authorities": 0,
            "current_host_runtime_promotion_claim": False,
            "promotion_semantics": "CI_REFERENCE_CONFORMANCE_PASS_NOT_CURRENT_HOST_RUNTIME_EVIDENCE",
        }
        _write(root / "evidence/reference/animation-production-ci-2026-09-02.json", evidence)
        report = gate(root, require_evidence=True)
    report_path = Path(args.report) if args.report else root / "reports/animation-production-gate-report.json"
    _write(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
