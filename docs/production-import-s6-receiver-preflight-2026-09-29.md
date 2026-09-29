# FA3 S6 — szelektív produkcióimport: célalkalmazás és gép szerinti fogadó-ellenőrzés

Date: 2026-09-29. Parent: [PR #528](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/528), [17 immutable selector labels](production-import-selective-content-plan-2026-09-29.md), [S5 combined delivery intents](production-import-s5-delivery-preview-2026-09-29.md), [historical conversion reconciliation](production-import-historical-conversion-reconciliation-2026-09-29.md).

Status: **S6 synthetic, side-effect-free PREVIEW_ONLY implementation**. No application RPC, actual file or AV inspection, conversion, model inference, publication, desktop build, verified receiver registration, remote transfer, current-host execution or production admission. No new conversion authority, host planner, software daemon, database, public port, fixed model, additional capability, provider, or donor copy. Canonical capability baseline remains **175**, providers dynamic. Existing source-family-scoped **TEXT 4 / AUDIO 6 / VIDEO 7** are unchanged.

## 1. User outcome

One original video can request, in a single user-approved plan:
- only silent picture to Video Editor on a designated FA3 host,
- timed original/Hungarian/German transcript **without AV publication** to Subtitle Studio on a different authorized host,
- authorized original instrumental stems to Music Studio,
- genuine separately verified ambience/SFX to Sound Design, or an explicit *unsupported/estimated* status if source and admitted specialist cannot isolate it.

One receiving app must not be substituted for another, and a failed named leaf must not prevent unrelated approved leaves from remaining individually inspectable. One requested language is one independently identified delivery intent. All derivatives preserve original source SHA-256, requested selector, source stream/timebase, source span, language/stem variant and S5 independent gates.

## 2. Bounded recipient inventory and exact binding

New **subordinate planning schema**, not a new discovery authority: `fa3.receiver-capability-claims.v1` is a caller-supplied *untrusted snapshot* of claimed app/host registrations and exact format/version/selector/content/delivery support. Real receiver capabilities and installed application versions come only from the existing FA3 Application Catalog, authorized app receiver declaration, installer-validated machine role, Security/Identity and actual application handshake. A caller-provided `ref:...` receipt is only an opaque **claim** until canonical Evidence independently authenticates it.

`receiver_handoff_preview(S5, claimed_inventory, explicit_placements)`:
1. Re-check S5 source identity, fixed 175, per-leaf original **not published, not approved** flags, uniqueness, approved canonical selector/target identities and the explicit requested publication class.
2. For each S5 derived language/stem/media deliverable, require a user-selected **exact app, host, output format ID and format version**. No “first available host” selection, app remapping, cross-host secret sharing or silent format downgrade.
3. Match the receiver's advertised app **and** host, selector **and** family, delivery type, content class (text / audio / video / AV), format **and** version; normalize none implicitly. Require bidirectional *claimed* support for editable copy, then separately verify real external same-format/version/feature round-trip before editable project promotion.
4. Return a deterministic idempotency **intent** fingerprint bound to source hash, selected output and target; this is not authorization or an executable UAF idempotency token. Maintain duplicate-language destination review, unsupported isolated stems and all upstream S5 blocking states.
5. Every match remains `PENDING_INDEPENDENT_RECEIVER_HANDSHAKE_AND_ADMISSION`. Every missing placement, absent exact receiver or incompatible format has an explicit non-success status. All output `publish_*`, `execution_authorized`, `receiver_verified`, `editable_project_verified`, `format_verified` remain **false**.

Files:
- `src/fa3_selective_import_receiver_preview.py`: pure stdlib, no external effects.
- `canonical/schemas/selective-receiver-handoff-preview.v1.json`: no-execution S6 result contract.
- `canonical/schemas/selective-receiver-capability-claims.v1.json`: bounded **untrusted input** inventory claim contract, NOT an independently authenticated application registry.
- `tests/test_selective_import_receiver_preview.py`: synthetic app/host/format/round-trip/stem/privacy/locale negative and positive assertions.

## 3. Authority boundary and the next **real** bridge

| Concern | Sole existing authority / dependency | Evidence still required |
|---|---|---|
| Real per-stream source inventory | #195 `FA3-FILE-CONVERSION-001` `file.convert.inspect`, authoritative inspector linked into existing Security and Evidence | Source hash + per-stream original PTS/timebase/channel and signed inspector attestation. #195 currently lacks the complete S2–S6 authenticated per-stream result, already tracked in its PR discussion. |
| Exact selected output and execution | Existing File Conversion, Whisper/Caption Studio, Language Fabric, Audio Separation and Video Editor/FFmpeg/OTIO | Real format-specific source fixtures, STT/translation QC, HRB/Model Router approved specialists, exact typed UAF effect permissions. |
| Project/application receiver | Existing FA3 application catalog + UAF/Central MCP Gateway + target app's own inbox/command bus | Versioned real `prepare/ack/verify` recipient handshake, exact format claims, output hash match, no raw arbitrary command or external project script execution. |
| Multi-host location | Existing installer-validated role declarations, Director/Workforce, HRB and CAP-150 via Logistics | Approved host identity, per-job resource leases, TLS/PKI, transfer checksums/ACL, per-host Software Coexistence, app-inbox readiness and cancellation. |
| Lifecycle and proof | Temporal, canonical Evidence/Security and human approval | `PREPARED → TRANSFERRED → TARGET_VERIFIED → PUBLISHED` or independently evidenced `BLOCKED/ROLLED_BACK`; no self-reported or synthetic PASS. |
| Editable migration | #520 Story symmetric subset, #413 broader Story, external formats tested through admitted adapters and CAP-171 native artifact preservation | Same-format/version **import + export + feature diff** on actual external app project fixtures. PDF/SRT/WAV/MP4 are derivatives, never full editable project conversion proof. |

Only the existing UAF contract may initiate a side effect. The S6 preview does **not** register a new UAF action, execute a direct subprocess, bind a model/provider, mutate the existing receiver or make a real network connection. Subsequent physical receiver implementation must reuse the existing app-specific command bus / inbox and workflow signals. A previously accepted shared source *inspection hint* is not consent to share decoded media workspaces across hosts or trust domains.

## 4. Research and donor registry reuse

This slice consulted the existing FA3 central Donor & Reference Registry first, including all previous production-migration, historical converter and specialist selective-import research already recorded on PR #528. Relevant previously registered candidates include:
- [OpenAssetIO](https://github.com/OpenAssetIO/OpenAssetIO) and [MediaCreation traits](https://github.com/OpenAssetIO/OpenAssetIO-MediaCreation): *entity identity rather than brittle paths*, version/proxy relationships and host↔manager dialogue. MediaCreation remains **beta/reference-only**, not a drop-in FA3 asset authority or production dependency.
- [OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) and the separately captured AAF/FCP7/FCPX/XGES adapters: exact per-adapter, per-version editability and independently checked round-trip, not unconditional effect fidelity.
- [AYON OpenAssetIO manager bridge](https://github.com/ynput/ayon-openassetio-manager-plugin) and existing Kitsu/Zou/Gazu candidates: cross-DCC shot/asset identity and optional authorized metadata export, not another FA3 production database.
- [Open Job Description](https://github.com/OpenJobDescription/openjd-specifications) and [OpenCue](https://github.com/AcademySoftwareFoundation/OpenCue): portable batch-job specification *patterns*, never an alternate Director/Temporal scheduler.
- The previously registered [C2PA-RS](https://github.com/contentauth/c2pa-rs) and [BagIt](https://github.com/LibraryOfCongress/bagit-python) reference material can assist source lineage and offline fixity manifests, but **neither alone authenticates** the real producing application or proves a completed import.

This S6 code slice adds **no new source-key donor** because all applicable source identities were already captured; reuse them without changing IDs or duplicating records. Source snippets and externally supplied project text remain untrusted. New donor candidates in subsequent research must be normalized and captured immediately in the same canonical registry, with separate license, security and distribution reviews.

## 5. Exact-head and real-E2E exit conditions

S6 synthetic tests must exercise multiple host/app placements, translated-text isolation, independent stemming blockers, declared-format/version mismatches, no implicit fallback, exact editable reverse export, no ghost receiver, duplicate destinations, malformed claims, source tampering and 17 selectors / 175 invariants. They are only **preview/code correctness**, not real readiness.

Before changing PR #528 to merge-ready: reconcile newest `main` and any simultaneous PR registry modifications **by normalized source key**; regenerate/adopt release projection for final exact source head; run Canonical/Promotion, Reuse Discovery, app/donor inventory, static tests and release-baseline evidence checks on the **adopted** head. All historical snapshots remain immutable.

Independently require real current-host signed `source → inspected source streams → selected derivative → approved Logistics transfer → exact target receiver acknowledges and opens result` and separate GUI E2E, rollback, provider/model/weights/CPU/GPU and quality admission. Do not treat hosted CI or synthetic mock receiver manifests as real application proof.
