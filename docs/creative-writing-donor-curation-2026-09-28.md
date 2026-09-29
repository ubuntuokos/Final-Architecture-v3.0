# Creative-writing and novel-generation donor curation — 2026-09-28

**Status:** metadata-only donor capture and architecture proposal. This is not a source-copy, dependency, install, model, provider, runtime, GUI implementation, or promotion approval.

## Scope and capture

The user supplied two distinct NovelWriter repositories and three GitHub topic indexes. Five additional individual repositories were inspected from the topic/repository research. Ten *distinct* source/index candidates have been entered into `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json` with status `CANDIDATE`. The indexes are discovery sources and must never be confused with an approval for all repositories they list.

The FA3 application-donor index already declares `fa3.story-screenplay`, `fa3.video-editor`, `fa3.quickclip`, and `fa3.character-studio`. This curation proposes strengthening those existing applications rather than adding a competing isolated novel-writing application or architectural authority.

## Candidate-specific assessment

| Source | Selective capability/pattern worth evaluating | License metadata observed | Boundary |
| --- | --- | --- | --- |
| [saga-soft/novelWriter](https://github.com/saga-soft/novelWriter) | Human-first project tree; chapters/scenes; notes and cross-references; manuscript export; human-readable source | GPL-3.0 | Reference/format adapter first. GPL and bundled assets require independent review before source copy. 2026.2 moves documents toward Markdown plus TOML header; version migration must not overwrite originals. |
| [EdwardAThomson/NovelWriter](https://github.com/EdwardAThomson/NovelWriter) | Genre/worldbuilding/character/scene planning; multi-agent consistency review; chapter/batch quality analytics | Undeclared in repo metadata/root on review date | Architecture inspiration only; no source copying or direct external model/backend authority. |
| [olivierkes/manuskript](https://github.com/olivierkes/manuskript) | Outline and index-card navigation; premise elaboration; world/character organization; writing focus | GPL-3.0-or-later | UX/reference patterns first; PyQt5 is not the FA3 GUI surface. |
| [EdwardAThomson/StoryDaemon](https://github.com/EdwardAThomson/StoryDaemon) | Emergent story planning, POV, evolving character memory, goals, checkpoint and recovery patterns | Undeclared in repo metadata/root on review date | Architecture inspiration only; prohibit autonomous promotion of generated prose to accepted project canon. |
| [Nigh/show-me-the-story](https://github.com/Nigh/show-me-the-story) | Explicit outline/chapter acceptance; fact extraction with references; foreshadowing; targeted revision; backup/restore | MIT | Its local web server, direct endpoint configuration and API-key storage are not FA3 authorities. |
| [Xiaoyangy/novel-studio](https://github.com/Xiaoyangy/novel-studio) | Chapter contracts, causal and POV constraints, source-bound retrieval, content digests, checkpoint/idempotent resume | Apache-2.0 | Reuse discovery should check overlap with existing FA3 Temporal, Journal, evidence and agent facilities; no duplicate orchestration authority. |
| [modoojunko/awesome-novel-agent](https://github.com/modoojunko/awesome-novel-agent) | Creative-writing skill/workflow ideas | AGPL-3.0 declared; README separately requests commercial authorization | Distinct commercial/third-party provenance review required. No copied skills by default. |
| [novel-writer topic](https://github.com/topics/novel-writer) | Future repository discovery | Not applicable | Index only; each discovered repository separately captured and reviewed. |
| [novel-generator topic](https://github.com/topics/novel-generator) | Future long-form and agentic generation discovery | Not applicable | Index only. |
| [creative-writing topic](https://github.com/topics/creative-writing) | Future writing/editor/skill discovery | Not applicable | Index only. |

The repository-level source inspections were not full supply-chain, license-file, security, CI, functionality or current-host audits. The recorded license value is a declaration observed during research, not FA3 legal clearance.

## Proposed place in existing FA3

**Existing entry point:** `fa3.story-screenplay` in the Creative Studio. Treat novel writing, short story, screenplay, series bible and narrative treatment as related *modes and document types* inside the existing shared project, not an extra runtime application or a new independent story authority.

1. **Human-first story workspace:** an author-controlled manuscript tree (part, chapter, scene, beat), outliner/card view, notes, character/world entries, relationships, research references, per-scene status, focus mode and manuscript assembly. Keep original document and third-party native project files intact. Support lossless import where demonstrable; otherwise import copies plus an explicit loss report and unchanged originals.
2. **Common narrative contracts:** use stable object IDs for `Project / Work / Arc / Chapter / Scene / Character / Location / Faction / TimelineEvent / Fact / Foreshadow / SourceReference`. Scene-to-shot mapping is an explicit versioned link, never destructive conversion. The existing project layer/file model, asset graph and editing-vs-render visibility remain authoritative.
3. **Optional AI assistant:** explicit, human-directed `idea -> outline -> detail -> draft -> review` jobs; specialized planning, continuity, point-of-view, character-motivation and editorial-review roles may be proposed through the existing Director/Workforce, UAF and Central MCP Gateway. All model execution goes through the central Model Router to an admitted provider/runtime and a designated model, with HRB-mediated resources; no embedded per-donor LLM or default CLI model selector and no silent fallback.
4. **Evidence-backed narrative review:** verify deterministic requirements separately from subjective AI suggestions. Record source-version/hash, scene/chapter, acceptance criteria, detected inconsistencies, reviewer source, prompt/model provenance and human disposition. No agent can approve its own finished prose, auto-merge human-edited text, silently rewrite canon, or mark a production gate PASS on its own.
5. **Production hand-off:** an accepted Scene/Beat can emit screenplay segments, character/asset needs, shot proposals and storyboard task references to the existing FA3 Video Editor, QuickClip and Character Studio. A shot may update its derivative plan without rewriting the manuscript. Preserve provenance back to accepted narrative versions.
6. **Export and portability:** Markdown/TOML or equivalent lossless text representation, explicit project metadata, import/export contracts, manuscript assembly and separately approved DOCX/EPUB/PDF output adapters; validate round-trip semantics per supported format.

## Hardware Audit — mandatory before implementation or admission

- Metadata capture and documentation create no runtime demand, change no host settings and require no GPU.
- The planned writer must be fully usable **CPU-only** and on hosts with 0..N accelerators. Backends remain vendor-neutral and hardware detection is dynamic.
- Keep Wayland preferred with X11 supported; do not couple the application to a specific desktop environment.
- Only the central HRB allocates CPU/GPU/NPU resources and memory; only Model Router authorizes model/provider/runtime paths. A display GPU remains reserved for display except under FA3's two explicit permitted policies, including task-and-model-specific user designation when another GPU/NPU exists.
- Do not import direct .env API-key storage or hardcoded provider selection from donor projects. Use the FA3 governed secret and routing paths.

## Execution plan and acceptance gates

**Phase A — contract inventory:** query Reuse Discovery and Application Donor Index, reconcile existing Story/Screenplay and creative GUI surfaces, find any already implemented story/note/asset interfaces, and test whether source document round trips are possible without destructive conversion.

**Phase B — non-AI authoring:** build the common narrative document contracts, explicit versioning, scene hierarchy, outliner/cards, character/world cross-references, notes and import/export adapters using existing FA3 GUI/component and native-file handling. Acceptance: real sample projects survive save/reopen, reordering, undo and import/export, with originals untouched and a loss report for non-lossless imports.

**Phase C — optional AI assistance:** wire pre-authorized roles through existing Director/Workforce, UAF, Central MCP Gateway, HRB and Model Router. Acceptance: CPU-only run; explicit model assignment; unavailability reported rather than hidden fallback; human prose approval; edit-detection/provenance; continuity and source tests whose output is independently inspected.

**Phase D — integrated production:** add versioned scene/beat to shot/storyboard mappings and export to FA3 Video Editor / QuickClip / Character Studio without mutating author originals. Acceptance: an approved scene change produces scoped downstream impact records; rejected AI proposals do not alter accepted canon or native projects; interrupted work resumes idempotently.

**Phase E — release promotion:** complete exact upstream revision, licenses and all transitive asset/dependency assessments for any contemplated code import; security, coexistence, portability, current-host evidence and canonical independent gates before admission. Candidate status alone does not permit installation or promotion.

## Explicit exclusions

- No second novel-writing GUI/runtime that duplicates Story/Screenplay.
- No self-authorized AI model recruitment, per-donor direct LLM gateway, external secrets file, new orchestration authority, or automatic multi-GPU use.
- No direct code copying from repositories lacking an identified license; GPL/AGPL components are not silently folded into differently licensed FA3 artifacts.
- No automatic acceptance of generated text, automatic project overwrite or destructive native project conversion.
