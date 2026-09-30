# FA3 retroactive License & Rights audit

The retroactive audit exists to classify historical repository content without
assuming that a root-level license proves ownership of every old file.

## Current repository snapshot

Audit anchor: `0240bae4100d0410a11c3026657ba28af508c893`

The anchored tree contains 2636 tracked blobs. The initial structural inventory
found:

- 7 physically copied upstream research-snapshot files;
- 5 documentation SVG assets;
- 0 font files;
- 0 model-weight/model-binary files;
- 0 external subjects included in the canonical product distribution manifest.

Canonical reference records and third-party metadata records are FA3 metadata;
they do not, by themselves, mean the referenced upstream source is bundled.

## Proven copied upstream material

The only structurally detected vendored upstream snapshot is the pinned
`logicrw/awesome-jev-projects` research snapshot. Its exact pinned upstream
commit declares MIT and the exact LICENSE blob has been retained locally under
`LICENSES/third-party/`. The seven snapshot files therefore have a concrete
rights descriptor and attribution notice.

## What remains blocked

The audit is **not complete** merely because the copied upstream snapshot has
been resolved. Before repository/release audit PASS, FA3 still requires:

1. historical first-party origin/ownership attestation or equivalent evidence;
2. origin evidence for the five documentation SVG assets;
3. complete machine-readable file-level license coverage (REUSE/SPDX);
4. release SPDX and CycloneDX SBOM evidence;
5. zero unresolved license conflicts and zero required unknown rights facts.

The audit remains fail-closed and does not alter historical evidence.
