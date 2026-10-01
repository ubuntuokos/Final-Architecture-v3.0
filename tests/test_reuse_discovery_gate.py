from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_reuse_assessment import assess_intent
from fa3_reuse_catalog import build_catalog
from fa3_reuse_resolver import bounded_rank, resolve
from fa3_reuse_gate import (
    validate_assessment_donor_usage_edges,
    validate_donor_planning_snapshot,
    validate_shared_capability_placement,
)


class ReuseDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.intent = json.loads((ROOT / "canonical/intents/FA3-EMBEDDING-FABRIC-APPLICATION-INTENT-001.json").read_text(encoding="utf-8"))

    def test_catalog_discovers_existing_fa3_assets(self):
        ids = {row["candidate_id"] for row in build_catalog(ROOT)["entries"]}
        self.assertIn("FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001", ids)
        self.assertIn("FA3-INFERENCE-PORTABILITY-001", ids)
        self.assertIn("FA3-HARDWARE-BASELINE-001", ids)
        self.assertIn("fa3.document.retrieve", ids)

    def test_catalog_federates_khronos_open_standard_sources(self):
        rows = build_catalog(ROOT)["entries"]
        by_id = {row["candidate_id"]: row for row in rows}
        for adapter_id in (
            "fa3.khronos.glslang",
            "fa3.khronos.spirv-tools",
            "fa3.khronos.spirv-cross",
            "fa3.khronos.ktx",
            "fa3.khronos.openxr",
            "fa3.khronos.opencl",
            "fa3.khronos.anari",
            "fa3.khronos.openvx",
            "fa3.khronos.nnef",
        ):
            self.assertIn(adapter_id, by_id)
            self.assertEqual(by_id[adapter_id]["candidate_class"], "OPEN_STANDARD_ADAPTER")
            self.assertFalse(by_id[adapter_id]["authority"])
            self.assertFalse(by_id[adapter_id]["automatic_selection"])
        self.assertIn("FA3-KHRONOS-BINDING:SHADER_FABRIC", by_id)
        self.assertIn("FA3-KHRONOS-BINDING:ASSET_GRAPH", by_id)
        self.assertIn("FA3-KHRONOS-BINDING:RENDER_FABRIC", by_id)
        self.assertEqual(by_id["FA3-KHRONOS-BINDING:SHADER_FABRIC"]["candidate_class"], "OPEN_STANDARD_FABRIC_BINDING")

    def test_shader_intent_surfaces_khronos_shader_stack(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["shader", "spirv", "graphics"]
        intent["execution_classes"] = ["cpu"]
        intent["task_classes"] = ["shader", "compiler"]
        intent["skill_triggers"] = []
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        ids = {row["candidate_id"] for row in resolution["candidates"]}
        self.assertIn("fa3.khronos.glslang", ids)
        self.assertIn("fa3.khronos.spirv-tools", ids)
        self.assertIn("fa3.khronos.spirv-cross", ids)
        self.assertIn("FA3-KHRONOS-BINDING:SHADER_FABRIC", ids)

    def test_every_intent_gets_mandatory_khronos_source_review(self):
        resolution = resolve(ROOT, self.intent)
        review = next(
            row for row in resolution["mandatory_source_reviews"]
            if row["source_family_id"] == "FA3-KHRONOS-OPEN-STANDARDS-001"
        )
        self.assertIn(review["review_status"], {"MATCHED", "REVIEWED_NO_MATCH"})
        self.assertTrue(review["available_candidate_ids"])
        self.assertFalse(review["authority"])
        self.assertFalse(review["automatic_selection"])
        self.assertFalse(review["automatic_activation"])

    def test_assessment_projects_mandatory_khronos_source_review(self):
        result = assess_intent(ROOT, self.intent)
        review = next(
            row for row in result["mandatory_source_reviews"]
            if row["source_family_id"] == "FA3-KHRONOS-OPEN-STANDARDS-001"
        )
        self.assertIn(review["review_status"], {"MATCHED", "REVIEWED_NO_MATCH"})
        self.assertFalse(review["authority"])
        self.assertFalse(review["automatic_selection"])

    def test_donor_registry_backfill_is_central_and_non_authoritative(self):
        registry = json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8"))
        entries = registry["entries"]
        ids = {row["donor_id"] for row in entries}
        self.assertGreaterEqual(len(entries), 160)
        self.assertEqual(registry["backfill"]["entry_count"], len(entries))
        self.assertFalse(registry["authority"])
        self.assertFalse(registry["capture_policy"]["potential_donor_signal_requires_capture"])
        self.assertEqual(registry["capture_policy"]["default_status"], "NO_CAPTURE_ANALYSIS_ONLY")
        self.assertEqual(registry["capture_policy"]["owner_marker_required"], "donornak")
        self.assertTrue(registry["capture_policy"]["owner_role_required"])
        self.assertEqual(registry["capture_policy"]["owner_marked_capture_status"], "ACCEPTED_REFERENCE")
        self.assertEqual(
            registry["capture_policy"]["unmarked_link_disposition"],
            "ANALYSIS_ONLY_NO_REGISTRY_MUTATION",
        )
        self.assertFalse(registry["capture_policy"]["legacy_automatic_candidate_capture"])
        decision = json.loads((ROOT / "canonical/decisions/FA3-DEC-DONOR-REFERENCE-REGISTRY-2026-09-28.json").read_text(encoding="utf-8"))
        profile = json.loads((ROOT / "canonical/profiles/FA3-REUSE-DISCOVERY-001.json").read_text(encoding="utf-8"))
        contract = json.loads((ROOT / "canonical/contracts/FA3-REUSE-DISCOVERY-CONTRACTS-001.json").read_text(encoding="utf-8"))
        enforcement = json.loads((ROOT / "canonical/enforcement-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(decision["capture_rule"], "ONLY_LINKS_EXPLICITLY_PRECEDED_BY_OWNER_DONORNAK_MARKER_MAY_ENTER_REGISTRY")
        self.assertFalse(profile["donor_reference_binding"]["potential_donor_signal_requires_capture"])
        self.assertTrue(profile["donor_reference_binding"]["published_main_registry_only"])
        self.assertEqual(profile["donor_reference_binding"]["owner_marker_required"], "donornak")
        self.assertFalse(contract["contracts"]["DonorReferenceProjection"]["potential_signal_capture_required"])
        self.assertTrue(contract["contracts"]["DonorReferenceProjection"]["unmarked_links_analysis_only"])
        self.assertFalse(enforcement["donor_registry_serialization"]["deny_when_maintenance_or_open_donor_pr"])
        self.assertEqual(enforcement["donor_registry_serialization"]["planning_registry_source"],
                         "LATEST_VERIFIED_COMMITTED_MAIN_ONLY")
        self.assertTrue(registry["planning_policy"]["query_required_for_every_new_or_materially_modified_application_capability_or_module"])
        for donor_id in (
            "FA3-DONOR-AGENT0AI-AGENT-ZERO-001",
            "FA3-DONOR-MICROSOFT-MCP-GATEWAY-001",
            "FA3-DONOR-CYTOSTACK-OPENWOLF-001",
            "FA3-DONOR-VIGOZHAO-AI-VISUAL-PROMPT-COOKBOOK-001",
            "FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001",
            "FA3-DONOR-GARRYTAN-GSTACK-001",
            "FA3-DONOR-BOADIJ-PI-HERDSMAN-001",
            "FA3-DONOR-P4NDA0S-REVERSE-SKILLS-001",
            "FA3-DONOR-SYSTEM-ONE-HARNESS-001",
        ):
            self.assertIn(donor_id, ids)

    def test_reuse_catalog_federates_active_donors_and_excludes_rejected(self):
        registry = json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8"))
        expected = {
            row["donor_id"] for row in registry["entries"]
            if row["discoverable_for_planning"] is True and row["status"] not in {"REJECTED", "SUPERSEDED"}
        }
        rows = [row for row in build_catalog(ROOT)["entries"] if row["candidate_class"] == "DONOR_REFERENCE"]
        by_id = {row["candidate_id"]: row for row in rows}
        self.assertEqual(set(by_id), expected)
        self.assertNotIn("FA3-DONOR-DONUTBROWSER-001", by_id)
        self.assertIn("FA3-DONOR-MICROSOFT-MCP-GATEWAY-001", by_id)
        self.assertTrue(all(row["distribution_class"] == "REFERENCE_ONLY" for row in rows))
        self.assertTrue(all(row["release_bundle_status"] == "EXCLUDED" for row in rows))
        self.assertTrue(all(row["authority"] is False for row in rows))
        self.assertTrue(all(row["automatic_dependency"] is False for row in rows))
        self.assertTrue(all(row["automatic_code_import"] is False for row in rows))

    def test_donor_terms_surface_for_future_application_planning(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["code-anatomy", "context-broker", "agent-handoff"]
        intent["task_classes"] = ["agent"]
        intent["skill_triggers"] = []
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        by_id = {row["candidate_id"]: row for row in resolution["candidates"]}
        self.assertIn("FA3-DONOR-CYTOSTACK-OPENWOLF-001", by_id)
        donor = by_id["FA3-DONOR-CYTOSTACK-OPENWOLF-001"]
        self.assertEqual(donor["candidate_class"], "DONOR_REFERENCE")
        self.assertEqual(donor["reuse_mode"], "REFERENCE_ONLY")
        self.assertFalse(donor["authority"])
        self.assertFalse(donor["activation_candidate"])

    def test_visual_prompt_donor_surfaces_for_planned_creative_apps(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["visual-prompt", "camera", "style"]
        intent["task_classes"] = ["creative"]
        intent["skill_triggers"] = []
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        ids = {row["candidate_id"] for row in resolution["candidates"]}
        self.assertIn("FA3-DONOR-VIGOZHAO-AI-VISUAL-PROMPT-COOKBOOK-001", ids)

    def test_golden_embedding_intent_reuses_document_retrieval(self):
        result = assess_intent(ROOT, self.intent)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["implementation_readiness"], "PENDING_GAPS")
        ids = {row["id"] for row in result["selected_reuse"]}
        self.assertIn("fa3.document.retrieve", ids)

    def test_catalog_federates_admitted_skills_and_external_skill_sources(self):
        rows = build_catalog(ROOT)["entries"]
        by_id = {row["candidate_id"]: row for row in rows}
        self.assertIn("fa3-quality-code", by_id)
        skill = by_id["fa3-quality-code"]
        self.assertEqual(skill["candidate_class"], "SKILL")
        self.assertEqual(skill["admission_status"], "ADMITTED")
        self.assertTrue(skill["task_scoped"])
        self.assertFalse(skill["authority"])
        external = [row for row in rows if row["candidate_class"] == "EXTERNAL_SKILL_SOURCE"]
        self.assertGreaterEqual(len(external), 8)
        self.assertTrue(all(row["distribution_class"] == "REFERENCE_ONLY" for row in external))
        self.assertTrue(all(row["authority"] is False for row in external))
        self.assertTrue(all(row["automatic_install"] is False for row in external))

    def test_task_class_selects_only_admitted_skill_context(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["code"]
        intent["task_classes"] = ["code"]
        intent["skill_triggers"] = ["quality.code"]
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        skills = [row for row in resolution["candidates"] if row["candidate_class"] == "SKILL"]
        code = next(row for row in skills if row["candidate_id"] == "fa3-quality-code")
        self.assertEqual(code["reuse_mode"], "ADMITTED_SKILL_REUSE")
        self.assertTrue(code["activation_candidate"])
        self.assertEqual(code["status"], "ADMITTED")
        self.assertFalse(code["authority"])
        self.assertFalse(resolution["skill_activation_authority"])

    def test_external_skill_sources_never_gain_install_or_activation_authority(self):
        resolution = resolve(ROOT, self.intent)
        self.assertFalse(resolution["external_skill_source_install_authority"])
        rows = build_catalog(ROOT)["entries"]
        external = [row for row in rows if row["candidate_class"] == "EXTERNAL_SKILL_SOURCE"]
        self.assertTrue(external)
        self.assertTrue(all(row["status"] == "REFERENCE_ONLY" for row in external))
        self.assertTrue(all(row["automatic_activation"] is False for row in external))

    def test_security_intent_can_surface_external_skill_idea_source_without_trust(self):
        intent = copy.deepcopy(self.intent)
        intent["required_capabilities"] = []
        intent["optional_capabilities"] = []
        intent["problem_classes"] = ["security"]
        intent["declared_gaps"] = []
        resolution = resolve(ROOT, intent)
        refs = [row for row in resolution["candidates"] if row["candidate_class"] == "EXTERNAL_SKILL_SOURCE"]
        skillspector = next(row for row in refs if row.get("repository") == "NVIDIA/SkillSpector")
        self.assertEqual(skillspector["reuse_mode"], "REFERENCE_ONLY")
        self.assertFalse(skillspector["activation_candidate"])
        self.assertFalse(skillspector["authority"])
        self.assertFalse(skillspector["automatic_install"])

    def test_existing_authority_collision_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["proposed_authority_roles"] = ["model_routing"]
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("AUTHORITY_COLLISION", result["blocking_findings"])

    def test_upstream_uninstall_requirement_fails_coexistence(self):
        intent = copy.deepcopy(self.intent)
        intent["namespace_claims"]["requires_upstream_uninstall"] = True
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("COEXISTENCE_INVALID", result["blocking_findings"])

    def test_hardware_vendor_pin_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["hardware_audit"]["vendor_neutral"] = False
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("HARDWARE_AUDIT_INVALID", result["blocking_findings"])

    def test_duplicate_capability_declaration_fails(self):
        intent = copy.deepcopy(self.intent)
        intent["declared_new_capabilities"] = ["fa3.document.retrieve"]
        result = assess_intent(ROOT, intent)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("DUPLICATE_CAPABILITY_DECLARATION", result["blocking_findings"])

    def test_decision_fabric_cannot_expand_candidate_set(self):
        self.assertEqual(bounded_rank(["a", "b"], ["b", "a"]), ["b", "a"])
        with self.assertRaises(ValueError):
            bounded_rank(["a", "b"], ["a", "c"])

    def test_resolver_records_space_for_real_gaps_without_inventing_authority(self):
        resolution = resolve(ROOT, self.intent)
        self.assertEqual(resolution["authority_collisions"], [])
        self.assertEqual(resolution["decision_fabric_candidate_expansion"], "DENY")
        self.assertEqual(resolution["agent_native_output"], "PROPOSAL_ONLY")

    def test_donor_backfill_includes_earlier_red_flag_and_security_research(self):
        registry = json.loads((ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json").read_text(encoding="utf-8"))
        keys = {row["source"]["normalized_key"] for row in registry["entries"]}
        for key in ("github:anninhn/econ-research-skills", "github:sahielbose/tideline",
                    "github:pu11en/clinical-triage-agent", "github:paulveillard/cybersecurity-iam",
                    "github:anil-matcha/open-generative-ai"):
            self.assertIn(key, keys)

    def test_capture_does_not_conflate_same_name_distinct_repositories(self):
        import tempfile
        from fa3_donor_registry import capture_candidate, REJECTION_AUDIT_REL
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"id":"FA3-DONOR-REFERENCE-REGISTRY-001", "entries":[]}), encoding="utf-8")
            audit = root / REJECTION_AUDIT_REL
            audit.write_text(json.dumps({"id":"FA3-DONOR-REJECTION-AUDIT-001", "entries":[]}), encoding="utf-8")
            first = capture_candidate(root, name="Example", source_kind="GITHUB",
                source_locator="https://github.com/alice/example", seen_date="2026-09-28",
                explicit_donor_marker=True, owner_submitted_link=True)
            second = capture_candidate(root, name="Example", source_kind="GITHUB",
                source_locator="https://github.com/bob/example", seen_date="2026-09-28",
                explicit_donor_marker=True, owner_submitted_link=True)
            repeat = capture_candidate(root, name="Example", source_kind="GITHUB",
                source_locator="https://github.com/alice/example", seen_date="2026-09-28",
                explicit_donor_marker=True, owner_submitted_link=True)
            self.assertTrue(first["created"])
            self.assertTrue(second["created"])
            self.assertFalse(repeat["created"])
            self.assertEqual(2, len(json.loads(path.read_text(encoding="utf-8"))["entries"]))

    def test_conversation_mention_extracts_only_source_metadata(self):
        from fa3_donor_registry import parse_donor_mention
        name, kind, url = parse_donor_mention("Donornak: https://github.com/example/source")
        self.assertEqual((name,kind,url), ("example/source","GITHUB","https://github.com/example/source"))
        with self.assertRaises(ValueError):
            parse_donor_mention("Look at https://github.com/example/source")
        with self.assertRaises(ValueError):
            parse_donor_mention("donornak: https://github.com/a/one https://github.com/b/two")


    def test_donor_planning_snapshot_contract_rejects_stale_main(self):
        expected = {
            "published_main_commit": "a" * 40,
            "donor_registry_id": "FA3-DONOR-REFERENCE-REGISTRY-001",
            "donor_registry_blob_sha": "b" * 40,
            "donor_registry_sha256": "c" * 64,
            "donor_registry_entry_count": 1307,
        }
        assessment = {"id": "FA3-TEST-REUSE-ASSESSMENT-001",
                      "donor_planning_snapshot": {**expected, "published_main_commit": "d" * 40}}
        findings = validate_donor_planning_snapshot(assessment, expected)
        self.assertTrue(any(row["code"] == "REUSE-SNAPSHOT-002" for row in findings))

    def test_shared_capability_placement_requires_shared_or_reviewed_exception(self):
        assessment = {"id": "FA3-TEST-REUSE-ASSESSMENT-001",
                      "shared_capability_placement": {
                          "reviewed": True,
                          "multi_application_reuse_detected": True,
                          "disposition": "LOCAL_SINGLE_CONSUMER",
                          "retrospective_consumer_impact_reviewed": True}}
        findings = validate_shared_capability_placement(assessment)
        self.assertTrue(any(row["code"] == "REUSE-SNAPSHOT-017" for row in findings))
        assessment["shared_capability_placement"] = {
            "reviewed": True,
            "multi_application_reuse_detected": True,
            "disposition": "SHARED",
            "shared_component_ids": ["FA3-SHARED-TEST-001"],
            "retrospective_consumer_impact_reviewed": True}
        self.assertEqual(validate_shared_capability_placement(assessment), [])

    def test_actual_donor_pattern_use_requires_usage_edge(self):
        assessment = {"id": "FA3-TEST-REUSE-ASSESSMENT-001",
                      "donor_pattern_reuse": [{"donor_id": "FA3-DONOR-X-001"}]}
        links = {"donor_usage_records": []}
        findings = validate_assessment_donor_usage_edges(assessment, links)
        self.assertTrue(any(row["code"] == "REUSE-SNAPSHOT-018" for row in findings))
        links["donor_usage_records"] = [{"donor_id": "FA3-DONOR-X-001", "status": "ACTIVE"}]
        self.assertEqual(validate_assessment_donor_usage_edges(assessment, links), [])


if __name__ == "__main__":
    unittest.main()
