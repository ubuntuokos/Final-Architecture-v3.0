#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def run():
    findings = []
    profile = load("canonical/profiles/FA3-GENERATIVE-MEDIA-MESH-001.json")
    contract = load("canonical/contracts/FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001.json")
    assessment = load("canonical/assessments/FA3-HIDREAM-GENERATIVE-MEDIA-MESH-REUSE-ASSESSMENT-2026-10-04.json")
    decision = load("canonical/decisions/FA3-DEC-HIDREAM-GENERATIVE-MEDIA-MESH-2026-10-04.json")
    impact = load("canonical/current-host-impact/FA3-CH-IMPACT-HIDREAM-GENERATIVE-MEDIA-MESH-PR674-20261004.json")
    current_host = load("canonical/FA3-GENERATIVE-MEDIA-MESH-CURRENT-HOST-CONFORMANCE-001.json")
    links = load("canonical/FA3-APPLICATION-DONOR-LINKS-001.json")
    gui = load("canonical/FA3-GUI-SURFACE-REGISTRY-001.json")

    if profile.get("capability_count") != 175 or contract.get("capability_count") != 175:
        findings.append("GMM-001 capability baseline drift")
    if profile.get("new_capability") is not False or profile.get("new_architectural_authority") is not False:
        findings.append("GMM-002 capability or authority expansion")
    if assessment.get("pending_or_unmerged_donors_consumed") is not False:
        findings.append("GMM-003 pending donor consumed")
    if decision.get("child_admission_state") != "BLOCKED_PENDING_EXPLICIT_CHILD_DONOR_MARKERS_AND_INDIVIDUAL_GATES":
        findings.append("GMM-004 child admission not fail-closed")
    if decision.get("runtime_promotion_claim") is not False or decision.get("current_host_pass_claimed") is not False:
        findings.append("GMM-005 forbidden runtime/current-host claim")
    if impact.get("status") != "RECONCILED" or impact.get("physical_requalification_required") is not True:
        findings.append("GMM-005A current-host structural impact not reconciled")
    if impact.get("historical_evidence_reused") is not False:
        findings.append("GMM-005B historical current-host evidence reuse forbidden")
    if "canonical/FA3-GENERATIVE-MEDIA-MESH-CURRENT-HOST-CONFORMANCE-001.json" not in impact.get("current_host_changes", []):
        findings.append("GMM-005C current-host companion binding missing")
    expected_structural = {
        "canonical/contracts/FA3-GENERATIVE-MEDIA-MESH-CONTRACTS-001.json",
        "canonical/decisions/FA3-DEC-HIDREAM-GENERATIVE-MEDIA-MESH-2026-10-04.json",
        "canonical/gates/FA3-GATE-GENERATIVE-MEDIA-MESH-001.json",
        "src/fa3_generative_media_mesh_gate.py",
        "src/fa3_gui_gate.py",
    }
    if not expected_structural.issubset(set(impact.get("structural_changes", []))):
        findings.append("GMM-005D current-host structural coverage incomplete")
    if current_host.get("status") != "PENDING_FRESH_PHYSICAL_CURRENT_HOST_REQUALIFICATION":
        findings.append("GMM-005E current-host conformance must remain pending fresh physical evidence")
    if current_host.get("physical_pass_claimed") is not False or current_host.get("runtime_promotion_claim") is not False:
        findings.append("GMM-005F forbidden current-host pass/runtime promotion claim")
    if current_host.get("historical_evidence_reused") is not False or current_host.get("evidence_requirements", {}).get("synthetic_or_simulated_pass_allowed") is not False:
        findings.append("GMM-005G current-host evidence boundary weakened")
    rules = contract.get("hard_rules", {})
    for key in (
        "silent_provider_model_backend_fallback",
        "automatic_display_gpu_enrollment",
    ):
        if rules.get(key) is not False:
            findings.append(f"GMM-006 unsafe rule {key}")
    for key in (
        "child_repo_execution_requires_individual_admission",
        "org_level_donor_does_not_admit_children",
        "static_materialization_is_not_physical_current_host_pass",
    ):
        if rules.get(key) is not True:
            findings.append(f"GMM-007 missing rule {key}")

    def mesh_bound(row):
        primary = row.get("primary_consumer", {})
        profiles = row.get("fa3_bindings", {}).get("profile_ids", [])
        return (
            row.get("status") != "REMOVED"
            and (
                primary.get("id") == "FA3-GENERATIVE-MEDIA-MESH-001"
                or "FA3-GENERATIVE-MEDIA-MESH-001" in profiles
            )
        )
    active = {x.get("donor_id") for x in links.get("donor_usage_records", []) if mesh_bound(x)}
    required = {x["donor_id"] for x in assessment.get("donor_pattern_reuse", [])}
    if not required.issubset(active):
        findings.append("GMM-008 mesh-bound donor usage edge missing:" + ",".join(sorted(required-active)))

    child = profile.get("hidream_children", {})
    if child.get("canonical_child_queue") is not False or child.get("child_sources_canonicalized") is not False:
        findings.append("GMM-008A unmarked HiDream child source canonicalized")
    if child.get("automatic_registration") is not False or child.get("automatic_execution") is not False:
        findings.append("GMM-008B unsafe child registration/execution")

    studio = next((x for x in gui.get("surfaces", []) if x.get("route_id") == "create.ai-studio"), {})
    children = studio.get("children", [])
    if not any(x.get("surface_id") == "create.ai-studio.generative-media-mesh" for x in children):
        findings.append("GMM-009 GUI registry binding missing")

    qml = (ROOT / "apps/shared/generative-media/qml/GenerativeMediaMeshPanel.qml").read_text(encoding="utf-8")
    for token in ("RUNTIME GATED", "Model Router", "HRB", "175", "HiDream child providers: not admitted"):
        if token not in qml:
            findings.append("GMM-010 GUI boundary missing:" + token)
    return findings

if __name__ == "__main__":
    result = run()
    if result:
        print("\n".join(result))
        raise SystemExit(1)
    print("FA3 Generative Media Mesh static gate: PASS")