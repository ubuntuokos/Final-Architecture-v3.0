# CFA3 Shared Capability Compatibility Propagation

Status: **staged governance materialization during active PR reconciliation**.

This policy closes the forward-compatibility rule for CFA3 applications without creating a new application registry, workflow engine, permission authority, resource authority, model router, MCP authority, evidence authority or cross-layer fabric.

## Required behavior

Every new CFA3 application must assess compatibility with all applicable existing shared capabilities before admission. Every materially modified application must re-evaluate the same compatibility boundary.

When a shared capability, shared contract, shared profile, application lifecycle contract, plugin/extension contract, work-context contract, collaboration contract, UAF action contract, shared GUI component or shared interchange contract changes, the affected application scope is derived from the existing canonical application inventory and the derived shared-capability consumer map.

The impact scope includes:

- planned applications;
- applications currently being materialized;
- materialized applications;
- future applications through the admission rule.

A shared change is not complete merely because the shared layer passes its own tests. Each affected consumer must receive one of the explicit compatibility dispositions:

- `NO_CHANGE`
- `GUI_PROJECTION`
- `CONTRACT_ADAPTER`
- `SHARED_CAPABILITY_BINDING`
- `LOCAL_TO_SHARED_MIGRATION`
- `RUNTIME_REQUALIFICATION`

Unknown consumer scope fails closed.

## Existing canonical sources only

The policy deliberately reuses:

- `FA3-APPLICATION-DONOR-LINKS-001`;
- `fa3.application-donor-index.v1`;
- `fa3.shared-capability-consumer-map.v1`;
- `FA3-CURRENT-HOST-CHANGE-DELTA-AUTHORITY-001`;
- the existing Reuse Assessment and donor-usage rules.

No second application/capability registry is introduced.

## Forward compatibility

A future application uses `fa3.application-compatibility-assessment.v1` before admission.

The assessment records:

1. application identity and lifecycle state;
2. applicable shared components;
3. a disposition for every applicable component;
4. capability-regression result;
5. architectural-authority delta;
6. Current Host impact classification.

For an already registered application, the gate compares the assessment against the derived shared-capability consumer map and rejects an assessment that silently omits an existing shared consumer edge.

For a not-yet-registered future application, the design/admission process declares the applicable shared components. Registration remains in the existing application inventory; the compatibility assessment does not become a second application registry.

## Shared capability growth

A new or strengthened shared capability must not remain compatible only with the application that introduced it.

The required sequence is:

```text
shared capability / contract change
        |
        v
derive canonical consumer scope
        |
        v
classify every affected application
        |
        +-- NO_CHANGE
        +-- GUI_PROJECTION
        +-- CONTRACT_ADAPTER
        +-- SHARED_CAPABILITY_BINDING
        +-- LOCAL_TO_SHARED_MIGRATION
        '-- RUNTIME_REQUALIFICATION
        |
        v
tests / gates / evidence / release reconciliation
```

Existing verified functionality and native project/data compatibility must be preserved. If immediate migration is unsafe, a bounded compatibility adapter remains until the migration condition is met.

## Relationship to unfinished-PR reconciliation

The active unfinished-PR cleanup and completed-application compatibility repair is the parent process.

Therefore this materialization is intentionally staged:

- the policy, assessment schema, gate, tests and CI are available now;
- it does not introduce a new overlapping Fabric PR;
- it does not mutate the application inventory, shared consumer map, central enforcement policy or release projection while those surfaces are being reconciled by existing PRs;
- global mandatory P0 binding is activated only after the parent PR reconciliation reaches a stable exact `main`.

This avoids turning a compatibility safeguard into a new blocker for the cleanup that must precede it.

## Current Host

Static compatibility never creates Current Host PASS.

A structural or runtime shared change delegates impact calculation to the existing Current Host Change & Delta Authority. Physical positive, negative and rollback proof remains required where that authority classifies the change as requiring runtime requalification.

Current Host remains the final stage after the PR reconciliation and application compatibility chain reaches a stable exact head.

## Donors

This governance delta reuses already-materialized CFA3 repository mechanisms and introduces no new external donor adoption. Therefore it creates no new donor usage edge and no donor-registry mutation.

Future donor-backed capability growth remains subject to the existing donor registration and usage-edge rules; the project may not close with a materially used donor left unregistered.
