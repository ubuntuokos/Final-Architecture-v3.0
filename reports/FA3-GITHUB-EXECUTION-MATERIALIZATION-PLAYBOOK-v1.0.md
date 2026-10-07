# FA3 GitHub Execution & Materialization Playbook v1.0

**Status:** operational coordination projection  
**Date:** 2026-09-16  
**Authority delta:** 0  
**Capability delta:** 0  
**Runtime claims:** none  
**PASS claims:** none

## 1. Purpose

This playbook coordinates concurrent GitHub-side FA3 materialization without creating a new canonical authority, evidence authority, promotion authority, capability, or runtime truth source.

It exists to prevent four failure modes:

1. duplicate materialization of a workstream already owned by another PR/conversation;
2. conflicting edits to shared enforcement, release-projection, or Qt/QML registration surfaces;
3. stale generated release projection content becoming an accidental source of truth;
4. static/reference CI being misreported as real current-host or production evidence.

If this document conflicts with live GitHub state, canonical FA3 records, executable gates, or workstream evidence, those sources win. This document must then be refreshed.

## 2. Authority lock

This playbook is **read-only with respect to architectural truth**.

It MUST NOT:

- define or replace a canonical FA3 profile;
- change the 143-capability release baseline;
- create a new architectural authority;
- mark `PENDING_CURRENT_HOST`, `PENDING_EXECUTABLE_EVIDENCE`, or an equivalent state as PASS;
- promote a provider, runtime, host, application, or release;
- manufacture current-host evidence from GitHub-hosted CI;
- treat a coordination decision as an admission, placement, security, evidence, or lifecycle decision.

Workstream-specific canonical contracts, gates, evidence and promotion rules remain authoritative.

## 3. Hardware workstream exclusion

PR **#205 — `FA3-HARDWARE-FABRIC-RECONCILIATION-001`** is already owned and executed in a separate conversation/workstream.

For this playbook its state is:

`TRACK_ONLY_DO_NOT_DUPLICATE`

Therefore this branch MUST NOT independently edit or rematerialize the hardware reconciliation owned by #205. Its final merged result is consumed later as an integration input. Independent non-hardware work may continue, but accelerator/runtime closure must be reconciled against the final hardware state before promotion.

## 4. Open-workstream snapshot

The 2026-09-16 repository snapshot contains multiple concurrent workstreams. The primary execution set observed during this preflight is:

| PR | Workstream | Coordination state |
|---:|---|---|
| #205 | Hardware Fabric reconciliation | external owner; track only |
| #203 | ROCm accelerator backend | active; shared release projection |
| #202 | Development Mode + Update Fabric | active; shared enforcement + GUI |
| #201 | Accelerator Guard | active accelerator policy |
| #199 | Orchestration Workforce | active; shared enforcement |
| #195 | Tools Fabric + ConvertX | active; shared GUI |
| #186 | Language Fabric + LiteLLM gateway | active; shared enforcement |
| #181 | Blackhole runtime promotion replacement validation | active replacement path |
| #180 | earlier Blackhole runtime promotion path | open but superseded by #181 according to #181 |
| #177 | Marketing + Blackhole security hardening | active security/evidence path |
| #176 | Federated lifecycle + measured compute | dependency base |
| #178 | HU Content Studio + ONNX/CUDA acceptance | explicitly stacked on #176 |
| #187 | Live interpreter GUI | active language/GUI path |
| #155 | OpenModelDB browser/download manager | active model-manager GUI path |
| #152 | Persistent resource strip | active resource GUI path |
| #151 | llmfit Model Manager integration | active model-manager GUI path |
| #150 | Remote AI Hub | active remote-AI GUI path |
| #145 | Manager overlay | active manager path |
| #144 | GUI 0.4 operations surface | active GUI baseline path |
| #138 | mandatory-conversation reconciliation | open legacy reconciliation path |

This is a coordination snapshot, not a second PR registry. Live GitHub state always supersedes it.

## 5. Verified collision surfaces

### 5.1 Unified release projection

The same generated release-projection file is verified as modified by at least PRs #203, #202, #201, #199, #195, #186 and #177:

`canonical/releases/FA3-RELEASE-PROJECTION-POST-V3.0.11-2026-08-30.json`

**Lock rule:** `SERIALIZE_REBASE_RECONCILE`.

After one of these PRs lands, remaining affected PRs must be rebased/reconciled against the newest accepted `main`, and the repository's existing projection mechanism must be allowed to regenerate/reconcile the release surface. A stale generated file must not be hand-selected as architectural truth.

### 5.2 Permanent/static dispatcher

`bin/fa3-enforce` is verified as concurrently modified by PRs #202, #199 and #186.

**Lock rule:** `SERIALIZE_DISPATCHER`.

After each accepted merge:

1. rebase the remaining affected PRs;
2. preserve all still-required dispatcher commands/gates;
3. rerun their focused regression suites;
4. rerun the repository's applicable permanent/static enforcement path.

No workstream may resolve the conflict by silently dropping another workstream's gate registration.

### 5.3 Native Control Center build/registration

`apps/fa3-control-center/CMakeLists.txt` is verified as concurrently modified by PRs #202, #201 and #195. Several other open GUI PRs also touch the Control Center surface.

**Lock rule:** `SERIALIZE_GUI_WIRING`.

Every reconciliation must preserve all still-valid page/service registrations and be followed by the relevant Qt/QML build/static GUI validation. A successful merge conflict resolution is not itself GUI evidence.

## 6. Dependency and replacement rules

Three edges are already explicit in the open PR metadata:

- #181 **supersedes #180** as the replacement validation path. The execution lane must not merge both as independent solutions.
- #178 is **stacked on #176**. Its integration must preserve the dependency relationship or be rebased onto the accepted equivalent base.
- #202 delegates accelerator contention semantics to **#201 `FA3-ACCEL-GUARD-001`**. Development/Update current-host closure must therefore consume the accepted Accelerator Guard contract rather than recreate its policy.

The same rule generalizes: when a PR explicitly delegates to an existing FA3 authority/profile, the consumer may integrate against it but must not recreate that authority locally.

## 7. Execution lanes

### Lane A — externally owned hardware

- Track #205 only.
- Do not duplicate hardware canonical/runtime/evidence work in this branch.
- Independent authoring may proceed.
- Before accelerator-dependent closure/promotion, reconcile against the final accepted hardware state.

### Lane B — shared enforcement and release projection

Includes at minimum #202, #199 and #186, plus any workstream discovered to touch the same dispatcher/projection surfaces.

- Merge/reconcile one shared-hotspot change at a time.
- Rebase remaining branches after each accepted merge.
- Re-run static/global gates after the combined surface exists.

### Lane C — accelerator policy/providers

Includes #201 and #203, with #205 as a semantic integration input.

- Provider-specific compatibility constraints may remain provider-local.
- Global hardware/admission semantics must not be redefined by a provider.
- Current-host PASS requires the provider/workstream's real trusted-host evidence path.

### Lane D — native GUI integration

Includes #202, #201, #195 and the other open Control Center PRs.

- QML/CMake registration is serialized.
- Combined GUI validation occurs after reconciliation, not merely on isolated feature heads.
- GUI remains a projection/intent surface and does not gain backend authority through merge order.

### Lane E — dependent/replacement work

- Select the non-superseded Blackhole path (#181 over #180 unless repository state changes).
- Preserve #176 -> #178 dependency semantics.
- Do not merge both predecessor and replacement paths merely because both remain open.

## 8. Standard workstream lifecycle

For every materialization workstream, use this order unless its canonical contract is stricter:

1. **Preflight** — identify existing authority, open owner PR, dependency edges, shared files and generated surfaces.
2. **Authority lock** — confirm `authority_delta` and `capability_delta`; reject accidental parallel authorities.
3. **Feature materialization** — canonical/provider/runtime/GUI/test work only inside the workstream's accepted scope.
4. **Focused static validation** — run feature tests and fail-closed gates.
5. **Shared-surface reconciliation** — rebase and reconcile dispatcher, release projection and GUI registration against newest `main`.
6. **Global static validation** — execute the repository's applicable permanent canonical/promotion/static gates.
7. **Merge prerequisite check** — dependencies and replacement edges must be resolved.
8. **Trusted current-host execution** — run only the workstream's admitted current-host collector/workflow on the trusted host path.
9. **Evidence write** — create/update evidence only from actual receipts; otherwise retain PENDING state.
10. **Promotion/closure** — only the workstream's canonical acceptance/evidence authority may declare its supported terminal state.

## 9. Current-host truth boundary

GitHub-hosted/reference/static success is useful but insufficient for claims that require the real host.

The following are forbidden shortcuts:

- CI PASS -> `CURRENT_HOST_PASS` inference;
- documentation -> runtime evidence inference;
- design evidence -> production E2E inference;
- provider availability -> admission inference;
- a successful build -> measured execution inference;
- a GUI build -> backend runtime readiness inference.

Where a workstream is `PENDING_CURRENT_HOST`, it stays PENDING until the required trusted runner/collector produces the required receipt and its gate accepts it.

## 10. Merge/reconciliation algorithm for shared hot spots

For `bin/fa3-enforce`, the release projection, Control Center registration, or any newly discovered common surface:

1. choose one PR as the next integration candidate based on its real dependencies, not PR number alone;
2. verify its required checks on its current head;
3. merge only when repository rules and dependencies allow it;
4. update/rebase every remaining PR that touches the same surface;
5. regenerate generated artifacts through the repository mechanism;
6. inspect the semantic combined diff — not only conflict markers;
7. run focused tests for all affected workstreams;
8. run the applicable global/static gate;
9. only then proceed to the next PR in that collision group.

This prevents a green isolated PR from deleting or weakening a gate introduced by a previously merged PR.

## 11. Completion semantics

This playbook itself never reaches a canonical `PASS` or `CANONICAL_CLOSED` state because it has no such authority. Its useful completion condition is simply:

`COORDINATION_STATE = CONSISTENT_WITH_LIVE_REPOSITORY`

A workstream is only complete according to its own canonical requirements. In particular, a runtime-dependent workstream cannot be closed merely because this playbook records that its static branch is green.

## 12. Machine-readable companion

The current coordination snapshot is stored at:

`reports/fa3-github-execution-control-snapshot-2026-09-16.json`

It is intentionally non-authoritative and contains explicit `authority_delta: 0`, `capability_delta: 0`, empty runtime claims and empty PASS claims.

## 13. Next execution rule

After this coordination PR is accepted, subsequent conversations/workstreams should begin by checking live open PRs and this playbook before writing. If ownership already exists, they should continue or reconcile that owner branch rather than create a duplicate implementation.
