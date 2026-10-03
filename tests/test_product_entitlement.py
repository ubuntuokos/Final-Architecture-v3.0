# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json, tempfile, unittest
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from fa3_product_entitlement import load, resolve, validate, _findings

class ProductEntitlementTests(unittest.TestCase):
    def test_repository_model_passes(self):
        self.assertEqual(validate(ROOT),[])

    def test_story_and_render_requires_professional_without_3d_app_unlock(self):
        out=resolve(ROOT,["fa3.story-screenplay","fa3.render-manager"])
        self.assertEqual(out["status"],"ENTITLEMENT_INTENT_READY")
        self.assertEqual(out["minimum_required_operating_level"],"PROFESSIONAL")
        self.assertIn("FA3-COMP-3D-CORE",out["required_platform_dependencies"])
        self.assertEqual(out["selected_applications"],["fa3.story-screenplay","fa3.render-manager"])
        self.assertNotIn("fa3.3d-dcc-studio",out["selected_applications"])
        self.assertEqual(out["implicit_application_unlocks"],[])

    def test_single_story_application_can_run_at_enterprise(self):
        out=resolve(ROOT,["fa3.story-screenplay"],requested_level="ENTERPRISE")
        self.assertEqual(out["status"],"ENTITLEMENT_INTENT_READY")
        self.assertEqual(out["effective_operating_level"],"ENTERPRISE")
        self.assertEqual(out["selected_applications"],["fa3.story-screenplay"])

    def test_lan_feature_raises_level_to_studio(self):
        out=resolve(ROOT,["fa3.story-screenplay"],features=["LAN_DISTRIBUTED_EXECUTION"])
        self.assertEqual(out["minimum_required_operating_level"],"STUDIO")

    def test_requested_level_below_minimum_fails_closed(self):
        out=resolve(ROOT,["fa3.render-manager"],requested_level="PERSONAL")
        self.assertEqual(out["status"],"REJECTED")
        self.assertEqual(out["reason"],"REQUESTED_LEVEL_BELOW_MINIMUM")

    def test_unknown_application_fails_closed(self):
        out=resolve(ROOT,["fa3.unknown"])
        self.assertEqual(out["status"],"REJECTED")

    def test_pack_is_optional_and_individual_selection_remains_valid(self):
        individual=resolve(ROOT,["fa3.photo-image-studio"])
        bundled=resolve(ROOT,[],packs=["FA3-PACK-CREATIVE-MEDIA-001"])
        self.assertEqual(individual["status"],"ENTITLEMENT_INTENT_READY")
        self.assertFalse(individual["bundle_required"])
        self.assertGreater(len(bundled["selected_applications"]),1)

    def test_technical_component_cannot_be_user_facing(self):
        model=load(ROOT)
        mutated=deepcopy(model)
        mutated["deps"]["platform_components"][0]["user_facing_application"]=True
        findings=_findings(mutated,None)
        self.assertTrue(any(x["code"]=="TECHNICAL_DEPENDENCY_MAY_NOT_BE_USER_FACING_APPLICATION" for x in findings))

    def test_portfolio_state_is_separate_from_provisioning_states(self):
        lifecycle=json.loads((ROOT/"canonical/FA3-APP-LIFECYCLE-001.json").read_text())
        portfolio=load(ROOT)["portfolio"]
        self.assertTrue(set(lifecycle["states"]).isdisjoint(set(portfolio["portfolio_states"])))
        self.assertFalse(portfolio["provisioning_state_is_portfolio_state"])

if __name__=="__main__": unittest.main()
