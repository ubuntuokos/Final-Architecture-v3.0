# FA3 Control Center

Native Qt 6/QML reference GUI for FINAL ARCHITECTURE v3.0.

The application is deliberately a **projection and intent surface**, not a new FA3 authority. It reads canonical/evidence state, shows host telemetry, and can create local `DRAFT_NOT_SUBMITTED` typed ChangeSet JSON files. It does not execute privileged commands or mutate the canonical repository.

## Views

Command Center; Projects & Workspaces; AI Studio; Agents & Workflows; Models & Providers; Architecture Explorer; Resources; Security & Approvals; Observability; Evidence; Integrations; System.

AI Studio includes Image, Video, Animation, 3D/VFX, Audio, Music, and Story/Screenplay projections.

## Persistent resource status strip

The Control Center renders a compact 38 px bottom status strip across all views. It continuously projects CPU utilization, RAM utilization plus used/total capacity, GPU utilization plus VRAM/temperature when measurable, and NPU detection/utilization when measurable. Unknown accelerator utilization is rendered as `N/A` or `—`, never as a fabricated 0%.

The strip also derives a local read-only pressure summary (`NORMAL`, `WARN`, `CRITICAL`) for operator awareness. That summary is advisory only: host-resource admission remains owned by `FA3-AUTH-HOST-RESOURCE-BROKER-001`, and enforcement remains systemd unified cgroup v2.

GPU discovery is provider-neutral. NVIDIA telemetry uses an exact read-only `nvidia-smi` query when present; Linux DRM/sysfs is used as a fallback for supported GPU metrics. Linux NPU/accelerator detection uses the DRM accel class/device projection when available.

## Build

```bash
cmake -S apps/fa3-control-center -B build/fa3-control-center -GNinja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fa3-control-center
FA3_REPO_ROOT="$PWD" ./build/fa3-control-center/fa3-control-center
```

For Kubuntu/Ubuntu use `deployment/fa3-gui/install.sh`.

## Authority boundary

Mutating intent is expressed as a draft typed ChangeSet and must be submitted through an existing FA3 adapter/approval path. The GUI must never bypass identity, policy, MCP/tool mediation, workflow durability, model routing, Host Resource Broker admission, systemd/cgroup enforcement, evidence/provenance, secrets, or promotion authorities.
