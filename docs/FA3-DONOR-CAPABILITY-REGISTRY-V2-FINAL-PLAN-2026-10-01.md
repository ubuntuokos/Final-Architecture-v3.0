# FA3 Donor & Capability Registry v2 — final plan

**Date:** 2026-10-01
**Status:** OWNER APPROVED / MATERIALIZED SHADOW ARCHITECTURE
**Capability baseline:** 175, unchanged
**Authority delta:** 0
**Canonical donor cutover:** not performed by this change

## Goal

Replace the operational cost of repeatedly scanning one ever-growing donor file with a logical Registry v2 that preserves one donor identity, indexes by application/category and capability, keeps frequently growing donors together, and scales by ordered continuation volumes.

The migration is zero-reentry: existing donor, capability, usage and provenance information is migrated from the existing canonical records. Manual recreation is forbidden as a migration requirement.

## Existing sources remain authoritative until cutover

Registry v2 consumes the published donor registry, application-donor links, 175 capability model and Reuse Catalog. The shadow engine never promotes itself to canonical donor authority. Donor intake remains serialized by the existing lifecycle policy.

## Identity and locality

A donor has exactly one canonical identity: stable donor_id, stable source.normalized_key and stable historical provenance. A donor may be discoverable through several categories, but its full canonical payload is stored in one physical locality. Category files are routing/index structures, not duplicate donor authorities.

Low or unknown-growth donors may share an application/category volume. A donor with high/bursty upstream activity, high/bursty Registry growth impact, or a record too large for the shared target receives a DEDICATED_SERIES location.

This models the bookshelf rule: a frequently expanding series gets one contiguous shelf section with room reserved for later volumes instead of scattering later additions around unrelated shelves.

## Growth-aware intake

When history is available, intake/refresh may supply a source-backed activity observation: commits in the previous 90 days, releases in the previous 12 months, Registry-relevant changes in the previous 90 days, burst behavior and source references.

UPSTREAM_ACTIVITY and REGISTRY_GROWTH_IMPACT are separate values. No activity observation changes admission, license, security or runtime status.

## Capacity policy

The reserve is defined against total planned capacity:

- normal target fill: 70%;
- free growth reserve: 30%;
- at 90%: open/prepare the next continuation volume and stop treating the remaining space as normal new-record capacity;
- at 95%: controlled rebalance is required;
- rebalance deterministically selects the minimum practical donor-record set (largest records first, donor ID as tie-break) needed to restore reserve;
- rebalance stops at 70% or slightly below when an indivisible record crosses the target, restoring at least 30% free reserve;
- the target volume must remain below the 90% rollover threshold, otherwise a new continuation volume is required.

For current used size U:

    capacity >= ceil(U / 0.70)

The physical handling-limit size is not guessed. A measured benchmark must establish it before canonical cutover. The shadow tool therefore requires --handling-limit-bytes explicitly.

## Ordered continuation volumes

A category is one logical dataset even when physically represented by video.001.json, video.002.json and video.003.json. Consumers address donor IDs, categories or capabilities, never physical volume names.

Dedicated donors use donor-series/<donor-id>/record.001.json and later continuation volumes. Later donor-local annexes remain in the same series locality.

## Migration-time refresh

Migration may refresh source-backed metadata, but every change must be auditable, non-destructive, source-backed, separated from governance decisions, and fail closed on conflict. Previous, observed and effective values must remain distinguishable. Refresh cannot silently change rejection, supersession, admission or runtime decisions.

The first shadow materialization performs lossless migration and accepts source-backed activity observations. Upstream metadata refresh and canonical cutover remain later gated migration stages.

The shadow migration also stores an exact byte-preserved source snapshot and verifies **full donor-record semantic parity**, not only ID/count parity. A generated legacy compatibility projection must reproduce the original registry semantics exactly before reader cutover.

## Derived usage and capability views

FA3-APPLICATION-DONOR-LINKS-001 remains the usage declaration source. Registry v2 projects derived views and does not create a second usage authority. The existing donor → capability → consumer graph is reused; CAP IDs are never inferred from names.

Required lookup directions include donor → capability → consumer, capability → donors and consumers, consumer/application → capabilities and donors, source key → donor, category → donor and donor → physical location.

The materialized Resolver exposes donor, category and capability queries. Category/capability queries first resolve IDs and physical volume paths from indexes, so callers do not scan unrelated volumes.

## Shadow migration command

    ./bin/fa3-registry-v2 shadow-migrate \
      --output /tmp/fa3-registry-v2 \
      --handling-limit-bytes <measured-or-test-limit>

It validates the legacy registry, 175 model and application/donor index; preserves every donor ID, normalized source key and full donor record; stores an immutable source snapshot; derives category indexes from existing hints; applies source-backed growth observations when supplied; packs initial volumes to at most 70%; keeps high-growth donors in dedicated series; emits receipts/indexes; and verifies zero-loss semantic parity.

Legacy compatibility can be proven with:

    ./bin/fa3-registry-v2 project-legacy \
      --shadow /tmp/fa3-registry-v2 \
      --output /tmp/fa3-donor-registry-legacy.json

Unknown categorization remains cross-domain/REVIEW_REQUIRED rather than being guessed.

## Cutover sequence

M0 inventory and benchmark.
M1 schemas/resolver/volume manager.
M2 shadow migration.
M3 migration-time source refresh with receipts.
M4 usage/capability equivalence verification.
M5 legacy compatibility projection.
M6 reader cutover.
M7 writer cutover.
M8 Current Host structural alignment and full gates.
M9 atomic canonical manifest switch.
M10 immutable legacy snapshot and rollback path.

This materialization implements M1–M2 and verification foundations on the published donor-lifecycle baseline without creating a second donor-intake authority.

## Required cutover gates

Canonical cutover fails unless donor loss is zero; donor IDs and source keys are unchanged; capability baseline is exactly 175; CAP IDs are unchanged; usage and provenance are preserved; silent merge/governance changes are absent; index integrity passes; every initial volume has at least 30% free logical capacity; 90/95/70 transitions pass; rollback passes; Software Coexistence and Hardware Safety remain satisfied; and Current Host structural alignment is complete.

## Non-goals

Registry v2 does not adopt or install donors, admit providers/models, change the 175 capability baseline, create architectural authority, infer CAP IDs, rewrite history, or claim physical Current Host PASS from static CI.

## Materialized files

- canonical/FA3-DONOR-REGISTRY-V2-POLICY-001.json
- canonical/decisions/FA3-DEC-DONOR-REGISTRY-V2-2026-10-01.json
- canonical/FA3-DONOR-REGISTRY-V2-CURRENT-HOST-IMPACT-001.json
- canonical/schemas/FA3-DONOR-REGISTRY-V2-VOLUME-SCHEMA-001.json
- canonical/schemas/FA3-DONOR-REGISTRY-V2-ACTIVITY-SCHEMA-001.json
- src/fa3_registry_v2.py
- bin/fa3-registry-v2
- tests/test_registry_v2.py
- .github/workflows/fa3-donor-registry-v2.yml

The legacy registry itself remains unchanged until the benchmark, cutover stages and required gates are satisfied.
