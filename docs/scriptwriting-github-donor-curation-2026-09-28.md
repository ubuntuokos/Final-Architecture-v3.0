# Scriptwriting GitHub donor curation — 2026-09-28

**Discovery source:** https://github.com/topics/scriptwriting
**Canonical registry:** `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`
**Scope:** source-specific metadata-only candidates and the topic-level discovery index, not approved implementation or runtime adoption.

This inventory adds new inputs to the existing **FA3 Story/Screenplay** application and its Professional Screenplay & Production Script Fabric. It does **not** propose another standalone editor, document authority, orchestration layer, AI provider, model route or replacement for FA3-native creative project files. Candidate functions should pass through the existing Donor/Reuse Discovery flow before implementation.

## Verified discovery and FA3 reuse candidates

| Candidate | Upstream evidence / declared license | Selective FA3 use | Boundary |
| --- | --- | --- | --- |
| [OpenDraft](https://github.com/Proteus-Technologies-Private-Limited/OpenDraft) | GitHub MIT; README: screenplay editing, Fountain/FDX/PDF workflow, beat board, co-writing, revision history | Script editor interactions; beat cards; review and tracked-revision concepts | Independently test format round-trips, real collaboration behavior and code provenance |
| [ScriptFlow](https://github.com/YoLin02/ScriptFlow) | GitHub Apache-2.0; README: text-to-card visual canvas, media, timeline and Markdown import/export | Story branches, scene/shot planning and linkable text/asset cards in FA3-native Qt/QML | Do not introduce React/IndexedDB as parallel project authority |
| [Story Architect / STARC](https://github.com/story-apps/starc) | GitHub GPL-3.0; README: C++/Qt, production documents, story bible, breakdown, statistics | Production-aware document profiles, character/location views and native UI reference | GPL analysis before code copy; public/community build notes private/commercial submodules; office import/export may differ by format and direction |
| [Scenarly](https://github.com/Lycoon/scenarly) | GitHub NOASSERTION; README says source-available and All Rights Reserved | Page/scene locking, alternates shelf, writing sessions, focus mode and statistics as UX references | Reference-only; no source copying without separate permission |
| [How to Make Script](https://github.com/XucroYuri/how-to-make-script) | GitHub MIT; intent × medium × stage × output routing and narrative rubrics | Reusable production-profile and quality-review criteria | Never import its model/router authority; use FA3 Model Router, HRB and existing approvals |
| [ai-novel2script](https://github.com/Axelxrd/ai-novel2script) | GitHub MIT; chapter-to-scene mapping, story bible, YAML schema and coverage reports | Traceable novel-to-screenplay adaptation and explicit provenance | Upstream fixed model option/automatic local fallback must **not** cross FA3 integration; no silent fallback or unsanctioned external manuscript upload |
| [Fountain Mode](https://github.com/rnkn/fountain-mode) | GitHub GPL-3.0; Fountain 1.1 editing and pagination | Fountain conformance fixtures, navigation and editor interaction references | License review before code copying |
| [afterwriting-labs](https://github.com/ifrost/afterwriting-labs) | README declares MIT; GitHub API does not resolve a license | Fountain-to-PDF/FDX interchange and screenplay statistics | Verify actual file licenses and document semantic round-trip loss |
| [rsdoiel/fdx](https://github.com/rsdoiel/fdx) | GitHub/root LICENSE AGPL-3.0; some source-file headers BSD-2-Clause; inactive project badge, last upstream push 2025-08-09 | Typed FDX XML model, FDX→Fountain-like text and Fountain→FDX CLI examples; test structure for an FA3-native bidirectional FDX codec | Reference-only: mixed license declarations require per-file/legal review; upstream TODO leaves embedded styles, compatibility and layout behavior unresolved; no lossless round-trip claim |
| [Narrative Soundstage](https://github.com/IdaAkiwumi/narrative-soundstage) | README proprietary badge links to an MIT page; GitHub reports no SPDX license | Character voice assignment, table reads, TTS timing and synced prompter pattern | Conflicting/unclear rights: reference-only; approved providers and explicit user consent |
| [Tome Editor](https://github.com/Oleg-Avdeev/Tome-Edtior) | GitHub GPL-3.0; branching TSV narrative editor, last push 2022 | Alternative continuations and typed branch/condition/asset references | Architectural reference; no separate canonical story schema; older upstream |
| [meander](https://github.com/lichendust/meander) | GitHub GPL-3.0; portable screenplay/manuscript command-line project | Script packaging/transformation ideas and CLI reference | Independently inspect actual format support and tests |
| [screenplay-latex](https://github.com/karthikv792/screenplay-latex) | README declares MIT; GitHub API does not resolve a license | Production tagging (props, wardrobe, shot, light, SFX, VFX), revisions, scene breakdown reports | Verify exact file licenses and validate templates against each production profile |
| [scriptwriting topic](https://github.com/topics/scriptwriting) | Public discovery index, not a code repository | Future donor discovery | Discoveries are separate candidates, never auto-installed or auto-promoted |

The repository feature summaries above are **upstream README claims**, not FA3 current-host test results. License declarations are metadata; all upstream versions, transitive licenses, security and compatibility must be checked at implementation admission.

## FDX codec acceptance note — rsdoiel/fdx

Source examined at upstream commit `e2ee6728c511d03922692bffaaef5b23da639889` (2025-08-09). The repository implements `Parse`, `ParseFile`, `ToXML`, `FromFountain`, the `fdx2txt` and `txt2fdx` CLIs, and a typed XML model covering screenplay paragraphs, title pages, scene properties, revisions, script-note definitions, casting and some page settings. Its Go module depends on `github.com/rsdoiel/fountain`.

**Current limitations in the upstream author's own TODO:** embedded styling is not preserved by `StringToTextArray`; Fountain→FDX output still awaits validation in Final Draft, Fade In and Trelby; paragraph alignment, document-wide format definitions and header/footer field ordering are incomplete. XML marshal/unmarshal tests are not proof of semantic or visual fidelity. The README marks the project inactive, so pin the examined commit and retest instead of assuming sustained updates.

**Selective FA3 design:** implement any admitted FDX codec through the pre-existing FA3 canonical document/interchange layer, not as a new app or a Go runtime requirement. Source-agnostic parsing/serialization ideas can inform a separately licensed FA3-native implementation; never copy upstream code while AGPL-3.0 root/repository declarations and BSD-2-Clause source headers remain unresolved. Preserve source bytes or an opaque extension payload **only where safe and rights-compliant**, and produce explicit unsupported-field/loss reports. Neither FDX nor Fountain may be advertised as supported merely because one direction happens to parse.

**Required gated fixture matrix:** separate FA3-authored, license-cleared samples for (a) title-page metadata, (b) scene headings/numbers and insertions, (c) action, dual dialogue, parentheticals and text style spans, (d) script notes, revisions, page locks, casts and headers/footers, (e) XML entities, Unicode/Hungarian accents and mixed-language text, (f) malformed and hostile XML with resource limits, and (g) FDX → canonical → FDX and Fountain → canonical → Fountain as well as cross-format conversions. Validate against supported external application versions where available; distinguish semantic, metadata and pagination/visual fidelity. Any profile failing bidirectional export or its declared fidelity gate stays unadmitted.

**Hardware Audit:** inspection and planned codec tests must run CPU-only with zero GPUs/NPUs required, remain vendor-neutral and function in a headless test runner. GUI features remain FA3 Qt/QML with Wayland preferred and X11 supported. No change to HRB, Model Router, AdGuardHome ports or FA3-native project ownership.

## Related script-breakdown research

See [script-breakdown source-specific curation](script-breakdown-github-donor-curation-2026-09-28.md) for wildwinter's bidirectional but lossy Fountain/FDX Script model, ScriptBreak scene/shot/schedule workflow, staged human approval and visual-asset continuity references, typed narrative-beat validation and **OpenDraft's existing record enrichment**. This extends the prior FDX acceptance work; it does not admit a second document authority or duplicate OpenDraft donor.

## Selective design for the existing FA3 Story/Screenplay Fabric

1. **Canonical story graph and document profiles:** keep the existing FA3 source of truth for scenes, acts, characters, alternatives, versioning, annotations and production metadata. Validate separate film, TV film, episodic/series, advertising/commercial, live broadcast and future profiles. No donor schema becomes canonical by import.
2. **One FA3-native screenwriting editor:** implement/extend the planned Qt6/QML/KF6 editor for scene/page locking, Fountain authoring, beat cards, character/location reports, writer goals, writing statistics, sprint timer, Midnight and Typewriter/focus modes. Reuse donor ideas selectively rather than replacing the editor with web applications.
3. **Alternative continuations:** model independently editable/versioned branches on the shared story graph, not forks of the complete FA3 project. Story and card changes must preserve stable scene/asset identifiers, provenance and per-scene inheritance.
4. **Interchange:** use the existing canonical FA3 document/interchange layer. Each admitted import format needs a corresponding export path: Fountain, FDX, applicable Office families (Microsoft Office, LibreOffice, Apache OpenOffice, WPS Office, ONLYOFFICE) and other explicitly supported formats. Define version-specific format profiles, round-trip tests and explicit lossy/unsupported-feature reports. An unsupported one-way importer is not admitted. For PDF, document extraction loss and do not claim edit-fidelity parity.
5. **Pre-production handoff:** derive scene-tagged shot, set, costume, props, camera, lighting, VFX, casting, dialogue and timing projections for Film Planning, storyboard, FA3 Video Editor, QuickClip, Voice/Vocal and Creative Studio. Preserve integrated apps' native project formats and FA3's own canonical project data.
6. **Human-authority AI:** prose proposals, dialogue alternatives, adaptation drafts, rubric findings and table-read assistance remain identifiable AI outputs separate from user writing and notes. Require human approval for acceptance. Every model invocation goes through the existing FA3 Model Router → admitted provider/model, with HRB authority, security and explicit no-silent-fallback rules. Do not adopt donor-specific fixed models, independent AI agents or cloud upload defaults.
7. **Proof before promotion:** for each format/profile and feature, require deterministic acceptance fixtures, branch/merge/concurrency tests, license/provenance review, privacy/security tests, relevant UI checks and FA3 current-host evidence. Keep experimental ideas in CANDIDATE until separately admitted.

## Hardware Audit — mandatory design boundary

This curation and registry change is **metadata-only**. It is vendor-neutral, CPU-only compatible and imposes zero required accelerators (`0..N` GPU/NPU). Qt/QML must support Wayland-preferred sessions and X11, without hard-coding KDE or one GPU vendor. Optional AI audio/model use remains under the existing HRB/Model Router policy. The assigned display GPU must not be recruited for AI compute except under FA3's explicit display-GPU exception rules; there is no automatic secondary-accelerator enlistment. This curation neither changes AdGuardHome ports nor installs runtimes.

## Admission and order of implementation

- **Interchange and schema fixtures first:** Fountain/FDX/Office symmetrical codec contracts, canonical story graph and production profiles.
- **Then editor and planning:** integrated scene editor, beat cards, branch workflow, revision locking, writing metrics and focus UI.
- **Then production handoff:** annotation breakdowns, storyboard/VE/QuickClip projections, table-read previews, novel adaptation with chapter-to-scene traceability.
- **Independent gated reuse:** per-donor upstream commit pin, license/transitive-license review, tests, security/privacy, no redundant package installation, coexistence and current-host evidence.

**Status:** inventory and candidate registration only. No external library was installed, no license approval or source-copy permission was inferred, and no FA3 screenwriting capability was presented as newly implemented.
