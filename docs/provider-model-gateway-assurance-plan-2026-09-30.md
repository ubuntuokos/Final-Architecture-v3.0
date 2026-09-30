# FA3 Provider, Model & Gateway Assurance — materialized final plan

## Status

This is the owner-approved integration architecture plan. It introduces **zero
new capabilities and zero new architectural authorities**. The capability
baseline remains **175**. This document does not admit, install, copy or activate
any external project, provider or model.

The external repositories analyzed during planning were submitted as ordinary
links rather than canonical `donornak` intake. Their functional lessons may
inform this owner-approved FA3-native design, but they are not donor identities,
dependencies or runtime authorities in this materialization.

## Architecture

```text
Provider Intelligence
        ↓
Provider Evidence Dossier
        ↓
Assurance Plane
 ├─ protocol conformance
 ├─ model identity
 ├─ health
 ├─ entitlement / quota
 └─ privacy / license / region
        ↓
Provider Admission
        ↓
FA3 Model Router — sole route authority
 ├─ deterministic eligibility
 ├─ optional bounded advisory ranking
 ├─ stage-aware route contract
 └─ explicit bounded fallback / ROUTE_EXHAUSTED
        ↓
Gateway Enforcement
 ├─ identity
 ├─ authorization
 ├─ Layer Guard
 ├─ capability visibility
 ├─ tool/resource/prompt policy
 ├─ quota/budget
 ├─ security/privacy
 └─ protocol mediation
        ↓
Execution
        ↓
Existing Evidence authority
        ↓
Donor ↔ Capability ↔ Consumer Usage Graph
```

## Authority boundaries

- Model/provider selection remains `FA3-AUTH-MODEL-ROUTER-001`.
- MCP/tool mediation remains `FA3-AUTH-MCP-GATEWAY-001`.
- Host placement/reservation/leases remain
  `FA3-AUTH-HOST-RESOURCE-BROKER-001`.
- Action contracts remain under `FA3-UNIFIED-ACTION-FABRIC-001`.
- Security policy and authorization remain with existing Security Governance.
- Secret custody/projection remains with the existing FA3 secrets boundary.
- Durable workflow lifecycle remains Temporal.
- Evidence remains under the existing Observability/Evidence authority.
- The Donor & Reference Registry remains the only donor identity catalog.

No gateway, provider adapter, marketplace, plugin runtime or advisory router may
become a parallel authority.

## Provider assurance

Protocol availability and model identity are separate evidence questions.
A successful generic completion is not evidence that streaming, tool calls,
structured output, multimodal payloads or another protocol feature works.
Likewise, protocol compatibility does not prove that the provider actually
served the claimed model.

The target chain is therefore:

```text
claimed capability
→ bounded synthetic protocol probe
→ protocol evidence
→ requested/claimed/detected model evidence
→ provider admission/requalification
```

Probe content must be bounded and synthetic. Arbitrary user prompts or outputs
must not be persisted merely to prove provider identity.

## Model routing

Routing remains deterministic-eligibility-first. An AI classifier or advisory
decision component may rank only candidates that are already eligible; it may
not expand the set, authorize egress or override the Model Router.

Long tasks may hold a route for a declared stage rather than reselecting on
every tool call. A stage transition, explicit reselection, policy change,
context rebuild or route failure may trigger a new decision.

Fallback is bounded and explicit:

```text
primary
→ approved fallback candidate
→ next approved candidate
→ ROUTE_EXHAUSTED
```

Every transition requires policy compatibility and evidence. Silent
cross-provider or model substitution remains forbidden.

## Gateway enforcement and MCP visibility

Gateway enforcement occurs after identity/authorization and before execution.
Where possible, unauthorized MCP tools/resources/prompts are filtered from the
discovery projection rather than merely rejected at call time.

The Gateway executes only a router-approved destination. It does not choose a
model or provider independently.

## Protocol projection

One canonical FA3 action/capability contract may have controlled protocol
projections:

```text
canonical UAF action
   ├─ internal invocation
   ├─ REST/OpenAPI projection
   └─ MCP projection
```

The Central MCP Gateway remains the external MCP trust boundary. Projection does
not duplicate the capability implementation and cannot expand authorization.

## Plugin execution

An isolated WASM execution backend may be added beneath the existing Plugin &
Extension governance. It is optional rather than a mandatory host dependency.
Admission requires source provenance, immutable artifact digest, license/rights
review, security checks, declared scope and Layer Guard enforcement.

## Evidence and update impact

Existing evidence authority remains singular. Provider, routing, fallback,
gateway-policy, protocol-projection and plugin-provenance receipts are typed
evidence families, not new authorities.

The Donor ↔ Capability ↔ Consumer graph closes the maintenance loop:

```text
donor change
→ declared donor capability
→ canonical FA3 binding
→ typed consumers
→ regression / security / Current Host impact
```

Historical usage must not be fabricated from names or old mentions. Backfill
requires existing canonical adoption/usage evidence.

## Materialization sequence

1. Capability Usage Graph.
2. Multi-source Provider Intelligence reconciliation.
3. Protocol + model-identity assurance.
4. Stage-aware routing + bounded fallback receipts.
5. Gateway capability visibility and policy enforcement.
6. Controlled REST/MCP protocol projection.
7. Optional plugin isolation/provenance backend.
8. Physical Current Host requalification wherever an actual structural/runtime
   path changes.

This plan itself changes no runtime service, provider route, port, socket,
package, credential path or host resource policy.
