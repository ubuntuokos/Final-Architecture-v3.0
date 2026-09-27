import unittest

from fa3_story_studio import (
    StoryStudioError,
    add_collaboration_comment,
    apply_collaborative_edit,
    create_branch,
    issue_final_release,
    new_reference_project,
    render_note_markdown,
    save_stash_as_note,
    stash_rejected_content,
    validate_codec_registry,
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


if __name__ == "__main__":
    unittest.main()
