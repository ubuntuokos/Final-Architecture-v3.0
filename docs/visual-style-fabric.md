# FA3 Visual Style / Art Direction Fabric

## Status

The Visual Style Fabric is a canonical, authority-neutral shared creative service. It is materialized under the existing **175-capability** release baseline and introduces **zero new capabilities** and **zero new architectural authorities**.

It is intentionally implemented before most consuming creative applications. Their bindings are canonical requirements, not claims that those applications already have a working runtime.

## Purpose

The fabric converts reusable visual-style descriptions into canonical FA3 objects that can be shared by Photo, Video Editor, QuickClip, Story / Screenplay, Storyboard, Vector Graphics, World / Location Generator, Character / Animation, 3D, VFX, Credits / Titles, Marketing and Live / Broadcast surfaces.

The architecture is:

```text
application
  -> VisualStyleBinding
  -> VisualStyleRecipe / StyleDNA
  -> VisualIntentIR
  -> FA3 Model Router
  -> HRB
  -> admitted provider/runtime/model
```

No consumer may introduce a parallel model-selection, resource-selection or visual-style authority.

## Upstream reference

`VigoZhao/AI-Visual-Prompt-Cookbook` is used as a pinned **reference and import source**, not as a runtime provider or mandatory installed application.

Pinned source revision:

`d320e7a99819a54da6ff56abbc19a83fb6741772`

At that revision the upstream README reports 154 styles and style.json v2.1. The number is observational only; FA3 discovers catalog cardinality at import time and never uses 154 as a canonical constant.

Licensing is preserved as declared upstream:

- code, scripts and documentation: MIT;
- `style.json` prompt content: CC BY 4.0 with attribution;
- preview images: visual reference only, not bundled by default.

## Canonical objects

### VisualStyleRecipe

Provider-neutral normalized recipe. It preserves source provenance, license, attribution, style constraints, variables, source-content avoidance, negative constraints, composition, typography, palette and optional examples.

FA3 extends the source model with film/3D-oriented fields such as camera language, lens language, lighting, materials, environment, character, motion, animation, era, genre, weather, time of day, production type and continuity constraints.

### StyleDNA

A weighted mixture of one or more recipe IDs. Weights are normalized to 1.0. The object is descriptive; it does not pick a model or allocate hardware.

### StyleCompileReceipt

A deterministic compiler resolves declared `{VARIABLE}` placeholders into a derived prompt receipt. Missing required variables fail closed. The receipt is explicitly non-canonical and still contains no provider, model or runtime selection; those remain Model Router responsibilities.

### VisualIntentIR

A provider-neutral intermediate representation bound to exactly one of:

- PROJECT
- SCENE
- SHOT
- ASSET

The IR carries style constraints and continuity information plus an unpinned route request. Provider, model and runtime fields remain null until the Model Router resolves them. Silent fallback is forbidden.

## Planned application bindings

`canonical/visual-style-consumer-bindings.json` reserves mandatory use of the shared fabric for the already designed creative lines. Every planned binding has:

- `status: PLANNED_REQUIRED`;
- `parallel_style_authority_allowed: false`;
- `runtime_promoted: false`.

This means a future application implementation immediately inherits the shared style contract, but the repository does not falsely claim that the application is already implemented or current-host verified.

## Preservation boundaries

The Visual Style Fabric may guide art direction but it cannot replace canonical creative data.

- native project files remain authoritative;
- Story / Screenplay documents remain authoritative;
- the canonical 3D scene/geometry authority remains authoritative;
- a style binding may change look-development intent, not silently mutate scene/document semantics.

## Hardware Audit

The metadata/import/Style DNA/IR path is CPU-only viable and vendor-neutral. Accelerator cardinality is 0..N. Downstream generation may use accelerators only after normal HRB admission and Model Router resolution. The Hardware Safety Envelope remains non-bypassable.

## Coexistence

All persistent state is FA3 namespaced under XDG roots or project-local `.fa3/visual-style`. The fabric never requires uninstalling or replacing the upstream cookbook or independently installed creative software, never claims a default port, and never performs global environment mutation.

## Runnable surfaces

Static gate:

```bash
./bin/fa3-enforce visual-style-fabric
```

Importer:

```bash
PYTHONPATH=src python3 src/fa3_visual_style.py import \
  --input style.json \
  --source-project VigoZhao/AI-Visual-Prompt-Cookbook \
  --source-revision d320e7a99819a54da6ff56abbc19a83fb6741772 \
  --source-license CC-BY-4.0 \
  --attribution @VigoCreativeAI
```

Compile a provider-neutral derived prompt receipt:

```bash
PYTHONPATH=src python3 src/fa3_visual_style.py compile \
  --recipe canonical-recipe.json \
  --values values.json
```

Visual Intent IR:

```bash
PYTHONPATH=src python3 src/fa3_visual_style.py intent \
  --recipe canonical-recipe.json \
  --values values.json \
  --scope SHOT \
  --target-id shot-001
```

These utilities materialize and validate the shared contract; they do not claim downstream image/video generation or current-host provider admission.
