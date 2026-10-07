# FA3 MCP Current-Host Regression Gate

Applies to `FA3-MCP-CURRENT-HOST-001` and its parent authority `FA3-AUTH-MCP-GATEWAY-001`.

## Required assertions

| # | Assertion | Expected |
| --- | --- | --- |
| 1 | Gateway service health/readiness | PASS |
| 2 | One logical caller-facing gateway endpoint | PASS |
| 3 | Canonical capability discovery | PASS |
| 4 | Typed input validation rejects malformed request | DENY |
| 5 | Admitted provider invocation | PASS |
| 6 | Managed stdio adapter invocation where applicable | PASS |
| 7 | Security policy deny decision | DENY |
| 8 | Missing mandatory approval | DENY |
| 9 | Direct agent-to-provider bypass | DENY |
| 10 | Durable credential exposed in request/provider environment | DENY |
| 11 | HRB-governed execution without valid lease | DENY |
| 12 | HRB-governed execution with valid lease | PASS |
| 13 | Timeout/cancellation propagation | PASS |
| 14 | Required execution receipt emitted | PASS |
| 15 | Unhealthy provider is not dispatched to | PASS |
| 16 | Unknown capability/provider | DENY |
| 17 | GUI cannot self-promote ADAPTER-GATED target | PASS |
| 18 | Gateway attempts to become policy/resource/model/workflow authority | DENY |
| 19 | Registry/evidence reconciliation | PASS |

## Promotion rule

Promotion from `PENDING_CURRENT_HOST` to runtime-conformant status is fail-closed. Every mandatory assertion must have machine-verifiable or explicitly admitted evidence. Missing evidence is failure, not `N/A`, unless the canonical profile explicitly marks the feature as MUST-IF-USED and proves it is unused.

## Evidence minimum

Each assertion should record:

```yaml
check_id: MCP-CH-01
timestamp: RFC3339
host_profile: string
commit: git-sha
result: PASS|DENY|FAIL
command_or_test: string
evidence_ref: string
notes: optional
```

The gate does not permit a documentation-only PASS for runtime assertions.
