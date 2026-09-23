# FA3 Decision Fabric

Canonical profile: `FA3-DECISION-FABRIC-001`

The Decision Fabric provides bounded semantic judgments to existing FA3 authorities. It does not execute actions, grant permissions, acquire resources or secrets, admit providers/models/agents, or become a routing authority.

## Authority boundary

- Model routing: `FA3-AUTH-MODEL-ROUTER-001`
- MCP/capability boundary: `FA3-AUTH-MCP-GATEWAY-001`
- Resource admission/placement/lease: `FA3-AUTH-HOST-RESOURCE-BROKER-001`
- Security: existing FA3 security policy plane
- Source truth: `FA3-JOURNAL-001` and original artifacts
- Decision Fabric: advisory structured judgment only

Every result records `authority=false` and `candidate_set_expanded=false`.

## Contracts

`SELECT_ONE`, `BOOLEAN`, `SCORE`, `RANK`, `MULTI_LABEL`, `RELEVANCE`, `STOP_CONTINUE`.

The caller must provide the complete pre-authorized candidate set. A provider response that refers to a candidate outside that set is rejected fail-closed.

## Providers

### Deterministic rules

`FA3-PROVIDER-DECISION-RULES-001` is the mandatory reference provider. It needs no network, secret, GPU, NPU, CUDA, ROCm or vendor-specific runtime.

### Local semantic provider

`FA3-PROVIDER-DECISION-LOCAL-001` is optional. It may access a model only through the central Model Router using a logical route. It must not contain a physical provider or model pin. Any accelerator resource is requested through HRB; CPU-only operation remains supported.

### Jev provider

`FA3-PROVIDER-JEV-DECISION-001` is optional and externally admitted. Applications never call Jev directly.

Runtime enablement requires all of:

- explicit policy/admission;
- `FA3_JEV_ENABLE=1`;
- Secret Broker-projected `TYPESAFE_API_KEY`;
- runtime-selected `FA3_JEV_MODEL`.

There is no silent local-to-cloud fallback.

## Rollout

Semantic decision points start in `SHADOW`.

Promotion sequence:

`SHADOW -> ADVISORY -> ACTIVE`

Promotion evidence includes agreement, false-allow, false-deny, uncertainty, decision stability, latency, provider failure and fallback behavior. High-risk security decisions may remain permanently advisory.

## Context Selection

`FA3-CONTEXT-SELECTION-001` uses `PROTECTED`, `ACTIVE`, `HIDDEN`, and `ARCHIVED`.

`HIDDEN` and `ARCHIVED` never mean deleted. Canonical decisions, explicit user constraints/corrections, security evidence, errors, commands, provenance, current-host evidence, unresolved blockers and approval records are protected. The original Journal/artifact remains authoritative.

## External Project Radar

The Jev ecosystem source is stored under:

`research/external-project-radar/jev/upstream/<commit>/`

The snapshot must be pinned to an immutable upstream commit. Upstream listing or upstream source-review status is not FA3 verification.

Disposition states:

- `IMPLEMENTED`
- `CODE_CANDIDATE`
- `PATTERN_SOURCE`
- `REFERENCE`
- `BLOCKED_LICENSE`
- `BLOCKED_SECURITY`
- `SUPERSEDED`

External code may be copied only after per-project license, provenance, security, architecture and distribution review. Unknown/problematic license means pattern reuse only.

## New-project adoption

Every new FA3 profile/provider or material capability extension must carry an `FA3-DECISION-FABRIC-ASSESSMENT-001` assessment with one of:

`REQUIRED`, `RECOMMENDED`, `OPTIONAL`, `NOT_APPLICABLE`, `PROHIBITED`.

The assessment must identify candidate source, final policy owner, failure policy, deterministic-first analysis, Project Radar review and Hardware Audit compliance.

## Operator commands

Static canonical gate:

`./bin/fa3-enforce decision-fabric`

Current-host positive/negative/rollback evidence:

`./bin/fa3-decision-current-host`

Project Radar validation/normalization:

`./bin/fa3-jev-radar`

One bounded decision request:

`./bin/fa3-decision --request request.json`

## Current-host semantics

Current-host PASS proves the Decision Fabric runtime and its positive/negative/rollback boundaries on the real `fa3-current-host` runner. It does not automatically admit the optional Jev provider and does not create a global FA3 production-promotion claim.

The optional external Jev E2E is a separate provider-admission obligation.

## GUI

FA3 Control Center surfaces:

- Decision Fabric
- Decision Inspector
- Project Radar
- Context Inspector

These are inspection/projection surfaces. The GUI does not self-approve or directly execute a model/tool decision.
