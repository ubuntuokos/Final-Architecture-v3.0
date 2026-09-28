"""PR Watch UAF bridge regression tests with the *existing* real dispatcher."""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from fa3_pr_watch import preview_goal_plan,PRWatchDenied
from fa3_pr_watch_workload_bridge import (
    build_admitted_start_request, dispatch_with_existing_uaf,sha256_ref)
from fa3_uaf import (ActionContract,ActionRegistry,CallableProvider,ProviderDescriptor,
                     ProviderRegistry,ActionDispatcher,UafError)
from test_goal_execution_foundation import fixture,task,preflight

HEAD="a"*40
ITEM={"kind":"PR","head_sha":HEAD,"repository":"fa3/reference-fixture",
      "external_key":"github:fa3/reference-fixture:pr:1"}


def setup_request():
    p={**preflight(),"source_sha":HEAD,"repository_scope":ITEM["repository"]}
    plan=preview_goal_plan(ROOT,ITEM,fixture(),[task()],p)
    workload=plan["proposal"]["steps"][0]["workload_candidate"]
    return build_admitted_start_request(
        ITEM,plan,fixture(),task_id="task-01",principal={"id":"verified-reference-user"},
        runtime_admission_receipt_ref="receipt:existing-scoped-runtime-reference",
        task_spec_ref=sha256_ref(workload),execution_plan_ref=sha256_ref(plan["proposal"]),
        approval={"approval_id":"external-reference-human-approval"},
    ),plan


def dispatcher(*,allow=True,approved=True,lease=True,provider=True):
    c=ActionContract.from_dict(json.loads(
        (ROOT/"canonical/actions/agent.workload.start.json").read_text()))
    providers=ProviderRegistry()
    if provider:
        providers.register(CallableProvider(ProviderDescriptor(
            provider_id="FA3-CI-REFERENCE-PROVIDER-NO_PRODUCTION_ADMISSION",
            action_ids=("agent.workload.start",)),
            lambda request,resource,secrets:{"status":"REFERENCE_ACCEPTED",
                "evidence_refs":["ci-reference-only"]}))
    receipts=[]
    releases=[]
    return ActionDispatcher(ActionRegistry([c]),providers,
        authorize=lambda request,contract:allow and request.context.workspace==ITEM["repository"],
        verify_approval=lambda request,contract:approved and bool(request.approval),
        acquire_resources=lambda request,contract,provider:{"lease_id":"ci-only"} if lease else None,
        release_resources=releases.append,evidence_sink=receipts.append),receipts,releases


class PRWatchUafBridgeTests(unittest.TestCase):
    def test_real_uaf_dispatcher_reference_only(self):
        request,_=setup_request()
        engine,receipts,releases=dispatcher()
        output=dispatch_with_existing_uaf(request,engine)
        self.assertEqual("SUBMITTED_TO_EXISTING_UAF_NOT_VERIFIED",output["status"])
        self.assertFalse(output["canonical_evidence_verified"])
        self.assertEqual(1,len(receipts))
        self.assertEqual(1,len(releases))
        self.assertEqual("agent.workload.start",output["uaf_action_id"])

    def test_no_scoped_auth_or_missing_hrb_denied(self):
        request,_=setup_request()
        for kw in ({"allow":False},{"lease":False},{"provider":False}):
            with self.subTest(kw=kw):
                engine,receipts,_=dispatcher(**kw)
                with self.assertRaises(UafError):
                    dispatch_with_existing_uaf(request,engine)
                self.assertEqual([],receipts)

    def test_missing_external_approval_denied_before_effect(self):
        request,_=setup_request()
        engine,receipts,_=dispatcher(approved=False)
        with self.assertRaises(PRWatchDenied):
            dispatch_with_existing_uaf(request,engine)
        self.assertEqual([],receipts)

    def test_missing_security_hrb_evidence_bridges_denied(self):
        request,_=setup_request()
        engine,_,_=dispatcher()
        engine.acquire_resources=None
        with self.assertRaises(PRWatchDenied):
            dispatch_with_existing_uaf(request,engine)

    def test_stale_sha_or_cross_repository_scope_denied(self):
        request,plan=setup_request()
        task_record=plan["proposal"]["steps"][0]["workload_candidate"]
        for item in ({**ITEM,"head_sha":"b"*40},
                     {**ITEM,"repository":"other/repo"}):
            with self.assertRaises(PRWatchDenied):
                build_admitted_start_request(item,plan,fixture(),task_id="task-01",
                    principal={"id":"verified-reference-user"},
                    runtime_admission_receipt_ref="receipt:reference",
                    task_spec_ref=sha256_ref(task_record),
                    execution_plan_ref=sha256_ref(plan["proposal"]),
                    approval={"approval_id":"reference"})

    def test_forged_task_digest_denied(self):
        _,plan=setup_request()
        with self.assertRaises(PRWatchDenied):
            build_admitted_start_request(ITEM,plan,fixture(),task_id="task-01",
                principal={"id":"verified-reference-user"},
                runtime_admission_receipt_ref="receipt:reference",
                task_spec_ref="sha256:"+"f"*64,
                execution_plan_ref=sha256_ref(plan["proposal"]),
                approval={"approval_id":"reference"})

if __name__=="__main__":unittest.main()
