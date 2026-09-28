# FA3 System One Reflex Runtime

The System One Reflex Runtime is an extension of `FA3-DECISION-FABRIC-001`, not a new architectural authority.

It materializes the reusable parts of HarnessRouter/SystemOneHarness as the `BOUNDED_ACTION` contract:

`observe/bounded state -> compile finite actions -> Model Router -> typed System One answers -> confidence gate -> authorization-ready intent or handoff`

The runtime deliberately stops before execution.

## Authority boundary

- model/provider selection: `FA3-AUTH-MODEL-ROUTER-001`
- resource placement/leases: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- secrets: central Secret Broker projection
- MCP/tool capability boundary: `FA3-AUTH-MCP-GATEWAY-001`
- final execution policy: the existing consumer/application authority
- System One Reflex Runtime: no authority; it only returns a bounded intent

A confidence result is evidence about a choice, not permission to execute it.

## Finite action space

Every action is a normal Decision Fabric candidate. Candidate metadata declares:

- `risk`: `read`, `write`, or `destructive`
- `parameters`: a map whose values are one of `choices`, `candidates`, `flag`, or `levels`

Free-text parameters fail closed. Dynamic `candidates` must already be supplied by the calling FA3 authority in `constraints.parameter_candidates`. The model cannot add actions or parameter values.

The provider compiles the selected action, all of its finite parameters, `finish`, `escalate`, and `goal_reached` into one System One request.

## Confidence gate

Defaults:

- read: 0.50
- write: 0.60
- destructive: 0.80
- finish: 0.50

The gate uses the weakest probability required by the selected transition: the action choice plus every used parameter decision. A caller may override thresholds explicitly, but values must stay inside 0..1.

If the action clears the threshold, the runtime returns `READY_FOR_AUTHORIZATION`. It still has `authority=false`, `execution_performed=false`, and requires the existing policy owner to authorize any effect.

Low confidence returns a structured handoff for a System Two path or human review. Explicit `escalate` does the same. `finish` is accepted only when the action confidence and the separate `goal_reached` probability both clear the finish threshold.

## Provider path

`FA3-PROVIDER-SYSTEM-ONE-DECISION-001` has no physical model pin and no direct vendor endpoint. It sends the native decision request only through the central Model Router logical route `fa3-decision-system-one`.

The current Jev-specific provider remains supported for existing structured Decision Fabric contracts. The new provider is the provider-neutral route for bounded reflex steps and may be backed by Jev or a future admitted System One model without changing applications.

## Upstream provenance

Pattern source:

- repository: HarnessRouter/SystemOneHarness
- pinned review commit: `ab8e8f08b4a6268c0633a474423d556599ee06a4`
- license: Apache-2.0
- FA3 disposition: `PATTERN_SOURCE`, no vendored upstream source file

FA3 replaces upstream direct provider transport, secret loading, resource choices, and environment execution with existing FA3 authorities.

## Hardware Audit

The contract is vendor- and accelerator-neutral. CPU-only operation remains valid. CUDA, ROCm, oneAPI and NPU runtimes are optional provider/runtime details admitted through Model Router and HRB, never requirements of the reflex contract.
