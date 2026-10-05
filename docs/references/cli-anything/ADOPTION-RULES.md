# FA3 CLI-Anything Adoption Rules

Canonical reference: `FA3-REFERENCE-CLI-ANYTHING-001`

## Purpose

CLI-Anything is an FA3-controlled external reference corpus, not an FA3 authority and not a runtime dependency. It may inform FA3-native implementations when relevant patterns exist.

## Required adoption path

Any material reuse must follow this sequence:

1. Identify the relevant CLI-Anything pattern or implementation.
2. Map it to the existing FA3 canonical capability/action model.
3. Determine whether an existing FA3 provider already covers the capability.
4. Perform security and supply-chain review.
5. Map resource use to FA3 admission and HRB requirements.
6. Preserve accelerator authorization through `AcceleratorExecutionLease@1` where applicable.
7. Preserve generic CPU/memory workload authorization through the applicable FA3 resource-admission contract where applicable.
8. Materialize an FA3-native provider/action contract only if runtime execution is actually required.
9. Add unit, integration, true-backend E2E, and artifact/evidence checks appropriate to the capability.
10. Reconcile canonical registry, conformance, evidence, and GUI mappings as applicable.

## Prohibited shortcuts

The following are prohibited:

- treating CLI-Anything as canonical authority;
- granting CLI-Anything security, admission, execution, or resource authority;
- direct automatic import into FA3;
- blind copy/paste of upstream implementation as canonical FA3 code;
- bypassing FA3 SCS/security review;
- bypassing HRB or accelerator/resource authorization;
- treating `SKILL.md` content as authorization;
- treating CLI-Hub or any external registry as a trust authority;
- creating a Git submodule dependency solely for reference use;
- marking a generated harness as PASS without real-backend/current-host evidence when such evidence is required.

## Provider promotion

`FA3-PROVIDER-CLI-ANYTHING-001` is not created merely because this reference exists.

It is created only when FA3 intentionally executes a CLI-Anything component or a CLI-Anything-derived/generated harness as a maintained runtime integration.

Even after provider promotion:

- canonical authority remains with FA3;
- execution remains subject to FA3 policy/admission;
- security remains subject to FA3 security/SCS controls;
- CPU/memory/GPU/NPU resources remain subject to FA3 resource contracts and HRB;
- the provider cannot mint or sign its own authorization or accelerator lease.

## Update review

The controlled fork may advance independently. A new fork revision does not automatically alter FA3.

When `CURRENT_FORK_REVISION != LAST_REVIEWED_REVISION`, review the delta for:

- new or changed harnesses;
- new backend patterns;
- security-relevant changes;
- preview/live-preview/trajectory changes;
- skill/capability contract changes;
- testing methodology changes;
- new applications relevant to current FA3 scope.

If the delta has no FA3 impact, update the reviewed/pinned revision only after review. If it has FA3 impact, create a separate impact/materialization task and preserve the previous canonical behavior until that work passes its gates.
