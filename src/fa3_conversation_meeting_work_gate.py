#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
from fa3_conversation_meeting_work import self_test
GATE_ID="FA3-CONVERSATION-MEETING-WORK-GATESET-001"
def loadj(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def gate(root:Path)->dict:
    root=Path(root).resolve()
    p=loadj(root/"canonical/profiles/FA3-CONVERSATION-MEETING-WORK-FABRIC-001.json")
    c=loadj(root/"canonical/contracts/FA3-CONVERSATION-MEETING-WORK-CONTRACTS-001.json")
    i=loadj(root/"canonical/intents/FA3-CONVERSATION-MEETING-WORK-APPLICATION-INTENT-001.json")
    a=loadj(root/"canonical/assessments/FA3-CONVERSATION-MEETING-WORK-REUSE-ASSESSMENT-001.json")
    d=loadj(root/"canonical/assessments/FA3-CONVERSATION-MEETING-WORK-DECISION-ASSESSMENT-2026-10-01.json")
    h=loadj(root/"canonical/FA3-CONVERSATION-MEETING-WORK-CURRENT-HOST-IMPACT-001.json")
    r=loadj(root/"canonical/FA3-GATE-REGISTRY-001.json"); e=loadj(root/"canonical/enforcement-policy.json")
    checks={"baseline_175":p.get("capability_baseline")==175,"zero_capability_delta":p.get("capability_delta")==0,"zero_authority_delta":p.get("authority_delta")==0,
      "shared_views":len(p.get("projections",[]))>=8 and c.get("projection_rules",{}).get("views_share_one_graph") is True,
      "ai_optional":p.get("ai_policy",{}).get("optional") is True and p.get("ai_policy",{}).get("disabled_means_no_model_or_provider_call") is True,
      "proposal_not_canonical":c.get("materialization_rules",{}).get("ai_proposal_never_directly_canonical") is True,
      "human_review":c.get("materialization_rules",{}).get("human_verification_required") is True,
      "permission_required":c.get("materialization_rules",{}).get("approval_permission_required")=="MATERIALIZE_WORK",
      "speaker_not_authority":p.get("group_meeting_policy",{}).get("speaker_identity_is_authorization") is False,
      "reuse_pass":a.get("result")=="PASS" and a.get("implementation_readiness")=="READY_FOR_NORMAL_ADMISSION","decision_assessment":d.get("assessment") in {"REQUIRED","RECOMMENDED","OPTIONAL","NOT_APPLICABLE","PROHIBITED"} and d.get("capability_delta")==0 and d.get("authority_delta")==0,
      "no_donor_adoption":a.get("adopted_donors")==[] and a.get("donor_registry_mutated") is False,
      "cpu_only":p.get("hardware",{}).get("cpu_only_required") is True,
      "pending_physical_current_host":h.get("status")=="PENDING_PHYSICAL_CURRENT_HOST_EVIDENCE" and h.get("runtime_promotion_claim") is False,
      "gate_registry":GATE_ID in r.get("mandatory_reference_gates",[]),"policy_mirror":r.get("mandatory_reference_gates",[])==e.get("mandatory_reference_gates",[]),
      "reference_core":self_test().get("result")=="PASS","intent_zero_new_caps":i.get("declared_new_capabilities")==[]}
    failed=[k for k,v in checks.items() if not v]
    return {"schema":"fa3.conversation-meeting-work-gate-report.v1","gate_id":GATE_ID,"result":"PASS" if not failed else "FAIL","checks":checks,"blocking_findings":failed,"current_host_promotion_claim":False}
if __name__=="__main__":
    x=gate(Path(__file__).resolve().parents[1]); print(json.dumps(x,indent=2)); raise SystemExit(0 if x["result"]=="PASS" else 2)
