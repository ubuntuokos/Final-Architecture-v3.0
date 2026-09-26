# FA3 Software Coexistence & Host Non-Interference

Status: canonical candidate under CAP-175. Capability count remains 175.

## Rule

Every ordinary FA3 application, provider, adapter, integration, derived implementation, service, desktop component and local runtime must coexist with independently installed upstream/original software and independently installed alternatives. There is no grandfathering for previously VERIFIED/CLOSED components.

Ordinary components must not require upstream removal, replace or shadow upstream binaries, take ownership of upstream configuration or user data, silently seize ports, sockets, MIME handlers or protocol handlers, or perform persistent global runtime/environment mutation.

## Classification

- Ordinary Application: full coexistence required.
- Provider / Runtime: coexistence plus runtime isolation required.
- Local Service: service, port and IPC isolation required.
- System-Level Authority: explicit authority, conflict detection, previous-state capture, controlled mutation, rollback and recovery evidence are required instead of mechanically applying ordinary-app rules.

## Namespace defaults

FA3-owned state uses FA3 namespaces: ~/.config/fa3, ~/.local/share/fa3, ~/.cache/fa3, $XDG_RUNTIME_DIR/fa3 or /run/fa3, and fa3-* systemd units.

Upstream-native files, project formats and independently installed applications remain upstream-owned. Interoperability is explicit and removable.

## Hardware Audit

The policy is vendor-neutral, supports CPU-only operation where the component itself permits CPU-only operation, recognizes 0..N accelerators, and must not hard-code NVIDIA/CUDA, KDE-only or Wayland-only assumptions. Wayland remains preferred where applicable; X11 compatibility remains supported.

## Evidence truth boundary

A manifest, schema, static auditor result or GitHub Actions PASS is not a current-host runtime PASS. Physical current-host proof is required for install, start, simultaneous execution where meaningful, resource/port/service/path/process inspection, reboot where applicable, FA3 uninstall with upstream verification, restoration and reciprocal verification.

Missing or unsafe-to-collect physical evidence remains PENDING_CURRENT_HOST. It must never be converted to PASS by documentation.

## AdGuardHome

FA3 must not move the existing AdGuardHome port merely to make an FA3 service fit. The FA3 service must adapt using dynamic endpoints, Unix sockets or another non-conflicting mechanism.

## Model Router

FA3-AUTH-MODEL-ROUTER-001 remains the sole model-routing authority. Ollama, LM Studio, llama.cpp and other external runtimes remain independently usable applications; FA3 interacts through provider adapters and must not mutate their global environment.

## Current implementation

- Policy: canonical/FA3-COEXISTENCE-POLICY-001.json
- Footprint schema: canonical/contracts/FA3-COEXISTENCE-FOOTPRINT-001.schema.json
- Evidence schema: canonical/contracts/FA3-COEXISTENCE-EVIDENCE-001.schema.json
- Static auditor: src/fa3_coexistence_audit.py
- Gate record: canonical/FA3-GATE-COEXISTENCE-001.json
- Command: ./bin/fa3-enforce coexistence
- CI: .github/workflows/fa3-software-coexistence.yml

Retroactive component coverage and physical current-host evidence are intentionally tracked separately until proven.


## Dynamic canonical provider count

The FA3 capability baseline is fixed at 175. The canonical provider count is deliberately not fixed.

The provider count is derived from valid records under `canonical/providers/*.json`. There is no architectural maximum, release quota or numeric target that may force creation, deletion, merging or splitting of provider identities.

A new canonical provider increases the count automatically when it satisfies the normal provider identity, admission, coexistence and evidence requirements. Removing or superseding a provider changes the derived count only through the corresponding canonical lifecycle transition.

The authoritative policy is `canonical/FA3-PROVIDER-COUNT-POLICY-001.json`; `src/fa3_provider_count.py` produces the derived count report.
