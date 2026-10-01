from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_computer_interaction_runtime import (
    ComputerInteractionDenied,
    MutationLedger,
    TELEMETRY_DEFAULT,
    attach_execution_parameters,
    bind_selected_action,
    build_action_space,
    execute_interaction,
    make_trajectory_event,
    normalize_observation,
    revalidate,
    verify_outcome,
)


def observation(*, revision: int = 1, capture_id: str = "cap-1", occluded: bool = False):
    return {
        "session_id": "session-1",
        "observation_id": "obs-1",
        "revision": revision,
        "application_id": "org.example.Editor",
        "window_id": "window-7",
        "window_fingerprint": "sha256:window-a",
        "capture_id": capture_id,
        "trust_class": "TRUSTED_SYSTEM",
        "targets": [
            {
                "target_id": "name",
                "role": "textbox",
                "label": "Name",
                "value": "",
                "visible": True,
                "enabled": True,
                "occluded": False,
                "visual_region": False,
                "supported_actions": ["TYPE_TEXT"],
            },
            {
                "target_id": "save",
                "role": "button",
                "label": "Save",
                "visible": True,
                "enabled": True,
                "occluded": occluded,
                "visual_region": True,
                "supported_actions": ["CLICK"],
            },
        ],
        "provenance": {"source": "test-fixture"},
    }


class ComputerInteractionRuntimeTests(unittest.TestCase):
    def test_desktop_content_is_always_untrusted(self):
        self.assertEqual(
            "UNTRUSTED_DESKTOP_CONTENT",
            normalize_observation(observation())["trust_class"],
        )

    def test_action_space_is_bounded_to_observed_targets(self):
        space = build_action_space(observation())
        ids = {row["action_id"] for row in space["candidates"]}
        self.assertIn("TYPE_TEXT:name", ids)
        self.assertIn("CLICK:save", ids)
        self.assertNotIn("CLICK:name", ids)
        self.assertEqual("DENY", space["candidate_set_expansion"])
        self.assertEqual("DENY_BY_DEFAULT", space["raw_coordinate_only_action"])

    def test_candidate_escape_is_denied(self):
        space = build_action_space(observation())
        with self.assertRaises(ComputerInteractionDenied) as caught:
            bind_selected_action(space, "999")
        self.assertEqual("COMPUTER-CANDIDATE-ESCAPE", caught.exception.code)

    def test_stale_revision_is_denied(self):
        space = build_action_space(observation())
        row = next(x for x in space["candidates"] if x["action_id"] == "CLICK:save")
        binding = bind_selected_action(space, row["id"])
        with self.assertRaises(ComputerInteractionDenied) as caught:
            revalidate(binding, observation(revision=2))
        self.assertEqual("STALE_OBSERVATION", caught.exception.code)

    def test_stale_capture_is_denied(self):
        space = build_action_space(observation())
        row = next(x for x in space["candidates"] if x["action_id"] == "CLICK:save")
        binding = bind_selected_action(space, row["id"])
        with self.assertRaises(ComputerInteractionDenied) as caught:
            revalidate(binding, observation(capture_id="cap-2"))
        self.assertEqual("STALE_OBSERVATION", caught.exception.code)

    def test_occluded_click_is_denied(self):
        space = build_action_space(observation())
        row = next(x for x in space["candidates"] if x["action_id"] == "CLICK:save")
        binding = bind_selected_action(space, row["id"])
        with self.assertRaises(ComputerInteractionDenied) as caught:
            revalidate(binding, observation(occluded=True))
        self.assertEqual("TARGET_OCCLUDED", caught.exception.code)

    def test_mutation_requires_authorization(self):
        current = observation()
        space = build_action_space(current)
        row = next(x for x in space["candidates"] if x["action_id"] == "CLICK:save")
        binding = bind_selected_action(space, row["id"])
        with self.assertRaises(ComputerInteractionDenied) as caught:
            execute_interaction(binding, current, lambda c, o, p: {"ok": True})
        self.assertEqual("AUTHORIZATION_REQUIRED", caught.exception.code)

    def test_blind_mutation_retry_is_denied(self):
        current = observation()
        space = build_action_space(current)
        row = next(x for x in space["candidates"] if x["action_id"] == "CLICK:save")
        binding = bind_selected_action(space, row["id"])
        ledger = MutationLedger()
        executor = lambda c, o, p: {"accepted": True}
        receipt = execute_interaction(
            binding, current, executor, authorization_ref="approval:1", ledger=ledger
        )
        self.assertEqual("EXECUTED", receipt["status"])
        self.assertTrue(receipt["reobserve_required"])
        self.assertFalse(receipt["verified_success"])
        with self.assertRaises(ComputerInteractionDenied) as caught:
            execute_interaction(
                binding, current, executor, authorization_ref="approval:1", ledger=ledger
            )
        self.assertEqual("BLIND_MUTATION_RETRY_DENIED", caught.exception.code)

    def test_reobserve_and_abstain_are_not_success(self):
        current = observation()
        space = build_action_space(current)
        for action_id, expected in (("REOBSERVE", "REOBSERVE_REQUIRED"), ("ABSTAIN", "ABSTAINED")):
            row = next(x for x in space["candidates"] if x["action_id"] == action_id)
            receipt = execute_interaction(
                bind_selected_action(space, row["id"]),
                current,
                lambda c, o, p: {"unexpected": True},
            )
            self.assertEqual(expected, receipt["status"])
            self.assertFalse(receipt["verified_success"])

    def test_execution_parameters_are_bounded(self):
        space = build_action_space(observation())
        row = next(x for x in space["candidates"] if x["action_id"] == "TYPE_TEXT:name")
        binding = bind_selected_action(space, row["id"])
        attached = attach_execution_parameters(binding, {"text": "Alice"})
        self.assertEqual("Alice", attached["execution_parameters"]["text"])
        with self.assertRaises(ComputerInteractionDenied):
            attach_execution_parameters(binding, {"text": "x", "script": "rm -rf /"})

    def test_independent_verification(self):
        post = observation()
        post["targets"][0]["value"] = "Alice"
        result = verify_outcome(
            [{"type": "target_value_equals", "target_id": "name", "value": "Alice"}],
            post,
        )
        self.assertEqual("VERIFIED_SUCCESS", result["result"])

    def test_trajectory_is_metadata_minimal(self):
        current = observation()
        space = build_action_space(current)
        row = next(x for x in space["candidates"] if x["action_id"] == "TYPE_TEXT:name")
        binding = attach_execution_parameters(bind_selected_action(space, row["id"]), {"text": "secret text"})
        receipt = execute_interaction(
            binding,
            current,
            lambda c, o, p: {"raw": "provider result", "typed": p["text"]},
            authorization_ref="approval:2",
        )
        event = make_trajectory_event(binding, receipt)
        serialized = str(event)
        self.assertNotIn("secret text", serialized)
        self.assertNotIn("provider result", serialized)
        self.assertNotIn("window title", serialized.lower())
        self.assertEqual("METADATA_MINIMAL", event["privacy_profile"])

    def test_telemetry_is_default_off_and_cpu_only_path_works(self):
        old = {k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK")}
        try:
            for key in old:
                os.environ[key] = ""
            self.assertEqual("DISABLED", TELEMETRY_DEFAULT)
            self.assertTrue(build_action_space(observation())["candidates"])
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
