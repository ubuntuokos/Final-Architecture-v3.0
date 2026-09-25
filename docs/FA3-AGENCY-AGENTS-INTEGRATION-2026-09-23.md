# FA3 Agency Agents integration — 2026-09-23

## Status

This integration is deliberately **open, not closed**.

`FA3-PROVIDER-AGENCY-AGENTS-001` materializes `msitarzewski/agency-agents` as an optional immutable reference provider for agent personas, domain-role taxonomy, team/runbook rosters, handoff/escalation patterns and multi-runtime conversion patterns.

The upstream runtime, NEXUS orchestration authority and generated runtime-specific agent files are **not** imported as FA3 authorities or production runtime dependencies.

## Immutable upstream snapshot

- Repository: `msitarzewski/agency-agents`
- Commit: `053ddbbf392a1688fc7043d81529f47ef2cf86c8`
- License observation: MIT; redistributed copies or substantial portions retain the applicable copyright and permission notice.
- Observed structural anchors: 18 divisions, four machine-readable runbooks, standardized handoff templates and an executable multi-runtime conversion script.

A new upstream commit requires a new admission decision. Floating `main` is never production identity.

## Reconciliation with current FA3

### Agent Native

Imported persona text is `UNTRUSTED_SCOPED_CONTEXT`. It is not a canonical `AGENTS.md` projection and cannot override the precedence of `FA3-AGENT-INSTRUCTIONS-001`.

Persona, tone, role and upstream tool hints cannot grant security identity, capability, authorization, tool permission, model/provider selection, secrets or resources.

### Developer-agent coordination

Agency Agents NEXUS handoff/runbook concepts reuse the existing `FA3-DEVELOPER-AGENT-COORDINATION-CONTRACTS-001` vocabulary:

- task → `AgentTask`
- roster delegation → `AgentDelegation`
- handoff → `AgentMessage`
- QA result → `AgentResult`
- escalation → `HumanEscalation`
- evidence → `ExecutionEvidence`

No second FA3 handoff/result/escalation contract family is created.

### Unified Action Fabric

An imported agent can only propose or invoke executable behavior through the existing FA3 execution boundaries. Direct agent → provider execution and direct tool/secret/resource bypass remain forbidden.

### Decision Fabric / Jev

Agency catalog metadata may participate in a bounded FA3 selection step, but the candidate set must originate from the calling FA3 authority. Imported ranking is not authorization and cannot expand the candidate set. Optional Jev semantics remain subject to the existing Decision Fabric contract and rollout policy.

### Human-auditable AI communication

All agent-to-agent communication remains subject to `FA3-AI-COMMS-CONTRACTS-001`. Private model language, emergent codebooks, model-only slang and provider-defined private protocols are denied.

### Skill Fabric

Persona and skill are separate concepts. A reusable procedure extracted from Agency Agents must be normalized and separately admitted under `FA3-SKILL-PACKAGE-ADMISSION-CONTRACTS-001`. Conversion into a SKILL.md or another runtime-specific representation does not constitute admission.

### Hardware Audit

The provider is inert reference content and has no fixed host hardware requirement. Any later executable adapter remains subject to the existing vendor-neutral Hardware Discovery / HRB rules and cannot introduce accelerator vendor, SKU, runtime or device-count requirements.

## Curated source set and FA3-native Agent Definitions

`FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001` records 12 agent-role sources and 5 template sources by immutable upstream path/blob identity. These source records remain **inert reference provenance**; they are not runnable agents and do not grant authority.

The usable FA3 semantic layer is now materialized separately through:

- `FA3-AGENT-DEFINITION-CONTRACTS-001`
- `FA3-AGENT-DEFINITION-REGISTRY-001`
- `FA3-AGENT-DEFINITION-GATESET-001`

The registry contains 12 canonical FA3 role definitions and 5 canonical FA3 templates, with exact 1:1 source-candidate lineage. The upstream persona/runbook bodies are **not vendored**. FA3 stores its own human-readable role/template summaries, competency intents, anti-capabilities, risk/human-gate metadata and immutable provenance.

The separation is strict:

- source candidate ≠ security identity;
- Agent Definition ≠ runtime provider;
- Agent Definition ≠ workforce specialist authority;
- no authority/capability/tool/model/secret/resource grant may originate from a definition;
- definitions may only decorate an already eligible workforce specialist and cannot expand the specialist or AI-participant set;
- runtime provider selection, model routing, authorization, resource admission and evidence remain with their existing FA3 authorities;
- any future verbatim/substantial upstream-content import would require a separate Distribution Compliance/content-admission path.

## GUI reconciliation

PR #371 is merged on canonical `main`. Agency Agents is projected as a read-only child of `agents.workflows`:

- surface: `agency-agents.imported-pack`;
- source catalog: `FA3-AGENCY-AGENTS-CURATED-CANDIDATES-001`;
- canonical definitions: `FA3-AGENT-DEFINITION-REGISTRY-001`;
- execution-intent destination: `agents.action-center`;
- direct provider execution: forbidden;
- GUI authority: none.

The GUI displays the 12+5 canonical definitions but does not claim that an execution runtime/provider has been admitted by this provider.

## Distribution state

Distribution Compliance is canonical and reconciled:

- `FA3-PROVIDER-AGENCY-AGENTS-001` → `EXTERNAL_REDISTRIBUTABLE / EXCLUDED`;
- immutable upstream reference → `REFERENCE_ONLY / EXCLUDED`;
- FA3-native Agent Definition metadata is not an upstream-body bundle;
- product-bundle inclusion of external Agency content would still require a canonical Distribution Decision Receipt.

## Deliberately open reconciliation items

1. **Unified release projection:** it must be regenerated/adopted after the Agent Definition, Workforce and GUI binding changes. The projection is never hand-edited.
2. **Fresh permanent CI:** the new Agency + Agent Definition + Workforce + GUI cross-gates must pass together on the latest topic head after projection reconciliation.
3. **GUI physical current-host evidence:** `FA3-GUI-RUNTIME-CONFORMANCE-001` remains `PENDING_CURRENT_HOST`; `evidence/receipts/fa3-gui-current-host.json` is absent. Static/reference GUI PASS must not be promoted into a physical desktop-runtime claim.

The overall integration therefore remains intentionally **open**. The Agency source/reference, distribution classification, FA3-native definition normalization and static GUI surface are materialized; release-projection adoption, fresh cross-gate CI and real GUI current-host evidence remain outstanding.
