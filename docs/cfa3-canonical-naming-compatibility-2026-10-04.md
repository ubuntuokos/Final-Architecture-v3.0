# CFA3 canonical naming and backward-compatibility policy — 2026-10-04

**Status:** owner-approved policy materialization.

## Canonical identity

The final canonical product/system name is **CFA3**.

The following natural-language system references are semantically equivalent:

- `CFA3`
- `FA3`
- `FA3/CFA3`
- `CFA3/FA3`

They refer to one system. `FA3` records the historical origin of the project; it is not a second product.

## Retroactive interpretation

The equivalence is both retroactive and forward-looking. Historical plans, decisions, donor analyses, capability records, PR descriptions and documentation that refer to FA3 are interpreted as references to the system now canonically named CFA3.

This does **not** authorize rewriting history.

## Non-destructive compatibility

Do not rename or rewrite historical commits, commit SHAs, merged/closed PR history, audit/evidence records, published canonical IDs or historical test evidence merely to replace the text FA3 with CFA3.

Existing machine-readable identifiers such as `FA3-*`, `fa3.*`, `fa3_*`, filenames, schema IDs, decision/profile IDs, namespaces, API/ABI identifiers, environment variables, storage paths and automation contracts may remain unchanged for compatibility.

A literal machine identifier rename requires its own explicitly approved compatibility migration. Bulk search-and-replace is forbidden.

## New content

Use **CFA3** as the primary user-facing, planning and documentation name. When migration context is useful, `CFA3 (formerly FA3)`, `FA3/CFA3` and `CFA3/FA3` remain valid.

For new machine identifiers, prefer CFA3 only when doing so is compatible with established canonical conventions and does not break referential integrity.

## Architecture impact

This policy creates no new capability and no new architectural authority.

- capability baseline: **175**
- capability delta: **0**
- authority delta: **0**
- donor delta: **0**
- Current Host runtime impact: **none**

The canonical machine-readable policy is `canonical/FA3-CFA3-CANONICAL-NAMING-COMPATIBILITY-POLICY-001.json`.
