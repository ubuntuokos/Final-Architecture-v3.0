from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_marketing_uaf import AdapterMode, register_marketing_provider, register_reference_marketing_providers
from fa3_uaf import ActionDispatcher, ActionRegistry, ActionRequest, ExecutionContext, ProviderRegistry, UafError


class MarketingUafTests(unittest.TestCase):
    def test_reference_adapter_routes_through_uaf_without_mutation(self):
        providers = ProviderRegistry()
        register_reference_marketing_providers(providers)
        receipts = []
        dispatcher = ActionDispatcher(
            ActionRegistry.from_directory(ROOT / "canonical/actions"),
            providers,
            authorize=lambda request, contract: True,
            evidence_sink=receipts.append,
        )
        result = dispatcher.execute(ActionRequest(
            action_id="marketing.segment.preview",
            arguments={
                "operation_id": "op-1",
                "payload_ref": "canonical:segment/1",
                "candidate_ids": ["segment-a", "segment-b"],
                "context_refs": ["campaign:1"],
            },
            principal={"id": "user:test"},
            context=ExecutionContext("ctx-1"),
        ))
        self.assertEqual("FA3-PROVIDER-MAUTIC-001", result.provider_id)
        self.assertEqual("REFERENCE_ONLY_NO_PROVIDER_MUTATION", result.output["status"])
        self.assertEqual("CONTINUE", result.output["decision_receipt"]["outcome"])
        self.assertEqual(1, len(receipts))

    def test_external_transport_cannot_connect_without_current_host_admission(self):
        providers = ProviderRegistry()
        with self.assertRaises(UafError) as error:
            register_marketing_provider(
                providers,
                "FA3-PROVIDER-MAUTIC-001",
                transport=lambda request, leases: {"status": "PROVIDER_APPLIED"},
                mode=AdapterMode("LIVE", True, False),
            )
        self.assertEqual("MKT-PROVIDER-NOT-ADMITTED", error.exception.code)

    def test_live_external_provider_requires_secret_broker_lease(self):
        providers = ProviderRegistry()
        register_marketing_provider(
            providers,
            "FA3-PROVIDER-TWENTY-001",
            transport=lambda request, leases: {"status": "PROVIDER_APPLIED"},
            mode=AdapterMode("LIVE", True, True),
        )
        provider = providers.select("marketing.contact.project")
        request = ActionRequest(
            action_id="marketing.contact.project",
            arguments={"operation_id": "op", "payload_ref": "contact:1", "candidate_ids": ["contact:1"]},
            principal={"id": "user:test"},
            context=ExecutionContext("ctx"),
        )
        with self.assertRaises(UafError) as error:
            provider.execute(request, None, ())
        self.assertEqual("UAF-SECRET-DENIED", error.exception.code)


if __name__ == "__main__":
    unittest.main()
