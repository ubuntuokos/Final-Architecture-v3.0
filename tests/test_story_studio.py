import unittest

from fa3_story_studio import (
    StoryStudioError,
    add_collaboration_comment,
    apply_collaborative_edit,
    build_dubbing_conformance_plan,
    build_presentation_projection,
    create_branch,
    issue_final_release,
    new_reference_project,
    plan_scoped_revision,
    render_note_markdown,
    save_stash_as_note,
    stash_rejected_content,
    validate_codec_registry,
    validate_dubbing_script,
    validate_project,
)


class StoryStudioTests(unittest.TestCase):
    def test_reference_project_validates(self):
        result = validate_project(new_reference_project())
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["collaborators"], 2)

    def test_collaborative_edit_is_attributed_and_revisioned(self):
        p = new_reference_project()
        revision = apply_collaborative_edit(
            p,
            actor_id="writer-b",
            document_id="screenplay-1",
            base_revision=0,
            content="INT. ROOM — DAY",
            change_summary="Open scene",
        )
        self.assertEqual(revision["revision"], 1)
        self.assertEqual(revision["author"], "writer-b")
        self.assertEqual(p["documents"][0]["revision"], 1)

    def test_stale_collaborative_edit_fails_closed(self):
        p = new_reference_project()
        apply_collaborative_edit(
            p,
            actor_id="writer-a",
            document_id="screenplay-1",
            base_revision=0,
            content="Version A",
            change_summary="First edit",
        )
        with self.assertRaises(StoryStudioError):
            apply_collaborative_edit(
                p,
                actor_id="writer-b",
                document_id="screenplay-1",
                base_revision=0,
                content="Stale Version B",
                change_summary="Conflicting edit",
            )

    def test_collaborator_can_comment_without_edit_authority(self):
        p = new_reference_project()
        p["collaboration"]["members"].append(
            {"actor_id": "reviewer", "display_name": "Reviewer", "roles": ["COMMENTER"]}
        )
        comment = add_collaboration_comment(
            p, actor_id="reviewer", document_id="screenplay-1",
            body="Check this dialogue.", anchor="scene-1/dialogue-2",
        )
        self.assertEqual(comment["author"], "reviewer")
        with self.assertRaises(StoryStudioError):
            apply_collaborative_edit(
                p, actor_id="reviewer", document_id="screenplay-1",
                base_revision=0, content="Not allowed", change_summary="Edit",
            )

    def test_scoped_revision_preserves_unrelated_nodes_and_hits_approval_boundary(self):
        p = new_reference_project()
        p["nodes"].append({"node_id": "unrelated-note", "type": "REVIEW_NOTE", "locked": False})
        plan = plan_scoped_revision(p, actor_id="writer-a", changed_node_ids=["scene-1"])
        self.assertEqual(plan["affected_node_ids"], ["delivery-1", "scene-1", "shot-1"])
        self.assertIn("unrelated-note", plan["preserved_node_ids"])
        self.assertTrue(plan["approval_required"])
        self.assertEqual(plan["approval_boundary_node_ids"], ["delivery-1"])
        self.assertFalse(plan["full_project_regeneration_default"])

    def test_nested_branches_supported(self):
        p = new_reference_project()
        create_branch(p, actor_id="writer-b", branch_id="alt-a", label="Alt A", parent_branch_id="main")
        create_branch(p, actor_id="writer-b", branch_id="alt-a-1", label="Alt A1", parent_branch_id="alt-a")
        self.assertEqual(p["branches"][-1]["parent_branch_id"], "alt-a")

    def test_non_publisher_cannot_issue_final(self):
        p = new_reference_project()
        with self.assertRaises(StoryStudioError):
            issue_final_release(p, actor_id="writer-b", revision_digest="1234567890abcdef")

    def test_designated_publisher_can_issue_final(self):
        p = new_reference_project()
        receipt = issue_final_release(p, actor_id="writer-a", revision_digest="1234567890abcdef")
        self.assertTrue(receipt["final"])
        self.assertEqual(receipt["released_by"], "writer-a")

    def test_rejected_content_can_be_saved_as_note(self):
        p = new_reference_project()
        stash_rejected_content(
            p, actor_id="writer-b", stash_id="stash-1", content="Alternative ending.",
            source_document_id="screenplay-1", source_range="scene-42", source_revision="r17",
            reason="Not selected for current branch",
        )
        note = save_stash_as_note(p, actor_id="writer-a", stash_id="stash-1", note_id="note-1", title="Discarded endings")
        rendered = render_note_markdown(note)
        self.assertIn("Alternative ending.", rendered)
        self.assertTrue(note["standalone_export_allowed"])

    def test_one_way_codec_fails_closed(self):
        with self.assertRaises(StoryStudioError):
            validate_codec_registry([
                {"media_type": "application/x-test", "import": True, "export": False, "roundtrip_test_required": True}
            ])


    def test_story_to_presentation_projection_is_non_authoritative(self):
        p = new_reference_project()
        plan = build_presentation_projection(
            p,
            actor_id="writer-a",
            presentation_type="PITCH_DECK",
            selected_node_ids=["story-1", "scene-1"],
            title="Project pitch",
        )
        self.assertEqual(plan["document_capability"], "CAP-018")
        self.assertEqual(plan["optional_generation_provider"], "FA3-PROVIDER-PRESENTON-001")
        self.assertFalse(plan["provider_authority"])
        self.assertFalse(plan["silent_story_mutation"])

    def test_dubbing_script_requires_video_timing_and_as_recorded_audio_binding(self):
        doc = {
            "schema": "fa3.dubbing-script.v1",
            "document_id": "dub-hu-1",
            "document_type": "DUBBING_ADAPTATION_SCRIPT",
            "target_language": "hu-HU",
            "source_video_digest": "a" * 64,
            "source_revision": "picture-lock-r7",
            "events": [{
                "cue_id": "C001",
                "source_event_ref": "DL-001",
                "source_character": "CHARACTER A",
                "in_timecode_ms": 1000,
                "out_timecode_ms": 2500,
                "source_text": "Where are you going?",
                "target_text": "Hová mész?",
                "adapted_text": "Hová mész?",
                "lip_sync_note": "close-up",
            }],
        }
        result = validate_dubbing_script(doc)
        self.assertEqual(result["voice_authority"], "FA3-VOICE-001")
        self.assertEqual(result["caption_timing_profile"], "FA3-CAPTION-SUBTITLE-001")

        final_doc = dict(doc)
        final_doc["document_type"] = "AS_RECORDED_DUBBING_SCRIPT"
        final_doc["events"] = [dict(doc["events"][0], as_recorded_text="Hová mész?")]
        with self.assertRaises(StoryStudioError):
            validate_dubbing_script(final_doc)
        final_doc["final_audio_digest"] = "b" * 64
        self.assertEqual(validate_dubbing_script(final_doc)["result"], "PASS")

    def test_dubbing_conformance_does_not_silently_rewrite_adaptation(self):
        doc = {
            "schema": "fa3.dubbing-script.v1",
            "document_id": "dub-hu-1",
            "document_type": "DUBBING_ADAPTATION_SCRIPT",
            "target_language": "hu-HU",
            "source_video_digest": "c" * 64,
            "source_revision": "dl-r1",
            "events": [{
                "cue_id": "C001",
                "source_event_ref": "DL-001",
                "source_character": "CHARACTER A",
                "in_timecode_ms": 1000,
                "out_timecode_ms": 2100,
                "source_text": "Stop!",
                "target_text": "Állj!",
            }],
        }
        plan = build_dubbing_conformance_plan(
            doc, new_source_revision="dl-r2", changed_source_event_refs=["DL-001"]
        )
        self.assertEqual(plan["affected_cue_ids"], ["C001"])
        self.assertEqual(plan["stage_1"], "ALIGN_AND_RETIME")
        self.assertFalse(plan["silent_target_text_rewrite"])
        self.assertTrue(plan["human_review_required"])


if __name__ == "__main__":
    unittest.main()
