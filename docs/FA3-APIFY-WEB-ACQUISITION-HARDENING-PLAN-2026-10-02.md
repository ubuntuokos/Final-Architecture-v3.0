# FA3 Apify / Web Acquisition hardening plan — 2026-10-02

## Approval basis

Owner approved the HD-A through HD-J plan in the 2026-10-02 Apify donor-source continuation conversation.

## Published planning snapshot

- repository: `ubuntuokos/Final-Architecture-v3.0`
- published main: `eaf6ea69897db229e6e6973bb57f2182f153ec3c`
- Donor Registry: `FA3-DONOR-REFERENCE-REGISTRY-001`
- donor registry blob: `7059b3a8c816400f4dee221744be2d13038c48f8`
- donor registry SHA-256: `3e97b1a1ee56dd81c224c3601cb2ebc088e92af0c56d7008bf84b6c45e5cbbd0`
- donor entries: **1339**
- capability baseline: **175**
- provider count: dynamic

Open PR #614 is a separate active donor intake. Its unmerged donor record is excluded from this plan. This plan does not mutate the Donor Registry and does not claim the donor-intake slot.

## Donor boundary

`FA3-DONOR-APIFY-ORG-001` is the only canonical Apify donor/reference identity in the published snapshot. Child repositories remain analysis-only because they were not individually marked `donornak`.

No child repository is adopted, copied, installed, activated, or assigned a usage edge by this work. Material child-repository adoption remains blocked until explicit source registration and normal License & Rights, provenance, security, Software Coexistence, Hardware Safety, Reuse Assessment and usage-edge approval.

## Scope

Materialize a provider-neutral, shared-first hardening delta for existing FA3 web acquisition, Browser Action Runtime and Knowledge/RAG consumers without adding capabilities or architectural authorities.

### HD-A — snapshot/provenance refresh

Record exact observed upstream revisions for the already classified Apify child repositories and distinguish changed versus unchanged snapshots. This is analysis/reference metadata only.

### HD-B — reuse/overlap matrix

Classify proposed subfunctions as `ALREADY_COVERED`, `PARTIAL_GAP`, or `REJECT` against existing FA3 Web AI, Browser Action Runtime, Knowledge/RAG, MCP, HRB and donor/reuse boundaries.

### HD-C — durable acquisition state

Add shared request-state semantics for stable request identity, dedupe key, ownership lease, lease extension, claim/reclaim, retry/requeue, terminal handling and crash-safe recovery receipts.

### HD-D — backend parity

Define one provider-neutral acquisition envelope so HTTP/static and browser-backed execution preserve request identity, policy, provenance and result semantics. Browser mutation/execution authority remains the existing Browser Action Runtime.

### HD-E — origin and session policy

Define origin-scoped robots/politeness/rate policy and session lifecycle state. No proxy/session/provider automatic fallback is authorized.

### HD-F — HRB feedback boundary

Expose load/concurrency observations only as advisory telemetry. Host Resource Broker remains sole physical resource placement/reservation/lease authority.

### HD-G — recovery assurance

Provide deterministic reference implementation and tests for stale leases, lease extension, competing workers, crash recovery, requeue, duplicate prevention, retry limits, origin policy and session replacement.

### HD-H — MCP/Skill boundary

Keep Apify MCP/Agent Skills sources as analysis-only references. Any future execution remains behind Central MCP Gateway, Skill admission, credential, egress, privacy, billing and telemetry gates.

### HD-I — consumer impact

Record shared-first impact for Browser Action Runtime, Web AI, Knowledge/RAG ingestion and agent-web/research consumers. Avoid edits to open-PR-owned contract files where possible.

### HD-J — adoption/usage-edge gate

Encode that a canonical usage edge is mandatory for actual registered donor adoption, while this materialization creates zero new donor usage edges.

## Non-goals

- no Apify Cloud or Actor Store activation
- no Crawlee/Crawl4AI runtime dependency
- no provider/model/MCP/skill admission
- no fingerprint/stealth default capability
- no new browser or web authority
- no new capability ID
- no hardware mutation
- no Current Host PASS claim
- no donor registry mutation

## Materialization artifacts

1. shared child profile and contract family;
2. deterministic reference state machine;
3. P0 fail-closed gate and dedicated CI workflow;
4. ApplicationIntent and Reuse Assessment bound to the published donor snapshot;
5. upstream analysis refresh and overlap matrix;
6. consumer-impact reconciliation;
7. Current Host impact record;
8. documentation and regression tests.

## Acceptance conditions

- capability baseline remains 175;
- capability delta is 0;
- architectural authority delta is 0;
- donor registry count remains 1339 on this branch;
- no child repository donor registration or usage edge;
- no overlap edits to open PR #602 owned Web/Browser contract files;
- deterministic tests cover positive, negative and rollback/recovery semantics;
- dedicated gate fails closed on missing/drifted artifacts;
- runtime/provider promotion remains false;
- exact-head repository gates must be reviewed before merge.
