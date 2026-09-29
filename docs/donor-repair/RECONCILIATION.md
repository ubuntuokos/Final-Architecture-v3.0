# FA3 Donor Registry repair — exact source reconciliation

**Maintenance only.** This branch is NOT planning readiness, runtime admission, or an authorized merge while donor PRs are pending. Main input: `cb3e5b34da3e0f4002f8fb82b4d1c0ae05375194` (592 donors). Across 40 open PRs changing the canonical registry, plus the separately staged 58-source media intake #537 (57 new sources, one previously captured), source-key union results in **1116 distinct donors** after removing three historical alias duplicates. Capability model **175**; dynamic provider count; no new authority.

Open-PR registry sources reviewed: #536, #534, #533, #532, #531, #530, #529, #528, #526, #525, #524, #522, #520, #519, #518, #517, #516, #515, #514, #513, #512, #510, #507, #498, #497, #488, #487, #484, #483, #478, #475, #469, #468, #467, #466, #463, #461, #460, #446, #445, plus staged #537. All 128 then-open PRs were examined for direct changes to the canonical registry; the other 88 did not touch that file.

## Reconciled source aliases

- `project:g'mic` -> existing `FA3-DONOR-G-MIC-001` (`github:greyclab/gmic`), retaining ANALYZED and historical first_seen.
- `project:nvidia-model-optimizer` -> existing `FA3-DONOR-NVIDIA-MODEL-OPTIMIZER-001` (`github:nvidia/model-optimizer`), retaining ACCEPTED_REFERENCE and historical provenance.
- `project:openimageio` -> existing `FA3-DONOR-OPENIMAGEIO-001`, now keyed to `github:academysoftwarefoundation/openimageio`; the old project key is retained as a legacy lookup alias, not a second donor.

## Preserved evidence and remaining tasks

Per-source union statistics, alternate-name conflicts and resolved ID collisions: `docs/donor-repair/batch-01.json` through `batch-09.json`. Source history, candidate status and existing non-admission flags retained. Differing labels of an identical source remain in these audit packets, not discarded silently. No unresolved license/status conflict was identified in these 40 branch registry snapshots. The registry in this branch is structurally coherent, **but NOT globally ready**: donor PRs remain open, individual PR documentation and tests are not merged by the registry union alone, and exact-head current-host/release gates remain pending. Those PRs must be reconciled/closed without source or evidence loss, and a future live pending-PR scan must report zero before new planning or finalization.

## Media intake #537

The 58-source structured delta is now mirrored into canonical staging with status `RECONCILED_IN_REPAIR_BRANCH`, with the exact pending original preserved under `docs/donor-repair/intake-537-original.json`. 57 new source identities and one existing `rikorose/deepfilternet` were upserted, not adopted. PR #537 remains open until exact-head registry reconciliation lands; while it is open, project entry remains blocked.

## Existing Intel regression reconciliation

The merged #469 OpenVINO source observation declares Apache-2.0 at repository level. The Intel ecosystem regression now verifies **only this one source** as `KNOWN_DECLARATION`, while continuing to require `upstream_observation.license_audited == false`, source copying disabled and all other Intel entries at their original unknown-license status. This is not approval to copy code or import models.
