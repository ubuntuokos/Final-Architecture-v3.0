import json
import unittest
from pathlib import Path

from fa3_communications_contacts import authorize, reference_cases
from fa3_communications_contacts_gate import gate

ROOT = Path(__file__).resolve().parents[1]

class CommunicationsContactsTests(unittest.TestCase):
    def permissions(self):
        return {"mail.read","mail.compose","mail.send","mail.forward","mail.assign","mail.note","contacts.read","contacts.write","contacts.export","ai.mail.summarize","ai.mail.draft_reply","ai.contact.deduplicate"}

    def gates(self):
        names = {"identity","authentication","authorization","context_scope","layer_guard","application_boundary","data_classification","privacy","secret_broker","communication_security","audit_evidence","software_coexistence","hardware_safety","current_host","attachment_security","anti_phishing","dlp","explicit_approval","provider_admission","ai_permission","ai_context_isolation","prompt_injection","context_minimization","secret_filter","pii_filter","model_router","hrb","tool_permission","output_validation"}
        return {x: True for x in names}

    def base(self, **kw):
        p = self.permissions()
        data = {"surface_mode":"FULL","operation":"mail.read","user_permissions":p,"role_permissions":p,"application_permissions":p,"context_permissions":p,"data_permissions":p,"security_gates":self.gates()}
        data.update(kw)
        return data

    def test_reference_cases(self):
        self.assertTrue(all(reference_cases().values()))

    def test_embedded_requires_context(self):
        self.assertFalse(authorize(self.base(surface_mode="EMBEDDED", context_ids=[])).allowed)
        self.assertTrue(authorize(self.base(surface_mode="EMBEDDED", context_ids=["project:A"])).allowed)

    def test_permissions_are_intersection(self):
        self.assertFalse(authorize(self.base(surface_mode="EMBEDDED", context_ids=["project:A"], role_permissions=[])).allowed)

    def test_fail_closed_missing_gate(self):
        self.assertFalse(authorize(self.base(security_gates={})).allowed)

    def test_ai_off_means_no_ai(self):
        self.assertFalse(authorize(self.base(operation="ai.mail.summarize", external_message=True, ai_policy={})).allowed)

    def test_ai_untrusted_content_cannot_be_instruction(self):
        policy = {x: True for x in ("global","application","module","capability","operation")}
        result = authorize(self.base(operation="ai.mail.summarize", external_message=True, ai_policy=policy, message_content_as_system_instruction=True, requested_provider="a", selected_provider="a"))
        self.assertFalse(result.allowed)

    def test_static_gate(self):
        result = gate(ROOT)
        self.assertEqual("PASS", result["result"], json.dumps(result, indent=2))

if __name__ == "__main__":
    unittest.main()
