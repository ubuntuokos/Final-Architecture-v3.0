from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from fa3_capability_count_dehardcode_gate import gate, scan_active_python
from fa3_release_baseline import BaselineError, load_active_release_baseline


class ReleaseBaselineLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[1]

    def fixture(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="fa3-release-baseline-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        src = self.repo_root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
        dst = tmp / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return tmp

    def test_repository_loader_matches_baseline_document(self) -> None:
        baseline = load_active_release_baseline(self.repo_root)
        raw = json.loads((self.repo_root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json").read_text(encoding="utf-8"))
        self.assertEqual(baseline.release, raw["current_release"])
        self.assertEqual(baseline.capability_count, raw["current_release_capability_count"])

    def test_future_release_count_is_data_driven(self) -> None:
        root = self.fixture()
        path = root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["current_release"] = "future/test-release"
        data["current_release_capability_count"] = 151
        data["release_baselines"] = [{"release": "future/test-release", "capability_count": 151, "status": "ACTIVE_BASELINE"}]
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        baseline = load_active_release_baseline(root)
        self.assertEqual(baseline.release, "future/test-release")
        self.assertEqual(baseline.capability_count, 151)

    def test_mismatched_mirror_fails_closed(self) -> None:
        root = self.fixture()
        path = root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["current_release_capability_count"] += 1
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        with self.assertRaises(BaselineError):
            load_active_release_baseline(root)

    def test_ambiguous_active_release_fails_closed(self) -> None:
        root = self.fixture()
        path = root / "canonical/FA3-RELEASE-CAPABILITY-BASELINE-001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        active = next(item for item in data["release_baselines"] if item.get("status") == "ACTIVE_BASELINE")
        data["release_baselines"].append(dict(active))
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        with self.assertRaises(BaselineError):
            load_active_release_baseline(root)

    def test_repository_dehardcode_gate_passes(self) -> None:
        result = gate(self.repo_root)
        self.assertEqual(result["result"], "PASS", result)
        self.assertEqual(result["active_hardcode_hits"], 0)
        self.assertEqual(result["authority_delta"], 0)
        self.assertEqual(result["capability_delta"], 0)

    def test_scanner_detects_reintroduced_literal(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="fa3-dehardcode-scan-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        path = tmp / "src/example.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("CAPS = 143\n", encoding="utf-8")
        hits = scan_active_python(tmp)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["path"], "src/example.py")


if __name__ == "__main__":
    unittest.main()
