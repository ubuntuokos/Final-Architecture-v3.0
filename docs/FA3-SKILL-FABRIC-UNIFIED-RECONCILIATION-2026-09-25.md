# FA3 Skill Fabric 1.3 — Unified Skills and Browser Session Reconciliation

Date: 2026-09-25

## Decision

FA3 keeps `FA3-SKILL-FABRIC-001` as the sole Skill Fabric profile and raises it to 1.3.0 without adding a capability or architectural authority. Existing Reuse Discovery, Skill Package Admission, Security/SCS, UAF/MCP, Model Router, HRB, Secret, Evidence and Agent Federation authorities remain unchanged.

## Added hardening

1. **Typed skill interfaces.** Skills declare typed inputs, outputs, preconditions and postconditions. Interface metadata never grants authority.
2. **Context budgets.** Metadata, primary instructions and optional references receive explicit task-scoped budgets. Overflow fails closed and requires reselection or reduced context; global corpus injection remains forbidden.
3. **Activation preview.** Before active materialization, FA3 produces a side-effect-free preview of requested tools, resources, models, secrets, filesystem/network access and browser-session needs. Requested permissions must remain a subset of the admitted skill permissions.
4. **Host projection.** An admitted skill may be projected into supported agent skill directories only after collision analysis. Host precedence such as first-found-wins is never accepted as an FA3 collision resolution mechanism. Existing files are not overwritten; duplicate names fail closed unless an exact content digest reuse is explicitly recorded.
5. **Provenance attestation.** Cryptographic provenance may strengthen evidence, but a valid signature by itself never grants admission. When present it must bind immutable source, commit and content/manifest digests and match expected source/builder policy.
6. **Browser session interaction.** Selected Tencent BrowserSkill patterns are reimplemented natively above `FA3-BROWSER-ACTION-RUNTIME-001`: Agent Window separation, explicit TTL-bound tab borrow/return, human assistance and mandatory cleanup. Browser content stays untrusted and credentials/cookies/tokens cannot be exported.

## External radar

The radar remains reference-only and now records engineering, evaluation, UI, code-review, browser-session and host-compatibility sources. GitHub Topic pages are discovery feeds only; GitHub Skills is training reference only. Discovery does not imply installation, admission, activation or execution.

## Browser evidence boundary

`FA3-BROWSER-SESSION-INTERACTION-001` is statically materialized but makes no current-host runtime claim. Physical promotion requires real extension/native-messaging/Unix-socket integration, Agent Window isolation, borrow/return, human takeover/resume, stale-observation denial and cleanup evidence. Remote browser execution remains not admitted.

## Hardware Audit

All new validation and contract logic is CPU-only and vendor-neutral. Accelerator cardinality remains 0..N. Optional model-assisted review continues through the central Model Router and HRB. No CUDA/ROCm/vendor/SKU assumption is introduced.

## Software coexistence

FA3 does not install, overwrite, shadow or globally reconfigure upstream skills, Claude/Copilot/Codex/OpenCode/Antigravity skill directories, Tencent BrowserSkill, browser profiles or browser extensions. FA3 uses namespaced artifacts and explicit projection/session operations only.

## Current-host truth

Static PASS does not imply current-host browser-session PASS, federation runtime PASS or cross-host host-projection execution proof.
