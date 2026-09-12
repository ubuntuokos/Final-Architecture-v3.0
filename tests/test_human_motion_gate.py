import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fa3_human_motion_gate import PATHS, combined_gate, gem_x_gate, soma_x_gate


class HumanMotionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def copy_fixture(self, target: Path) -> None:
        for rel in set(PATHS.values()):
            src = self.root / rel
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())

    def mutate_and_gate(self, key, mutation, gate):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            self.copy_fixture(target)
            path = target / PATHS[key]
            data = json.loads(path.read_text())
            mutation(data)
            path.write_text(json.dumps(data))
            return gate(target)

    def test_reference_gates_pass(self):
        self.assertEqual("PASS", soma_x_gate(self.root)["result"])
        self.assertEqual("PASS", gem_x_gate(self.root)["result"])
        self.assertEqual("PASS", combined_gate(self.root)["result"])

    def test_soma_source_license_drift_fails(self):
        report = self.mutate_and_gate("soma_provider", lambda d: d["upstream"].update(source_code_license="UNKNOWN"), soma_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_soma_optional_model_license_bypass_fails(self):
        report = self.mutate_and_gate("soma_provider", lambda d: d["licensing"].update(separate_license_receipt_required=False), soma_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_soma_authority_claim_fails(self):
        report = self.mutate_and_gate("soma_provider", lambda d: d["authority_boundaries"].update(human_identity=True), soma_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_source_model_license_collapse_fails(self):
        report = self.mutate_and_gate("gem_provider", lambda d: d["model_policy"].update(source_code_license_does_not_substitute_for_model_license=False), gem_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_runtime_auto_download_fails(self):
        report = self.mutate_and_gate("gem_provider", lambda d: d["model_policy"].update(automatic_huggingface_download_in_production=True), gem_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_silent_cpu_fallback_fails(self):
        report = self.mutate_and_gate("gem_provider", lambda d: d["execution"].update(silent_cpu_fallback=True), gem_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_quality_gate_drift_fails(self):
        report = self.mutate_and_gate("gem_provider", lambda d: d["quality_gate"].update(dynamic_camera_trajectory_required=False), gem_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_runtime_promotion_without_receipt_fails(self):
        report = self.mutate_and_gate("gem_runtime", lambda d: d.update(production_admitted=True), gem_x_gate)
        self.assertEqual("FAIL", report["result"])

    def test_gem_authority_claim_fails(self):
        report = self.mutate_and_gate("gem_provider", lambda d: d["authority_boundaries"].update(model_registry=True), gem_x_gate)
        self.assertEqual("FAIL", report["result"])


if __name__ == "__main__":
    unittest.main()
