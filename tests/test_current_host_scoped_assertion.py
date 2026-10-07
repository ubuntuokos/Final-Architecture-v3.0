from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from fa3_current_host_scoped_assertion import assert_scoped_requalification
class T(unittest.TestCase):
 def test_scoped(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td); d=r/"reports"; d.mkdir(); s=["CAP-013","CAP-083"]; common={"global_promotion_claim":False}
   rows={
    "current-host-capability-qualification-constituent-orchestrator.json":{**common,"orchestrator_integrity":"PASS","requested_subjects":s,"selected_producer_count":6,"constituents_materialized":6},
    "current-host-capability-test-orchestrator.json":{**common,"orchestrator_integrity":"PASS","requested_subjects":s,"selected_executor_count":6,"results_materialized":6},
    "current-host-capability-test-bundle-assembler.json":{**common,"assembler_integrity":"PASS","bundles_materialized":2,"materialized_capability_ids":s},
    "current-host-capability-attestation-producer.json":{**common,"producer_integrity":"PASS","attestations_materialized":2,"materialized_capability_ids":s},
    "current-host-capability-handoff.json":{**common,"handoff_integrity":"PASS","receipts_materialized":2,"materialized_capability_ids":s},
   }
   for n,v in rows.items():(d/n).write_text(json.dumps(v))
   x=assert_scoped_requalification(r,s); self.assertEqual("PASS",x["result"]); self.assertEqual(6,x["obligation_count"])
if __name__=="__main__":unittest.main()
