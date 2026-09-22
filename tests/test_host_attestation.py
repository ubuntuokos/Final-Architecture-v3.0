from __future__ import annotations

import copy
import platform
import socket
import unittest

from src.fa3_host_attestation import build_artifact, utcnow, validate_artifact


def attestation_fixture() -> dict:
    return {
        "schema": "fa3.host-attestation.v1",
        "host_attestation_id": "FA3-HOST-TEST",
        "captured_at": utcnow(),
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "os_release": {"ID": "test"},
        "cpu_model": "test-cpu",
        "cpu_microcode": ["test"],
        "cpu_topology": {"schema": "fa3.cpu-topology-descriptor.v2"},
        "numa_topology": {"nodes": 1},
        "memory_total_bytes": 1024,
        "accelerators": [],
        "driver_versions": {},
        "runtime_versions": {"python": platform.python_version()},
        "pcie_topology": [],
        "storage_identity": {"status": "OBSERVED"},
        "thermal_power_state": {"status": "UNAVAILABLE"},
        "collector_version": "test",
        "secret_collection": "PROHIBITED",
    }


class HostAttestationTests(unittest.TestCase):
    def test_digest_bound_artifact_passes(self) -> None:
        artifact = build_artifact(attestation_fixture())
        findings, reference, _ = validate_artifact(artifact)
        self.assertEqual([], findings)
        self.assertRegex(reference, r"^sha256:[0-9a-f]{64}$")

    def test_tampered_attestation_is_rejected(self) -> None:
        artifact = build_artifact(attestation_fixture())
        tampered = copy.deepcopy(artifact)
        tampered["attestation"]["kernel"] = "tampered"
        findings, _, _ = validate_artifact(tampered, require_current_host=False)
        self.assertIn("host attestation artifact digest mismatch", findings)
        self.assertIn("host attestation reference does not bind the canonical attestation digest", findings)

    def test_identifier_is_not_accepted_as_digest_reference(self) -> None:
        artifact = build_artifact(attestation_fixture())
        artifact["host_attestation_ref"] = "FA3-HOST-TEST"
        findings, _, _ = validate_artifact(artifact)
        self.assertIn("host attestation reference must be sha256:<64 lowercase hex>", findings)


if __name__ == "__main__":
    unittest.main()
