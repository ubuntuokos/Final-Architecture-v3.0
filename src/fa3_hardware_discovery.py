#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
from typing import Any, Iterable


BACKEND_CLASSES = {"native", "portable", "translation"}

_VENDOR_NAMES = {
    "0x10de": "NVIDIA",
    "0x1002": "AMD",
    "0x8086": "INTEL",
}


def parse_cpu_list(value: str) -> list[int]:
    cpus: set[int] = set()
    for token in str(value or "").strip().split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"invalid CPU range: {token}")
            cpus.update(range(start, end + 1))
        else:
            cpus.add(int(token))
    return sorted(cpus)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _read_int(path: Path) -> int | None:
    raw = _read_text(path)
    if raw in (None, ""):
        return None
    try:
        return int(raw, 0)
    except ValueError:
        return None


def _current_cgroup_v2_dir() -> Path | None:
    mount = Path("/sys/fs/cgroup")
    if not mount.exists():
        return None
    try:
        lines = Path("/proc/self/cgroup").read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    relative = ""
    for line in lines:
        if line.startswith("0::"):
            relative = line[3:].lstrip("/")
            break
    return mount / relative if relative else mount


def effective_cpu_ids() -> list[int]:
    online_raw = _read_text(Path("/sys/devices/system/cpu/online"))
    online = set(parse_cpu_list(online_raw)) if online_raw else set(os.sched_getaffinity(0))
    affinity = set(os.sched_getaffinity(0))
    cgroup_dir = _current_cgroup_v2_dir()
    cpuset: set[int] | None = None
    if cgroup_dir is not None:
        cpuset_raw = _read_text(cgroup_dir / "cpuset.cpus.effective")
        if cpuset_raw:
            cpuset = set(parse_cpu_list(cpuset_raw))
    effective = online & affinity
    if cpuset is not None:
        effective &= cpuset
    return sorted(effective)


def _numa_node(cpu: int) -> int | None:
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}")
    for candidate in sorted(base.glob("node[0-9]*")):
        try:
            return int(candidate.name[4:])
        except ValueError:
            continue
    return None


def _topology_entry(cpu: int) -> dict[str, Any]:
    topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
    package_id = _read_int(topology / "physical_package_id")
    core_id = _read_int(topology / "core_id")
    if package_id is None or core_id is None:
        raise RuntimeError(f"cannot discover physical topology for CPU {cpu}")
    die_id = _read_int(topology / "die_id")
    cluster_id = _read_int(topology / "cluster_id")
    siblings_raw = _read_text(topology / "thread_siblings_list")
    siblings = parse_cpu_list(siblings_raw) if siblings_raw else [cpu]
    return {
        "cpu_id": cpu,
        "package_id": package_id,
        "socket_id": package_id,
        "die_id": die_id,
        "cluster_id": cluster_id,
        "core_id": core_id,
        "numa_node": _numa_node(cpu),
        "online_sibling_cpus": siblings,
    }


def physical_core_key(entry: dict[str, Any]) -> tuple[int, int | None, int | None, int]:
    package_id = entry.get("package_id", entry.get("socket_id"))
    if package_id is None:
        raise ValueError("CPU topology entry has no package/socket identity")
    return (
        int(package_id),
        None if entry.get("die_id") is None else int(entry["die_id"]),
        None if entry.get("cluster_id") is None else int(entry["cluster_id"]),
        int(entry["core_id"]),
    )


def summarize_cpu_topology(
    entries: Iterable[dict[str, Any]],
    effective_ids: Iterable[int],
) -> dict[str, Any]:
    rows = list(entries)
    effective = {int(cpu) for cpu in effective_ids}
    groups: dict[tuple[int, int | None, int | None, int], set[int]] = {}
    for entry in rows:
        groups.setdefault(physical_core_key(entry), set()).add(int(entry["cpu_id"]))

    visible_groups: dict[tuple[int, int | None, int | None, int], set[int]] = {}
    full = 0
    partial = 0
    for key, online_siblings in groups.items():
        visible = online_siblings & effective
        if not visible:
            continue
        visible_groups[key] = visible
        if visible == online_siblings:
            full += 1
        else:
            partial += 1

    packages = {key[0] for key in groups}
    dies = {(key[0], key[1]) for key in groups if key[1] is not None}
    clusters = {(key[0], key[1], key[2]) for key in groups if key[2] is not None}
    numa = {
        int(entry["numa_node"])
        for entry in rows
        if entry.get("numa_node") is not None
    }
    max_threads = max((len(cpus) for cpus in groups.values()), default=0)
    return {
        "packages_total": len(packages),
        "dies_total": len(dies) if dies else None,
        "clusters_total": len(clusters) if clusters else None,
        "physical_cores_total": len(groups),
        "logical_cpus_total": len(rows),
        "physical_cores_visible": len(visible_groups),
        "logical_cpus_visible": len({int(row["cpu_id"]) for row in rows} & effective),
        "physical_cores_fully_allocated": full,
        "physical_cores_partially_allocated": partial,
        "max_threads_per_core": max_threads,
        "numa_domains_total": len(numa),
    }


def discover_cpu_topology() -> dict[str, Any]:
    online_raw = _read_text(Path("/sys/devices/system/cpu/online"))
    if not online_raw:
        online = sorted(os.sched_getaffinity(0))
    else:
        online = parse_cpu_list(online_raw)
    entries = [_topology_entry(cpu) for cpu in online]
    effective = effective_cpu_ids()
    summary = summarize_cpu_topology(entries, effective)
    return {
        "schema": "fa3.cpu-topology-descriptor.v2",
        "source": "LIVE_SYSFS_AFFINITY_CGROUPV2",
        "online_logical_cpus": online,
        "effective_logical_cpus": effective,
        "logical_processors": entries,
        "summary": summary,
    }


@dataclass(frozen=True)
class AcceleratorBackendDescriptor:
    name: str
    backend_class: str
    available: bool
    detected: bool = True
    binding_scope: str = "DEVICE"
    runtime_version: str | None = None
    driver_version: str | None = None
    framework_backends: tuple[str, ...] = ()
    experimental: bool = False
    evidence_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("backend name must be non-empty")
        if self.backend_class not in BACKEND_CLASSES:
            raise ValueError(f"unsupported backend class: {self.backend_class}")
        if self.binding_scope not in {"DEVICE", "HOST_UNBOUND"}:
            raise ValueError(f"unsupported backend binding scope: {self.binding_scope}")
        if self.available and (not self.detected or self.binding_scope != "DEVICE"):
            raise ValueError("available backend must be detected and bound to one device")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["class"] = value.pop("backend_class")
        return value


@dataclass(frozen=True)
class AcceleratorDeviceDescriptor:
    discovery_id: str
    kind: str
    vendor: str
    vendor_id: str
    device_id: str
    health: str = "DISCOVERED"
    stable_device_id: str | None = None
    device_uuid: str | None = None
    pci_bdf: str | None = None
    numa_node: int | None = None
    kernel_driver: str | None = None
    device_nodes: tuple[str, ...] = ()
    memory_bytes: int | None = None
    architecture: str | None = None
    backends: tuple[AcceleratorBackendDescriptor, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.discovery_id.strip():
            raise ValueError("discovery_id must be non-empty")
        if not self.kind.strip():
            raise ValueError("accelerator kind must be non-empty")
        if not self.vendor_id.strip() or not self.device_id.strip():
            raise ValueError("vendor_id and device_id are required")

    @property
    def workload_compatible(self) -> bool:
        return any(
            backend.available and backend.backend_class in {"native", "portable"}
            for backend in self.backends
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["backends"] = [backend.as_dict() for backend in self.backends]
        value["workload_compatible"] = self.workload_compatible
        return value


def _driver_name(device: Path) -> str | None:
    driver = device / "driver"
    try:
        if driver.exists():
            return driver.resolve().name
    except OSError:
        return None
    return None


def _device_nodes_for_bdf(bdf: str) -> tuple[str, ...]:
    nodes: set[str] = set()
    for pattern in ("/sys/class/drm/renderD*", "/sys/class/accel/accel*"):
        for sys_node in Path("/").glob(pattern.lstrip("/")):
            try:
                resolved = (sys_node / "device").resolve()
            except OSError:
                continue
            if bdf in {resolved.name, *(part for part in resolved.parts)}:
                if sys_node.parent.name == "drm":
                    nodes.add(f"/dev/dri/{sys_node.name}")
                elif sys_node.parent.name == "accel":
                    nodes.add(f"/dev/accel/{sys_node.name}")
    return tuple(sorted(nodes))


def discover_accelerator_devices() -> list[AcceleratorDeviceDescriptor]:
    devices: list[AcceleratorDeviceDescriptor] = []
    pci_root = Path("/sys/bus/pci/devices")
    if not pci_root.is_dir():
        return devices
    for device in sorted(pci_root.iterdir()):
        class_code = (_read_text(device / "class") or "").lower()
        if not (class_code.startswith("0x03") or class_code.startswith("0x12")):
            continue
        vendor_id = (_read_text(device / "vendor") or "unknown").lower()
        device_id = (_read_text(device / "device") or "unknown").lower()
        vendor = _VENDOR_NAMES.get(vendor_id, "UNKNOWN")
        numa = _read_int(device / "numa_node")
        if numa is not None and numa < 0:
            numa = None
        kind = "gpu" if class_code.startswith("0x03") else "accelerator"
        bdf = device.name
        devices.append(
            AcceleratorDeviceDescriptor(
                discovery_id=f"pci:{bdf}",
                kind=kind,
                vendor=vendor,
                vendor_id=vendor_id,
                device_id=device_id,
                pci_bdf=bdf,
                numa_node=numa,
                kernel_driver=_driver_name(device),
                device_nodes=_device_nodes_for_bdf(bdf),
            )
        )
    return devices
