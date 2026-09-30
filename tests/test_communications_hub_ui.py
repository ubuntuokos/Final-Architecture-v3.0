import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class CommunicationsHubUiTests(unittest.TestCase):
    def test_qt6_standalone_build_contract(self):
        cmake=(ROOT/"apps/fa3-communications-hub/CMakeLists.txt").read_text()
        self.assertIn("Qt6",cmake)
        self.assertIn("qt_add_qml_module",cmake)
        self.assertIn("CommunicationsSharedSurface.qml",cmake)

    def test_shared_surface_is_full_and_embedded_capable(self):
        qml=(ROOT/"apps/fa3-communications-hub/qml/CommunicationsSharedSurface.qml").read_text()
        self.assertIn('property string surfaceMode: "EMBEDDED"',qml)
        self.assertIn('surfaceMode === "EMBEDDED"',qml)
        self.assertIn("openFullHubRequested",qml)
        self.assertIn("actionIntent",qml)

    def test_qml_has_no_direct_network_or_provider_execution(self):
        qml=(ROOT/"apps/fa3-communications-hub/qml/CommunicationsSharedSurface.qml").read_text()
        for token in ("XMLHttpRequest","WebSocket","QNetworkAccessManager","smtp://","imap://"):
            self.assertNotIn(token,qml)

    def test_canonical_ui_binding_denies_global_embedded_enumeration(self):
        data=json.loads((ROOT/"canonical/FA3-COMMUNICATIONS-CONTACTS-UI-BINDINGS-001.json").read_text())
        self.assertFalse(data["direct_qml_network_execution"])
        self.assertFalse(data["direct_provider_execution"])
        self.assertTrue(data["action_intent_only"])
        self.assertFalse(data["embedded"]["global_mailbox_enumeration"])
        self.assertFalse(data["embedded"]["global_address_book_enumeration"])
        self.assertEqual("CONTEXT_AND_PERMISSION_INTERSECTION",data["embedded"]["binding_rule"])

if __name__=="__main__":
    unittest.main()
