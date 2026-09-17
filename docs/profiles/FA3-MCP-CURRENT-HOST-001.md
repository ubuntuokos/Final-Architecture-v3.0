# FA3-MCP-CURRENT-HOST-001 — Current-Host Central MCP/Capability Gateway Runtime Projection

- **Status:** CANONICAL-PROJECTION / P0 / MUST
- **Parent authority:** `FA3-AUTH-MCP-GATEWAY-001`
- **Scope:** current-host runtime materialization
- **Authority rule:** this profile introduces **no new authority**. It materializes the existing Central MCP/Capability Gateway authority on the current host.

## 1. Purpose

Provide one production execution boundary for agent-operable tools and capabilities on the FA3 workstation. MCP, native application adapters, plugins, controlled REST/API adapters, shell/file adapters and other admitted tool providers are exposed through the same typed mediation boundary.

The gateway is the canonical authority for:

- capability/tool registration and exposure;
- typed invocation and dispatch;
- provider/adapter mediation;
- MCP transport handling and compatibility adaptation;
- enforcement of externally supplied policy decisions at the tool boundary;
- execution receipts and invocation telemetry emission.

The gateway is **not** the authority for durable orchestration, security-policy authorship, identity, secrets, model routing, host resource scheduling or evidence retention.

## 2. Authority boundaries

| Concern | Canonical owner | Gateway relationship |
| --- | --- | --- |
| Tool/capability mediation | `FA3-AUTH-MCP-GATEWAY-001` | OWNER |
| Durable workflow | Temporal / workflow authority | participant/consumer |
| Policy | Security Governance / Policy Plane | PEP only |
| Identity | Identity authority | validates/propagates context |
| Secrets | Central Secret Broker | consumes opaque references only |
| CPU/GPU/RAM placement and lease | Host Resource Broker (HRB) | requests and verifies leases |
| Model/provider selection | Model Router / model capability authority | not owner |
| Evidence/provenance retention | Evidence/Observability authority | emits receipts/events |
| Canonical architecture registry | Canonical Registry | projects metadata; no authority transfer |

Any implementation that moves one of these authorities into the MCP Gateway is non-conformant.

## 3. Mandatory runtime topology

```text
FA3 UI / Agents / Temporal tasks
             |
             v
+----------------------------------+
| Central MCP / Capability Gateway |
| FA3-AUTH-MCP-GATEWAY-001         |
+----------------+-----------------+
                 |
     +-----------+-----------+
     |           |           |
     v           v           v
 MCP server   Native app   Controlled
 adapter      adapter      API/tool adapter
```

Production-mode direct agent-to-provider execution that bypasses the gateway is **DENY** unless an explicit canonical break-glass profile exists.

## 4. Current-host service contract

A conforming implementation MUST provide:

1. a single logical loopback gateway endpoint;
2. health/readiness reporting;
3. deterministic capability discovery;
4. typed request validation before dispatch;
5. provider/adapter admission state validation;
6. policy-decision enforcement;
7. approval-state enforcement where required;
8. HRB lease validation for governed compute workloads;
9. secret-reference resolution without exposing durable credentials to callers;
10. timeout, cancellation, concurrency and result-size controls;
11. invocation receipt emission to the Evidence/Observability path;
12. fail-closed behaviour for unknown identities, capabilities, providers, schemas, policies or required leases.

## 5. Protocol baseline

The runtime SHOULD prefer the current MCP Streamable HTTP/stateless-capable protocol baseline where supported and MUST retain compatibility adapters where needed for admitted providers.

Supported provider-facing modes:

- current MCP HTTP transport;
- compatible Streamable HTTP implementations;
- managed stdio MCP adapter;
- typed native/application adapters;
- controlled non-MCP adapters exposed as canonical FA3 capabilities.

Transport differences MUST NOT leak into the caller-facing capability contract.

## 6. Capability-centric namespace

Callers target canonical FA3 capabilities rather than provider-specific tool names.

Examples:

```text
fa3.image.open
fa3.image.edit
fa3.image.export
fa3.video.transcode
fa3.video.track
fa3.audio.separate
fa3.audio.transcribe
fa3.document.index
fa3.document.retrieve
fa3.browser.navigate
fa3.memory.retrieve
fa3.3d.mesh.generate
```

Provider-specific names remain implementation metadata and may be replaced without changing the canonical caller contract.

A capability record MUST minimally contain:

```yaml
capability_id: fa3.image.edit
schema_version: 1
risk_class: R2
provider_candidates:
  - provider_id: PROVIDER-KRITA-001
    adapter_id: fa3.adapter.krita
transport: native-or-mcp
policy_ref: fa3.policy.image.edit
resource_profile: optional
approval: session
```

## 7. MCP Firewall / Policy Enforcement Point

The gateway contains an MCP Firewall as an **enforcement component**, not a policy authority.

Mandatory controls:

- identity-context validation;
- capability allow/deny enforcement;
- request schema validation;
- argument constraints;
- filesystem scope checks;
- network scope checks;
- secret-reference validation;
- required approval validation;
- required HRB lease validation;
- rate/concurrency controls;
- execution timeout/cancellation;
- result schema/size validation;
- receipt generation.

Risk-class baseline:

| Class | Typical action | Default handling |
| --- | --- | --- |
| R0 | read/search/query | policy-auto if allowed |
| R1 | create/export non-destructive data | policy enforcement |
| R2 | modify project/application state | session approval where policy requires |
| R3 | delete/overwrite/destructive action | explicit approval |
| R4 | privilege/security/system-boundary change | explicit strong approval or deny |

## 8. HRB integration

The gateway MUST NOT self-allocate governed CPU/GPU/RAM resources.

For a governed workload:

```text
invocation -> policy -> HRB lease request/validation -> dispatch -> receipt
```

If a required lease is absent, expired, incompatible or revoked, dispatch MUST fail closed.

## 9. Secrets integration

The caller and provider SHOULD receive only scoped secret references/handles. Durable secret material remains owned by the Secret Broker.

The gateway MUST reject:

- unapproved inline durable credentials;
- secret references outside caller/provider scope;
- expired or revoked secret handles.

## 10. Evidence and Event Ledger projection

Every invocation MUST emit a structured receipt sufficient to reconstruct the execution decision without storing unrestricted secret payloads.

Minimum fields:

```yaml
receipt_version: 1
timestamp: RFC3339
actor_id: string
agent_or_client_id: string
session_id: string
capability_id: string
provider_id: string
adapter_id: string
policy_decision_id: string
approval_id: optional
resource_lease_id: optional
request_hash: string
result_status: success|denied|failed|cancelled|timeout
duration_ms: integer
evidence_refs: []
```

The receipt is projected to the canonical Evidence/Observability path and may also feed the FA3 OS Workstation Activity Timeline / Event Ledger. The gateway does not become the retention authority.

## 11. Provider admission lifecycle

A discovered MCP server or tool catalog entry is never directly executable.

```text
discovery
  -> metadata normalization
  -> supply-chain/security admission
  -> capability mapping
  -> policy binding
  -> adapter conformance
  -> current-host health check
  -> E2E invocation test
  -> CONNECTED
```

Until the full path passes, status remains `ADAPTER-GATED`, `PENDING`, `QUARANTINED` or equivalent non-executable state.

## 12. MCP Control Chat integration

`FA3-MCP-CONTROL-CHAT-001` is a client/control surface of this runtime projection. It MUST NOT acquire execution authority.

The canonical flow is:

```text
GUI_CAPTURE
 -> PLANNER
 -> POLICY
 -> APPROVAL
 -> MCP_GATEWAY
 -> TARGET_ADAPTER
 -> EVIDENCE
```

A GUI target MAY be shown before runtime wiring is complete, but it MUST remain visibly non-connected and MUST NOT claim operational status until E2E evidence exists.

## 13. Initial adapter convergence

Existing and future MCP/application integrations SHOULD converge on this boundary, including media/DCC/editorial/document/browser/tool providers. Provider-specific architecture MUST NOT create a second gateway or parallel policy/resource authority.

Priority adapter families:

- Krita / GIMP / Inkscape;
- Bforartists / Blender;
- Kdenlive / OpenShot;
- Ardour and admitted audio editors;
- ComfyUI and generative-media tool adapters;
- document/RAG providers such as admitted PageIndex-style providers;
- controlled browser automation providers;
- developer/agent tools admitted by canonical policy.

## 14. Fail-closed rules

The following conditions MUST deny dispatch:

```text
UNKNOWN_IDENTITY
UNKNOWN_CAPABILITY
UNKNOWN_PROVIDER
UNADMITTED_ADAPTER
INVALID_SCHEMA
MISSING_POLICY_DECISION
MISSING_REQUIRED_APPROVAL
MISSING_OR_INVALID_HRB_LEASE
INVALID_SECRET_REFERENCE
BYPASS_PATH_DETECTED
EVIDENCE_RECEIPT_UNAVAILABLE_WHEN_REQUIRED
```

No implicit fallback may bypass policy, resource, secret or evidence requirements.

## 15. Acceptance gate

`FA3-MCP-CURRENT-HOST-001` is runtime-conformant only if all mandatory checks pass:

1. service health/readiness PASS;
2. one logical caller-facing endpoint PASS;
3. canonical capability discovery PASS;
4. typed request validation PASS;
5. admitted provider invocation PASS;
6. managed stdio compatibility test PASS where used;
7. policy deny test PASS;
8. approval-required test PASS;
9. direct provider bypass test DENY;
10. secret-leak negative test DENY;
11. HRB-required/no-lease test DENY;
12. valid HRB lease execution PASS;
13. timeout/cancellation PASS;
14. evidence receipt generation PASS;
15. provider health-loss/circuit-break behaviour PASS;
16. unknown capability/provider tests DENY;
17. MCP Control Chat cannot self-promote target to CONNECTED PASS;
18. no model-router/workflow/policy/resource authority capture PASS;
19. canonical registry/evidence reconciliation PASS.

Runtime status MUST remain `PENDING_CURRENT_HOST` until current-host evidence demonstrates all required checks.

## 16. Rollback

Rollback MUST disable the current-host gateway projection and revoke its runtime registrations without deleting canonical provider records or transferring execution authority to individual clients. Direct-to-provider execution remains disabled unless separately authorized by an explicit canonical emergency profile.

## 17. Canonical conclusion

`FA3-MCP-CURRENT-HOST-001` is the runtime projection of `FA3-AUTH-MCP-GATEWAY-001`; it is not a competing root. It converts the already-decided FA3 Central MCP/Capability Gateway authority into an executable, testable and fail-closed current-host contract while preserving all existing authority boundaries.
