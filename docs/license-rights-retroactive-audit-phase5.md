# FA3 License & Rights retroactive audit — Phase 5

Phase 5 normalizes the distinction between an **FA3-authored canonical metadata
file** and the **external rights subject** described by that file.

## Why this is required

A file such as `canonical/references/EXAMPLE.json` is repository-native
metadata. Its presence does not mean that upstream source code is copied into
FA3, and the metadata file itself must not be treated as though it were the
external project's source tree.

Conversely, classifying the metadata file as FA3-authored must never erase the
external project's rights obligations. The external subject remains a separate
audit object.

## Evidence-backed reference-only resolution

An excluded external subject may be classified as
`REFERENCE_ONLY_EVIDENCE_BACKED` only when all of the following are true:

1. distribution class is exactly `REFERENCE_ONLY`;
2. release bundle status is exactly `EXCLUDED`;
3. an immutable 40- or 64-hex source revision is recorded;
4. a non-UNKNOWN license value is recorded;
5. concrete license evidence is recorded (for example `license_blob_sha`).

This resolution means that the **reference-only provenance record is complete
enough for the current no-bundle use**. It is not a general legal clearance and
does not permit copying, bundling, runtime admission, model admission, provider
promotion, trademark use, or redistribution of upstream material.

## Fail-closed cases

The subject remains `REVIEW_REQUIRED` when, among other cases:

- the license is unknown, unverified or pending;
- only a floating branch/tag is recorded;
- immutable provenance is missing;
- the subject is not REFERENCE_ONLY;
- distribution status is not EXCLUDED.

## Audit consequence

This phase may reduce duplicate or incorrectly modeled work-queue items. It does
not close the repository-wide audit. The canonical audit remains
`IN_PROGRESS_RETROACTIVE_AUDIT`, `release_eligible = false`, and historical
evidence remains append-only.
