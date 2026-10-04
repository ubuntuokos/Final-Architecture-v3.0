# CUDA-oriented portability and shared-function rule — 2026-10-04

## Scope

This rule applies in two places at the same time:

1. **FA3/CFA3 development** — donor analysis, design, planning, implementation, review and runtime admission.
2. **FA3/CFA3 product behavior** — hardware-aware backend selection, shared capability placement and user-visible compatibility/limitation reporting.

It extends the existing vendor-neutral Hardware Baseline, Hardware Safety Envelope, Host Resource Broker and Model Router boundaries. It does not create a new capability or authority and does not ban CUDA.

## Rule

Any donor, library, model, runtime component, algorithm or feature path that is **strongly CUDA-oriented** must undergo a target-hardware portability assessment before it may be integrated into an application or admitted for runtime execution.

The assessment must examine the actual target hardware and approved deployment targets. At minimum, NVIDIA, AMD and Intel are reference vendor families. When AMD or Intel hardware is a target, their viable execution alternatives must not be skipped merely because the upstream project is CUDA-first.

Candidate paths include:

- native backend;
- portable backend;
- translation or compatibility backend;
- independently admitted alternative implementation or provider.

No translation layer or framework claim establishes equivalence by itself.

## Required result

Each target-hardware/backend combination must be classified as exactly one of:

- **FULL_EQUIVALENCE** — required feature behavior is available;
- **FUNCTIONALLY_REDUCED** — usable, but one or more functions are missing, restricted or materially changed;
- **UNAVAILABLE** — the required function cannot be safely and correctly provided on that target.

The assessment must record target device/family, backend, feature coverage, known limitations, material performance or memory constraints when known, rights/runtime constraints, and HRB/Hardware Safety admission state.

## Shared-only placement

A strongly CUDA-oriented **functional core is shared-only**.

It may live only in a shared FA3/CFA3 layer, service or contract. Vendor-specific implementations are backend/provider adapters behind the shared contract.

Application-local code may contain only:

- UI integration;
- workflow adapters;
- application context;
- presentation;
- compatibility and limitation disclosure.

A separate CUDA-oriented functional core duplicated inside an individual application is forbidden unless an explicit reviewed exception is approved. An exception may not create a parallel hardware-placement or model-routing authority.

## Product UX

For **FUNCTIONALLY_REDUCED**, FA3/CFA3 must visibly tell the user:

- which target hardware is being used;
- which backend or alternative path was selected;
- which functions are missing or reduced;
- material performance or memory restrictions when known.

For **UNAVAILABLE**, the function must be disabled or shown as unavailable. The system must fail closed.

The system must never hide reduced functionality, claim full parity without evidence, or silently switch to CUDA, another accelerator, another provider, or cloud execution.

## Existing authorities

- Hardware discovery identifies devices and compatible execution paths.
- HRB remains the only resource placement/reservation/lease authority.
- Model Router remains the model/provider routing authority.
- Hardware Safety overrides performance optimization.
- Existing display-GPU restrictions remain unchanged.
- A static policy/gate PASS is not physical Current Host evidence.

## Baseline impact

- capability baseline: **175 unchanged**
- capability delta: **0**
- new architectural authority: **0**
- current-host runtime PASS claimed by this rule change: **no**
