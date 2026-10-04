# FA3 EcoPasteHub GitHub organization donor intake — 2026-10-04

## Owner marker

The owner explicitly marked the exact source `https://github.com/EcoPasteHub` as **donornak** on 2026-10-04.

## Source classification

- canonical source key: `github:ecopastehub`
- donor id: `FA3-DONOR-ECOPASTEHUB-ORG-001`
- source kind: `GITHUB_ORGANIZATION`
- status: `ACCEPTED_REFERENCE`
- mode: metadata-only `DISCOVERY_INDEX`
- observed public child repositories during intake scan: **4**
- capability delta: **0**
- authority delta: **0**
- capability baseline: **175**
- runtime impact: **NO_RUNTIME_IMPACT**

Organization-level registration is a discovery index only. It does not recursively admit repositories, source code, packages, runtimes, services, providers or dependencies.

## High-value FA3 discovery areas

The principal observed project, `EcoPasteHub/EcoPaste`, is a local-first Rust/Tauri clipboard manager. High-value reference material includes:

- multi-format clipboard capture for text, HTML, RTF, images, files and folders;
- source-application provenance and application exclusion;
- BLAKE3 content-hash deduplication;
- content-hash-based writeback loop suppression;
- SQLite FTS5 local search and pagination;
- sensitive-content detection/redaction/skip policy;
- encrypted local backup using Argon2id and XChaCha20Poly1305;
- native global shortcuts, tray integration and drag-out;
- live storage-root relocation and local-first persistence patterns.

The organization also exposes documentation, branding and Homebrew distribution repositories.

## License, platform and runtime boundary

The observed `EcoPasteHub/EcoPaste` root declares Apache-2.0 at upstream head `5139d30b0f4c1309356a9b308c05092f1038bc9b`. This observation does not bypass exact provenance, dependency, asset, security or License & Rights review for any material reuse.

EcoPaste explicitly scopes upstream support to macOS and Windows. FA3 must not inherit that limitation for shared clipboard/capture capabilities. Linux support and existing FA3 host/platform requirements remain mandatory.

## Candidate FA3 targets

Likely future target surfaces include:

- Shared Clipboard & Transfer Core;
- Capture & Inbox Fabric;
- Security / Privacy Guard;
- Shared Search / Indexing Fabric;
- File / Project / Asset handoff;
- shared desktop integration and application-to-application transfer surfaces.

## Admission boundaries

No code is copied and no package is installed. No runtime, provider, model, dependency, service or child repository is admitted. No usage edge is created by this intake.

Material child-repository adoption requires exact-source provenance, License & Rights clearance, security review, Software Coexistence review, platform/runtime review, capability/layer placement, canonical typed usage-edge registration and Current Host requalification only when runtime behavior is actually affected.

The fixed FA3 capability baseline remains **175**.

## Rolling intake state

This intake is one-source metadata-only work. Earlier open donor-intake PRs already occupy the canonical rolling order, so this request is created as **draft / FIFO waiting** and must not be finalized ahead of them.
