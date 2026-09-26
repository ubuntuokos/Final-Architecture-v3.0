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
