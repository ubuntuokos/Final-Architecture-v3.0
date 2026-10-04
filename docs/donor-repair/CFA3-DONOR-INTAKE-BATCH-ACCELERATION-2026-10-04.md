# CFA3 donor-intake batch acceleration — 2026-10-04

## Goal

Remove donor-intake PR backlog without weakening donor provenance, License & Rights, Security Governance, Software Coexistence, Hardware Safety, Reuse Discovery, release-projection or protected-main checks.

## Executed backlog strategy

The 15 open donor-intake PRs are reconciled into one current-main batch. Only their donor/reference delta is retained. Historical branches and exact heads remain provenance; stale feature or workflow payload is not rebased or merged.

Parent registry: 1427 entries. Exact source-key union: 85 new identities. Target registry: 1512 entries. Capability delta: 0. Authority delta: 0. Usage-edge delta: 0.

The exact union and source PR heads are recorded in `canonical/deltas/CFA3-DONOR-BACKLOG-CONSOLIDATION-2026-10-04.json`.

## Permanent acceleration model

CFA3 keeps at most five concurrently collected donor-intake work items, but only one canonical registry mutation PR may exist at a time. New owner-marked donor submissions append to the current rolling batch when one exists instead of opening another registry-mutating PR.

Each append gets a fast donor preflight: schema, normalized source identity, donor-ID/source-key uniqueness, provenance, rights metadata presence, fixed 175 capability baseline, zero authority delta and derived donor count. The expensive repository-wide protected checks run once on the final batch head.

A queue-only or pending donor never becomes a planning input. Planning continues to use only the latest verified committed-main donor registry.

## Stale PR handling

An old donor PR is never repaired by blindly rebasing hundreds of unrelated commits. Its exact donor delta is rehydrated onto current main, deduplicated by normalized source key, and bound to its original PR number and head SHA. Non-donor payload is excluded.

If a source itself has moved, been archived or deleted, or its license/security state materially regressed, it is reclassified before adoption. Backlog consolidation itself does not claim a new upstream network validation, code reuse, provider admission, model admission or runtime promotion.

## Finalization

The batch must pass donor serialization, Reuse Discovery, Permanent Canonical + Promotion, release-projection reconciliation and all existing protected checks on one exact head. After successful publication, the constituent source PRs are closed as superseded with their exact heads preserved.
