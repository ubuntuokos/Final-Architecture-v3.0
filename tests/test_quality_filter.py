import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_quality_filter import _candidate_paths, analyze_text, infer_concerns, load_rules, select_quality_skills

class QualityFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_rules(ROOT)

    def test_hard_gate_blocks_placeholder_even_with_justification(self):
        text = "// FA3-QUALITY-JUSTIFY Q-CORE-001: legacy demo\nText { text: 'Lorem ipsum' }"
        report = analyze_text("apps/demo.qml", text, self.registry, {"CORE"})
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any(x["rule_id"] == "Q-CORE-001" for x in report["findings"]))

    def test_purpose_gate_requires_named_reason(self):
        bad = analyze_text("apps/demo.qml", 'Text { text: "World-class workflow" }', self.registry, {"COPY"})
        good = analyze_text(
            "apps/demo.qml",
            '// FA3-QUALITY-JUSTIFY Q-COPY-003: claim is backed by the linked benchmark\nText { text: "World-class workflow" }',
            self.registry,
            {"COPY"},
        )
        self.assertEqual(bad["result"], "FAIL")
        self.assertEqual(good["result"], "PASS")

    def test_quality_lock_warns_without_blocking(self):
        report = analyze_text("src/example.py", "# ==========\nvalue = 1\n", self.registry, {"CODE"})
        self.assertEqual(report["result"], "PASS")
        self.assertGreaterEqual(report["warnings"], 1)

    def test_qml_placeholder_text_property_is_not_placeholder_copy_marker(self):
        qml_property = analyze_text(
            "apps/demo.qml",
            'TextField { placeholderText: "Mit keresel?" }',
            self.registry,
            {"CORE"},
        )
        marker = analyze_text(
            "apps/demo.qml",
            '// PLACEHOLDER_TEXT\nText { text: "replace before release" }',
            self.registry,
            {"CORE"},
        )
        self.assertEqual(qml_property["result"], "PASS")
        self.assertEqual(marker["result"], "FAIL")
        self.assertTrue(any(x["rule_id"] == "Q-CORE-002" for x in marker["findings"]))

    def test_direct_provider_execution_is_blocked_in_ui(self):
        report = analyze_text("apps/demo.qml", 'Text { text: "run" }\n// ollama run model', self.registry, {"UI"})
        self.assertEqual(report["result"], "FAIL")
        self.assertTrue(any(x["rule_id"] == "Q-UI-004" for x in report["findings"]))

    def test_concern_inference_is_scope_bounded(self):
        self.assertEqual(infer_concerns("docs/architecture.md"), set())
        self.assertIn("UI", infer_concerns("apps/fa3-control-center/qml/Main.qml"))
        self.assertEqual(infer_concerns("src/example.py"), {"CODE"})

    def test_quality_skill_selection_is_minimal_and_deterministic(self):
        selected = select_quality_skills(["ui", "accessibility"])
        self.assertEqual(
            selected,
            ["fa3-quality-ui", "fa3-quality-copy", "fa3-quality-human", "fa3-quality-responsive"],
        )
        self.assertNotIn("fa3-quality-code", selected)

    def test_deleted_changed_path_is_not_scan_candidate(self):
        from unittest import mock
        with mock.patch("fa3_quality_filter._git_changed_paths", return_value=["src/deleted_provider.py"]):
            self.assertEqual(_candidate_paths(ROOT, "repo", "origin/main"), [])

    def test_registry_shape(self):
        ids = [r["id"] for r in self.registry["rules"]]
        self.assertGreaterEqual(len(ids), 24)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"CORE", "UI", "COPY", "HUMAN", "RESPONSIVE", "CODE", "FA3"}.issubset(
            {r["concern"] for r in self.registry["rules"]}
        ))

if __name__ == "__main__":
    unittest.main()
