# FA3 Shared Asset Processing Fabric — WP1

**Status:** owner-approved WP1 static materialization  
**Parent:** `FA3-DEC-GAME-CREATION-CAPABILITY-WP0-2026-10-01`  
**Capability baseline:** 175; delta 0  
**Authority delta:** 0

WP1 turns the game-editor asset-pipeline lessons into an FA3-native shared core. It does **not** vendor O3DE/Godot/Defold or any other engine and does not execute transforms.

## Canonical model

A logical asset identity is stable across revisions and is derived from the FA3 project namespace plus an explicit stable asset key. Content/path/provider identities are separate. Every concrete revision receives a separate version identity.

```text
Logical Asset
  ├─ stable logical id
  ├─ source/product role
  ├─ current version id
  ├─ media/type metadata
  ├─ rights state
  ├─ provenance
  └─ dependency edges
```

Dependency kinds are **BUILD**, **REFERENCE** and **OPTIONAL**. BUILD edges must form a DAG and are the only edges that drive deterministic build ordering and transitive invalidation. Reference cycles are permitted because scene/story/project references are not necessarily build dependencies.

## Deterministic planner

`src/fa3_asset_processing.py` materializes:

- stable logical asset IDs;
- source version IDs from content digest;
- deterministic recipe digests;
- stable product logical IDs from explicit output keys;
- predicted product version IDs from source/dependency versions + recipe + output declaration;
- deterministic topological build order;
- rights-aware execution eligibility;
- transitive invalidation planning.

The planner is deliberately non-executing: no files are transformed, no cache is written, no subprocess/provider/model/codec is selected, no network locator is dereferenced.

## Rights / provenance

`CLEARED`, `REFERENCE_ONLY`, `PENDING`, and `RESTRICTED` are distinct. Planning may retain non-cleared assets for inspection/reference, but a processing job is execution-eligible only when all required BUILD inputs are `CLEARED`. Products must retain input lineage.

## Consumer scope

Retroactive consumer scope is Video Editor, QuickClip, Story/Screenplay, Music Studio, Character Studio and AI Module Factory. External curated applications remain behind adapters and retain native project formats.

## Deferred

Actual importer/transcoder execution, cache writes, filesystem watchers, hot reload, worker scheduling and GUI bindings are not WP1. Those are separately gated follow-on stages and require Current Host requalification when executable host paths appear.

