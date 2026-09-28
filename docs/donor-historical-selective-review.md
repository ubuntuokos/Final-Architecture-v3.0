# Historical selective-donor curation — 2026-09-28

## Review boundary

This is a **source-file** review, not a claim to have read all of the user's
ChatGPT conversations. The accessible Library project folders contained
48 files: six in Final Architecture v1.0, 37 in Final Architecture v2.0,
four in Final Architecture v3.0 and one Kernel archive. Ten other named
Library folders contained no accessible files. The separate
**Optimalizálás** project was intentionally excluded.

37 markdown/YAML/Python text files from the Architecture v1.0/v2.0/v3.0
folders were screened for named upstream sources and descriptions of
selective capability, algorithm, workflow, architecture, UX, research and
adapter reuse; the three Architecture ZIP bundles and Kernel archive
were also inspected for source names. Checksum-only files were not
treated as semantic evidence. The scan located many upstream links,
including full providers and excluded software; **a hyperlink alone
never creates a donor record**. Documented historical dispositions are
evidence about an earlier design, not verification of current upstream
code, licensing, availability or admission.

The backfill added **77** source-distinct candidate references and
enriched **14** existing records with specific selective-use metadata,
preserving the pre-existing 174 records and their lifecycle states.
The resulting registry contains **251 records**. The root
`historical_partial_reuse_review` reports the bounded review.
The record-level `selection_scope` distinguishes the selected
capabilities/patterns from the upstream application's overall scope.

## Selection semantics

- `SELECTIVE_CAPABILITIES_AND_PATTERNS_ONLY` means the **named ideas,
  features, interfaces or workflow examples** can be considered when
  planning the named FA3 application. It never means wholesale import
  of the source application.
- `selected_capabilities` gives the narrow pattern or API;
  `intended_fa3_targets` includes existing and **planned** modules;
  `historical_source_class` distinguishes earlier REF (pattern),
  RESEARCH_REF, SELECTIVE_ADAPTER and scoped enrichment of existing
  entries. `source_group` identifies the historical evidence family.
- Current new entries remain `CANDIDATE`, even if a historical text
  described them as required or a reference: upstream availability,
  dependency constraints, version, licence, security, distribution and
  hardware compatibility still require dedicated review before any
  actual source-code reuse or runtime admission.
- References with no reliable exact GitHub locator retain `project:`
  identity. They must not be mistaken for verified upstream repositories.
- Repeated source keys are merged, never duplicated. Existing lifecycle
  states and known licences are not reset when annotating old entries.

## Examples of partial capabilities and FA3 consumers

| Historical source | Selected feature or pattern | Intended FA3 consumer |
|---|---|---|
| AutoCache | Layered cache and context breakpoints | Model Manager, Inference Fabric, HRB |
| AgentBase | Visual mission-control and worktree isolation | Agent Collaboration Room, Developer Agent |
| LLM Council | Parallel answers, blind peer review | Decision Fabric, Verification Fabric |
| MovieAgent | Film-oriented multi-agent coordination | Story/Screenplay, Film Planning |
| Dramatron | Outline/continuation planning | Story/Screenplay, Prompt Builder |
| Toonflow | Continuity registry and reference-first creative workflow | FA3 Video Editor, World Generator |
| Pixelle-Video | Scene-task pipelines and media capability routing | Video Editor, QuickClip |
| TestZeus Hercules | Evidence-backed browser QA | Verification Fabric, Browser Action Runtime |
| IP-Adapter | Reference-image conditioning | Generative Media Studio, Character Studio |
| FreeMoCap | Skeletal motion capture | Choreography, Character Studio |
| OpenViking | Hierarchical context provider patterns | Memory Fabric, Knowledge Fabric |
| Restic | Encrypted, deduplicated artifact backup | Backup/Recovery Fabric |

## Integration and authority boundaries

This is metadata used by FA3 Reuse Discovery, not a new runtime or
architectural authority. Before materially new application work,
Reuse Discovery may match these hints but cannot independently install,
download, select, admit or execute any reference.

**Hardware Audit:** metadata capture has no global accelerator
requirement, is vendor-neutral and CPU-only viable, supports 0..N
accelerators. The HRB is the sole runtime resource authority. Model
routing remains under the canonical central Model Router, with no
donor-specific fixed provider and no silent fallback. Historical
platform-specific host hints are not promoted into architectural policy.

The prohibited proprietary real-time 3D engine is excluded; neither its historical mentions nor
historical alternatives in the separate Optimalizálás project were
admitted into this backfill. Offensive tooling mentioned in research
is usable only as a bounded authorized defensive reference; unverified
licenses block copying. Existing native projects (such as .kra and the
FA3 editor format) retain their normal ownership and interchange rules.

## Provenance and coverage

The review sources were the accessible archived files in the
**Final Architecture v1.0**, **Final Architecture v2.0** and
**Final Architecture v3.0** Library folders, particularly
`FINAL_ARCHITECTURE_v1.1_PROGRAMLISTA_GITHUB.md`,
`FINAL_ARCHITECTURE_v1.2.md`,
`FINAL_ARCHITECTURE_v2.0.20.md` and
`FINAL_ARCHITECTURE_v3.0.14_MUSIC_GENERATION_COMPOSITION_CANONICAL_PROFILE.md`.
This imported **source metadata only**. No raw private ChatGPT messages,
project titles, account IDs or entire documents were copied into GitHub.
Any donor mentioned only in an unexported ChatGPT conversation remains
outside this file review until separate evidence is available.
