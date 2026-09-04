from __future__ import annotations

from pathlib import Path
import pytest
from fa3_xyops_gate import CAPABILITY_COUNT, P0_RULES, capacity_pool_valid, credential_transport_valid, execution_receipt_valid, hardware_discovery_valid, hrb_admission_valid, least_privilege_valid, local_enforcement_valid, production_policy_admission_valid, resource_projection_valid, resume_valid, retry_valid, rollback_valid, secret_projection_valid, shell_execution_valid, supply_chain_valid, terminal_control_evidence_valid, typed_execution_request_valid, http_execution_valid, gate
ROOT = Path(__file__).resolve().parents[1]

def test_rule_inventory_is_fail_closed_p0_30():
    assert CAPABILITY_COUNT == 143; assert len(P0_RULES) == 30; assert len(P0_RULES) == len(set(P0_RULES))

def test_reference_gate_passes_repository_materialization():
    report=gate(ROOT); assert report["result"]=="PASS",report; assert report["blocking_findings"]==0; assert report["rule_count"]==30; assert report["current_host_runtime_promotion_claimed"] is False

@pytest.mark.parametrize(("kwargs","expected"), [({"typed":True,"versioned":True,"request_id":"req-1"},True),({"typed":False,"versioned":True,"request_id":"req-1"},False),({"typed":True,"versioned":False,"request_id":"req-1"},False),({"typed":True,"versioned":True,"request_id":""},False)])
def test_typed_request_gate(kwargs,expected): assert typed_execution_request_valid(**kwargs) is expected

def test_production_policy_and_hrb_are_mandatory():
    assert production_policy_admission_valid(production=True,policy_decision="ALLOW"); assert not production_policy_admission_valid(production=True,policy_decision=None); assert hrb_admission_valid(host_workload=True,admitted=True,placement_owner="FA3-AUTH-HOST-RESOURCE-BROKER-001"); assert not hrb_admission_valid(host_workload=True,admitted=True,placement_owner="FA3-PROVIDER-XYOPS-001"); assert not hrb_admission_valid(host_workload=True,admitted=False,placement_owner="FA3-AUTH-HOST-RESOURCE-BROKER-001")

def test_resource_limits_and_hardware_are_projection_only():
    assert resource_projection_valid(provider_native_limit=True,canonicalized=True,provider_is_authority=False); assert not resource_projection_valid(provider_native_limit=True,canonicalized=False,provider_is_authority=False); assert not resource_projection_valid(provider_native_limit=True,canonicalized=True,provider_is_authority=True); assert hardware_discovery_valid(host_workload=True,live_discovery=True,static_accelerator_placement=False); assert not hardware_discovery_valid(host_workload=True,live_discovery=False,static_accelerator_placement=False); assert not hardware_discovery_valid(host_workload=True,live_discovery=True,static_accelerator_placement=True)

def test_local_host_enforcement_requires_systemd_cgroup_v2(): assert local_enforcement_valid(local_host=True,systemd_cgroup_v2=True); assert not local_enforcement_valid(local_host=True,systemd_cgroup_v2=False)
def test_secret_and_credential_boundaries():
    assert secret_projection_valid(secret_refs=["secret-ref:ops/api"],raw_secret_values=[],provider_persisted_raw=False); assert not secret_projection_valid(secret_refs=["secret-ref:ops/api"],raw_secret_values=["plaintext"],provider_persisted_raw=False); assert not secret_projection_valid(secret_refs=["api-token"],raw_secret_values=[],provider_persisted_raw=False); assert credential_transport_valid(production=True,location="HEADER",short_lived=True,rotatable=True,identity_bound=True); assert not credential_transport_valid(production=True,location="QUERY",short_lived=True,rotatable=True,identity_bound=True); assert not credential_transport_valid(production=True,location="HEADER",short_lived=False,rotatable=True,identity_bound=True)
def test_least_privilege_is_exact_scope(): assert least_privilege_valid(granted={"run"},required={"run"}); assert not least_privilege_valid(granted={"run","admin"},required={"run"}); assert not least_privilege_valid(granted=set(),required={"run"})
def test_arbitrary_shell_and_http_require_policy():
    assert shell_execution_valid(arbitrary_shell=True,explicit_policy=True,bounded_executor=True); assert not shell_execution_valid(arbitrary_shell=True,explicit_policy=False,bounded_executor=True); assert not shell_execution_valid(arbitrary_shell=True,explicit_policy=True,bounded_executor=False); assert http_execution_valid(arbitrary_http=True,egress_policy=True,destination_admitted=True); assert not http_execution_valid(arbitrary_http=True,egress_policy=False,destination_admitted=True); assert not http_execution_valid(arbitrary_http=True,egress_policy=True,destination_admitted=False)
def test_execution_receipt_schema_is_required():
    receipt={key:None for key in {"request_id","workflow_id","job_id","provider","provider_version","executor","target","started_at","finished_at","exit_status","resource_admission","policy_decision","artifacts","logs","metrics","alerts","snapshots","incident_ids","provenance","evidence_hash"}}; assert execution_receipt_valid(receipt); receipt.pop("evidence_hash"); assert not execution_receipt_valid(receipt)
def test_retry_resume_terminal_control_evidence():
    assert retry_valid(retry=True,idempotency_classified=True,idempotency_key="idem-1"); assert not retry_valid(retry=True,idempotency_classified=False,idempotency_key="idem-1"); assert not retry_valid(retry=True,idempotency_classified=True,idempotency_key=None); assert resume_valid(resume=True,committed_checkpoint=True,provider_resume_receipt=False); assert resume_valid(resume=True,committed_checkpoint=False,provider_resume_receipt=True); assert not resume_valid(resume=True,committed_checkpoint=False,provider_resume_receipt=False); assert terminal_control_evidence_valid(cancelled=True,timed_out=False,aborted=False,evidence_written=True); assert not terminal_control_evidence_valid(cancelled=True,timed_out=False,aborted=False,evidence_written=False)
def test_supply_chain_rollback_and_capacity_pool_boundaries():
    assert supply_chain_valid(runtime_promotion=True,sbom=True,provenance=True,license_gate=True); assert not supply_chain_valid(runtime_promotion=True,sbom=False,provenance=True,license_gate=True); assert rollback_valid(mutating_production=True,rollback_path=True); assert not rollback_valid(mutating_production=True,rollback_path=False); assert capacity_pool_valid(declarative_policy=True,provider_is_resource_authority=False); assert not capacity_pool_valid(declarative_policy=True,provider_is_resource_authority=True)
