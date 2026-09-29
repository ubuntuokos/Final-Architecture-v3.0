# openSUSE and novel-writing donor curation — 2026-09-29

Five user-submitted source identities are registered once in the existing `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. All remain metadata-only `CANDIDATE` entries. Organization and GitHub topics are dynamic **discovery indexes**, not bulk admission of their repositories.

| Source | Type | Selective FA3 use |
|---|---|---|
| [openSUSE organization](https://github.com/openSUSE) | Organization index | FA3 Installer, Application Fabric, Hardware Audit and Software Coexistence reference discovery; no openSUSE-only requirement |
| [steven-tey/novel](https://github.com/steven-tey/novel) | Concrete repository | Structured rich-text UX, editor block/command patterns and explicitly invoked AI autocompletion for Story/Screenplay and Creative Studio |
| [webnovel topic](https://github.com/topics/webnovel) | Dynamic topic index | Serial/chapter continuity, long-form fictional story organization, publishing patterns |
| [novel-generation topic](https://github.com/topics/novel-generation) | Dynamic topic index | Human-controlled narrative planning, iterative drafting, chapter consistency and revision patterns |
| [light-novels topic](https://github.com/topics/light-novels) | Dynamic topic index | Illustration metadata, chapter layout and lawful offline ebook interchange references |

## Specific observations and limits

**openSUSE:** The organization exposes separate `openSUSE/snapper`, `openSUSE/open-build-service`, `openSUSE/libsolv`, `openSUSE/zypper` and `openSUSE/hwinfo` repositories. Consider respectively snapshot/rollback, reproducible building, dependency solving, package workflows and hardware enumeration as *ideas for future individual research*. These five are **not** additional registrations under this batch. Do not introduce a second FA3 package/install authority, mandate openSUSE or change an existing host's package database.

**Novel:** The upstream README describes a Notion-style WYSIWYG editor with AI-powered completions based on React/Next.js, Tiptap, OpenAI and Vercel components. Its top-level `LICENSE` declares Apache-2.0. Only portable **editing behavior and UI/workflow patterns** are presently in scope: structured blocks, context commands, suggestions with user approval, and non-destructive changes. Existing Qt6 Story/Screenplay remains the FA3 application; do not add a parallel React editor, required cloud service, Vercel account, hard-coded provider, exposed credential or independent model selector. An Apache-2.0 top-level license does not clear all transitive dependencies or every copied file.

**Topics:** Each page is a changing collection. None of their listed repositories, models, scraping tools, reader runtimes, paid endpoints or datasets is automatically admitted. Later selection requires exact repository URL, normalized source-key deduplication, verified project scope, license/provenance/redistribution, content rights, security and Software Coexistence reviews. Prefer original project and author data ownership, human approval of generated story text, deterministic branching/versions and bidirectional interchange for every admitted file format.

## FA3 mandatory boundaries

- Exactly five source-unique registry entries; `CANDIDATE` status only. Registry captures research, not execution approval. No new authority or capability; fixed baseline **175**, provider count remains dynamic.
- Keep existing Story/Screenplay and Creative Studio; use the canonical Reuse Discovery before any actual implementation. A topic index has no legal license on behalf of individual projects.
- HRB alone allocates resources; Model Router alone chooses models; Secret Broker protects credentials. Preserve CPU-only baseline, `0..N` accelerators and the display-GPU opt-in rules. Do not import runtime requirements from upstream example projects.
- Mandatory Hardware Audit and fail-closed Hardware Safety Envelope before implementation. Preserve Software Coexistence and Host Non-Interference (paths, ports, packages, sessions, caches and data). Wayland first and X11 fallback for native GUI.
- Source copying and runtime/provider/model admission require separate evidence-based legal, security, provenance, dependency and exact-head gates. **No current-host runtime PASS or code import is claimed by this metadata PR.**
- Reconcile the canonical JSON by normalized source key against concurrently open donor PRs before any merge. Update backfill count and regenerate exact-head release projection only after lossless reconciliation.

Sources checked: upstream GitHub organization/repositories, Novel README and LICENSE, and each exact user-supplied GitHub topic URL on 2026-09-29.
