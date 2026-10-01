"""Automatic and explicit FA3 donor count refresh regressions."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_donor_registry import (REGISTRY_REL, REJECTION_AUDIT_REL, _atomic_write,
                                capture_candidate, refresh_donor_count)
from fa3_donor_chat_import import ingest


class CountRefreshTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / REGISTRY_REL
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps({
            "id": "FA3-DONOR-REFERENCE-REGISTRY-001",
            "capability_count": 175,
            "entries": [], "backfill": {"entry_count": 0},
        }), encoding="utf-8")
        audit = self.root / REJECTION_AUDIT_REL
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps({
            "id": "FA3-DONOR-REJECTION-AUDIT-001", "entries": []
        }), encoding="utf-8")

    def current(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def add(self, name):
        return capture_candidate(
            self.root, name=name, source_kind="GITHUB",
            source_locator="https://github.com/example/" + name,
            owner_submitted_link=True, explicit_donor_marker=True,
            seen_date="2026-09-29")

    def test_direct_capture_refreshes_after_each_add_and_merge(self):
        self.add("one")
        self.assertEqual(self.current()["backfill"]["entry_count"], 1)
        self.add("two")
        self.assertEqual(self.current()["backfill"]["entry_count"], 2)
        self.assertFalse(self.add("two")["created"])
        state = self.current()
        self.assertEqual(state["backfill"]["entry_count"], len(state["entries"]))
        self.assertEqual(state["capability_count"], 175)

    def test_batched_ingest_commits_one_coherent_count(self):
        sources = " ".join("https://github.com/example/tool" + str(i) for i in range(4))
        result = ingest(self.root, [{
            "speaker_role": "user", "text": "donornak: " + sources,
        }], origin="chatgpt-export")
        self.assertEqual(result["created"], 4)
        self.assertEqual(self.current()["backfill"]["entry_count"], 4)
        before = self.path.read_bytes()
        again = ingest(self.root, [{
            "speaker_role": "user", "text": "donornak: " + sources,
        }], origin="chatgpt-export", dry_run=True)
        self.assertEqual(again["merged"], 4)
        self.assertEqual(self.path.read_bytes(), before)

    def test_stale_external_edit_blocks_intake_until_explicit_repair(self):
        self.add("one")
        state = self.current()
        state["entries"].append({
            "donor_id": "FA3-DONOR-TWO-001",
            "source": {"normalized_key": "github:example/two"},
            "status": "CANDIDATE",
        })
        self.path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "BACKFILL_COUNT_DRIFT_BEFORE_MUTATION"):
            self.add("three")
        before = self.path.read_bytes()
        command = [sys.executable, str(ROOT / "src/fa3_donor_registry.py"),
                   "--root", str(self.root), "--refresh-count"]
        dry = subprocess.run(command + ["--dry-run"], capture_output=True, text=True)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)["entry_count"], 2)
        self.assertEqual(self.path.read_bytes(), before)
        done = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.current()["backfill"]["entry_count"], 2)
        self.add("three")
        self.assertEqual(self.current()["backfill"]["entry_count"], 3)

    def test_duplicate_cannot_be_hidden_by_recount_or_written(self):
        self.add("one")
        previous = self.path.read_bytes()
        bad = self.current()
        bad["entries"].append(dict(bad["entries"][0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID_DONOR_ID"):
            refresh_donor_count(bad)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_INVALID_DONOR_ID"):
            _atomic_write(self.path, bad)
        self.assertEqual(self.path.read_bytes(), previous)

    def test_legacy_empty_registry_bootstraps_count_without_losing_records(self):
        self.path.write_text(json.dumps({
            "id": "FA3-DONOR-REFERENCE-REGISTRY-001", "entries": [],
        }), encoding="utf-8")
        self.add("one")
        result = self.current()
        self.assertEqual(result["backfill"]["entry_count"], 1)
        self.assertEqual(len(result["entries"]), 1)

    def test_historical_nonempty_registry_without_count_bootstraps(self):
        self.add("one")
        old = self.current()
        del old["backfill"]
        self.path.write_text(json.dumps(old), encoding="utf-8")
        self.add("two")
        new = self.current()
        self.assertEqual(new["backfill"]["entry_count"], 2)
        self.assertEqual(len(new["entries"]), 2)

    def test_bad_capability_baseline_cannot_be_recounted(self):
        bad = self.current()
        bad["capability_count"] = 174
        with self.assertRaisesRegex(ValueError, "CAPABILITY_BASELINE_NOT_175"):
            refresh_donor_count(bad)


if __name__ == "__main__":
    unittest.main()
