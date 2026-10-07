from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_shared_semantic_ontology import CORE, FILES, GUI, SDK, validate


ROOT = Path(__file__).resolve().parents[1]


class SharedSemanticOntologyTests(unittest.TestCase):
    def _copy_fixture(self) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="fa3-semantic-ontology-"))
        self.addCleanup(shutil.rmtree, temp, True)
        for rel in FILES:
            src = ROOT / rel
            dst = temp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return temp

    def _mutate(self, root: Path, rel: str, mutator) -> None:
        path = root / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        mutator(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_canonical_static_foundation_passes(self) -> None:
        self.assertEqual("PASS", validate(ROOT)["result"])

    def test_ai_direct_canonical_generation_fails_closed(self) -> None:
        root = self._copy_fixture()
        self._mutate(root, CORE, lambda d: d["required_semantics"].__setitem__("ai_generation", "CANONICAL"))
        self.assertEqual("FAIL", validate(root)["result"])

    def test_close_match_merge_fails_closed(self) -> None:
        root = self._copy_fixture()
        self._mutate(root, CORE, lambda d: d["required_semantics"].__setitem__("close_match", "MERGING"))
        self.assertEqual("FAIL", validate(root)["result"])

    def test_model_router_bypass_fails_closed(self) -> None:
        root = self._copy_fixture()
        self._mutate(root, SDK, lambda d: d["routing_policy"].__setitem__("provider_selection_outside_model_router", "ALLOWED"))
        self.assertEqual("FAIL", validate(root)["result"])

    def test_silent_fallback_fails_closed(self) -> None:
        root = self._copy_fixture()
        self._mutate(root, SDK, lambda d: d["routing_policy"].__setitem__("silent_fallback", "ALLOWED"))
        self.assertEqual("FAIL", validate(root)["result"])

    def test_gui_silent_identity_merge_fails_closed(self) -> None:
        root = self._copy_fixture()
        self._mutate(root, GUI, lambda d: d["identity_review"].__setitem__("silent_merge", True))
        self.assertEqual("FAIL", validate(root)["result"])

    def test_gui_mode_indicator_is_mandatory(self) -> None:
        root = self._copy_fixture()
        def remove_mode(d):
            d["global_requirements"] = [
                item for item in d["global_requirements"]
                if item != "MANDATORY_GLOBAL_WORKLOAD_MODE_INDICATOR"
            ]
        self._mutate(root, GUI, remove_mode)
        self.assertEqual("FAIL", validate(root)["result"])


if __name__ == "__main__":
    unittest.main()
