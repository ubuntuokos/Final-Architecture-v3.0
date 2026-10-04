# SPDX-License-Identifier: Apache-2.0
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fa3_local_ai_model_development_gate import gate

class LocalAiModelDevelopmentPolicyTests(unittest.TestCase):
    def test_gate_passes(self):
        report=gate(ROOT)
        self.assertEqual(report['result'],'PASS',report['findings'])
        self.assertEqual(report['capability_count'],175)
        self.assertFalse(report['runtime_promotion_claim'])
        self.assertFalse(report['physical_current_host_pass_claimed'])

    def test_policy_preserves_choice_and_authorities(self):
        p=json.loads((ROOT/'canonical/FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001.json').read_text(encoding='utf-8'))
        self.assertEqual(p['existing_authorities']['model_provider_routing'],'FA3-AUTH-MODEL-ROUTER-001')
        self.assertEqual(p['existing_authorities']['resource_admission_placement_reservation_lease'],'FA3-AUTH-HOST-RESOURCE-BROKER-001')
        self.assertTrue(p['application_ui_contract']['all_admitted_compatible_candidates_visible'])
        self.assertTrue(p['application_ui_contract']['manual_compatible_alternative_selection'])
        self.assertFalse(p['application_ui_contract']['application_may_hide_non_primary_eligible_candidates'])

    def test_hardware_and_download_are_bounded(self):
        p=json.loads((ROOT/'canonical/FA3-LOCAL-AI-MODEL-DEVELOPMENT-POLICY-001.json').read_text(encoding='utf-8'))
        self.assertTrue(p['hardware_aware_selection']['cpu_only_path_mandatory'])
        self.assertFalse(p['hardware_aware_selection']['display_gpu_policy']['default_ai_compute'])
        self.assertTrue(p['optional_download_install']['user_initiated_only'])
        self.assertFalse(p['optional_download_install']['automatic_download'])
        self.assertTrue(p['optional_download_install']['model_manager_mediated'])

if __name__=='__main__':
    unittest.main()
