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

`SELECT_ONE`, `BOOLEAN`, `SCORE`, `RANK`, `MULTI_LABEL`, `RELEVANCE`, `STOP_CONTINUE`, `BOUNDED_ACTION`.

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

### System One reflex provider

`FA3-PROVIDER-SYSTEM-ONE-DECISION-001` is the provider-neutral bounded reflex path. It accepts `BOUNDED_ACTION`, compiles only pre-authorized finite actions and parameters, and uses a runtime binding to the central Model Router. Confidence is evidence only: the result is an authorization-ready intent, never permission or execution.

An optional native System One route is declared in the committed Model Router registry, but it remains **unbound without real physical current-host admission**. The new bridge uses the LiteLLM authenticated pass-through, explicit primary-model designation and independent native-provider and Router E2E evidence. CI success never activates an external provider. Applications cannot call OpenRouter/TypeSafe directly; only the separately admitted backend adapter may contact its explicitly chosen upstream. See `docs/system-one-native-router-admission.md`.

The same contract is exposed to `FA3-WEB-AI-001` for bounded browser/UI reflexes and to the MCP Gateway through the finite MCP tool compiler. UHP remains an optional compatibility adapter, not an FA3 authority.

See `docs/system-one-reflex-runtime.md`.


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

### Reuse Discovery

Every new FA3 application, provider, profile, derived implementation, GUI module, Agent Native component or material extension must first pass `FA3-REUSE-DISCOVERY-001`.

As part of that deterministic pass, every new or materially modified ApplicationIntent must review `FA3-KHRONOS-OPEN-STANDARDS-001` through its canonical profile, adapter registry and integration map. The outcome is explicitly recorded as `MATCHED` or `REVIEWED_NO_MATCH`; review does not imply selection, authority, runtime admission or activation.

The project records an `FA3-APPLICATION-INTENT-001` intent and a machine-readable `FA3-REUSE-ASSESSMENT-001`. Existing capabilities, contracts, providers, patterns, GUI projections and references are discovered before gap analysis. A new implementation is permitted only for a real documented gap or an explicitly bounded provider-local mechanism. Reuse Discovery cannot admit a provider, grant authority or promote runtime state.

Skill discovery is part of the same mandatory stage. `FA3-REUSE-CATALOG-001` federates `FA3-SKILL-REGISTRY-001` and `FA3-EXTERNAL-SKILL-RADAR-001`: admitted FA3 skills may be proposed as task-scoped reusable context, while external skill repositories are reference/idea sources only. A skill selection is not activation; activation still requires the Skill Fabric materialization/use path. External skill sources never gain install, admission, activation, MCP, model, secret, resource or mutation authority through Reuse Discovery.

`ApplicationIntent.task_classes` and `ApplicationIntent.skill_triggers` can narrow deterministic skill discovery. Only `ADMITTED` registry skills can receive `ADMITTED_SKILL_REUSE`; non-admitted skill material remains reference/admission-pending, and External Skill Radar sources remain `REFERENCE_ONLY`.

After deterministic reuse eligibility filtering, every new FA3 profile/provider or material capability extension must carry an `FA3-DECISION-FABRIC-ASSESSMENT-001` assessment with one of:

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


## Donor & Reference Registry

`FA3-DONOR-REFERENCE-REGISTRY-001` is the central non-authoritative donor/reference knowledge base federated into `FA3-REUSE-DISCOVERY-001`. It exists so planned and future applications do not need to rediscover donor research from earlier conversations, notes, or isolated project assessments.

A source is captured as soon as FA3 research identifies it as potentially useful as a donor or reference. Tentative mention is sufficient for `CANDIDATE` capture; capture is deliberately weaker than analysis or admission. Repeated mentions merge into the same source-normalized record.

Every new or materially modified application, capability, or module queries the donor registry before a new implementation is proposed. Matching uses capability, domain, problem, target, and tag hints. `REJECTED` and `SUPERSEDED` entries remain recorded to prevent repeated research but are excluded from planning candidates.

Donor discovery never grants architectural authority and never performs dependency adoption, code import, fetch/install, provider admission, model selection, activation, or runtime promotion. Those actions remain behind the existing FA3 license/provenance, security, coexistence, provider, Model Router, HRB, and evidence gates.

The capture helper is:

`./bin/fa3-donor-capture --name "<name>" --source "<locator>" [--tag ...] [--capability ...] [--domain ...] [--problem ...] [--target ...] [--note ...]`

The helper deduplicates by normalized source key or name and atomically merges subsequent observations.
