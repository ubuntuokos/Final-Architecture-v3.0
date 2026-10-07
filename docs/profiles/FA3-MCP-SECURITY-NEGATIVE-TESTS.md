# FA3 MCP negative security conformance

Mandatory negative tests for the current-host Central MCP/Capability Gateway:

- unknown identity -> DENY;
- unknown capability -> DENY;
- unknown/unadmitted provider -> DENY;
- malformed typed arguments -> DENY;
- missing policy decision -> DENY;
- denied policy decision -> DENY;
- required approval missing/expired -> DENY;
- HRB-governed workload without valid lease -> DENY;
- inline durable secret where reference is required -> DENY;
- out-of-scope secret reference -> DENY;
- filesystem path outside admitted scope -> DENY;
- network destination outside admitted scope -> DENY;
- direct client-to-provider bypass -> DENY;
- provider attempts authority promotion -> DENY;
- GUI/discovery attempts CONNECTED promotion without E2E evidence -> DENY;
- evidence-required execution when receipt path is unavailable -> DENY.

Each denial must emit a non-secret-bearing decision receipt where the Evidence policy requires one.
