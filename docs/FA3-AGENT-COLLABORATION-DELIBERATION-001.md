# FA3 Agent Collaboration & Deliberation Fabric

Canonical profile: `FA3-AGENT-COLLABORATION-DELIBERATION-001`

## Purpose

This materialization derives useful coordination patterns from three Agent Room implementations while preserving all existing FA3 authorities. It creates no new capability and no new architectural authority. The active capability baseline remains 175 and the profile binds to existing `CAP-028` Managed External Agent Runtime and `CAP-070` Hybrid Orchestration Federation.

The upstream projects are pattern references only:

- `steviebuilds/agent-room@ae600ecb4790a4fdc526020fd6946e8f57e2b1b4`: local-first rooms, per-participant unread cursor, addressed-only mode, long-poll presence, objective/transcript/close-summary.
- `agent-room-alkl/agent-room@080b13d2bf927a1ee3e66981dece0d2eee698d37`: structured decision/status/result artifacts, evidence-gated task review, explicit turn discipline, presence and MCP-facing coordination.
- `msitarzewski/agent-room@c48e8036159c2bf0a03473a3352457a2ef2c3e7e`: human control-plane patterns, explicit approvals/interventions, canonical coordination records, and evidence-linked completion.

No upstream runtime, installer, home-directory layout, fixed port, service, or control-plane authority is imported.

## Authority chain

```text
authorized caller / human
        |
        v
FA3 Orchestration Workforce
        |
        +--> authorized participant set
        |
        v
Agent Collaboration & Deliberation
        |
        +--> FA3-AI-COMMS-001
        +--> Decision Fabric (optional advisory only)
        +--> UAF -> Security/Human approval -> side effect
        +--> Evidence authority -> completion/closure proof
        +--> Model Router -> provider/runtime/model
        +--> HRB -> host resources
        +--> Agent Federation -> signed cross-host coordination
```

A room is a coordination projection, not an authority. A participant, provider, model, moderator, structured artifact, consensus result, or chat message cannot grant permissions, expand the authorized participant set, select a physical model/provider, allocate resources, promote evidence, or perform side effects by itself.

## Deliberation modes

The canonical modes are `OPEN`, `DIRECTED`, `ROUND_ROBIN`, `MODERATOR`, `CHALLENGE`, `INDEPENDENT`, `CONSENSUS_CHECK`, `HUMAN_ONLY`, and `CLOSED`.

`INDEPENDENT` is intentionally stronger than a normal group chat: required deliberators submit sealed positions and peers cannot observe them before the reveal barrier. This reduces first-answer anchoring and simple agreement cascades.

`CONSENSUS_CHECK` requires an objection opportunity for every required deliberator. An unresolved objection blocks consensus. Consensus itself is never execution authorization, and policies that require a human approval receipt still require that receipt.

## Identity and trust

Display names are presentation only. Agent model/provider identity must be bound by a Model Router receipt. Participant identity must come from the existing FA3 identity/security boundary.

A client-supplied `hostVerified`-style field is explicitly untrusted. This incorporates the upstream security lesson that a browser-held write credential cannot prove who authored a host message. Only an FA3 identity/security receipt may establish trusted identity.

## Evidence and task completion

Structured room artifacts use `DECISION`, `TODO`, `STATUS`, `RESULT`, `BLOCKER`, and `EVIDENCE` kinds, but these markers are indexing/UI semantics only.

A chat message cannot transition a task to completed. Completion requires typed evidence references, a verifier different from the claimant, an explicit `COMPLETED` transition, and any human approval receipt required by policy.

## Hardware Audit

- Vendor neutral: PASS by construction.
- CPU-only contract/state-machine path: required and implemented.
- Accelerator cardinality: 0..N.
- No global accelerator requirement.
- Any model execution remains Model Router -> HRB admitted.
- This fabric does not mutate CPU/GPU/memory/storage tuning values.

## Software coexistence / CAP-175

The FA3 implementation does not write to `~/.codex`, `~/.claude`, `~/.agent-room`, or other upstream namespaces. It claims no fixed default port. Any future runtime endpoint must be dynamic or brokered and any state must live under FA3 XDG namespaces. Upstream Agent Room installations remain independently usable.

## FA3-native reference runtime

A runnable stdlib-only loopback reference runtime is materialized in `src/fa3_agent_deliberation_runtime.py`. It binds only to `127.0.0.1`, requests port `0` by default so the OS assigns an ephemeral port, keeps room state in memory, and does not install a daemon or claim a service name. Its HTTP surface is deliberately small: health, create/read session, validated message append, and receipt-bound close.

`evidence/collect-agent-deliberation-reference-e2e.py` exercises the real HTTP path in CI and proves a valid message is accepted, a forged client `hostVerified` claim is rejected without transcript mutation, closure works, and a closed room rejects new messages.

## Evidence boundary

The reference runtime and CI loopback E2E prove executable semantics only. They do not claim external-agent runtime admission, a persistent production room daemon, physical current-host PASS, cross-host production PASS, or global production promotion. Those require separate physical evidence.
