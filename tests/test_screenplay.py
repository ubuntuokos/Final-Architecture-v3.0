"""Deterministic non-current-host reference tests; no external donor code."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_screenplay import (ScreenplayError, derive_breakdown, digest, edit_scene, export_screenplay,
                            fork_branch, import_screenplay, project_handoff, review_candidate, validate_document)

FOUNTAIN = """Title: Árvizek
Author: Egy Szerző

INT. KONYHA - DAY #12A#

PROP: kék bögre; WARDROBE: szürke kabát; CLOSE ON the coffee.

@ANNA
(halkan)
Szép idő van!

EXT. KERT - NIGHT #12B#

@BÉLA
Elment a vihar.
"""

FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="1" Template="No"><TitlePage><Content>
<Paragraph><Text>Title: Árvizek</Text></Paragraph><Paragraph><Text>Author: Egy Szerző</Text></Paragraph>
</Content></TitlePage><Content>
<Paragraph Type="Scene Heading" Number="12A"><Text>INT. KONYHA - DAY</Text></Paragraph>
<Paragraph Type="Action"><Text Style="Bold">PROP: kék bögre;</Text><Text> CLOSE ON.</Text></Paragraph>
<Paragraph Type="Character"><Text>ANNA</Text></Paragraph>
<Paragraph Type="Parenthetical"><Text>halkan</Text></Paragraph>
<Paragraph Type="Dialogue"><Text>Szép idő van!</Text></Paragraph>
</Content></FinalDraft>"""


def _fountain():
    return import_screenplay(FOUNTAIN, "fountain", profile="EPISODIC")[0]


class CanonicalScreenplayTests(unittest.TestCase):
    def test_fountain_import_unicode_and_scene_numbers(self):
        doc, receipt = import_screenplay(FOUNTAIN, "fountain", profile="EPISODIC")
        self.assertEqual("SUBSET_SEMANTIC", receipt["fidelity"])
        self.assertEqual(2, len(doc["scenes"]))
        self.assertEqual("12A", doc["scenes"][0]["number"])
        self.assertEqual("Árvizek", doc["title_lines"][0].split(": ")[1])
        self.assertEqual("PARENTHETICAL", doc["scenes"][0]["elements"][2]["type"])

    def test_fountain_bidirectional_roundtrip_semantics(self):
        original = _fountain()
        out, receipt = export_screenplay(original, "fountain")
        reread, other = import_screenplay(out, "fountain", profile="EPISODIC")
        self.assertEqual(original["scenes"], reread["scenes"])
        self.assertEqual(original["title_lines"], reread["title_lines"])
        self.assertTrue(receipt["canonical_sidecar_required"])

    def test_fdx_bidirectional_with_style_and_metadata(self):
        original, receipt = import_screenplay(FDX, "fdx", profile="TV_MOVIE")
        self.assertEqual("SUBSET_SEMANTIC", receipt["fidelity"])
        self.assertEqual("Bold", original["scenes"][0]["elements"][0]["spans"][0]["styles"][0])
        output, _ = export_screenplay(original, "fdx")
        reread, _ = import_screenplay(output, "fdx", profile="TV_MOVIE")
        self.assertEqual(original["scenes"], reread["scenes"])
        self.assertEqual(original["title_lines"], reread["title_lines"])

    def test_cross_format_simple_script(self):
        doc, _ = import_screenplay(FDX, "fdx")
        with self.assertRaises(ScreenplayError):
            export_screenplay(doc, "fountain")  # mixed styling with multiple spans
        text, receipt = export_screenplay(doc, "fountain", allow_loss=True)
        self.assertEqual("LOSSY_OPT_IN", receipt["fidelity"])
        self.assertIn("@ANNA", text)
        reimported, _ = import_screenplay(text, "fountain")
        self.assertEqual("INT. KONYHA - DAY", reimported["scenes"][0]["heading"])

    def test_fdx_unknown_metadata_is_explicitly_blocked(self):
        bad = FDX.replace("<Content>\n<Paragraph Type=\"Scene Heading\"", "<Revisions/><Content>\n<Paragraph Type=\"Scene Heading\"")
        with self.assertRaisesRegex(ScreenplayError, "fidelity blocked"):
            import_screenplay(bad, "fdx")
        doc, receipt = import_screenplay(bad, "fdx", allow_loss=True)
        self.assertEqual("LOSSY_OPT_IN", receipt["fidelity"])
        self.assertTrue(receipt["losses"])
        self.assertTrue(doc["scenes"])

    def test_fdx_dtd_and_entity_prohibited(self):
        with self.assertRaisesRegex(ScreenplayError, "DTD/entity"):
            import_screenplay('<!DOCTYPE x [<!ENTITY leak SYSTEM "file:///etc/passwd">]>' + FDX, "fdx")

    def test_fdx_malformed_and_wrong_root_explicit(self):
        with self.assertRaisesRegex(ScreenplayError, "invalid FDX"):
            import_screenplay("<FinalDraft>", "fdx")
        with self.assertRaisesRegex(ScreenplayError, "FinalDraft/Content"):
            import_screenplay("<script><Content/></script>", "fdx")

    def test_unsupported_fountain_features_require_opt_in(self):
        bad = FOUNTAIN.replace("EXT. KERT", "[[private note]]\n\nEXT. KERT")
        with self.assertRaisesRegex(ScreenplayError, "fidelity blocked"):
            import_screenplay(bad, "fountain")
        doc, receipt = import_screenplay(bad, "fountain", allow_loss=True)
        self.assertTrue(receipt["losses"])
        self.assertEqual(2, len(doc["scenes"]))

    def test_no_unsupported_office_pdf_one_way_codec_admission(self):
        doc = _fountain()
        for fmt in ("docx", "odt", "pdf", "txt", "osf"):
            with self.assertRaisesRegex(ScreenplayError, "no admitted bidirectional codec"):
                import_screenplay(FOUNTAIN, fmt)
            with self.assertRaisesRegex(ScreenplayError, "no admitted bidirectional codec"):
                export_screenplay(doc, fmt)

    def test_large_input_and_nul_fail_closed(self):
        with self.assertRaisesRegex(ScreenplayError, "5 MiB"):
            import_screenplay("x" * (5 * 1024 * 1024 + 1), "fountain")
        with self.assertRaisesRegex(ScreenplayError, "NUL"):
            import_screenplay(FOUNTAIN + "\x00", "fountain")

    def test_all_production_profiles_supported(self):
        for p in ("FEATURE", "TV_MOVIE", "EPISODIC", "COMMERCIAL", "LIVE_BROADCAST", "OTHER"):
            doc, _ = import_screenplay(FOUNTAIN, "fountain", profile=p)
            self.assertEqual(p, doc["profile"])
        with self.assertRaisesRegex(ScreenplayError, "profile"):
            import_screenplay(FOUNTAIN, "fountain", profile="VIDEO_GAME")

    def test_duplicate_scene_ids_rejected(self):
        doc = _fountain()
        doc["scenes"][1]["scene_id"] = doc["scenes"][0]["scene_id"]
        with self.assertRaisesRegex(ScreenplayError, "unique"):
            validate_document(doc)

    def test_tampered_spans_rejected(self):
        doc, _ = import_screenplay(FDX, "fdx")
        doc["scenes"][0]["elements"][0]["spans"][0]["text"] = "tampered"
        with self.assertRaisesRegex(ScreenplayError, "mismatch"):
            validate_document(doc)

    def test_branch_independence_and_parent_hash(self):
        doc = _fountain()
        branch = fork_branch(doc, "alternate-ending")
        self.assertEqual(doc["scenes"], branch["scenes"])
        self.assertEqual(digest(doc), branch["provenance"]["parent_sha256"])
        edited = edit_scene(branch, "scene-000002", heading="EXT. VÁROS - NIGHT")
        self.assertEqual(doc["scenes"][1]["heading"], branch["scenes"][1]["heading"])
        self.assertNotEqual(doc["scenes"][1]["heading"], edited["scenes"][1]["heading"])
        self.assertEqual("scene-000002", edited["scenes"][1]["scene_id"])
        self.assertEqual(2, edited["revision"])

    def test_invalid_branch_and_scene_edit_fail_closed(self):
        doc = _fountain()
        for branch in ("../escape", "main", "bad name"):
            with self.assertRaises(ScreenplayError):
                fork_branch(doc, branch)
        with self.assertRaisesRegex(ScreenplayError, "unknown scene"):
            edit_scene(doc, "scene-404", heading="EXT. A")

    def test_derived_proposals_are_source_linked_pending(self):
        doc = _fountain()
        bd = derive_breakdown(doc)
        scene = bd["scenes"][0]
        self.assertEqual("KONYHA", scene["location"])
        self.assertIn("ANNA", scene["speaking_cast"])
        self.assertFalse(scene["silent_and_background_cast_verified"])
        self.assertTrue(all(p["approval"] == "PENDING" for p in scene["proposals"]))
        self.assertEqual({"PROP", "WARDROBE", "SHOT_CUE"}, set(p["kind"] for p in scene["proposals"]))
        self.assertEqual("EXPLICIT_SOURCE_MARKER", scene["proposals"][0]["confidence"])

    def test_no_invention_in_unmarked_action(self):
        doc = _fountain()
        doc["scenes"][1]["elements"].append({"type": "ACTION", "text": "The car drives past a tree."})
        scene = derive_breakdown(doc)["scenes"][1]
        self.assertEqual([], scene["proposals"])
        self.assertEqual([], [x for x in scene["speaking_cast"] if x != "BÉLA"])

    def test_local_review_and_stale_candidate_forbidden(self):
        doc = _fountain()
        bd = derive_breakdown(doc)
        cid = bd["scenes"][0]["proposals"][0]["id"]
        reviewed = review_candidate(bd, cid, "APPROVED", "Local Alice")
        self.assertEqual("APPROVED", reviewed["scenes"][0]["proposals"][0]["approval"])
        self.assertEqual("LOCAL_UNVERIFIED_REVIEW", reviewed["review_log"][0]["assurance"])
        self.assertEqual("PENDING", bd["scenes"][0]["proposals"][0]["approval"])
        changed = edit_scene(doc, "scene-000001", heading="INT. MÁS KONYHA - DAY")
        stale = derive_breakdown(changed, reviewed)
        self.assertEqual("STALE", stale["scenes"][0]["status"])
        with self.assertRaisesRegex(ScreenplayError, "stale"):
            review_candidate(stale, cid, "APPROVED", "Alice")

    def test_unchanged_scenes_keep_reviews_on_targeted_refresh(self):
        doc = _fountain()
        prior = derive_breakdown(doc)
        cid = prior["scenes"][0]["proposals"][0]["id"]
        prior = review_candidate(prior, cid, "APPROVED", "Editor")
        changed = edit_scene(doc, "scene-000002", heading="EXT. UDVAR - NIGHT")
        updated = derive_breakdown(changed, prior, refresh_affected=True)
        self.assertEqual(prior["scenes"][0], updated["scenes"][0])
        self.assertNotEqual(prior["scenes"][1]["heading"], updated["scenes"][1]["heading"])
        self.assertEqual("APPROVED", updated["scenes"][0]["proposals"][0]["approval"])

    def test_changed_scene_requires_explicit_refresh(self):
        doc = _fountain()
        old = derive_breakdown(doc)
        edited = edit_scene(doc, "scene-000001", heading="INT. KONYHA - NIGHT")
        stale = derive_breakdown(edited, old)
        self.assertEqual("STALE", stale["scenes"][0]["status"])
        self.assertEqual("BLOCKED", project_handoff(edited, stale)["status"])
        regenerated = derive_breakdown(edited, stale, refresh_affected=True)
        self.assertNotEqual("STALE", regenerated["scenes"][0]["status"])
        self.assertTrue(all(p["approval"] == "PENDING" for p in regenerated["scenes"][0]["proposals"]))

    def test_handoff_fails_closed_before_review(self):
        doc = _fountain()
        bd = derive_breakdown(doc)
        out = project_handoff(doc, bd)
        self.assertEqual("BLOCKED", out["status"])
        self.assertTrue(out["blockers"])
        self.assertFalse(out["schedule_authority"])
        self.assertFalse(out["publish_authority"])
        self.assertTrue(out["film_planning_scene_rows"][0]["silent_and_background_cast_unknown"])

    def test_handoff_approved_only_and_no_auto_editor_project(self):
        doc = _fountain()
        bd = derive_breakdown(doc)
        candidates = bd["scenes"][0]["proposals"]
        for i, p in enumerate(candidates):
            bd = review_candidate(bd, p["id"], "APPROVED" if i == 0 else "REJECTED", "Editor")
        handoff = project_handoff(doc, bd)
        self.assertEqual("LOCAL_REVIEW_ONLY", handoff["status"])
        self.assertEqual(1, len(handoff["film_planning_scene_rows"][0]["approved_tags"]))
        self.assertFalse(handoff["editorial_projection"]["editable_project_generated"])
        self.assertEqual(0, handoff["model_invocations"])

    def test_foreign_branch_handoff_prohibited(self):
        doc = _fountain()
        bd = derive_breakdown(doc)
        alt = fork_branch(doc, "alt")
        with self.assertRaisesRegex(ScreenplayError, "foreign"):
            project_handoff(alt, bd)

    def test_read_only_local_cli_flow(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        exe = [sys.executable, str(ROOT / "src" / "fa3_screenplay_cli.py")]
        with tempfile.TemporaryDirectory() as work:
            path = Path(work)
            (path / "script.fountain").write_text(FOUNTAIN, encoding="utf-8")
            imp = subprocess.run(exe + ["import", "--input", str(path / "script.fountain"),
                                         "--format", "fountain", "--profile", "COMMERCIAL",
                                         "--output", str(path / "doc.json")], env=env, capture_output=True, text=True)
            self.assertEqual(0, imp.returncode, imp.stderr)
            self.assertTrue((path / "doc.json").exists())
            repeat = subprocess.run(exe + ["import", "--input", str(path / "script.fountain"),
                                            "--format", "fountain", "--output", str(path / "doc.json")],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(2, repeat.returncode)
            bd = subprocess.run(exe + ["breakdown", "--input", str(path / "doc.json"),
                                        "--output", str(path / "breakdown.json")], env=env, capture_output=True, text=True)
            self.assertEqual(0, bd.returncode, bd.stderr)
            blocked = subprocess.run(exe + ["handoff", "--input", str(path / "doc.json"),
                                             "--breakdown", str(path / "breakdown.json"),
                                             "--output", str(path / "handoff.json")], env=env, capture_output=True, text=True)
            self.assertEqual(3, blocked.returncode, blocked.stderr)
            self.assertEqual("BLOCKED", json.loads((path / "handoff.json").read_text())["status"])
            ff = subprocess.run(exe + ["export", "--input", str(path / "doc.json"),
                                        "--format", "fdx", "--output", str(path / "export.fdx")],
                                env=env, capture_output=True, text=True)
            self.assertEqual(0, ff.returncode, ff.stderr)
            self.assertIn("FinalDraft", (path / "export.fdx").read_text())


if __name__ == "__main__":
    unittest.main()

class RuntimeWrapperTests(unittest.TestCase):
    def test_offline_venv_cli_launch_and_no_network_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, FA3_SCREENPLAY_VENV=str(Path(temp) / "venv"))
            proc = subprocess.run([str(ROOT / "bin" / "fa3-screenplay"), "formats"],
                                  env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertTrue((Path(temp) / "venv" / "bin" / "python").is_file())
            desc = json.loads(proc.stdout)
            self.assertEqual("NOT_ADMITTED", desc["office_codecs"])
            self.assertEqual("NOT_RUN", desc["current_host_evidence"])
