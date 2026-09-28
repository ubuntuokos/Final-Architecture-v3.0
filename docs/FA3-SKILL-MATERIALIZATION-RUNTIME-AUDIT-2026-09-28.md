# FA3 Skill Fabric — verified snapshot materialization (2026-09-28)

## Scope and source-grounded audit

This change follows the mandatory FA3 Donor & Reference Registry query. Existing
`addyosmani/agent-skills` and `NVIDIA/SkillSpector` remain pattern references,
not execution or admission authorities; `microsoft/SkillOpt` is captured as a
candidate for offline-only skill-improvement patterns. No upstream code is imported.

Actual repository surfaces inspected: `src/fa3_skill_discovery.py`,
`src/fa3_skill_ecosystem.py`, `src/fa3_skill_fabric_gate.py` and v1.3/v1.4
companions, `src/fa3_developer_agent_coordination.py`,
`src/fa3_language_gateway_gate.py`, `src/fa3_cap080_verified_skill_supply_chain_current_host.py`,
`canonical/skill-registry.json`, the materialization contract, and the skill CI.

Discovery and registry eligibility exist; package admission validates descriptor
claims; `skill_use_allowed` checks receipt field shape and routing assertions.
Those latter checks, by themselves, do **not** rehash the bytes supplied to an
agent. Current-host CAP-080 has descriptor-fixture positive/negative/rollback
tests; it must not be called live-consumer end-to-end evidence on that basis.

## Implemented gap closure

`src/fa3_skill_materialization.py` is a read-only verification helper that:
- binds a previously admitted one-entrypoint package and its declared registry
  record to explicit, caller-supplied admission and selection receipts;
- reads each asset through directory-fd-relative, no-symlink opens with byte
  budgets; computes actual SHA-256 from held file descriptors;
- defines a deterministic `fa3.skill-snapshot-manifest.v1` digest over sorted
  path/hash entries; admission must bind this exact scheme;
- creates a short-lived, task-scoped, **non-authorizing** lease;
- reopens and rehashes actual bytes on use and calls the existing Skill Fabric
  use gate for central MCP, Model Router, HRB and Secret Broker intent checks.

This helper does **not** authenticate receipt issuer signatures, query the live
registry, execute scripts, install packages, create new authority, or claim that
all consumers call it. Its caller must obtain and authenticate receipts through
existing FA3 authorities. No compatibility with another manifest serialization
is implied. It fails closed for multi-entrypoint packages until a selected
entrypoint contract is added.

## Integration follow-up and honest evidence boundary

Before production promotion, bind the real admission/selection issuance path
and all consumers (Developer Agent Coordinator, Director/Workforce, GUI agents,
creative apps, cross-host federation) to this shared verification boundary.
Existing quality skills need real digest-bound package snapshots, not synthetic
test digests. Connect task language through existing Language Gateway:
`user_language`, `work_language`, `output_language`; validated or bridged
language status remains allowed under current policy. Do not globally pin hu-HU.

Keep producer/consumer report path bindings reconciled if a durable report is
added. Tests in this change are local reference-runtime tests, **not**
physical current-host, cross-host federation or production promotion evidence.

## Hardware Audit

CPU-only and vendor/accelerator-neutral: no GPU, NPU, CUDA or ROCm dependency.
No display GPU is recruited. No Qt, KDE or Wayland requirement; any later UI
must preserve supported Wayland/X11 and session portability. Model-assisted
review, if later used, goes only through Model Router and HRB.
