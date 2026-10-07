# CFA3 Retroactive Redesign Compliance

Canonical policy: `CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-POLICY-001`

## Trigger

This rule applies when an application, service, shared fabric/layer, module, plugin, extension, provider/backend, workflow, agent/skill, adapter, infrastructure component, user function, or protocol/compatibility layer was designed before mandatory CFA3 donor use and later enters redesign, major revision, modernization, migration, reimplementation, compatibility refresh, or rematerialization.

A legacy component that is not being redesigned is not automatically invalidated. Naming work "refresh", "v2", "modernization", "migration", or similar does not bypass the trigger; the substance of the change controls.

## Legacy source recovery

Every external link actually used by the earlier design must be recovered with provenance. Existing canonical donors are reused without duplicate intake. Missing sources must enter the existing CFA3 Donor & Reference Registry process.

A missing source may be used temporarily for analysis, comparison, dependency/reference tracing, and redesign planning. Temporary use is planning-only: it grants no donor adoption, source-copy, dependency, provider/model, runtime, architectural, or finalization authority.

The canonical donor registry remains `FA3-DONOR-REFERENCE-REGISTRY-001`. No parallel donor registry or intake authority is created.

## Current-rule delta

The redesign captures the current canonical-main rule baseline and reviews every mandatory category:

- ARCHITECTURE
- APPLICATION_INTEGRATION
- DONOR_POLICY
- AI
- HARDWARE
- WORKLOAD_MODE
- SECURITY
- RIGHTS_LICENSING
- COMPATIBILITY
- PLUGIN_EXTENSION
- COMMUNICATION
- WORKFLOW
- GUI
- TELEMETRY
- FUTURE_ADMISSION
- DEVELOPMENT_PROCESS

Each category is classified as `APPLICABLE`, `NOT_APPLICABLE`, `ALREADY_COMPLIANT`, `REQUIRES_CHANGE`, or `BLOCKED`. `NOT_APPLICABLE` requires a rationale. Finalization permits only resolved `NOT_APPLICABLE` or `ALREADY_COMPLIANT` classifications.

## Lifecycle

```text
LEGACY_COMPONENT_IDENTIFIED
  -> LEGACY_SOURCE_DISCOVERY
  -> CURRENT_RULE_BASELINE_CAPTURE
  -> DONOR_GAP_ANALYSIS
  -> RULE_DELTA_ANALYSIS
  -> REDESIGN_IN_PROGRESS
  -> DONOR_CANONICALIZATION_PENDING
  -> RULE_DELTA_RESOLUTION
  -> RETROACTIVE_REDESIGN_FINALIZATION_GATE
  -> REDESIGN_FINAL
```

## Fail-closed finalization

`REDESIGN_FINAL` is allowed only when:

- legacy source discovery is complete;
- every recovered legacy source resolves to an `ACCEPTED_REFERENCE` or `ANALYZED` canonical donor;
- the record binds the current canonical donor-registry SHA-256;
- all current-rule delta categories are resolved;
- Architectural Authority, Integration, Security, Hardware, AI, and Development Policy checks all PASS;
- capability baseline is 175, capability delta is 0, and architectural-authority delta is 0.

Unknown or stale state blocks finalization.

## Development integration

The policy composes with `CFA3-DEVELOPMENT-AI-BEHAVIOR-GOVERNANCE-POLICY-001`, the existing application/donor link policy, the canonical gate registry, and global static enforcement. It does not replace Temporal, Security/UAF, HRB, Model Router, Evidence, License/Rights, or donor authorities.

The machine-readable redesign record contract is `canonical/contracts/CFA3-RETROACTIVE-REDESIGN-RECORD-001.schema.json`. The validator is `src/cfa3_retroactive_redesign_compliance.py`, and the mandatory static gate is `CFA3-RETROACTIVE-REDESIGN-COMPLIANCE-GATESET-001`.

## Current Host

This is governance/static validation only. It claims no physical Current Host PASS and requires no physical requalification by itself.
