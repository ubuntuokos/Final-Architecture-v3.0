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

## Deliberately open reconciliation items

1. **Curated agent/template admission:** the whole upstream repository is not automatically admitted. Individual personas, runbooks or extracted procedures still need scoped normalization/admission before enabled use.
2. **GUI:** the Imported Packs / Agency Agents surface must be reconciled with the ongoing FA3 GUI Decision Fabric + Agent Native work. This provider change does not modify GUI files.
3. **External redistribution taxonomy:** the planned `EXTERNAL_REDISTRIBUTABLE` source-intake classification is not yet canonical on current `main`; the Agency Agents record is designed for later binding but does not invent that authority early.
4. **Release projection:** the unified projection is regenerated through the repository reconciler; it is not edited manually here.
5. **Runtime/current-host:** this provider intentionally has no upstream runtime dependency. Any future executable adapter or converted runtime package requires separate admission and evidence.

These are not silently treated as PASS and therefore prevent calling the overall integration fully closed.
