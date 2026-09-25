from __future__ import annotations
import copy, datetime as dt, unittest
from pathlib import Path
from src.fa3_supply_chain_admission import evaluate_license_policy, evaluate_receipt
from src.fa3_provider_runtime import validate_runtime_environment,select_runtime_class,ProviderRuntimeError
from src.fa3_upstream_patchset import evaluate_patchset
from src.fa3_hrb_composite_lease import evaluate_reservation_plan,derive_child_lease,cascade_revocation,CompositeLeaseError,CompositeLeaseIssuer,RESOURCE_ORDER
from src.fa3_hrb_lease_lifecycle import LeaseKey, LeaseKeyring
from src.fa3_supply_runtime_hardening_gate import gate,regressions

ROOT=Path(__file__).resolve().parents[1]
H="a"*64; C="b"*40

class SupplyRuntimeHardeningTests(unittest.TestCase):
    def test_gate(self): self.assertEqual("PASS",gate(ROOT)["result"])
    def test_regressions(self): self.assertEqual("PASS",regressions()["result"])
    def test_license_policy_is_automatic_and_fail_closed(self):
        policy={"admitted_exact_spdx":["MIT","Apache-2.0"]}
        self.assertEqual("PASS",evaluate_license_policy("MIT",["MIT"],policy)["result"])
        self.assertEqual("FAIL",evaluate_license_policy("GPL-3.0-only",["GPL-3.0-only"],policy)["result"])
        self.assertEqual("FAIL",evaluate_license_policy("MIT OR Apache-2.0",["MIT","Apache-2.0"],policy)["result"])

    def test_runtime_selection(self):
        self.assertEqual("VENV",select_runtime_class(reproducible_venv=True,native_abi_complexity=True))
        self.assertEqual("OCI",select_runtime_class(reproducible_venv=False,native_abi_complexity=True))
        with self.assertRaises(ProviderRuntimeError): select_runtime_class(reproducible_venv=False,native_abi_complexity=False)
    def test_conda_refused(self):
        p={"schema":"fa3.provider-runtime-environment.v1","provider_id":"P","execution_class":"VENV","hrb_admission_required":True,"secret_delivery":"NONE","host_global_reconfiguration":False,"upstream_uninstall_required":False,"supply_chain_receipt_status":"PASS","venv":{"manager":"uv","dependency_lock_sha256":H,"environment_identity_sha256":H,"system_site_packages":False,"note":"conda"}}
        self.assertEqual("FAIL",validate_runtime_environment(p)["result"])
    def test_reference_only_cannot_promote(self):
        r={"schema":"fa3.upstream-patch-set.v1","disposition":"REFERENCE_ONLY","runtime_admission":True,"license_disposition":{}}
        self.assertEqual("FAIL",evaluate_patchset(r,today=dt.date(2026,9,25))["result"])
    def test_atomic_hold_and_wait_refused(self):
        p={"schema":"fa3.resource-reservation-plan.v1","authority_id":"FA3-AUTH-HOST-RESOURCE-BROKER-001","atomic_admission":True,"hold_and_wait":True,"acquisition_order":list(RESOURCE_ORDER),"queue_policy":{"max_waiters":8,"deadline_seconds":30},"workloads":[{"id":"a","resources":{}}],"accelerators":[]}
        self.assertEqual("FAIL",evaluate_reservation_plan(p,{k:0 for k in ("cpu_threads","ram_bytes","vram_bytes","io_bytes_per_second","network_bytes_per_second")})["result"])
    def test_child_scope_and_revocation(self):
        keyring=LeaseKeyring([LeaseKey("test",b"x"*32)],"test")
        parent={"lease_id":"p","generation":1,"issuer":"FA3-AUTH-HOST-RESOURCE-BROKER-001","state":"ACTIVE","expires_at_utc":"2099-01-01T01:00:00Z","resources":{"cpu_threads":8,"ram_bytes":16,"vram_bytes":12},"child_allocated_resources":{},"accelerator_assignments":[{"stable_id":"GPU-x"}],"scope":{},"authentication":{}}
        parent["authentication"]=keyring.sign(parent)
        req={"lease_id":"c","issued_at_utc":"2099-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:30:00Z","resources":{"cpu_threads":4,"ram_bytes":8,"vram_bytes":6},"accelerator_assignments":[{"stable_id":"GPU-x"}],"scope":{}}
        c=derive_child_lease(parent,req,keyring=keyring); self.assertFalse(c["may_mint_child_lease"]); keyring.verify(c)
        parent["state"]="REVOKING"; parent["authentication"]=keyring.sign(parent)
        active=copy.deepcopy(c); active["state"]="ACTIVE"; active["authentication"]=keyring.sign(active)
        casc=cascade_revocation(parent,[active],keyring=keyring); self.assertEqual("REVOKING",casc[0]["state"]); keyring.verify(casc[0])
        parent["state"]="ACTIVE"; parent["authentication"]=keyring.sign(parent)
        bad=copy.deepcopy(req); bad["resources"]["vram_bytes"]=13
        with self.assertRaises(CompositeLeaseError): derive_child_lease(parent,bad,keyring=keyring)
        forged=copy.deepcopy(parent); forged["authentication"]["mac"]="0"*64
        with self.assertRaises(CompositeLeaseError): derive_child_lease(forged,req,keyring=keyring)

    def test_stateful_child_budget_accounting(self):
        keyring=LeaseKeyring([LeaseKey("test",b"y"*32)],"test")
        parent={"lease_id":"p2","generation":1,"issuer":"FA3-AUTH-HOST-RESOURCE-BROKER-001","state":"ACTIVE","expires_at_utc":"2099-01-01T01:00:00Z","resources":{"cpu_threads":8,"ram_bytes":16,"vram_bytes":12},"accelerator_assignments":[{"stable_id":"GPU-x"}],"scope":{},"authentication":{}}
        parent["authentication"]=keyring.sign(parent)
        issuer=CompositeLeaseIssuer(keyring); issuer.register_parent(parent)
        base={"issued_at_utc":"2099-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:30:00Z","resources":{"cpu_threads":4,"ram_bytes":8,"vram_bytes":6},"accelerator_assignments":[{"stable_id":"GPU-x"}],"scope":{}}
        a=issuer.derive("p2",{**copy.deepcopy(base),"lease_id":"a"})
        b=issuer.derive("p2",{**copy.deepcopy(base),"lease_id":"b"})
        self.assertEqual(12,issuer.allocation("p2")["vram_bytes"])
        with self.assertRaises(CompositeLeaseError):
            issuer.derive("p2",{**copy.deepcopy(base),"lease_id":"c"})
        issuer.release("p2","a")
        c=issuer.derive("p2",{**copy.deepcopy(base),"lease_id":"c"})
        keyring.verify(c)
        casc=issuer.revoke_parent("p2")
        self.assertTrue(all(x["state"]=="REVOKING" for x in casc))
        for row in casc:keyring.verify(row)

    def test_child_scope_cannot_exceed_parent(self):
        keyring=LeaseKeyring([LeaseKey("scope",b"z"*32)],"scope")
        parent={"lease_id":"scope-parent","generation":1,"issuer":"FA3-AUTH-HOST-RESOURCE-BROKER-001","state":"ACTIVE","expires_at_utc":"2099-01-01T01:00:00Z","resources":{"cpu_threads":8,"ram_bytes":16,"vram_bytes":12},"accelerator_assignments":[],"scope":{"workload_id":["a","b"]},"authentication":{}}
        parent["authentication"]=keyring.sign(parent)
        req={"lease_id":"scope-child","issued_at_utc":"2099-01-01T00:00:00Z","expires_at_utc":"2099-01-01T00:30:00Z","resources":{"cpu_threads":1,"ram_bytes":1,"vram_bytes":0},"accelerator_assignments":[],"scope":{"workload_id":"c"}}
        with self.assertRaises(CompositeLeaseError):derive_child_lease(parent,req,keyring=keyring)

if __name__=="__main__": unittest.main()
