# CLI-Anything Reference Adoption Rules

Canonical reference: `FA3-REFERENCE-CLI-ANYTHING-001`

## Purpose

CLI-Anything is maintained as a controlled external reference source for agent-native application control. It is not an FA3 runtime dependency and it does not define FA3 authority.

## SHOULD-CONSULT trigger

Consult this reference when an FA3 task materially involves one or more of the following:

- agent-to-application control;
- GUI-to-CLI conversion or automation;
- application harness design;
- MCP-backed desktop/application control;
- agent skill/tool metadata;
- JSON-first CLI contracts;
- REPL/session state;
- preview/live-preview/trajectory state;
- native-backend or real-application E2E validation;
- DCC, media, office, GIS, or comparable desktop application automation.

`SHOULD-CONSULT` means the relevant pattern should be checked before finalizing a materially related design. It does not mean the pattern must be adopted.

## Allowed outcomes

For a materially relevant comparison, choose one of:

- `ADOPT` — the pattern is semantically compatible and is re-materialized inside FA3 controls.
- `ADAPT` — the pattern is useful but must be changed to satisfy FA3 contracts or authority boundaries.
- `REJECT` — the pattern conflicts with FA3 requirements or is inferior to the existing FA3 design.
- `NOT_APPLICABLE` — the reference contains no materially relevant pattern for the task.

## Required adoption path

Any code, contract, or runtime behavior derived from the reference follows this sequence:

1. Identify the exact source pattern and pinned revision.
2. Map the behavior to existing FA3 canonical semantics.
3. Verify provenance and license compatibility.
4. Perform applicable software-supply-chain and security review.
5. Preserve FA3 authority separation.
6. If execution is introduced, map workload admission through the applicable HRB/resource contract.
7. If accelerator execution is introduced, preserve the dedicated accelerator lease/guard path.
8. Create a provider/runtime canonical record only if the component actually becomes executable FA3 material.
9. Add executable conformance and evidence appropriate to that runtime materialization.
10. Reconcile registries/inventory/evidence before claiming closure.

## Forbidden shortcuts

The following are forbidden:

- treating CLI-Hub or any external registry as a trust authority;
- granting execution based on `SKILL.md` or registry metadata;
- direct runtime execution from the reference repository;
- importing a harness automatically because it exists upstream;
- bypassing FA3 supply-chain/security checks;
- bypassing HRB/resource admission;
- bypassing `ResourceAdmissionAuthorization@1` for CPU/memory workloads when that contract applies;
- bypassing `AcceleratorExecutionLease@1` for accelerator workloads when that contract applies;
- allowing a CLI harness to issue or sign its own FA3 authorization;
- treating reference review as runtime PASS evidence.

## Authority rule

CLI-Anything remains below FA3 canonical, policy, security, admission, HRB, and evidence layers. It may provide implementation ideas or an application adapter, but it never becomes the authority deciding whether execution is permitted.

## Provider escalation

Do not create `FA3-PROVIDER-CLI-ANYTHING-001` merely because the reference exists.

Create a provider record only when an FA3 workflow is designed to execute CLI-Anything code or a CLI-Anything-derived harness as a runtime component. At that point, define the exact provider scope, version/provenance, admission path, isolation requirements, tests, and evidence.

## Update review

When the controlled fork revision changes:

1. Compare the new revision with `PINNED-REVISION`.
2. Check for materially new patterns in the indexed domains.
3. If no materially relevant change exists, update the revision pin and review record.
4. If a materially relevant change exists, mark the reference `IMPACT_REVIEW_REQUIRED` until the affected FA3 design area has been assessed.
5. Never auto-merge upstream behavior into FA3 runtime or canonical semantics.
