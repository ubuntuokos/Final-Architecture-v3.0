import json
import unittest
from pathlib import Path

from fa3_shared_capability_fabric import internal_application_ids, resolve, resolve_slice, universal_surface_consumers
from fa3_shared_capability_gate import gate

ROOT=Path(__file__).resolve().parents[1]

class SharedCapabilityFabricTests(unittest.TestCase):
    def base_context(self):
        return {
            "application_relevant": True,
            "project_relevant": True,
            "authority_allowed": True,
            "policy_allowed": True,
            "workflow_allowed": True,
            "role_allowed": True,
            "service_available": True,
        }

    def test_materialization_gate(self):
        self.assertEqual("PASS", gate(ROOT)["result"])

    def test_not_applicable_is_hidden(self):
        ctx=self.base_context()
        ctx["application_relevant"]=False
        self.assertEqual("HIDDEN", resolve(ROOT,"render",ctx).state)

    def test_hobby_external_render_service_is_not_globally_denied(self):
        ctx=self.base_context()
        ctx.update({"project_profile":"HOBBY","external_service_selected":True})
        self.assertEqual("ACTIVE", resolve(ROOT,"render",ctx).state)

    def test_rfq_appears_only_for_external_service_context(self):
        ctx=self.base_context()
        self.assertEqual("HIDDEN", resolve(ROOT,"rfq.request",ctx).state)
        ctx["external_service_selected"]=True
        self.assertEqual("ACTIVE", resolve(ROOT,"rfq.request",ctx).state)

    def test_purchase_order_requires_explicit_authorization(self):
        ctx=self.base_context()
        ctx["external_service_selected"]=True
        decision=resolve(ROOT,"purchase.order",ctx)
        self.assertEqual("VISIBLE_DISABLED",decision.state)
        self.assertIn("explicit-purchase-authorization-required",decision.reasons)
        ctx["explicit_authorization"]=True
        self.assertEqual("ACTIVE",resolve(ROOT,"purchase.order",ctx).state)

    def test_cost_slices_contextual(self):
        ctx=self.base_context()
        self.assertEqual("HIDDEN",resolve(ROOT,"expense.request",ctx).state)
        ctx["cost_context"]=True
        self.assertEqual("ACTIVE",resolve(ROOT,"expense.request",ctx).state)

    def test_email_compose_available_even_when_full_management_not_applicable(self):
        ctx={"operation":"email.compose","authority_allowed":True,"policy_allowed":True,"provider_available":True}
        self.assertEqual("ACTIVE",resolve(ROOT,"email.management",ctx).state)

    def test_email_send_requires_explicit_send_intent(self):
        ctx={"operation":"email.send","authority_allowed":True,"policy_allowed":True,"provider_available":True}
        self.assertEqual("VISIBLE_DISABLED",resolve(ROOT,"email.management",ctx).state)
        ctx["explicit_send_intent"]=True
        self.assertEqual("ACTIVE",resolve(ROOT,"email.management",ctx).state)

    def test_email_provider_unavailable_is_explicit(self):
        ctx={"operation":"email.compose","authority_allowed":True,"policy_allowed":True,"provider_available":False}
        self.assertEqual("UNAVAILABLE",resolve(ROOT,"email.management",ctx).state)

    def test_hidden_slice_never_becomes_background_execution(self):
        record={"key":"expense.submit","activation_class":"COST_CONTEXT"}
        decision=resolve_slice(record,self.base_context())
        self.assertEqual("HIDDEN",decision.state)

    def test_email_send_covers_every_registered_internal_application(self):
        internal=set(internal_application_ids(ROOT))
        consumers=set(universal_surface_consumers(ROOT,"email.send"))
        self.assertTrue(internal)
        self.assertEqual(internal,consumers)

    def test_registry_has_exact_45_slices(self):
        data=json.loads((ROOT/"canonical/FA3-SHARED-CAPABILITY-FABRIC-001.json").read_text())
        self.assertEqual(45,data["slice_count"])
        self.assertEqual(45,len(data["slices"]))

if __name__=="__main__":
    unittest.main()
