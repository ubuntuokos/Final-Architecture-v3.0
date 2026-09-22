from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_uaf import (
    ActionContract,
    ActionDispatcher,
    ActionRegistry,
    ActionRequest,
    CallableProvider,
    ExecutionContext,
    ProviderDescriptor,
    ProviderRegistry,
    UafError,
    build_reference_runtime,
)


def contract(
    action_id: str = "test.echo",
    *,
    hrb: bool = False,
    approval: str = "policy",
    evidence: bool = True,
) -> ActionContract:
    return ActionContract.from_dict({
        "schema": "fa3.uaf.action-contract.v1",
        "id": action_id,
        "version": "1.0.0",
        "description": "fixture",
        "input_schema": {
            "type": "object",
            "required": ["value"],
            "properties": {"value": {"type": "integer"}},
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "required": ["echo"],
            "properties": {"echo": {"type": "integer"}},
            "additionalProperties": False,
        },
        "semantics": {"mutating": False, "idempotent": True},
        "exposure": {"cli": True, "mcp": True},
        "security": {
            "authentication": "required",
            "authorization": "required",
            "approval": approval,
        },
        "resources": {
            "hrb_required": hrb,
            "accelerator_required": False,
        },
        "provider": {"selection": "capability-match"},
        "evidence": {"required": evidence},
    })


def request(action_id: str = "test.echo") -> ActionRequest:
    return ActionRequest(
        action_id=action_id,
        arguments={"value": 7},
        principal={"id": "user:test"},
        context=ExecutionContext("ctx-1"),
    )


class UafTests(unittest.TestCase):
    def provider_registry(self) -> ProviderRegistry:
        providers = ProviderRegistry()
        providers.register(CallableProvider(
            ProviderDescriptor("P1", ("test.echo",), priority=10),
            lambda req, lease, secrets: {"echo": req.arguments["value"]},
        ))
        return providers

    def test_success_requires_external_authorization_and_evidence(self) -> None:
        receipts = []
        dispatcher = ActionDispatcher(
            ActionRegistry([contract()]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=receipts.append,
        )
        result = dispatcher.execute(request())
        self.assertEqual("success", result.status)
        self.assertEqual({"echo": 7}, result.output)
        self.assertEqual(1, len(receipts))
        self.assertFalse(receipts[0]["global_promotion_claim"])

    def test_missing_authorizer_fails_closed(self) -> None:
        dispatcher = ActionDispatcher(
            ActionRegistry([contract()]),
            self.provider_registry(),
            evidence_sink=lambda receipt: None,
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(request())
        self.assertEqual("UAF-UNAUTHORIZED", error.exception.code)

    def test_hrb_required_has_no_local_fallback(self) -> None:
        dispatcher = ActionDispatcher(
            ActionRegistry([contract(hrb=True)]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(request())
        self.assertEqual("UAF-RESOURCE-DENIED", error.exception.code)

    def test_conditional_approval_fails_without_grant(self) -> None:
        dispatcher = ActionDispatcher(
            ActionRegistry([contract(approval="conditional")]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(request())
        self.assertEqual("UAF-APPROVAL-REQUIRED", error.exception.code)

    def test_secret_refs_require_secret_broker_adapter(self) -> None:
        dispatcher = ActionDispatcher(
            ActionRegistry([contract()]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        req = ActionRequest(
            action_id="test.echo",
            arguments={"value": 7},
            principal={"id": "user:test"},
            context=ExecutionContext("ctx-1"),
            secret_refs=("provider/example",),
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(req)
        self.assertEqual("UAF-SECRET-DENIED", error.exception.code)

    def test_unknown_argument_rejected(self) -> None:
        dispatcher = ActionDispatcher(
            ActionRegistry([contract()]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        req = ActionRequest(
            action_id="test.echo",
            arguments={"value": 7, "extra": True},
            principal={"id": "user:test"},
            context=ExecutionContext("ctx-1"),
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(req)
        self.assertEqual("UAF-INPUT-INVALID", error.exception.code)

    def test_registry_rejects_duplicate_action_ids(self) -> None:
        with self.assertRaises(UafError):
            ActionRegistry([contract(), contract()])

    def test_provider_registry_rejects_duplicate_ids(self) -> None:
        providers = ProviderRegistry()
        provider = CallableProvider(
            ProviderDescriptor("P1", ("test.echo",)),
            lambda req, lease, secrets: {"echo": 7},
        )
        providers.register(provider)
        with self.assertRaises(UafError):
            providers.register(provider)

    def test_inline_secret_field_rejected_before_provider(self) -> None:
        base = contract()
        secret_contract = ActionContract(
            action_id=base.action_id,
            version=base.version,
            description=base.description,
            input_schema={
                "type": "object",
                "required": ["value", "api_key"],
                "properties": {
                    "value": {"type": "integer"},
                    "api_key": {"type": "string"},
                },
                "additionalProperties": False,
            },
            output_schema=base.output_schema,
            semantics=base.semantics,
            exposure=base.exposure,
            security=base.security,
            resources=base.resources,
            provider=base.provider,
            evidence=base.evidence,
            source_path=base.source_path,
        )
        dispatcher = ActionDispatcher(
            ActionRegistry([secret_contract]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        req = ActionRequest(
            action_id="test.echo",
            arguments={"value": 7, "api_key": "raw-secret"},
            principal={"id": "user:test"},
            context=ExecutionContext("ctx-1"),
        )
        with self.assertRaises(UafError) as error:
            dispatcher.execute(req)
        self.assertEqual("UAF-SECRET-DENIED", error.exception.code)

    def test_approval_is_digest_context_principal_and_expiry_bound(self) -> None:
        from fa3_uaf import _canonical_digest
        action = contract(approval="explicit")
        context = ExecutionContext("ctx-1")
        arguments = {"value": 7}
        approval = {
            "approval_id": "approval-1",
            "principal_ref": "user:test",
            "action_id": "test.echo",
            "action_version": "1.0.0",
            "argument_digest": _canonical_digest(arguments),
            "context_digest": _canonical_digest(context.as_dict()),
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(minutes=5)
            ).isoformat(),
            "single_use": True,
        }
        req = ActionRequest(
            action_id="test.echo",
            arguments=arguments,
            principal={"id": "user:test"},
            context=context,
            approval=approval,
        )
        dispatcher = ActionDispatcher(
            ActionRegistry([action]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            verify_approval=lambda req, action: True,
            evidence_sink=lambda receipt: None,
        )
        self.assertEqual("success", dispatcher.execute(req).status)
        bad = dict(approval)
        bad["argument_digest"] = "sha256:bad"
        with self.assertRaises(UafError) as error:
            dispatcher.execute(ActionRequest(
                action_id="test.echo",
                arguments=arguments,
                principal={"id": "user:test"},
                context=context,
                approval=bad,
            ))
        self.assertEqual("UAF-APPROVAL-INVALID", error.exception.code)

    def test_evidence_records_only_opaque_lease_ids(self) -> None:
        receipts = []
        dispatcher = ActionDispatcher(
            ActionRegistry([contract(hrb=True)]),
            self.provider_registry(),
            authorize=lambda req, action: True,
            acquire_resources=lambda req, action, provider: {
                "lease_id": "hrb-1",
                "secret": "must-not-leak",
            },
            release_resources=lambda lease: None,
            evidence_sink=receipts.append,
        )
        dispatcher.execute(request())
        self.assertEqual("hrb-1", receipts[0]["resource_lease_ref"])
        self.assertNotIn("must-not-leak", json.dumps(receipts[0]))

    def test_reference_runtime_lists_bootstrap_actions(self) -> None:
        receipts = []
        dispatcher = build_reference_runtime(
            ROOT / "canonical/actions",
            authorize=lambda req, action: True,
            evidence_sink=receipts.append,
        )
        result = dispatcher.execute(ActionRequest(
            action_id="system.capabilities.list",
            arguments={},
            principal={"id": "user:test"},
            context=ExecutionContext("ctx-1"),
        ))
        self.assertIn("hardware.describe", result.output["actions"])
        self.assertEqual(1, len(receipts))


if __name__ == "__main__":
    unittest.main()
