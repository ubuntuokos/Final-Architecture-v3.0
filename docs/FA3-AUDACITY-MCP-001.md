# FA3 Audacity MCP / CAP-124

## Final disposition

CAP-124 already defines **Audacity Native MCP Audio Editing, Repair & Utility Processing**. This materialization does not add a capability or an architectural authority.

- Audacity is a required-supported human waveform repair / utility editor reference. Ardour remains the primary human audio finishing DAW provider.
- `xDarkzx/Audacity-MCP` is the primary replaceable MCP control reference for Audacity 3.x at immutable reference `ef7612eb6766ee96d630783d64c1ce94d602dc9e`.
- `Dream-Pixels-Forge/audacity-mcp` is an optional local DSP / measurable before-after QA pattern source at immutable reference `9d812922e46f504f91cca48338ed68511f8d4243`.
- Audacity 4 is **not admitted through the legacy `mod-script-pipe` provider**. The provider fails closed until a stable admitted interface is available. No implicit GUI-click fallback is allowed.
- The Audacity 4 companion fork is not a baseline dependency.
- OpenVINO remains the existing optional FA3 inference provider; it does not become an Audacity, STT, routing, resource or evidence authority.

## Software coexistence

FA3 does **not** execute the upstream Audacity-MCP installer in managed mode. The upstream installer can enable `mod-script-pipe` in Audacity configuration and configure Claude Desktop; both are host/application configuration mutations outside the FA3 adapter namespace.

FA3 uses an isolated, namespaced adapter runtime. It detects the supported Audacity automation interface and reports missing configuration, but does not silently rewrite Audacity or third-party client configuration.

## Authority path

`Agent / FA3 application -> FA3-AUTH-MCP-GATEWAY-001 -> policy-filtered Audacity adapter -> admitted Audacity automation interface`

AI/model-backed audio operations additionally use the Model Router and HRB. Deterministic non-model DSP does not need a model route, but still remains under resource, policy and evidence governance.

## Hardware Audit

- CPU-only operation is mandatory.
- Accelerators are `0..N` and vendor-neutral.
- Fixed CPU/GPU/NPU/NUMA placement is forbidden.
- Accelerator execution requires HRB admission.
- Display-GPU use never implies compute entitlement.
- Wayland is preferred; X11 remains supported; the adapter is desktop-environment-neutral.

## Mutation safety

Original source audio and `.aup3` projects are preserved by default. Destructive changes require a checkpoint, overwrite/delete defaults to deny, recording/microphone activation requires authenticated approval, and export paths are canonicalized against policy allowlists.

## Evidence boundary

Hosted CI proves only the canonical static governance contract. It does **not** claim Audacity current-host runtime promotion. Real runtime promotion requires separate current-host E2E evidence.
