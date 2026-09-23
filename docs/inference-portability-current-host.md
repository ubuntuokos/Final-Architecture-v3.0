# FA3 inference portability — current-host pre-admission

This surface performs read-only provider inventory and safe runtime smoke tests on the labeled FA3 current-host runner.

It **does not install or upgrade** OpenVINO, ONNX Runtime, TensorRT or TensorRT-RTX, does not download models, does not mint HRB leases, and does not promote providers.

## Evidence levels

- `ABSENT_OPTIONAL`: provider is not installed; this is not a global FA3 failure.
- `PRESENT_UNADMITTED`: provider is discoverable but has no executable admission evidence.
- `CPU_SMOKE_PASS_PRODUCTION_ROUTE_PENDING`: an already-installed CPU-capable provider executed an ephemeral local smoke model. This is component evidence only.
- `ACCELERATOR_RUNTIME_PRESENT_HRB_E2E_PENDING`: an accelerator provider/EP is present, but no DEVICE-bound HRB execution evidence was produced.

A production provider runtime PASS requires the canonical Model Router resolution, provider adapter, backend compatibility evidence, and—when accelerated—a fresh HRB lease binding the exact device plus execution path. The pre-admission probe cannot grant those authorities.

The 2026-09-23 current-host decision is intentionally non-obligation-bearing and does not reopen the already proven global 429/429 capability closure.
