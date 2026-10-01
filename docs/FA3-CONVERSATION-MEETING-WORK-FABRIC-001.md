# FA3 Conversation & Meeting → Work Fabric

**Profile:** `FA3-CONVERSATION-MEETING-WORK-FABRIC-001`
**Status:** reference core materialized; physical Current Host promotion **PENDING**
**Capability baseline:** 175, delta 0. **Authority delta:** 0.

One shared FA3 layer converts chat, 1:1 meetings and group meetings into one structured work graph. Mind map, decision map, task list, work plan, timeline/milestones, minutes, open questions and follow-up agenda are projections rather than independent sources of truth.

Raw text, an AI extraction, a speaker identity, or the phrase “approved” never grants authority or directly creates a canonical task/decision. The flow is source event → proposal → human verification → authorized materialization approval → typed draft intent → existing target authority finalizes.

Speaker attribution carries provenance only. Raw recording, transcript and derived work objects have separate access scopes. AI assistance is optional; when disabled, the manual/deterministic path remains available and no model/provider call or silent fallback is permitted.

The materialization reuses canonical main Decision Fabric, Work Management projection, UAF, Journal, Model Router, HRB and Security Governance. It adopts no new donor and does not mutate the Donor Registry.

PR #552 (Mind Map Studio) and PR #556 (Objective Coordination Intelligence) are optional future adapter targets only; this branch has no required runtime dependency on unmerged work.

This is a structural change. Static tests/CI are not physical Current Host evidence. Runtime promotion requires the positive/negative/rollback matrix in `FA3-CONVERSATION-MEETING-WORK-CURRENT-HOST-IMPACT-001`, including CPU-only, restart/recovery, permission/privacy, Software Coexistence and Hardware Safety checks.
