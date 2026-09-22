from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fa3_hardware_discovery import (
    AcceleratorBackendDescriptor,
    AcceleratorDeviceDescriptor,
    physical_core_key,
    summarize_cpu_topology,
)


class HardwareDiscoveryDescriptorTests(unittest.TestCase):
    def _entries(self):
        return [
            {
                "cpu_id": 0, "package_id": 0, "socket_id": 0, "die_id": 0,
                "cluster_id": None, "core_id": 0, "numa_node": 0,
                "online_sibling_cpus": [0, 1],
            },
            {
                "cpu_id": 1, "package_id": 0, "socket_id": 0, "die_id": 0,
                "cluster_id": None, "core_id": 0, "numa_node": 0,
                "online_sibling_cpus": [0, 1],
            },
            {
                "cpu_id": 2, "package_id": 0, "socket_id": 0, "die_id": 0,
                "cluster_id": None, "core_id": 1, "numa_node": 0,
                "online_sibling_cpus": [2, 3],
            },
            {
                "cpu_id": 3, "package_id": 0, "socket_id": 0, "die_id": 0,
                "cluster_id": None, "core_id": 1, "numa_node": 0,
                "online_sibling_cpus": [2, 3],
            },
        ]

    def test_logical_and_physical_counts_are_distinct(self):
        summary = summarize_cpu_topology(self._entries(), [0, 1, 2, 3])
        self.assertEqual(summary["logical_cpus_total"], 4)
        self.assertEqual(summary["physical_cores_total"], 2)
        self.assertEqual(summary["logical_cpus_visible"], 4)
        self.assertEqual(summary["physical_cores_visible"], 2)

    def test_full_and_partial_core_allocation_are_distinct(self):
        summary = summarize_cpu_topology(self._entries(), [0, 2, 3])
        self.assertEqual(summary["logical_cpus_visible"], 3)
        self.assertEqual(summary["physical_cores_visible"], 2)
        self.assertEqual(summary["physical_cores_fully_allocated"], 1)
        self.assertEqual(summary["physical_cores_partially_allocated"], 1)

    def test_physical_identity_includes_optional_die_and_cluster(self):
        entry = self._entries()[0]
        self.assertEqual(physical_core_key(entry), (0, 0, None, 0))
        changed = dict(entry, cluster_id=7)
        self.assertEqual(physical_core_key(changed), (0, 0, 7, 0))

    def test_unknown_accelerator_vendor_is_valid_discovery_output(self):
        device = AcceleratorDeviceDescriptor(
            discovery_id="pci:0000:00:01.0",
            kind="gpu",
            vendor="UNKNOWN",
            vendor_id="0xabcd",
            device_id="0x1234",
            pci_bdf="0000:00:01.0",
        )
        self.assertEqual(device.vendor, "UNKNOWN")
        self.assertFalse(device.workload_compatible)

    def test_physical_device_presence_does_not_imply_backend_usability(self):
        device = AcceleratorDeviceDescriptor(
            discovery_id="pci:0000:00:02.0",
            kind="gpu",
            vendor="INTEL",
            vendor_id="0x8086",
            device_id="0x0001",
            pci_bdf="0000:00:02.0",
        )
        self.assertFalse(device.workload_compatible)

        vulkan = AcceleratorBackendDescriptor(
            name="vulkan",
            backend_class="portable",
            available=True,
            evidence_sources=("synthetic-test",),
        )
        enriched = AcceleratorDeviceDescriptor(
            discovery_id=device.discovery_id,
            kind=device.kind,
            vendor=device.vendor,
            vendor_id=device.vendor_id,
            device_id=device.device_id,
            pci_bdf=device.pci_bdf,
            backends=(vulkan,),
        )
        self.assertTrue(enriched.workload_compatible)
        self.assertEqual(enriched.as_dict()["backends"][0]["class"], "portable")

    def test_translation_backend_is_explicit(self):
        zluda = AcceleratorBackendDescriptor(
            name="zluda",
            backend_class="translation",
            available=True,
            experimental=True,
        )
        self.assertEqual(zluda.as_dict()["class"], "translation")
        self.assertTrue(zluda.experimental)

    def test_translation_only_device_is_not_default_workload_compatible(self):
        zluda = AcceleratorBackendDescriptor(
            name="zluda",
            backend_class="translation",
            detected=True,
            available=True,
            binding_scope="DEVICE",
            experimental=True,
        )
        device = AcceleratorDeviceDescriptor(
            discovery_id="pci:0000:00:03.0",
            kind="gpu",
            vendor="AMD",
            vendor_id="0x1002",
            device_id="0x0002",
            pci_bdf="0000:00:03.0",
            backends=(zluda,),
        )
        self.assertFalse(device.workload_compatible)

    def test_invalid_backend_class_is_rejected(self):
        with self.assertRaises(ValueError):
            AcceleratorBackendDescriptor(
                name="invalid",
                backend_class="magic",
                available=True,
            )


if __name__ == "__main__":
    unittest.main()
