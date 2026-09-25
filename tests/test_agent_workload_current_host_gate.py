import copy
import unittest
from pathlib import Path
from src.fa3_agent_workload_current_host_gate import LABELS, NATIVE, PROFILE, WORKLOAD, validate_materialization, validate_receipt

ROOT=Path(__file__).resolve().parents[1]

def fixture():
    return {
      "schema":"fa3.agent-workload-runtime-current-host-receipt.v1","profile_id":PROFILE,"provider_id":NATIVE,
      "status":"PASS","evidence_level":"CURRENT_HOST_PRODUCTION_E2E_PASS","synthetic":False,
      "execution_context":"REAL_SELF_HOSTED_FA3_CURRENT_HOST","runner_labels":LABELS,
      "resource_admission":{"authority":"FA3-AUTH-HOST-RESOURCE-BROKER-001","result":"PASS","workload_id":WORKLOAD,"authorization_id":"AUTH-1","receipt_sha256":"abc","fresh_scope_bound_required":True},
      "tests":{"static_gate":"PASS","non_root_execution":"PASS","cleanup":"PASS","cgroup_v2_systemd_scope":{"status":"PASS"},"real_process_pause_resume":{"status":"PASS"}},
      "admitted_provider_ids":[NATIVE],"provider_subclaims":{"podman":"NOT_TESTED","google_ax":"NOT_TESTED"},
      "non_claims":["GLOBAL_FA3_PROMOTION","GOOGLE_AX_PRODUCTION_ADMISSION","PODMAN_PRODUCTION_ADMISSION","PROCESS_CHECKPOINT_SUPPORT","VM_CHECKPOINT_SUPPORT"],
      "errors":[],"global_promotion_claim":False
    }

class AgentWorkloadCurrentHostTests(unittest.TestCase):
    def test_static_materialization(self):
        self.assertEqual([],validate_materialization(ROOT))
    def test_valid_receipt_contract(self):
        self.assertEqual([],validate_receipt(fixture()))
    def test_synthetic_rejected(self):
        r=fixture(); r["synthetic"]=True
        self.assertTrue(validate_receipt(r))
    def test_wrong_workload_scope_rejected(self):
        r=fixture(); r["resource_admission"]["workload_id"]="other"
        self.assertTrue(validate_receipt(r))
    def test_provider_scope_expansion_rejected(self):
        r=fixture(); r["admitted_provider_ids"].append("FA3-PROVIDER-GOOGLE-AX-001")
        self.assertTrue(validate_receipt(r))

if __name__=="__main__": unittest.main()
