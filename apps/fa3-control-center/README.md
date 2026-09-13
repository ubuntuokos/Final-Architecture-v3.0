# FA3 Control Center

Native Qt 6/QML reference GUI for FINAL ARCHITECTURE v3.0.

The application is deliberately a **projection and intent surface**, not a new FA3 authority. It reads canonical/evidence state, shows host telemetry and Model Manager recommendations, and can create local `DRAFT_NOT_SUBMITTED` typed ChangeSet JSON files. It does not directly perform model placement, production admission, privileged host changes, or canonical promotion.

## Views

Command Center; Projects & Workspaces; AI Studio; Agents & Workflows; Models & Providers; Architecture Explorer; Resources; Security & Approvals; Observability; Evidence; Integrations; System.

AI Studio includes Image, Video, Animation, 3D/VFX, Audio, Music, and Story/Screenplay projections.

## Model Manager / llmfit integration

`Models & Providers` contains a native **Model Manager** tab. It consumes the optional `FA3-PROVIDER-LLMFIT-001` provider through a local Unix domain socket and renders hardware-aware model-fit recommendations directly in Qt/QML. Normal operation does not launch a terminal, browser, upstream TUI, or upstream web dashboard.

Default transport:

```text
$XDG_RUNTIME_DIR/fa3/llmfit.sock
```

The GUI client can be pointed at another local socket for diagnostics with:

```bash
FA3_LLMFIT_SOCKET=/path/to/llmfit.sock ./build/fa3-control-center/fa3-control-center
```

The Model Manager tab exposes use-case, runtime and context filters and shows fit, quantization, memory, estimated throughput, runtime and estimate-confidence data. These values are **advisory estimates**, not production runtime evidence.

The `Benchmark ChangeSet` and `Placement ChangeSet` actions create typed local drafts only. Benchmark execution, accelerator placement, admission and promotion remain delegated to the existing FA3 authority chain, including the Model Router, Host Resource Broker and Unified Evidence authority.

Install/activate the pinned headless provider as the desktop user with:

```bash
deployment/model-manager/llmfit/install.sh
```

The installer deploys a user-level `fa3-llmfit.service` and serves llmfit over the Unix socket above; no TCP listener is required by the GUI integration.

## Build

Qt 6 `Quick`, `QuickControls2` and `Network` development components are required.

```bash
cmake -S apps/fa3-control-center -B build/fa3-control-center -GNinja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fa3-control-center
FA3_REPO_ROOT="$PWD" ./build/fa3-control-center/fa3-control-center
```

For Kubuntu/Ubuntu use `deployment/fa3-gui/install.sh` for the GUI itself.

## Authority boundary

Mutating intent is expressed as a draft typed ChangeSet and must be submitted through an existing FA3 adapter/approval path. The GUI must never bypass identity, policy, MCP/tool mediation, workflow durability, model routing, Host Resource Broker admission, systemd/cgroup enforcement, evidence/provenance, secrets, or promotion authorities.

`llmfit` is therefore a Model Manager **advisory provider**, not a model router, scheduler, placement authority, runtime-conformance authority, or evidence-promotion authority.
