# FA3 Story/Screenplay — native implementation, phase 1

**PR:** [#520](https://github.com/ubuntuokos/Final-Architecture-v3.0/pull/520)
**Contract:** `canonical/contracts/FA3-STORY-SCREENPLAY-IMPLEMENTATION-CONTRACTS-001.json`
**Existing application:** `fa3.story-screenplay` (declared in `FA3-APPLICATION-DONOR-LINKS-001`, not a new separate donor editor)
**State:** deterministic source-code foundation and reference tests. Real current-host application execution, GUI physical testing, production admission and full original plan remain pending.

## Implemented and locally testable

- **Canonical document:** `src/fa3_screenplay.py` owns typed scene/element data, a selectable production profile (feature, TV movie, episodic, commercial, live broadcast, other), stable scene IDs, story identity, independent branch IDs and parent/revision SHA-256 provenance. It does not add a competing general FA3 project authority.
- **Paired experimental interchange:** import **and** export for a deliberately bounded Fountain subset and a deliberately bounded Final Draft FDX XML subset, with source/export receipts. FDX preserves scene numbers, plain title lines, common paragraph types and supported inline styles within this restricted subset. Input is capped at 5 MiB; XML DTD/entities and silent parser recovery are forbidden. Unknown/lossy structures are rejected by default; `--allow-loss` is explicit and documented in a field-level receipt. Native canonical JSON is the sidecar for all FA3-only metadata. These are **not** advertised as full Fountain 1.1 or production-grade FDX codecs before externally validated interop fixtures pass.
- **Derived preproduction proposal:** source-anchored deterministic explicit tags (PROP, WARDROBE, VFX, SFX, VEHICLE, EXTRA, CAST) and shot-cue suggestions, scene/location/day-night breakdown, speaking cast only, revision-aware stale detection and scoped refresh. A beat graph, true page layout/length, silence/background cast inference, shooting calendar and automatic camera direction are not claimed.
- **Human review:** every uncertain candidate begins PENDING; only a named local reviewer can approve/reject via `review_candidate`. The receipt clearly states `LOCAL_UNVERIFIED_REVIEW`; authenticated UAF approval remains mandatory before any real production execution or publish.
- **Fail-closed preview:** `project_handoff` blocks on stale, incomplete or pending data and returns non-authoritative Film Planning rows plus placeholders for storyboard/VE/QuickClip. It never writes `project.fa3video`, `.fa3clip`, real schedule, external AI prompt or cloud manuscript. Silent cast remains explicitly unknown.
- **CLI and graphical integration:** `bin/fa3-screenplay` invokes the stdlib-only Python CLI inside an isolated user venv. The integrated Qt6/QML `StoryScreenplayPage` in the **existing** FA3 Control Center is served by a local, file-only `ScreenplayService` process boundary; it offers text/local-file import, local canonical project save/load, scoped export, local candidate review, branch creation, scene heading revisions, production profile, writing goal, sprint timer, Midnight and Typewriter/focus controls and a blocked/preview handoff. No separate React/Tauri application, independent provider router, model manager, MCP server or fixed network port is introduced.
- **Contract and gate:** the new canonical contract and JSON Schema declare exactly which features are experimental, prohibited and pending; `src/fa3_screenplay_gate.py` self-checks donors, contract, actual codec behavior, blocked handoff and GUI registration. The report explicitly says `REFERENCE_ONLY_NOT_CURRENT_HOST`.

## Tests and CI

Locally verified: **31 tests PASS** (`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_screenplay*.py' -v`), plus Python syntax and Bash wrapper checks. The workflow `.github/workflows/fa3-screenplay-reference-gate.yml` runs the stdlib suite and donor/GUI reference gates on PR updates. These are reference tests, **not** external FDX/Office interoperability or FA3 current-host evidence.

## Developer commands

From the repository root:

```bash
./bin/fa3-screenplay formats
./bin/fa3-screenplay import --format fountain --profile EPISODIC --input sample.fountain --output document.json
./bin/fa3-screenplay breakdown --input document.json --output breakdown.json
# Human reviews a candidate ID shown in breakdown.json:
./bin/fa3-screenplay review --input breakdown.json --candidate-id candidate-... --decision APPROVED --actor "Local editor" --output reviewed.json
./bin/fa3-screenplay handoff --input document.json --breakdown reviewed.json --output handoff-preview.json
./bin/fa3-screenplay export --format fdx --input document.json --output exported.fdx
PYTHONPATH=src python3 -m pytest -q tests/test_screenplay.py tests/test_screenplay_gate.py
```

The `handoff` command returns exit code **3** when the preview is BLOCKED; blocked preview JSON is still written for inspection. Every output refuses to overwrite an existing file unless the caller explicitly supplies `--replace`. The GUI's local review is not cryptographically authenticated and cannot promote a project to production on its own.

## Donor provenance and no code copying

The implementation consults the central donor registry and uses only architectural reference ideas from `wildwinter/screenplay-tools`, `rsdoiel/fdx`, `OpenDraft`, `wassermanproductions/scriptbreak`, `Coco Preproduction`, `Script Breakdown Workflow`, `Jellyfish` and the structural beat skill. **No donor source files, bundled fixtures, prebuilt binaries, new third-party dependency or model/provider authority have been copied or installed.** License and transitive dependency review remain prerequisites for any future source reuse. `rsdoiel/fdx` stays blocked for code copying because root AGPL-3.0 and source-file BSD notices need per-file review.

## Explicitly outstanding before fulfilling the complete #520 plan

- Full symmetric and version-scoped **Microsoft Office, LibreOffice, Apache OpenOffice, WPS Office and ONLYOFFICE** codec families; full Fountain 1.1/FDX fidelity and independently tested Final Draft/Fade In/OpenDraft interoperability; no unsupported one-way codecs may be admitted.
- Shared, layered story graph with scene-local independent branch merge, graph-level source-span revisions, full writing statistics and persistent writing goals, multiple document-profile templates and standards-based production timing.
- Verified production tag taxonomies with human-friendly extraction confidence, real character/costume/asset identity reconciliation, visual relationship graphs, narrative rhythm/beat detail pipelines, storyboard rendering, schedule/Day Out of Days constraints and real approved film-planning handoffs.
- Authenticated UAF approval, fully governed AI assistance through Director/Workforce → Central MCP Gateway/UAF → Temporal → HRB/Model Router; safe model outputs in separate AI text/notes panels with explicit human acceptance. No automatic external manuscript upload.
- Bidirectional editable native FA3 Video Editor/QuickClip project connectors and integration with other Creative Studio modules; additional application GUI work, responsive/accessibility review and manual Wayland/X11 GUI testing.
- Real current-host hardware and application evidence, negative security cases, vendor-neutral CPU-only proof on the actual supported FA3 host, external interoperability certification and canonical promotion. This local reference-stage code and CI cannot stand in for current-host evidence.

### Hardware Audit block

The implemented code is stdlib Python and CPU-only, with no required accelerator and dynamic `0..N` hardware compatibility. GUI uses the existing portable Qt6/QML FA3 Control Center, not KDE-only code; Wayland is preferred and X11 remains supported subject to actual runtime validation. It neither allocates any GPU (including the display GPU), changes AdGuardHome ports, makes direct provider calls nor installs any donor app. Real current-host compliance and evidence are pending; this document must not be used as a promotion receipt.
