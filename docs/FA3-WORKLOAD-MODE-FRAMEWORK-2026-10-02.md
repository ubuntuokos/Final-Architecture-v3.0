# Workload Mode Framework — canonical materialization plan and boundary

This materializes the conversation-approved shared framework as a standalone-first project while preserving the FA3 capability baseline of 175 and creating no new FA3 architectural authority.

## Architecture

AIMode and RenderMode are domains of one Workload Mode broker. GameMode remains an optional independent Linux peer. When FA3 is present, the bidirectional handshake changes the effective physical resource authority to the existing Host Resource Broker. The Workload Mode broker may describe workload intent and coexistence state but may not mint FA3 HRB leases or directly override HRB placement.

External applications are first-class workloads and remain external. Their integration state is OBSERVED, COORDINATED or MANAGED. A Blender/Bforartists reference add-on reports actual render lifecycle rather than treating application startup as render activity.

## Global UI visibility

Every supported primary graphical FA3 surface inherits one shared Workload Mode indicator from the Control Center shell. The indicator displays effective mode, authority, FA3 state, GameMode state, safety, conflicts, resource pressure and workload count. Critical degraded/safety/conflict/authority-loss states cannot be hidden and are never represented by color alone.

## Mandatory FA3 installation

Workload Mode is mandatory in FULL, HOBBY, MINIMAL, HEADLESS, SINGLE_HOST, MULTI_HOST, CPU_ONLY and accelerator-enabled FA3 profiles. It is not a first-use application. A missing, disabled, unhealthy or protocol-incompatible component forces explicit SAFE_DEGRADED state; FA3 resource-changing operations fail closed while safe non-resource functionality may continue.

GameMode itself is not a mandatory dependency. GameMode interoperability support is mandatory.

## Safety and coexistence

No automatic overclock, voltage increase, power-limit escalation, thermal/fan bypass, unknown hardware mutation or automatic persistent sysctl mutation is permitted. Existing tuners must be observed/coordinated, never silently uninstalled or disabled.

The initial source materialization is deliberately read/state-oriented. Physical systemd transient-scope resource mutation, direct cgroup-v2 fallback, NVIDIA NVML, AMD SMI, Intel Level Zero Sysman, GameMode coexistence under real load and current-host FA3↔HRB execution remain separate physical evidence obligations.

## Research provenance boundary

GameMode, System76 Scheduler, OpenCue and Flamenco were reviewed as analysis/reference candidates during design. They were **not owner-marked with `donornak` in this conversation**, therefore this change does not register them in the canonical donor registry, adopt their code, or create donor usage edges. Any future source/code adoption requires the normal owner donor marking, license/provenance/security review and usage edge.

## Release semantics

Static gates can prove only schema, authority, coexistence, source and UI wiring invariants. They cannot promote physical current-host runtime. Physical receipts remain PENDING until executed on the admitted host.
