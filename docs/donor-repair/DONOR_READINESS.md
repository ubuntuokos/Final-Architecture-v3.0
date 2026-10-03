# FA3 donor readiness: mandatory serialization and approval

The canonical Donor & Reference Registry remains the only donor catalog and grants no execution authority.

* Maintenance mode validates exact local registry identity, cardinality, source keys, aliases, statuses and all deny-by-default flags. It never authorizes planning.
* Status mode additionally lists every live open GitHub PR and every PR's changed files. Unreadable or truncated GitHub evidence, a moving main SHA, corrupt registry, or a local snapshot that differs from the published main registry blocks planning, implementation and finalization. Pending donor PRs are listed, but do not block work against that exact committed main snapshot.
* Intake mode also checks the live PR inventory. Only PRs that actually change the canonical registry or a canonical donor-intake delta claim an intake slot. At most five such PRs are active; FIFO admits the next waiting PR whenever a slot is released. Within the active five, finalization is ascending by canonical donor-mutation workload, with FIFO for equal workloads. A sixth or later PR returns DONOR_INTAKE_ACTIVE_WINDOW_FULL_WAIT_FOR_SLOT; an active non-smallest PR returns DONOR_INTAKE_ACTIVE_WAIT_FOR_SMALLER_FINALIZATION. Local imports retain a nonblocking single-writer filesystem lock.
* Entry mode also requires a committed Reuse Assessment bound to the exact donor registry SHA256, including either REVIEWED_MATCH or REVIEWED_NO_MATCH. Donor adoption is optional; each explicitly selected donor requires a user-approved canonical decision. This gate never authorizes code copying, installation, provider or model admission.
* Finalize mode additionally requires an exact-HEAD committed approved plan bound by SHA256 to a canonical human-approved decision and explicit repository-owner APPROVED review of the current head; existing Security Governance, evidence and promotion gates are still mandatory.

CLI: PYTHONPATH=src python3 src/fa3_donor_readiness.py --phase maintenance

With a verified committed main snapshot, use --phase entry --assessment canonical/assessments/<assessment>.json with GITHUB_TOKEN from the existing Secret Broker or GitHub Actions environment. No tokens in chat, logs or committed files.

Limit: live PR checks detect known GitHub work but do not constitute an atomic distributed lease against unregistered off-GitHub mutations. Release-wide orchestration and a required branch-protection check still must consume this gate. Pending donor PRs do not block design/finalization on the published exact main registry. A second intake remains BLOCKED. Unmerged sources must never enter an assessment; new publication never automatically re-runs prior work.

## Automatic donor count refresh and validation

Every authorized capture and staged batch import writes through
`fa3_donor_registry._atomic_write`, which calls `refresh_donor_count`
before the atomic registry replacement. Counts are derived from the
actual source-unique entry set after each operation, not from hard-coded
expected totals or an incremented counter. An incoming registry with
an already stale count is refused by normal intake; malformed/duplicate
IDs or source keys and any altered capability baseline are never
silently corrected.

After an explicitly reviewed **external JSON maintenance edit** (such
as a GitHub donor-batch commit, removal, or historical reconciliation),
run `PYTHONPATH=src python3 src/fa3_donor_registry.py --refresh-count`
on the working branch before committing its registry change. Use
`--dry-run` to preview; it never writes. This dedicated maintenance
operation does **not** approve donor adoption or bypass serialized
publication. The read-only readiness gate still detects stale counts
and fails closed; it must never update evidence implicitly.

The mandatory donor-serialization workflow runs count-refresh
regression tests alongside readiness tests. A donor batch that omits
the refreshed count fails CI before publication; manual count
editing is neither required nor an accepted substitute for using
the shared writer or reconciliation command.

## 2026-09-29 hidden donor-reference detection hardening

Audit of the complete post-reconciliation open-PR file inventory uncovered #435: its PR title was generic and its central-registry file did not change, but it created a separate `canonical/references/*DONOR*` reference set. The original #435 PR was closed without merge; issue #540 preserves its exact head and holds the non-donor application changes, and the original Git history remains available. The canonical preflight and CI maintenance classifier now recognize donor reference-set files, donor intake deltas, donor research and application/donor index changes as pending maintenance, even when the PR title is generic. They still do not treat ordinary Reuse Assessments as registry mutation. A reference catalog is not a second donor authority, and its candidate pins are not automatic code import or provider admission.

## 2026-09-29 P0 maintenance exemption: repair always remains possible

Donor Registry repair, intake reconciliation, historical preservation and protection of the **existing** donor gate are maintenance work, not new application planning, development or finalization. They MUST proceed through the maintenance-only path even when donor PRs are pending, the registry is corrupt, an application Reuse Assessment is unavailable or an approved *application* plan does not exist. These conditions block non-maintenance work, never the act of fixing its donor dependency. No separate application-plan approval or new-development preflight may be imposed on maintenance. The maintenance workflow must recognize its own narrowly scoped changes and may report non-PASS registry integrity until the repair is coherent; this is not authority to call the registry ready. Existing evidence, source-history, safety, security, exact-head verification and serial maintenance requirements remain in force. No concurrent second registry, runtime admission or application implementation is authorized.

## 2026-09-29 explicit donor-maintenance operations

For the P0 maintenance exemption, **donor maintenance includes** (1) expansion of the existing donor registry with new sources, metadata, aliases or provenance, (2) removal of donor entries from the active candidate set, with historical evidence, identity and removal rationale preserved in the existing canonical history, and (3) synchronization/reconciliation of already recorded donor data across the existing registry, intake, source identities, aliases, historical provenance, application/donor index and donor-derived release projection. These operations and their protective checks are **maintenance only**: they may proceed even while normal design, development and finalization are blocked. A synchronization touching donor-derived release-projection fields does not authorize unrelated release/application edits. Deletion of historical evidence is never implied by active-set removal. Serial maintenance, exact-head CI, provenance and existing security governance still apply. No new donor registry, separate authority, unapproved donor adoption or application implementation is permitted.

## Held #435 source identity reconciliation (donor metadata only)

The seven upstream GitHub repository identities and immutable commit SHAs in original #435 reference-set Git blob `61997f1a5fb988b1d7dfb952fb7caa467742b355` were independently resolved through the GitHub repository and commit APIs on 2026-09-29. The existing canonical donor record for `Anil-matcha/Open-Generative-AI` retained its upstream key. Six existing `project:`-key records (Donkey, OpenCut, hyperframes, vibe, Wan2.2, presenton) were normalized **in place** to those exact verified upstream GitHub repository keys, preserving their historical project keys as `legacy_source_keys`, their previous locators, status, research, targets and license gates. The upstream commit pins are attached to the seven existing records with original PR lineage. Canonical donor count remains **1116**, capability baseline **175**; no independent reference-set authority or automatic code import, provider/model admission or implementation is created. GitHub repository license metadata is not file-level license clearance. The historical #435 application code remains on hold under issue #540.

## 2026-09-29 historical owner rule: strict marker and single intake (superseded 2026-10-03)

Historical retrospective PR extraction is optional and the 14 original PR exemptions stand. Only a LINK introduced by the owner with explicit `donornak` label (with or without a colon) preceding it is eligible for donor registration; a single marker may introduce a clear multi-link batch. `donor:`, `potential donor`, assistant research and unmarked links may be analyzed but MUST NOT create, queue, modify, sync or promote donor records without later explicit owner instruction. Authenticated marked links finalize as `ACCEPTED_REFERENCE` on published intake without a second catalog approval. This does not grant source adoption or runtime admission.

From 2026-09-29 until superseded on 2026-10-03, exactly one conversation could carry out donor intake at a time. That exclusivity rule is historical only. Current behavior is governed by `FA3-DEC-DONOR-INTAKE-CONCURRENCY-2026-10-03`: up to five genuine canonical donor-intake requests are active in a rolling FIFO window; finalization is smallest-workload-first with FIFO ties. Local file locking still guards same-checkout writes, and off-repository importers must participate in the existing shared orchestrator before publication.

All other FA3 work is allowed to continue during donor maintenance, using ONLY the latest committed, validated main registry SHA. Pending PRs and working-copy registry edits are not admissible donor inputs. On main publication, rerun old plans or finalized outputs only when the owner explicitly requests it. A stale/corrupt or unverified main snapshot still fails closed. No new donor authority or parallel registry is created.

## P0 donor planning snapshot and shared-placement gate (2026-10-01)

Every new or materially modified FA3 application, capability, module, profile, provider or shared component must carry a fresh Reuse Assessment bound to the exact published-main donor planning snapshot used for the design. The assessment records `published_main_commit`, donor registry Git-blob SHA, SHA-256 and entry count in `donor_planning_snapshot`. Pending PR donor data is never a planning input.

The same assessment must record `shared_capability_placement`. Multi-application functions are shared-first; a local duplicate is valid only with an explicit reviewed justification and retrospective impact review covering planned, in-progress and materialized consumers. Existing verified capability may not be lost during migration.

Entry/finalize readiness rechecks the assessment against the live published main. If main or the donor registry changed after planning, finalization is blocked until a fresh assessment is produced. This is reassessment, not automatic redesign. Actual donor adoption still requires the canonical usage edge in `FA3-APPLICATION-DONOR-LINKS-001`; reference-only analysis must not fabricate an adoption edge.
