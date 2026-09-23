from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from fa3_model_router_current_host_gate import gate


def receipt(head: str, include_evidence: bool = True) -> dict:
    provider_id="FA3-PROVIDER-LM-STUDIO-MODEL-001"
    binding={
        "provider_id":provider_id,
        "runtime_id":"lmstudio-openai-loopback",
        "model":"runtime-model",
        "selection":"RUNTIME_DISCOVERED",
        "provider_failover_performed":False,
    }
    routes=("fa3-text-primary","fa3-text-secondary","fa3-pageindex-index","fa3-pageindex-reason")
    value={
        "schema":"fa3.model-router-current-host-receipt.v1",
        "authority":"FA3-AUTH-MODEL-ROUTER-001",
        "gate_id":"FA3-MODEL-ROUTER-CURRENT-HOST-GATESET-001",
        "result":"PASS",
        "provider_neutral":True,
        "endpoint":"http://127.0.0.1:4000",
        "logical_routes":list(routes),
        "route_bindings":{route:dict(binding,route=route) for route in routes},
        "route_probes":{route:{"result":"PASS"} for route in routes},
        "physical_backend_pinned":False,
        "physical_model_pinned":False,
        "runtime_selected":True,
        "service_active":True,
        "selection_receipt_verified":True,
        "captured_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "repository_head":head,
        "full_429_runtime_closure_claim":False,
        "global_release_promotion_claim":False,
        "global_promotion_claim":False,
    }
    if include_evidence:
        value["provider_admission_evidence_sha256"]={provider_id:"a"*64}
    return value


class TestModelRouterCurrentHostGate(unittest.TestCase):
    def run_gate(self, value: dict) -> dict:
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            path=root/"receipt.json"
            path.write_text(json.dumps(value),encoding="utf-8")
            with patch("fa3_model_router_current_host_gate.subprocess.check_output", return_value="test-head\n"):
                return gate(root,path)

    def test_provider_admission_evidence_binding_required(self):
        result=self.run_gate(receipt("test-head",include_evidence=False))
        self.assertEqual(result["result"],"FAIL")
        self.assertTrue(any(f["code"]=="MRH-015" for f in result["findings"]))

    def test_valid_provider_admission_evidence_binding_passes(self):
        result=self.run_gate(receipt("test-head",include_evidence=True))
        self.assertEqual(result["result"],"PASS",result["findings"])

    def test_provider_failover_or_promotion_overclaim_fails(self):
        value=receipt("test-head",include_evidence=True)
        route=next(iter(value["route_bindings"]))
        value["route_bindings"][route]["provider_failover_performed"]=True
        value["global_release_promotion_claim"]=True
        result=self.run_gate(value)
        self.assertEqual(result["result"],"FAIL")
        codes={f["code"] for f in result["findings"]}
        self.assertIn("MRH-016",codes)
        self.assertIn("MRH-017",codes)


if __name__=="__main__":
    unittest.main()
