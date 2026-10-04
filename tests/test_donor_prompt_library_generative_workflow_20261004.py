"""FIFO-waiting prompt-library / prompt-template / generative-workflow donor intake."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
DELTA = ROOT / "canonical/deltas/FA3-DONOR-PROMPT-LIBRARY-GENERATIVE-WORKFLOW-2026-10-04.json"

SUBMITTED_URLS = [
    "https://github.com/topics/prompts",
    "https://github.com/topics/prompt-library?l=shell&o=desc&s=stars",
    "https://github.com/topics/prompt-library?l=css&o=desc&s=stars",
    "https://github.com/topics/prompts",
    "https://github.com/JuliusBrussee/the-prompt-library",
    "https://github.com/hubertusgbecker/prompt-library",
    "https://github.com/aakashg/pm-prompt-library",
    "https://github.com/aakashg/pm-prompt-library",
    "https://github.com/topics/prompts-template",
    "https://github.com/hubertusgbecker/prompt-library",
    "https://github.com/topics/ai-prompts?o=desc&s=stars",
    "https://github.com/jamez-bondos/awesome-gpt4o-images",
    "https://github.com/jamez-bondos",
    "https://github.com/carson-katri/dream-textures",
    "https://github.com/lllyasviel",
    "https://github.com/Comfy-Org",
    "https://github.com/Sygil-Dev",
    "https://github.com/carson-katri/dream-textures",
    "https://github.com/topics/prompt-library?l=jupyter+notebook&o=asc&s=updated",
    "https://github.com/topics/prompt-templates",
    "https://github.com/topics/prompt?l=html",
    "https://github.com/topics/system-prompts",
    "https://github.com/topics/chatgpt-prompts"
]

LOCAL_IDS = {
    "FA3-DONOR-GITHUB-TOPIC-PROMPTS-001",
    "FA3-DONOR-GITHUB-TOPIC-PROMPT-LIBRARY-001",
    "FA3-DONOR-JULIUSBRUSSEE-THE-PROMPT-LIBRARY-001",
    "FA3-DONOR-HUBERTUSGBECKER-PROMPT-LIBRARY-001",
    "FA3-DONOR-AAKASHG-PM-PROMPT-LIBRARY-001",
    "FA3-DONOR-GITHUB-TOPIC-PROMPTS-TEMPLATE-001",
    "FA3-DONOR-GITHUB-TOPIC-AI-PROMPTS-001",
    "FA3-DONOR-JAMEZ-BONDOS-AWESOME-GPT4O-IMAGES-001",
    "FA3-DONOR-JAMEZ-BONDOS-PROFILE-001",
    "FA3-DONOR-CARSON-KATRI-DREAM-TEXTURES-001",
    "FA3-DONOR-LLLYASVIEL-PROFILE-001",
    "FA3-DONOR-SYGIL-DEV-ORG-001",
    "FA3-DONOR-GITHUB-TOPIC-PROMPT-TEMPLATES-001",
    "FA3-DONOR-GITHUB-TOPIC-PROMPT-001",
    "FA3-DONOR-GITHUB-TOPIC-SYSTEM-PROMPTS-001",
    "FA3-DONOR-GITHUB-TOPIC-CHATGPT-PROMPTS-001",
}

class WaitingPromptDonorIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.delta = json.loads(DELTA.read_text(encoding="utf-8"))

    def test_waiting_delta_is_bound_to_exact_parent(self):
        d = self.delta
        self.assertEqual(d["schema"], "fa3.donor-intake-delta.v1")
        self.assertEqual(d["parent_main"], "9b328ff1582ba92d67562b10336b1ccaf8a8da84")
        self.assertEqual(d["parent_registry_blob_sha"], "1362d75186c6da74e5cf947fdf0b8867d462636a")
        self.assertEqual(d["parent_entry_count"], 1427)
        self.assertFalse(d["canonical_registry_materialized"])
        self.assertTrue(d["waiting_queue_only"])

    def test_submission_counts_and_exact_duplicates(self):
        d = self.delta
        self.assertEqual(d["submitted_url_count"], 23)
        self.assertEqual(d["submitted_urls"], SUBMITTED_URLS)
        self.assertEqual(d["duplicate_submission_count"], 4)
        self.assertEqual(d["unique_submitted_url_count"], 19)
        self.assertEqual(d["matched_existing_count"], 1)
        self.assertEqual(d["published_registry_reuse_count"], 1)
        self.assertEqual(d["mutation_submitted_url_count"], 18)
        self.assertEqual(d["canonical_alias_collapse_count"], 2)
        self.assertEqual(d["unique_source_count"], 16)
        self.assertEqual(d["new_source_count"], 16)
        self.assertEqual(d["proposed_entry_count"], 1443)

    def test_prompt_library_filtered_views_share_one_identity(self):
        rows = [row for row in self.delta["sources"] if "/topics/prompt-library" in row[0]]
        self.assertEqual(len(rows), 3)
        self.assertEqual({row[1] for row in rows}, {"FA3-DONOR-GITHUB-TOPIC-PROMPT-LIBRARY-001"})

    def test_comfy_org_reuses_published_identity(self):
        reuse = self.delta["published_registry_reuse"]
        self.assertEqual(len(reuse), 1)
        self.assertEqual(reuse[0]["submitted_url"], "https://github.com/Comfy-Org")
        self.assertEqual(reuse[0]["donor_id"], "FA3-DONOR-COMFY-ORG-001")
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertIn("FA3-DONOR-COMFY-ORG-001", current_ids)

    def test_waiting_records_are_not_prematurely_canonical(self):
        current_ids = {e["donor_id"] for e in self.registry["entries"]}
        self.assertTrue(LOCAL_IDS.isdisjoint(current_ids))
        self.assertEqual(self.registry["backfill"]["entry_count"], len(self.registry["entries"]))
        self.assertEqual(len(self.registry["entries"]), 1427)
        self.assertEqual(self.registry["capability_count"], 175)
        self.assertFalse(self.delta["boundaries"]["canonical_planning_visibility"])

    def test_no_runtime_content_or_authority_admission(self):
        b = self.delta["boundaries"]
        for key in (
            "automatic_fetch", "automatic_install", "automatic_activation",
            "automatic_code_import", "automatic_content_import",
            "automatic_dependency", "automatic_provider_admission",
            "automatic_model_selection", "child_repository_auto_registration",
            "usage_edge_created", "capability_count_change", "authority_change",
            "runtime_change", "current_host_pass_claimed",
        ):
            self.assertFalse(b[key])
        self.assertEqual(self.delta["capability_baseline"], 175)
        self.assertEqual(self.delta["capability_delta"], 0)
        self.assertEqual(self.delta["authority_delta"], 0)
        self.assertEqual(self.delta["usage_edges_created"], 0)

if __name__ == "__main__":
    unittest.main()
