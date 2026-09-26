import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from fa3_hardware_portability_gate import (
    CAPABILITY_COUNT,
    REFERENCE_PLATFORM_FAMILIES,
    REFERENCE_VENDOR_FAMILIES,
    evaluate,
    portable_hardware_floor_valid,
    scan_repository,
)

class HardwarePortabilityGateTests(unittest.TestCase):
    def test_repository_gate_passes(self):
        result=evaluate(ROOT)
        self.assertEqual("PASS",result["result"],result)
        self.assertEqual(CAPABILITY_COUNT,result["capability_count"])
        self.assertEqual("FORBIDDEN",result["accelerator_floor"]["vendor_pin"])
        self.assertEqual("FORBIDDEN",result["accelerator_floor"]["runtime_api_pin"])
        self.assertEqual(0,result["accelerator_floor"]["minimum_device_count"])
        self.assertTrue(result["accelerator_floor"]["cpu_only_host_conforms"])
        self.assertFalse(result["accelerator_floor"]["cpu_only_workload_requires_lease"])
        self.assertFalse(result["current_host_runtime_promotion_claim"])
        self.assertEqual("MANDATORY_FAIL_CLOSED",result["hardware_safety"]["policy"])
        self.assertEqual("FORBIDDEN",result["hardware_safety"]["unsafe_or_unknown_mutation"])
        self.assertFalse(result["hardware_safety"]["installer_override"])
        self.assertFalse(result["hardware_safety"]["expert_mode_override"])

    def test_vendor_neutral_reference_families(self):
        self.assertTrue({"NVIDIA","AMD","INTEL"} <= REFERENCE_VENDOR_FAMILIES)
        self.assertIn("NVIDIA_DGX",REFERENCE_PLATFORM_FAMILIES)
        for vendor in ("NVIDIA","AMD","INTEL"):
            self.assertTrue(portable_hardware_floor_valid(
                cpu_packages=1, physical_cores_per_qualifying_cpu=8,
                accelerator_count=1, accelerator_vendor=vendor,
            ))

    def test_vendor_specific_capability_is_not_global_floor(self):
        self.assertTrue(portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_qualifying_cpu=8,
            gpu_count=1, gpu_vendor="AMD", gpu_compute_capability=0.0,
        ))
        self.assertFalse(portable_hardware_floor_valid(
            cpu_packages=1, physical_cores_per_qualifying_cpu=8,
            accelerator_count=1, accelerator_vendor="AMD", workload_compatible=False,
            accelerator_required=True,
        ))

    def test_floor_rejects_only_global_minimum_failures(self):
        self.assertFalse(portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=7,accelerator_count=1))
        self.assertTrue(portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=0))
        self.assertFalse(portable_hardware_floor_valid(cpu_packages=1,physical_cores_per_qualifying_cpu=8,accelerator_count=0,accelerator_required=True))
        self.assertTrue(portable_hardware_floor_valid(cpu_packages=4,physical_cores_per_qualifying_cpu=64,accelerator_count=16,accelerator_vendor="FUTURE_VENDOR"))

    def test_canonical_profile_has_no_vendor_or_runtime_pin(self):
        obj=json.loads((ROOT/"canonical/profiles/FA3-HARDWARE-BASELINE-001.json").read_text(encoding="utf-8"))
        accelerator=obj["portable_minimum"]["accelerator"]
        self.assertEqual(0,accelerator["qualifying_device_count_min"])
        self.assertTrue(accelerator["cpu_only_host_conforms"])
        self.assertFalse(accelerator["cpu_only_workload_requires_lease"])
        self.assertEqual("FORBIDDEN",accelerator["vendor_pin"])
        self.assertEqual("FORBIDDEN",accelerator["global_runtime_api_pin"])
        self.assertTrue(accelerator["global_cuda_compute_capability_floor"].startswith("FORBIDDEN"))
        self.assertTrue({"NVIDIA","AMD","INTEL"} <= set(accelerator["supported_reference_vendor_families"]))
        self.assertIn("NVIDIA_DGX",accelerator["supported_reference_platform_families"])

    def test_discovery_contract_distinguishes_cpu_and_backend_dimensions(self):
        obj=json.loads((ROOT/"canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json").read_text(encoding="utf-8"))
        self.assertEqual("1.5.0",obj["version"])
        cpu=obj["descriptor_schemas"]["cpu"]
        accel=obj["descriptor_schemas"]["accelerator"]
        self.assertIn("physical_cores_fully_allocated",cpu["required_counts"])
        self.assertIn("physical_cores_partially_allocated",cpu["required_counts"])
        self.assertEqual(
            set(obj["discovery_semantics"]["backend_classes"]),
            {"native","portable","translation"},
        )
        self.assertFalse(obj["discovery_semantics"]["device_presence_implies_workload_compatibility"])
        self.assertFalse(obj["discovery_semantics"]["unknown_accelerator_vendor_is_error"])
        self.assertEqual(
            accel["unknown_vendor_policy"],
            "VALID_DISCOVERY_RESULT_NOT_GLOBAL_ADMISSION_FAILURE",
        )
        binding=accel["backend_binding_semantics"]
        self.assertTrue(binding["available_true_requires"]=="DETECTED_AND_DEVICE_BOUND")
        self.assertEqual(
            binding["host_unbound_admission"],
            "FORBIDDEN_UNTIL_PROVIDER_OR_RUNTIME_PROVES_DEVICE_BINDING",
        )
        self.assertIn(
            "UNBOUND_HOST_BACKEND_DETECTION_MUST_NOT_AUTHORIZE_DEVICE_ADMISSION",
            obj["invariants"],
        )


    def test_hardware_safety_envelope_is_fail_closed_and_non_bypassable(self):
        profile=json.loads((ROOT/"canonical/profiles/FA3-HARDWARE-BASELINE-001.json").read_text(encoding="utf-8"))
        contract=json.loads((ROOT/"canonical/contracts/FA3-HARDWARE-DISCOVERY-CONTRACTS-001.json").read_text(encoding="utf-8"))
        enforcement=json.loads((ROOT/"canonical/hardware-portability-enforcement.json").read_text(encoding="utf-8"))
        decision=json.loads((ROOT/"canonical/decisions/FA3-DEC-HARDWARE-SAFETY-2026-09-26.json").read_text(encoding="utf-8"))

        safety=profile["hardware_safety_envelope"]
        self.assertEqual("MANDATORY_FAIL_CLOSED",safety["policy"])
        self.assertTrue(safety["vendor_supported_operating_envelope_required"])
        self.assertEqual("NO_MUTATION_FAIL_CLOSED",safety["unknown_safe_range"])
        self.assertFalse(safety["installer_override"])
        self.assertFalse(safety["expert_mode_override"])
        self.assertFalse(safety["user_override_bypass"])

        mutation=contract["hardware_mutation_safety"]
        self.assertEqual("REJECT_MUTATION",mutation["unknown_safe_range"])
        self.assertEqual("REJECT_MUTATION",mutation["out_of_supported_range"])
        self.assertEqual("FORBIDDEN",mutation["installer_and_expert_override"])

        self.assertTrue(enforcement["hardware_safety_fail_closed"])
        self.assertEqual("FA3-DEC-HARDWARE-SAFETY-2026-09-26",enforcement["hardware_safety_decision_id"])
        self.assertEqual(40,enforcement["mandatory_rule_count"])
        self.assertEqual(
            "MANDATORY_FAIL_CLOSED_HARDWARE_SAFETY_ENVELOPE_NO_UNSAFE_HARDWARE_TUNING",
            decision["decision"],
        )
        self.assertFalse(decision["enforcement"]["user_override_may_bypass_safety_envelope"])

    def test_runtime_fixed_vendor_lists_are_blocking(self):
        for line in (
            'CUDA_VISIBLE_DEVICES="0,1"\n',
            'ROCR_VISIBLE_DEVICES="0,1"\n',
            'ZE_AFFINITY_MASK="0.0"\n',
            'DEVICE="0000:3b:00.0"\n',
        ):
            with self.subTest(line=line), tempfile.TemporaryDirectory() as td:
                root=Path(td); (root/"apps").mkdir()
                (root/"apps"/"bad.py").write_text(line,encoding="utf-8")
                audit=scan_repository(root)
                self.assertEqual("FAIL",audit["result"],audit)

    def test_apps_qml_cpp_are_audited(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"apps").mkdir()
            (root/"apps"/"bad.qml").write_text('property string gpu: "RTX 4070"\n',encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("FAIL",audit["result"],audit)

    def test_legacy_host_reference_is_blocking_even_outside_runtime(self):
        old_cpu = "E5-" + "26" + "96 v4"
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"docs"; p.mkdir()
            (p/"legacy.md").write_text("Historical machine: " + old_cpu + "\n",encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("FAIL",audit["result"],audit)
            self.assertEqual(1,audit["legacy_repository_reference_count"])

    def test_legacy_host_reference_embedded_in_identifier_is_blocking(self):
        old_host = "NOT_" + "T" + "79" + "10" + "_EVIDENCE"
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"canonical"; p.mkdir()
            (p/"bad.json").write_text(json.dumps({"claim": old_host}),encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("FAIL",audit["result"],audit)
            self.assertEqual(1,audit["legacy_repository_reference_count"])

    def test_legacy_global_accelerator_floor_tokens_are_blocking(self):
        old_rules = (
            "ACCELERATOR_CARDINALITY_DYNAMIC_" + "1_TO_N",
            "GPU_CARDINALITY_IS_LIVE_DISCOVERED_DYNAMIC_" + "1_TO_N",
        )
        for old_rule in old_rules:
            with self.subTest(old_rule=old_rule), tempfile.TemporaryDirectory() as td:
                root=Path(td); p=root/"canonical"; p.mkdir()
                (p/"bad.json").write_text(json.dumps({"invariant": old_rule}),encoding="utf-8")
                audit=scan_repository(root)
                self.assertEqual("FAIL",audit["result"],audit)

    def test_reference_evidence_hardware_tuple_is_non_normative(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"canonical"/"references"; p.mkdir(parents=True)
            (p/"fixture.md").write_text("Reference evidence only: Xeon Xeon Gold 6430, RTX 4070, 0000:3b:00.0.",encoding="utf-8")
            audit=scan_repository(root)
            self.assertEqual("PASS",audit["result"])
            self.assertGreaterEqual(audit["non_normative_hardware_mentions"],2)

if __name__=="__main__":
    unittest.main()
