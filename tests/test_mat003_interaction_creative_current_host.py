import copy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.fa3_mat003_interaction_creative_current_host import (
    CAPABILITIES,
    browser_target_allowed,
    cap013_authority_scope,
    cap013_computer_use_desktop_admission,
    computer_use_intent_allowed,
    exact_rollback,
    skill_package_allowed,
    validate_animation_spec,
    validate_film_plan,
)


class Mat003InteractionCreativeCurrentHostTests(unittest.TestCase):
    def test_batch_identity(self):
        self.assertEqual(
            CAPABILITIES,
            ("CAP-011", "CAP-012", "CAP-013", "CAP-014", "CAP-015"),
        )

    def test_skill_package_is_inert_and_gateway_routed(self):
        good = {
            "name": "skill",
            "version": "1.0.0",
            "trigger": "test",
            "entrypoint_path": "SKILL.md",
            "content_sha256": "a" * 64,
            "executable_directives": [],
            "tool_intents_route": "CENTRAL_MCP_GATEWAY",
        }
        self.assertTrue(skill_package_allowed(good))
        self.assertFalse(skill_package_allowed({**good, "entrypoint_path": "../SKILL.md"}))
        self.assertFalse(skill_package_allowed({**good, "executable_directives": ["bash"]}))
        self.assertFalse(skill_package_allowed({**good, "tool_intents_route": "DIRECT_PROVIDER"}))

    def test_browser_target_policy(self):
        self.assertTrue(browser_target_allowed("http://127.0.0.1:8123/test"))
        self.assertTrue(browser_target_allowed("http://localhost:8123/test"))
        self.assertFalse(browser_target_allowed("file:///etc/passwd"))
        self.assertFalse(browser_target_allowed("javascript:alert(1)"))
        self.assertFalse(browser_target_allowed("https://user:pass@example.com/"))
        self.assertFalse(browser_target_allowed("https://example.com/"))
        self.assertTrue(browser_target_allowed("https://example.com/", approved_external=True))

    def test_computer_use_intent_denies_privilege_shell_and_private_api(self):
        good = {
            "execution_scope": "CURRENT_USER_SESSION",
            "broker": "XDG_PORTAL_OR_APPROVED_ADAPTER",
            "privileged": False,
            "private_kde_api": False,
            "free_form_shell": False,
            "argv": ["xdg-open", "https://example.invalid/"],
        }
        self.assertTrue(computer_use_intent_allowed(good))
        self.assertFalse(computer_use_intent_allowed({**good, "argv": ["sudo", "id"]}))
        self.assertFalse(computer_use_intent_allowed({**good, "free_form_shell": True}))
        self.assertFalse(computer_use_intent_allowed({**good, "private_kde_api": True}))
        self.assertFalse(computer_use_intent_allowed({**good, "broker": "DIRECT_KWIN"}))

    def test_cap013_uses_canonical_current_user_session_discovery(self):
        text = (ROOT / "src/fa3_mat003_interaction_creative_current_host.py").read_text(encoding="utf-8")
        self.assertIn("discover_current_user_session_environment", text)
        self.assertIn('"session_discovery": session_context["evidence"]', text)
        self.assertNotIn("def _systemd_user_environment", text)

    def test_cap013_authority_scope_keeps_secrets_under_cap003(self):
        scope = cap013_authority_scope(ROOT)
        self.assertEqual(scope["cap013_subject"], "KDE/Wayland Computer Use")
        self.assertNotIn("AUTH-SECRETS", scope["cap013_authority_owners"])
        self.assertEqual(scope["secrets_authority_owner"], "CAP-003")
        self.assertFalse(scope["secret_backend_required_for_cap013"])
        self.assertTrue(scope["desktop_projection_source_present"])

    def test_cap013_scoped_admission_allows_only_secret_backend_full_gate_failure(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "KDE_PLASMA"},
            "session": {"type": "wayland"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "PASS",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
                "xdg_desktop_portal": "PASS",
            },
        }
        session_evidence = {
            "active_local_graphical_session_proven": True,
            "wayland_socket_proven": True,
            "kde_bus_identity_proven": True,
            "portal_bus_identity_proven": True,
        }
        scoped = cap013_computer_use_desktop_admission(report, session_evidence)
        self.assertEqual(scoped["result"], "PASS")
        self.assertEqual(scoped["full_desktop_admission_result"], "FAIL")
        self.assertEqual(scoped["full_desktop_required_failures"], ["secret_backend"])
        self.assertEqual(scoped["secret_backend_status"], "FAIL")
        self.assertFalse(scoped["secret_backend_used_for_cap013_admission"])

    def test_cap013_scoped_admission_still_fails_on_computer_use_prerequisite(self):
        report = {
            "result": "FAIL",
            "desktop": {"desktop": "KDE_PLASMA"},
            "session": {"type": "wayland"},
            "capabilities": {
                "linux_host": "PASS",
                "xdg_runtime": "PASS",
                "dbus_session": "FAIL",
                "uri_open": "PASS",
                "secret_backend": "FAIL",
                "local_gui_session": "PASS",
                "xdg_desktop_portal": "PASS",
            },
        }
        session_evidence = {
            "active_local_graphical_session_proven": True,
            "wayland_socket_proven": True,
            "kde_bus_identity_proven": True,
            "portal_bus_identity_proven": True,
        }
        scoped = cap013_computer_use_desktop_admission(report, session_evidence)
        self.assertEqual(scoped["result"], "FAIL")
        self.assertIn("dbus_session", scoped["failed_checks"])
        self.assertIn("full_desktop_failure:dbus_session", scoped["failed_checks"])

    def _film_plan(self):
        return {
            "schema": "fa3.film-direction-plan.v1",
            "human_approval": {"status": "APPROVED", "approval_id": "a1"},
            "authoritative_final_cut": False,
            "shots": [
                {
                    "shot_id": "S1",
                    "start_frame": 0,
                    "end_frame": 10,
                    "intent": "establish",
                    "framing": "wide",
                    "camera": "locked",
                    "audio": "room",
                },
                {
                    "shot_id": "S2",
                    "start_frame": 10,
                    "end_frame": 20,
                    "intent": "advance",
                    "framing": "medium",
                    "camera": "push",
                    "audio": "dialogue",
                },
            ],
        }

    def test_film_plan_requires_human_approval_unique_nonoverlap_and_no_final_cut_authority(self):
        good = self._film_plan()
        self.assertTrue(validate_film_plan(good))
        duplicate = copy.deepcopy(good)
        duplicate["shots"][1]["shot_id"] = "S1"
        self.assertFalse(validate_film_plan(duplicate))
        overlap = copy.deepcopy(good)
        overlap["shots"][1]["start_frame"] = 9
        self.assertFalse(validate_film_plan(overlap))
        unapproved = copy.deepcopy(good)
        unapproved["human_approval"]["status"] = "PENDING"
        self.assertFalse(validate_film_plan(unapproved))
        authoritative = copy.deepcopy(good)
        authoritative["authoritative_final_cut"] = True
        self.assertFalse(validate_film_plan(authoritative))

    def test_animation_spec_is_finite_monotonic_and_source_preserving(self):
        good = {
            "fps": 24,
            "interpolation": "LINEAR",
            "authoritative_source_preserved": True,
            "keyframes": [
                {"time": 0.0, "x": 0.0, "y": 0.0},
                {"time": 1.0, "x": 1.0, "y": 0.0},
            ],
        }
        self.assertTrue(validate_animation_spec(good))
        nonmonotonic = copy.deepcopy(good)
        nonmonotonic["keyframes"][1]["time"] = -1.0
        self.assertFalse(validate_animation_spec(nonmonotonic))
        duplicate_time = copy.deepcopy(good)
        duplicate_time["keyframes"][1]["time"] = 0.0
        self.assertFalse(validate_animation_spec(duplicate_time))
        bad_interp = copy.deepcopy(good)
        bad_interp["interpolation"] = "PROVIDER_MAGIC"
        self.assertFalse(validate_animation_spec(bad_interp))
        lost_source = copy.deepcopy(good)
        lost_source["authoritative_source_preserved"] = False
        self.assertFalse(validate_animation_spec(lost_source))

    def test_exact_rollback_restores_identical_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            result = exact_rollback(
                Path(td),
                "state.json",
                b'{"state":"SAFE"}\n',
                b'{"state":"FAULT"}\n',
            )
            self.assertTrue(result["rollback_hash_equal"])
            self.assertEqual(result["pre_sha256"], result["post_sha256"])
            self.assertNotEqual(result["pre_sha256"], result["mutated_sha256"])


if __name__ == "__main__":
    unittest.main()
