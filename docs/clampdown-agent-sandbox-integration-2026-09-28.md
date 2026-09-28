# Clampdown-derived containment patterns in FA3 Agent Sandbox

**Scope:** selective, FA3-native security-pattern implementation for CAP-028; not installation of Clampdown, provider activation, a new sandbox application, or a new architectural authority.

**Upstream reference:** [89luca89/clampdown](https://github.com/89luca89/clampdown), inspected revision 4ba28fda0c5e7df729c251d49e5736bfdb53f6f7. The upstream README declares GPL-3.0-only. No upstream code has been copied. Any source-level import would need separate license, provenance, distribution and security review. Registry record: FA3-DONOR-CLAMPDOWN-001.

## Existing architecture is preserved

- FA3-AGENT-SANDBOX-001 remains the mandatory isolation profile, not a parallel Clampdown sandbox.
- Untrusted native OCI code stays with gVisor, subject to verified host compatibility. WASI-native tools stay with the existing preferred Wasmtime route. Hardened rootless OCI alone is not an arbitrary-code fallback.
- FA3-UNIFIED-ACTION-FABRIC-001 authorizes mutating tool actions; the Central MCP Gateway mediates tool access. An agent must never receive Docker or Podman control sockets.
- The HRB owns CPU, memory and any accelerator reservations. The Model Router remains the sole model/provider/runtime routing authority. The existing Secret Broker owns credential issuance; container environment passthrough is not a secret-delivery method.
- Temporal remains the durable workflow authority. All observations and promotion claims remain subordinate to the canonical evidence and current-host gates.

## Materialized, executable code

The FA3-native source module src/fa3_nested_tool_guard.py independently implements a default-deny, allowlisted *pre-launch compiler*. It accepts only a fixed schema (fa3.nested-tool-request.v1) and a separate admission record already verified by the trusted FA3 caller. It rejects:

- unpinned images, arbitrary Podman flags, host/privileged namespaces, capabilities, writable base rootfs, direct runtime sockets or inherited credentials;
- unapproved workspace paths, unverified seccomp digests, default-allow seccomp profiles, unbounded CPU/memory/PID requests, missing HRB scope;
- direct public egress, implicit egress, model/tool gateway bypass, sandbox downgrade and current-host incompatibility.

A successful compile creates a rootless Podman argument array with gVisor runsc, a digest-pinned preloaded image, pull disabled, network disabled, immutable seccomp profile binding, all capabilities dropped, private namespaces, no-new-privileges, a read-only base rootfs, a single approved *ephemeral* workspace bind and an isolated /tmp.

**Important limitation:** the compiler neither executes Podman nor verifies kernel Landlock/seccomp/gVisor activation; the admission record must be authenticated by the trusted caller. The existing workload runtime and current-host promotion gates remain responsible for enforcing that precondition. No signed runtime receipt is created by compiling a plan. The command must be launched by a trusted executor, not by the agent.

The existing fa3_agent_workload.compile_nested_tool_action() API exposes the compiler through the workload surface, validates the parent workload and rejects cross-task launch requests and direct runtime flag injection. The permanent Runtime Hardening reference gate now includes an executable positive/negative regression pair, and the Agent Workload CI runs tests.test_nested_tool_guard.

## Explicitly not adopted from Clampdown

Clampdown's elevated-capability sidecar and default-allow internet access for nested tool containers are not carried into FA3. Clampdown does not become a provider, runtime, scheduler, resource authority or network policy authority. Landlock and seccomp-notify designs remain separately reviewable references; this patch does not claim to deploy either kernel mechanism outside Podman's verified seccomp and existing gVisor controls. A new privileged sidecar is not introduced.

## Hardware Audit

This reference compiler requires no accelerator and is independent of NVIDIA, AMD, Intel and other vendor-specific APIs. CPU-only remains valid; device inventory cardinality remains 0..N. No PCI/driver setting, GPU index, power state, device identity, kernel configuration or port is changed by this patch. The only CPU/memory limits compiled are projections of a previously admitted HRB lease; the compiler cannot allocate resources.

## Evidence and remaining runtime work

- Static evidence: Python unit tests for valid plans and rejection of dangerous nested container requests, plus the Runtime Hardening gate.
- Runtime evidence not yet claimed: a trusted executor invoking the compiler after signature/freshness/scope validation; actual kernel and gVisor enforcement; no agent-visible runtime socket; nested-container escape, credential, network and mount negative tests on a current host.
- Production activation remains pending, with no silent fallback. A future admitted UAF/Podman executor must use this pre-launch compiler (or an equivalent separately admitted strict validator), bind its observed argv/runtime/namespace status into signed current-host receipts, and pass the unchanged canonical 19-point promotion gate.

This implementation does not modify the FA3 Video Editor, any native creative project file, KDE/Wayland/X11 behavior, or the AdGuardHome port.
