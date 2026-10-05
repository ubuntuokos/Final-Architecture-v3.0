from __future__ import annotations
import json,unittest
from pathlib import Path
from fa3_ai_comms import CommunicationDenied
from fa3_orchestration_provider_spi import ProviderAdapterError,ProviderParticipantExpansionDenied,ProviderRuntimeNotPromoted,compile_plan_envelopes,compile_provider_envelope,validate_provider_message
from fa3_orchestration_workforce import compile_cross_domain_plan,route_task
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
 def test_uaf_projection(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"],"authorized_ai_participants":["primary"]};e=compile_provider_envelope(ROOT,t,route_task(ROOT,t));self.assertEqual(e["uaf_action"]["action_id"],"orchestration.delegate");self.assertFalse(e["direct_runtime_invocation_allowed"])
 def test_pending_runtime(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"]}
  with self.assertRaises(ProviderRuntimeNotPromoted):compile_provider_envelope(ROOT,t,route_task(ROOT,t),runtime_execution=True)
 def test_participant_expand(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"],"authorized_ai_participants":["a"],"metadata":{"provider_requested_ai_participants":["a","b"]}}
  with self.assertRaises(ProviderParticipantExpansionDenied):compile_provider_envelope(ROOT,t,route_task(ROOT,t))
 def test_direct_model_override(self):
  t={"task_id":"c","domain":"media-production","required_capabilities":["media_production_planning"],"metadata":{"direct_model_provider":"x"}}
  with self.assertRaises(ProviderAdapterError):compile_provider_envelope(ROOT,t,route_task(ROOT,t))
 def test_ai_comms(self):
  m={"communication_mode":"HUMAN_LANGUAGE","language_tag":"en-US","human_readable_text":"x","human_readable_authoritative":True,"codebook":{"z":"x"}}
  with self.assertRaises(CommunicationDenied):validate_provider_message(m,sender="a",recipient="b")
 def test_plan_no_hrb_adapter(self):
  req=json.loads((ROOT/"examples/orchestration-workforce-media.json").read_text());ap=compile_plan_envelopes(ROOT,req,compile_cross_domain_plan(ROOT,req));self.assertEqual({e["task_id"] for e in ap["envelopes"]},{"creative","transcode","ingest","live-avatar"})
if __name__=="__main__":unittest.main()
