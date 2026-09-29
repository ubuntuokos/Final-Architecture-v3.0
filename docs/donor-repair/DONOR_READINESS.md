# FA3 donor readiness: mandatory serialization and approval

The canonical Donor & Reference Registry remains the only donor catalog and grants no execution authority.

* Maintenance mode validates exact local registry identity, cardinality, source keys, aliases, statuses and all deny-by-default flags. It never authorizes planning.
* Status mode additionally lists every live open GitHub PR and every PR's changed files. Unreadable or truncated GitHub evidence, a moving main SHA or any donor-editing PR blocks the start of all planning, implementation and finalization.
* Entry mode also requires a committed Reuse Assessment bound to the exact donor registry SHA256, including either REVIEWED_MATCH or REVIEWED_NO_MATCH. Donor adoption is optional; each explicitly selected donor requires a user-approved canonical decision. This gate never authorizes code copying, installation, provider or model admission.
* Finalize mode additionally requires an exact-HEAD committed approved plan bound by SHA256 to a canonical human-approved decision and explicit repository-owner APPROVED review of the current head; existing Security Governance, evidence and promotion gates are still mandatory.

CLI: PYTHONPATH=src python3 src/fa3_donor_readiness.py --phase maintenance

After source reconciliation and closure of all donor maintenance PRs, use --phase entry --assessment canonical/assessments/<assessment>.json with GITHUB_TOKEN from the existing Secret Broker or GitHub Actions environment. No tokens in chat, logs or committed files.

Limit: live PR checks detect known GitHub work but do not constitute an atomic distributed lease against unregistered off-GitHub mutations. Release-wide orchestration and a required branch-protection check still must consume this gate. While donor PRs remain pending, global readiness is BLOCKED.

## 2026-09-29 hidden donor-reference detection hardening

Audit of the complete post-reconciliation open-PR file inventory uncovered #435: its PR title was generic and its central-registry file did not change, but it created a separate `canonical/references/*DONOR*` reference set. The original branch remains archived in recovery #540; it was not merged. The canonical preflight and CI maintenance classifier now recognize donor reference-set files, donor intake deltas, donor research and application/donor index changes as pending maintenance, even when the PR title is generic. They still do not treat ordinary Reuse Assessments as registry mutation. A reference catalog is not a second donor authority, and its candidate pins are not automatic code import or provider admission.

## 2026-09-29 P0 maintenance exemption: repair always remains possible

Donor Registry repair, intake reconciliation, historical preservation and protection of the **existing** donor gate are maintenance work, not new application planning, development or finalization. They MUST proceed through the maintenance-only path even when donor PRs are pending, the registry is corrupt, an application Reuse Assessment is unavailable or an approved *application* plan does not exist. These conditions block non-maintenance work, never the act of fixing its donor dependency. No separate application-plan approval or new-development preflight may be imposed on maintenance. The maintenance workflow must recognize its own narrowly scoped changes and may report non-PASS registry integrity until the repair is coherent; this is not authority to call the registry ready. Existing evidence, source-history, safety, security, exact-head verification and serial maintenance requirements remain in force. No concurrent second registry, runtime admission or application implementation is authorized.

## 2026-09-29 explicit donor-maintenance operations

For the P0 maintenance exemption, **donor maintenance includes** (1) expansion of the existing donor registry with new sources, metadata, aliases or provenance, (2) removal of donor entries from the active candidate set, with historical evidence, identity and removal rationale preserved in the existing canonical history, and (3) synchronization/reconciliation of already recorded donor data across the existing registry, intake, source identities, aliases, historical provenance, application/donor index and donor-derived release projection. These operations and their protective checks are **maintenance only**: they may proceed even while normal design, development and finalization are blocked. A synchronization touching donor-derived release-projection fields does not authorize unrelated release/application edits. Deletion of historical evidence is never implied by active-set removal. Serial maintenance, exact-head CI, provenance and existing security governance still apply. No new donor registry, separate authority, unapproved donor adoption or application implementation is permitted.
