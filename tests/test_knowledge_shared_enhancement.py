from __future__ import annotations

import json
import unittest
from pathlib import Path

from fa3_hybrid_retrieval import build_plan
from fa3_knowledge_shared_enhancement_gate import gate
from fa3_release_baseline import load_active_release_baseline

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeSharedEnhancementTests(unittest.TestCase):
    def test_static_gate_passes(self):
        report = gate(ROOT)
        self.assertEqual("PASS", report["result"], json.dumps(report, indent=2))

    def test_active_baseline_is_preserved(self):
        baseline = load_active_release_baseline(ROOT)
        self.assertEqual(175, baseline.capability_count)
        report = gate(ROOT)
        self.assertEqual(baseline.capability_count, report["capability_count"])
        self.assertEqual(0, report["new_capabilities"])
        self.assertEqual(0, report["new_architectural_authorities"])

    def test_default_retrieval_budget_is_explicit_policy_reference(self):
        plan = build_plan({"query": "q", "source_scope": {"project_id": "P"}})
        self.assertEqual("POLICY_RESOLVED", plan["effort_budget"]["mode"])
        self.assertEqual("FA3-KNOWLEDGE-RETRIEVAL-BUDGET-POLICY-001", plan["effort_budget"]["policy_ref"])
        self.assertEqual("CANONICAL_SECURITY_DECISION_REQUIRED_BEFORE_CANDIDATE_GENERATION", plan["authorization_requirement"])

    def test_explicit_retrieval_budget_is_bounded(self):
        bounds = {
            "mode": "EXPLICIT_BOUNDS",
            "max_query_decomposition": 2,
            "max_retrieval_rounds": 3,
            "max_candidate_expansion": 100,
            "max_rerank_candidates": 40,
            "max_graph_depth": 4,
            "max_context_tokens": 12000,
            "max_model_tokens": 4000,
            "max_latency_ms": 5000,
        }
        plan = build_plan({"query": "q", "source_scope": {}, "effort_budget": bounds})
        self.assertEqual("EXPLICIT_BOUNDS", plan["effort_budget"]["mode"])
        self.assertEqual(3, plan["effort_budget"]["max_retrieval_rounds"])

    def test_unbounded_explicit_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            build_plan({"query": "q", "source_scope": {}, "effort_budget": {"mode": "EXPLICIT_BOUNDS", "max_retrieval_rounds": 3}})

    def test_ragflow_is_reference_only(self):
        provider = json.loads((ROOT / "canonical/providers/FA3-PROVIDER-RAGFLOW-001.json").read_text())
        self.assertEqual("OPTIONAL_DISABLED_BY_DEFAULT", provider["activation_mode"])
        self.assertEqual("NOT_PROMOTED_REFERENCE_ONLY", provider["runtime_activation_status"])
        self.assertFalse(provider["architectural_authority"])

    def test_analysis_sources_do_not_forge_donor_adoption(self):
        assessment = json.loads((ROOT / "canonical/assessments/FA3-KNOWLEDGE-SHARED-MULTISOURCE-REUSE-ASSESSMENT-001.json").read_text())
        reference = json.loads((ROOT / "canonical/references/FA3-KNOWLEDGE-MULTISOURCE-PATTERN-REFERENCE-2026-10-01.json").read_text())
        self.assertFalse(assessment["adoption_authorized"])
        self.assertEqual([], assessment["selected_existing_donor_ids"])
        self.assertFalse(reference["formal_donor_registry_mutation"])
        self.assertFalse(reference["donor_usage_edge_created"])


if __name__ == "__main__":
    unittest.main()
