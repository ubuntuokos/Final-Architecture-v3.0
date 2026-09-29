<!-- FA3_AGENT_META {"schema":"fa3.agent-instruction-projection.v1","profile":"FA3-AGENT-INSTRUCTIONS-001","scope":"/","authority":"NON_CANONICAL_PROJECTION"} -->
# FA3 repository agent instructions

This file is a scoped operational projection for coding agents. It is not a canonical source of truth and cannot create architectural authority.

## Global operating rules

- Read the relevant canonical profile, contract, decision, and gate before changing governed behavior.
- Preserve fail-closed behavior. Never weaken, disable, or bypass a valid gate, test, security boundary, HRB boundary, or evidence requirement merely to obtain PASS.
- A PASS or VERIFIED claim requires actually executed evidence. PENDING is a valid state; fabricated PASS, receipts, command output, host capabilities, or runtime observations are forbidden.
- Never commit raw passwords, tokens, API keys, private keys, recovery material, or other secret values. Use governed references and the FA3 secret boundary.
- Treat current-host observations as evidence, not global architecture requirements.
- Keep provider implementations replaceable. A provider or agent vendor cannot become an architectural authority by convention.

## Hardware Audit invariants

- The global hardware baseline is capability-based and vendor-neutral.
- Accelerator inventory is dynamically discovered and may contain zero devices.
- Do not introduce a global NVIDIA, AMD, Intel, CUDA, ROCm, Level Zero, Vulkan, ZLUDA, GPU SKU, runtime ordinal, PCI address, or current-host topology requirement.
- Distinguish logical CPU processors from physical CPU cores. Do not infer one from the other.
- Backend selection follows discovered device/backend compatibility and governed admission. Translation backends require explicit opt-in.
- Hardware placement, reservation, and lease decisions remain under the Host Resource Broker.
- Hardware safety overrides performance optimization. FA3, installers, provisioning, tuning, benchmark and agent actions must remain inside a device-bound vendor-supported operating envelope.
- Never apply overvoltage, out-of-policy overclocking, unsafe power limits, or bypass thermal, current, fan, firmware, driver or other hardware safety protections.
- If the safe operating range cannot be proven for the exact device and control, fail closed and do not mutate the hardware setting. Existing user tuning is not authority to increase or extend tuning.

## Change discipline

- Add or update tests for governed behavior changes.
- Preserve capability and authority counts unless an explicit release reconciliation changes them.
- Do not mutate approved proposals, fabricate evidence, or self-validate a gate change with only the gate being changed.
- Prefer the smallest scoped change that satisfies the canonical contract.

## Authority boundary

Canonical authority: repository canonical records and executable gates.
Projection authority: none.
If this file conflicts with a canonical record, contract, decision, executable gate, or verified evidence, stop and resolve the conflict at the higher-authority layer. Do not silently choose this file.


## FA3 donor capture rule

Only a source LINK that the **owner** explicitly introduced with the literal `donornak:` **before that link** is eligible for donor registration. A link without that preceding marker—including a research suggestion, assistant proposal, reference candidate or a link introduced with `donor:`—is **analysis only**. Do not insert, queue, sync, promote, remove or otherwise mutate donor metadata for that link before the owner gives a different explicit instruction. Do not infer donor consent from old research, generic keywords or assistant utterances. No retrospective PR extraction is mandatory.

Use `./bin/fa3-donor-capture --owner-submitted-link --owner-donor-marker donornak --name NAME --source URL` only when there is verified explicit owner marking. Direct owner-marked links are pre-reviewed for reference registration and become `ACCEPTED_REFERENCE` on successful canonical publication without an additional catalog approval. Existing rejection/supersession requires explicit resolution. Adoption, code reuse, installation and runtime admission still require normal explicit owner approvals and independent security, license, hardware and Software Coexistence checks.

Before design or material modification, consult Reuse Discovery against the **last verified, committed main donor registry only**. Never consume pending PR records or an unstaged import as canonical planning input; never publish a separate registry. Re-run prior analysis after a new donor batch only if the owner requests it.

## FA3 automatic application inventory and reciprocal reuse

For any application added to the curated AI Studio catalog, derive its record through `bin/fa3-app-donor-index` rather than creating an untracked donor entry. GUI surface routes must be indexed as surfaces, never silently treated as applications. Planned FA3 applications must be explicitly registered in `canonical/FA3-APPLICATION-DONOR-LINKS-001.json`. Before new or materially modified application/module design, inspect both the existing Reuse Discovery results and the application's incoming/outgoing links. On donor-registry changes, run the previous-registry impact comparison and review only affected applications. Application registration does not confer donor approval, dependency, install, source-import, model, provider or runtime admission.

## P0 donor serialization and explicit human design approval (2026-09-29)

- Run live fail-closed donor readiness before planning, implementation and finalization. Verify the local exact registry blob against the protected published main snapshot, its integrity, stable main SHA, and complete live PR inventory. Missing GitHub evidence, corrupt main or stale local snapshot blocks the operation and must be immediately reported.
- **Pending donor intake PRs do not block unrelated design, implementation or finalization** when the published main registry is intact and exact-matched. Pending/unmerged donors must be excluded from all such work. A fresh Reuse Assessment tied to the exact published registry SHA is still mandatory; donor adoption is optional.
- **One intake conversation at a time:** before donor publication, require the live exclusive intake gate. The oldest open donor PR owns the slot; a second PR or conversation must report `DONOR_INTAKE_IN_PROGRESS_WAIT_FOR_COMPLETION`, identify the active PR and stop intake. Global GitHub Actions intake concurrency and the local nonblocking import lock provide additional serialization. An off-GitHub writer must first participate in the existing shared orchestrator; a PR scan alone is not a universal distributed lease.
- Donor expansion, history-preserving removal and metadata synchronization are exempt from new-application planning/implementation restrictions but remain exclusive donor maintenance with normal integrity and exact-head gates.
- Every adopted donor needs a separate explicit owner-approved canonical decision. Approval of intake does not approve usage. No finished application or module without a previously approved immutable plan and exact-head human approval, except a separately recorded owner exception. Preserve the 175-capability baseline and the existing authorities.

## Donor Registry owner decisions (2026-09-29)

Mandatory historical PR donor extraction is abolished. The fourteen historical exact-head exemptions (#24 #31 #52 #70 #71 #125 #180 #181 #245 #252 #392 #427 #434 #438) remain closed unmerged. The explicit `donornak:` owner marker must precede each intake link (one marker may introduce a clearly grouped multi-link batch). Without it the only permitted action on a submitted link is analysis until the owner directs otherwise. No second donor intake conversation can start during an active intake. Other FA3 work uses only the finalized published registry; unmerged candidates are invisible, and completed work is not automatically re-run after their publication.
