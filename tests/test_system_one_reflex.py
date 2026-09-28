from __future__ import annotations

import os
import unittest

from fa3_decision_fabric import DecisionFabric, DecisionRequest
from fa3_system_one_decision_provider import SystemOneDecisionProvider
from fa3_system_one_reflex import (
    FINISH,
    SystemOneReflexRuntime,
    SystemOneSpecError,
    compile_system_one_step,
    evaluate_system_one_answers,
)


def action(action_id, *, risk="write", parameters=None):
    return {
        "id": action_id,
        "description": f"{action_id} action",
        "metadata": {
            "risk": risk,
            "parameters": parameters or {},
        },
    }


class SystemOneReflexTests(unittest.TestCase):
    def test_one_router_call_selects_bounded_action_and_parameters(self):
        calls = []

        def transport(envelope):
            calls.append(envelope)
            self.assertEqual(envelope["authority"], "FA3-AUTH-MODEL-ROUTER-001")
            self.assertEqual(envelope["logical_route"], "fa3-decision-system-one")
            self.assertEqual(envelope["protocol"], "system-one-decision-v1")
            self.assertNotIn("model", envelope["request"])
            questions = envelope["request"]["questions"]
            self.assertIn("next_action", questions)
            self.assertIn("open__record", questions)
            return {
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "open",
                        "probabilities": {"open": 0.91, "refresh": 0.06, "__finish__": 0.01, "__escalate__": 0.02},
                        "confidence": 0.91,
                    },
                    "goal_reached": {"type": "noul", "noul": 0.02},
                    "open__record": {
                        "type": "choice",
                        "choice": "r2",
                        "probabilities": {"r1": 0.1, "r2": 0.9},
                        "confidence": 0.9,
                    },
                },
                "_fa3_routing": {
                    "authority": "FA3-AUTH-MODEL-ROUTER-001",
                    "receipt_ref": "evidence://router/system-one-test",
                    "provider_id": "TEST-SYSTEM-ONE",
                    "model_id": "runtime-selected",
                    "external_provider": False,
                    "protocol": "system-one-decision-v1",
                },
            }

        provider = SystemOneDecisionProvider(explicitly_enabled=True, router_transport=transport)
        runtime = SystemOneReflexRuntime(DecisionFabric([provider]))
        step = runtime.step(
            purpose="open the requested record",
            actions=[
                action("open", risk="read", parameters={
                    "record": {"kind": "candidates", "source": "visible_records"}
                }),
                action("refresh", risk="read"),
            ],
            state={"goal": "open r2", "observation": "records visible"},
            constraints={"parameter_candidates": {"visible_records": ["r1", "r2"]}},
            final_policy_owner="FA3-AUTH-MCP-GATEWAY-001",
            rollout="ACTIVE",
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(step["status"], "READY_FOR_AUTHORIZATION")
        self.assertEqual(step["selected_action"], "open")
        self.assertEqual(step["parameters"], {"record": "r2"})
        self.assertFalse(step["authority"])
        self.assertFalse(step["execution_performed"])
        self.assertTrue(step["requires_external_policy_authorization"])
        meta = step["decision_trace"]["provider_meta"]
        self.assertFalse(meta["confidence_is_authorization"])
        self.assertEqual(meta["model_router_authority"], "FA3-AUTH-MODEL-ROUTER-001")
        self.assertFalse(meta["physical_model_pinned"])
        self.assertFalse(meta["physical_backend_pinned"])

    def test_low_confidence_action_creates_typed_handoff(self):
        def transport(envelope):
            return {
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": "delete",
                        "probabilities": {"delete": 0.61, "__finish__": 0.1, "__escalate__": 0.29},
                        "confidence": 0.61,
                    },
                    "goal_reached": {"type": "noul", "noul": 0.01},
                },
                "_fa3_routing": {"authority": "FA3-AUTH-MODEL-ROUTER-001"},
            }

        provider = SystemOneDecisionProvider(explicitly_enabled=True, router_transport=transport)
        runtime = SystemOneReflexRuntime(DecisionFabric([provider]))
        step = runtime.step(
            purpose="choose a bounded operation",
            actions=[action("delete", risk="destructive")],
            state={"item": "x"},
            final_policy_owner="FA3-AUTH-MCP-GATEWAY-001",
            rollout="ACTIVE",
        )
        self.assertEqual(step["status"], "HANDOFF")
        self.assertEqual(step["decision_trace"]["status"], "NO_DECISION")
        self.assertEqual(step["handoff"]["reason"], "no_confident_action")
        self.assertEqual(step["handoff"]["risk"], "destructive")
        self.assertEqual(step["handoff"]["threshold"], 0.8)
        self.assertEqual(step["handoff"]["target_classes"], ["SYSTEM_TWO", "HUMAN"])
        self.assertFalse(step["execution_performed"])

    def test_free_text_parameter_fails_before_model_call(self):
        request = DecisionRequest.from_dict({
            "contract": "BOUNDED_ACTION",
            "purpose": "bad action space",
            "candidates": [action("search", parameters={
                "query": {"instructions": "write a query"}
            })],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "state": {},
            "failure_policy": "NO_DECISION",
            "rollout": "SHADOW",
            "final_policy_owner": "TEST",
        })
        with self.assertRaises(SystemOneSpecError):
            compile_system_one_step(request)

    def test_finish_requires_independent_goal_confirmation(self):
        def transport(envelope):
            return {
                "answers": {
                    "next_action": {
                        "type": "choice",
                        "choice": FINISH,
                        "probabilities": {FINISH: 0.95, "__escalate__": 0.01, "inspect": 0.04},
                        "confidence": 0.95,
                    },
                    "goal_reached": {"type": "noul", "noul": 0.2},
                },
                "_fa3_routing": {"authority": "FA3-AUTH-MODEL-ROUTER-001"},
            }

        provider = SystemOneDecisionProvider(explicitly_enabled=True, router_transport=transport)
        runtime = SystemOneReflexRuntime(DecisionFabric([provider]))
        step = runtime.step(
            purpose="finish only if complete",
            actions=[action("inspect", risk="read")],
            state={"complete": False},
            final_policy_owner="TEST",
            rollout="ACTIVE",
        )
        self.assertEqual(step["status"], "HANDOFF")
        self.assertEqual(step["handoff"]["reason"], "finish_not_confident")

    @staticmethod
    def _bounded_request(parameters=None):
        return DecisionRequest.from_dict({
            "contract": "BOUNDED_ACTION",
            "purpose": "strict probability gate negative proof",
            "candidates": [action("inspect", risk="read", parameters=parameters)],
            "constraints": {},
            "policy_context": {},
            "evidence_refs": [],
            "state": {"bounded": True},
            "failure_policy": "NO_DECISION",
            "rollout": "ACTIVE",
            "final_policy_owner": "TEST",
        })

    @staticmethod
    def _next_answer(compiled, selected=0.99):
        criteria = list(compiled.questions["next_action"]["criteria"])
        alternative = next(key for key in criteria if key != "inspect")
        return {
            "type": "choice",
            "choice": "inspect",
            "probabilities": {
                key: (selected if key == "inspect" else 1.0 - selected if key == alternative else 0.0)
                for key in criteria
            },
            "confidence": selected,
        }

    def test_nonfinite_confidence_and_incomplete_distributions_fail_closed(self):
        request = self._bounded_request()
        compiled = compile_system_one_step(request)
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=str(value)):
                with self.assertRaises(SystemOneSpecError):
                    evaluate_system_one_answers(
                        request, compiled, {
                            "next_action": self._next_answer(compiled, value),
                        },
                    )
        with self.assertRaises(SystemOneSpecError):
            evaluate_system_one_answers(
                request, compiled, {
                    "next_action": {
                        "type": "choice",
                        "choice": "inspect",
                        "probabilities": {"inspect": 0.99},
                        "confidence": 0.99,
                    },
                },
            )

    def test_missing_required_boolean_answer_cannot_gain_confidence(self):
        request = self._bounded_request({"flag": {"kind": "flag"}})
        compiled = compile_system_one_step(request)
        with self.assertRaises(SystemOneSpecError):
            evaluate_system_one_answers(
                request, compiled, {"next_action": self._next_answer(compiled)},
            )

    def test_missing_optional_presence_judgment_cannot_silently_default(self):
        request = self._bounded_request({
            "record": {
                "kind": "choices",
                "choices": ["one", "two"],
                "optional": True,
                "default": "one",
            },
        })
        compiled = compile_system_one_step(request)
        with self.assertRaises(SystemOneSpecError):
            evaluate_system_one_answers(
                request, compiled, {"next_action": self._next_answer(compiled)},
            )
        accepted = evaluate_system_one_answers(
            request, compiled, {
                "next_action": self._next_answer(compiled),
                "inspect__record__stated": {"type": "noul", "noul": 0.01},
            },
        )
        self.assertEqual(accepted.status, "DECIDED")
        self.assertEqual(accepted.result["parameters"], {"record": "one"})


    def test_choice_distribution_rejects_wrong_total_and_non_top_selection(self):
        request = self._bounded_request()
        compiled = compile_system_one_step(request)
        wrong_total = self._next_answer(compiled)
        wrong_total["probabilities"]["inspect"] = 0.8
        with self.assertRaisesRegex(SystemOneSpecError, "not normalized"):
            evaluate_system_one_answers(request, compiled, {"next_action": wrong_total})
        contradiction = self._next_answer(compiled)
        contradiction["probabilities"] = {
            key: (0.45 if key == "inspect" else 0.55 if key == "__escalate__" else 0.0)
            for key in compiled.questions["next_action"]["criteria"]
        }
        with self.assertRaisesRegex(SystemOneSpecError, "contradicts"):
            evaluate_system_one_answers(request, compiled, {"next_action": contradiction})

    def test_score_requires_all_compiled_levels_and_normalization(self):
        parameters = {"severity": {"kind": "levels", "levels": ["low", "medium", "high"]}}
        request = self._bounded_request(parameters)
        compiled = compile_system_one_step(request)
        choices = self._next_answer(compiled)
        valid = {"type": "score", "probabilities": {"low": 0.05, "medium": 0.05, "high": 0.9}}
        approved = evaluate_system_one_answers(
            request, compiled, {"next_action": choices, "inspect__severity": valid}
        )
        self.assertEqual(approved.result["parameters"]["severity"], "high")
        for invalid in (
            {"type": "score", "probabilities": {"low": 0.1, "high": 0.9}},
            {"type": "score", "probabilities": {"low": 0.05, "medium": 0.05, "high": 0.5}},
            {"type": "score", "probabilities": {"0": 0.05, "medium": 0.05, "2": 0.9}},
            {"type": "score", "probabilities": {"low": float("nan"), "medium": 0.05, "high": 0.95}},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(SystemOneSpecError):
                    evaluate_system_one_answers(
                        request, compiled, {"next_action": choices, "inspect__severity": invalid}
                    )
        indexed = evaluate_system_one_answers(
            request, compiled,
            {"next_action": choices, "inspect__severity": {"type": "score", "probabilities": {"0": 0.05, "1": 0.05, "2": 0.9}}},
        )
        self.assertEqual(indexed.result["parameters"]["severity"], "high")

    def test_duplicate_levels_rejected_before_provider_request(self):
        request = self._bounded_request({"severity": {"kind": "levels", "levels": ["low", "low"]}})
        with self.assertRaisesRegex(SystemOneSpecError, "unique"):
            compile_system_one_step(request)

    def test_finish_requires_explicit_finite_goal_confirmation(self):
        request = self._bounded_request()
        compiled = compile_system_one_step(request)
        probabilities = {
            key: (0.96 if key == FINISH else 0.04 if key == "inspect" else 0.0)
            for key in compiled.questions["next_action"]["criteria"]
        }
        finishing = {"type": "choice", "choice": FINISH, "probabilities": probabilities}
        for answer in (None, {"type": "noul"}, {"type": "noul", "noul": float("nan")},
                       {"type": "noul", "noul": float("inf")}, {"type": "choice", "noul": 0.99}):
            with self.subTest(answer=answer):
                values = {"next_action": finishing}
                if answer is not None:
                    values["goal_reached"] = answer
                with self.assertRaises(SystemOneSpecError):
                    evaluate_system_one_answers(request, compiled, values)

    def test_missing_model_router_receipt_authority_fails_closed(self):
        provider = SystemOneDecisionProvider(
            explicitly_enabled=True,
            router_transport=lambda _: {"answers": {}, "_fa3_routing": {}},
        )
        with self.assertRaisesRegex(ValueError, "routing authority mismatch"):
            provider.decide(self._bounded_request())

    def test_cpu_only_environment_has_no_accelerator_dependency(self):
        old = {k: os.environ.get(k) for k in ("CUDA_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES", "ZE_AFFINITY_MASK")}
        try:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            os.environ["ROCR_VISIBLE_DEVICES"] = ""
            os.environ["ZE_AFFINITY_MASK"] = ""

            def transport(envelope):
                return {
                    "answers": {
                        "next_action": {
                            "type": "choice",
                            "choice": "inspect",
                            "probabilities": {"inspect": 0.99, "__finish__": 0.0, "__escalate__": 0.01},
                            "confidence": 0.99,
                        },
                        "goal_reached": {"type": "noul", "noul": 0.0},
                    },
                    "_fa3_routing": {"authority": "FA3-AUTH-MODEL-ROUTER-001"},
                }

            provider = SystemOneDecisionProvider(explicitly_enabled=True, router_transport=transport)
            step = SystemOneReflexRuntime(DecisionFabric([provider])).step(
                purpose="cpu-only bounded step",
                actions=[action("inspect", risk="read")],
                state={},
                final_policy_owner="TEST",
                rollout="ACTIVE",
            )
            self.assertEqual(step["status"], "READY_FOR_AUTHORIZATION")
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
