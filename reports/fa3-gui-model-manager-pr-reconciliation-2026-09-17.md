# FA3 GUI / Model Manager stale PR reconciliation — 2026-09-17

Status: OPERATIONAL / NON-AUTHORITATIVE

## Scope

This reconciliation evaluates PR #144 (FA3 GUI 0.4) and PR #155 (OpenModelDB browser/download manager) against the current `main` after the hardware-fabric and workload-driven resource-admission reconciliations.

## Current baseline

- `main` is the only integration base for further Control Center work.
- `FA3-HARDWARE-FABRIC-RECONCILIATION-001` (#205) is merged.
- `FA3-RESOURCE-ADMISSION-RECONCILIATION-001` (#207) is merged.
- Control Center shared wiring follows `SERIALIZE_GUI_WIRING`.
- Release projection follows `SERIALIZE_REBASE_RECONCILE`.
- Capability and authority counts are unchanged by this operational decision.

## PR #144 decision

Decision: `SUPERSEDED_BY_CURRENT_MAIN_EVOLUTION`.

Do not merge or mechanically rebase PR #144.

Reasons:

- The branch is deeply divergent from current `main` and edits shared Control Center registration, CMake, QML shell, repository model, GUI gates and release projection.
- Current `main` already contains a newer Control Center architecture, including `ModelsProvidersPage.qml`, `SystemSettingsPage.qml`, `LanguageControlPage.qml`, `ModelLibraryService`, `SystemDeviceModel`, current hardware observation semantics and current resource-admission contracts.
- PR #144 contains its own `LlmfitClient` / `LlmfitPanel` implementation, which duplicates the dedicated llmfit workstream in PR #151.
- Any still-useful UX concepts from #144 must be re-materialized selectively from current `main`; the old branch is not an integration source of truth.

Residual feature ideas from #144 are explicitly not blockers for PR #151. They may be handled later as isolated current-main workstreams.

## PR #155 decision

Decision: `SUPERSEDED_AS_BRANCH; FEATURE_INTENT_RETAINED`.

Do not merge or mechanically rebase PR #155.

Current `main` already contains the canonical OpenModelDB provider integration under `FA3-MODEL-MANAGER-001` and the current `ModelsProvidersPage.qml`. The old PR also carries a stale `LegacyMain.qml` shell strategy and edits shared GUI/release surfaces from an obsolete baseline.

The following feature intent remains valuable and should be re-materialized later on current `main` only:

- native OpenModelDB catalog browsing;
- upstream tag/category/color projection;
- model/resource filtering;
- staged download queue with cancel/retry;
- SHA-256 verification before artifact admission;
- staging only, never direct runtime-store promotion;
- Model Artifact Security and measured runtime evidence remain mandatory after download.

This retained feature intent must use the current Model Manager, ModelLibraryService, Model Artifact Security, workload-driven resource-admission and current Control Center wiring. It must not restore the stale `LegacyMain.qml` architecture.

## Existing reconciliation branch quarantine

Branch `reconcile/gui-model-manager-2026-09-17` exists, but it is **not** an approved integration source.

Decision: `QUARANTINED_NOT_INTEGRATION_SOURCE`.

Reasons:

- it combines llmfit/OpenModelDB reconciliation with unrelated language, tools, update and remote-AI changes;
- it contains tracked generated/build outputs under `build/fa3-control-center/**`;
- it is already divergent from current `main`;
- it has no pull request establishing a reviewable integration boundary;
- using it as the base for #151 would violate the serialized shared-GUI integration rule.

Useful source fragments may be inspected for reference, but all accepted implementation must be re-materialized from current `main` on a clean, scoped branch.

## Sequencing decision

The stale shared-GUI workstreams are cleared before llmfit repair:

1. Close #144 as superseded.
2. Close #155 as superseded-as-branch while preserving its OpenModelDB UX intent in successor issue #220.
3. Quarantine `reconcile/gui-model-manager-2026-09-17` as non-integration reference only.
4. Reconcile PR #151 from current `main` using current hardware and resource-admission semantics.
5. Only after #151 is reconciled, re-materialize the retained OpenModelDB catalog/download UX on the then-current Model Manager surface.

## Authority and evidence invariants

- No stale PR or unreviewed reconciliation branch may overwrite current hardware semantics.
- Raw/provider hardware observations remain non-authoritative.
- HRB remains admission/placement/reservation/lease authority.
- Resource classes are derived from workload requirements.
- CPU/memory-only workloads must not imply accelerator requirements.
- Provider estimates and discovery metadata are not runtime evidence.
- Static/reference success is not current-host production PASS.
