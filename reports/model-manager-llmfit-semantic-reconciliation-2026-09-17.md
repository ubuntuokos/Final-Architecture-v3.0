# FA3 Model Manager / llmfit clean semantic reconciliation — 2026-09-17

Status: operational reconciliation record; non-authoritative.

## Integration base

PR #151 was rebuilt from the current `main` baseline rather than mechanically rebasing its stale implementation. The old monolithic `Main.qml` and stale release projection were not restored.

## Preserved current-main semantics

- `FA3-MODEL-MANAGER-001` remains version `2.0.0` and keeps the existing OpenModelDB provider extension.
- Capability baseline remains 143; architectural authority delta is zero.
- Hardware observations emitted by llmfit are `OBSERVED_NON_AUTHORITATIVE` advisory fit inputs only.
- HRB remains the admission / placement / reservation / lease authority.
- Resource classes are derived from the declared workload.
- CPU + memory workloads do not require accelerator discovery or an accelerator lease.
- Accelerator workloads require a current, scope-bound HRB accelerator lease and preserve `FA3-ACCEL-GUARD-001` conflict semantics.
- Provider-local compatibility constraints cannot redefine the global FA3 hardware baseline.
- llmfit estimates are not runtime evidence and cannot self-promote.

## GUI materialization

The current Qt/QML Control Center is preserved. `LlmfitClient` is added as a `fa3Llmfit` context object and the existing `ModelsProvidersPage.qml` becomes the native Model Manager / Hardware Fit + Providers surface. No terminal, browser UI, QProcess, privileged command execution, or direct model execution is introduced.

Benchmark and placement controls create `DRAFT_NOT_SUBMITTED` ChangeSets carrying workload-resource-envelope semantics only.

## Service materialization

llmfit runs as a user-level headless service over `%t/fa3/llmfit.sock`. The pinned upstream release is installed with SHA-256 verification. The service does not require a TCP listener.

## Evidence boundary

Static CI and Qt reference build may validate materialization only. Live Unix-socket responses, real model loading, measured throughput/memory/context behavior, and production admission remain `PENDING_REAL_CURRENT_HOST_EXECUTION` until collected through the existing FA3 authority/evidence chain.
