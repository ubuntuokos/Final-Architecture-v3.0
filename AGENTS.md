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

For FA3 research, planning, architecture, application, capability, module, provider, UI, workflow, model, standard, algorithm, SDK, library, paper, dataset, or external-project work, any source that is identified even tentatively as a potentially useful donor or reference MUST be captured or merged into `FA3-DONOR-REFERENCE-REGISTRY-001` before the task is closed.

Use `./bin/fa3-donor-capture --name "<name>" --source "<locator>" ...` for candidate capture. The default state is `CANDIDATE`. Capture is non-authoritative: it MUST NOT imply dependency adoption, code import, fetch/install, provider admission, model selection, activation, architectural authority, or runtime promotion. Source/code reuse still requires the normal FA3 license, provenance, security, coexistence, hardware, and admission paths.

Before designing or materially modifying an FA3 application, capability, or module, query Reuse Discovery including the donor registry. Rejected and superseded donors remain recorded so the same research is not repeated, but they are not planning candidates.

## FA3 automatic application inventory and reciprocal reuse

For any application added to the curated AI Studio catalog, derive its record through `bin/fa3-app-donor-index` rather than creating an untracked donor entry. GUI surface routes must be indexed as surfaces, never silently treated as applications. Planned FA3 applications must be explicitly registered in `canonical/FA3-APPLICATION-DONOR-LINKS-001.json`. Before new or materially modified application/module design, inspect both the existing Reuse Discovery results and the application's incoming/outgoing links. On donor-registry changes, run the previous-registry impact comparison and review only affected applications. Application registration does not confer donor approval, dependency, install, source-import, model, provider or runtime admission.

## P0 donor serialization and explicit human design approval (2026-09-29)

- Before ANY new FA3 planning, implementation, or finalization, run the live fail-closed donor readiness preflight against the exact canonical registry and ALL open GitHub PR file sets. Missing GitHub/token evidence, corrupted registry, pending donor-maintenance PR, or an active registered donor maintenance process means BLOCKED; report the blockers before work starts. Maintenance-only integrity validation never grants planning readiness.
- Donor Registry consultation and an exact-registry-hash Reuse Assessment are mandatory. An assessment may conclude REVIEWED_NO_MATCH: **using** the registry is mandatory; **adopting** a donor is optional. Candidate status is never permission for code import, install, provider/model admission or automatic selection.
- Every adopted donor/pattern requires its own explicit user-approved canonical decision or explicit authorized request, independent of subsequent license/provenance/security/coexistence/hardware gates. Never confuse a reference proposal with a user-approved source adoption.
- No final application, capability or production implementation without a written, previously approved immutable plan and a human approval tied to the exact head, except a separately recorded explicit user exception. Existing Security Governance and Evidence authorities remain exclusive for implementation/promotion. Do not complete plans or push final versions while donor maintenance is pending.
- **Donor maintenance exemption:** repairing/updating the existing donor registry and its protective preflight/CI is never subject to new-application design, development, approved-application-plan or pending-donor-PR restrictions. Use maintenance-only validation, even while repairing a corrupt registry; do not misreport integrity PASS until actually proven. All existing history, security, evidence and exclusive-maintenance controls still apply. This exception NEVER permits starting application design/implementation/finalization or adopting a donor.
- Global CI: .github/workflows/fa3-donor-serialization.yml. CLI: bin/fa3-donor-readiness. New validation metadata is NOT a new registry or architectural authority. Cross-host unregistered work must acquire an existing shared orchestration lock; GitHub PR scanning alone does not prove a distributed lease.
