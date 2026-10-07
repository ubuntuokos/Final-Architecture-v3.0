# CFA3 donor intake — exact-state missing baseline sources — 2026-10-07

## Owner authorization

The owner explicitly ordered every source that was identified as **MISSING** in the approved
"CFA3 Donor Baseline — exact-state closure report" to be added **donornak**, and ordered the
resulting donor batch to be included in the currently running donor-finalization process.

This source-intake staging PR therefore covers exactly **20** previously verified non-canonical,
non-staged sources.

## Exact source set

### DeepSeek / model / provider / agent references

1. https://github.com/deepseek-ai
2. https://github.com/topics/deepseek
3. https://github.com/topics/deepseek-v3
4. https://github.com/topics/deepseek-harness
5. https://github.com/esengine
6. https://github.com/topics/deepseek-tui
7. https://deepseekcoder.github.io/
8. https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash
9. https://github.com/dazeb/openclaw-deepseek-integration
10. https://github.com/huggingface/open-r1
11. https://github.com/doxdk/deepseek-desktop

### Discovery / tile / game-development references

12. https://github.com/starryrbs/awesome-ai-tools
13. https://github.com/topics/tileset-generator
14. https://github.com/meetpateltech/ai-infinity
15. https://github.com/tile-ai
16. https://github.com/tesslio/spec-driven-development-tile
17. https://github.com/topics/tilemap-editor

### Creative-media references

18. https://atlas.design/
19. https://github.com/TheOrcDev/videorc
20. https://vivago.ai/agent/home

## Serialization boundary

This PR is **source-intake staging only** for the existing single-writer rolling donor finalizer
**#727**. It does not independently modify
`canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

The finalizer must append this batch only after fresh exact-head reconciliation against the then
current published `main`, canonical registry blob, already staged source batches and canonical
source-key/alias/ID deduplication.

## CFA3 invariants

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- usage-edge delta: **0**
- code/dependency installation: **none**
- runtime/provider/model admission: **none**
- hosted service activation: **none**
- automatic local-to-cloud fallback: **none**
- Current Host PASS claim: **none**
- child source auto-admission: **none**

`FA3-AUTH-MODEL-ROUTER-001` remains the sole model/provider routing authority. CPU-only remains a
mandatory platform path. HRB and the existing Hardware Safety / Software Coexistence / License &
Rights / Security / Evidence authorities remain unchanged.

## Five-level dependency/reference analysis

The mandatory five-level lineage rule was applied to **all 20 source identities**. The canonical
delta records one five-node reference chain per source. These are analysis/reference chains, not
dependency-admission chains.

### DeepSeek ecosystem

The official DeepSeek organization exposes current model, kernel, agent-harness and infrastructure
work. Representative lineage passes from the organization or relevant topic index, through the
specific model/harness/kernel ecosystem, into model/provider/agent/hardware-adaptation patterns,
then to the corresponding CFA3 shared layer, and finally to independent fail-closed admission
gates.

The DeepSeek Coder site is retained as an official code-model architecture/evaluation reference.
The DeepSeek V4.1 Flash Hugging Face model is registered as a model-card/reference identity only;
model weights and execution are not admitted.

`dazeb/openclaw-deepseek-integration` is useful for OpenAI-compatible provider configuration,
reasoning-mode descriptors and secret/configuration boundary analysis. It does not gain provider
admission.

`huggingface/open-r1` remains valuable for SFT/GRPO/evaluation/synthetic-data lineage, but its
current upstream README explicitly states that the project is no longer maintained and directs
current training work toward TRL. CFA3 therefore treats it as a historical/reference source and
must re-evaluate current upstreams before any material adoption.

`doxdk/deepseek-desktop` is a desktop-wrapper UX reference. Its upstream metadata is internally
inconsistent for licensing: README/LICENSE indicate MIT while `package.json` declares ISC.
Direct material reuse is therefore fail-closed pending exact License & Rights reconciliation.

### Tile / game / discovery ecosystem

`starryrbs/awesome-ai-tools` and `meetpateltech/AI-Infinity` are catalog/discovery references.
Their linked tools and services do not become donors automatically.

The `tileset-generator` and `tilemap-editor` topic pages are dynamic discovery indexes for
2D game-asset, tileset, sprite, level and map-authoring workflows. Child repositories and assets
remain independently reviewed.

The explicit `https://github.com/tile-ai` organization identity is distinct from the already
handled TileLang/TileRT/TileOPs child-source work. It is registered as the organization-level
discovery index so future Tile-AI repositories can be found without treating children as
implicitly admitted.

`tesslio/spec-driven-development-tile` is an MIT-declared reference for requirement gathering,
spec-before-code, approval, verification and agent skill/rule packaging. Installation of the Tessl
CLI/tile is not authorized by this donor registration.

`https://github.com/esengine` is a profile/discovery reference for the ESEngine TypeScript ECS
and modular game-development ecosystem. Child modules require exact source/license review.

### Creative-media ecosystem

Atlas is registered as a hosted 3D workflow reference. Current public material demonstrates a
pipeline from concept/reconstruction through cleanup, retopology, UV/PBR, character rigging, LOD,
GLB export, provenance and engine import, plus a Blender-agent workflow. No Atlas service, model,
asset or API is admitted.

Videorc is registered as an architecture/reference source for AI-native desktop capture,
recording, RTMP streaming, captions and producer-agent UX. The repository declares
**AGPL-3.0-only**; code reuse requires explicit License & Rights disposition. Its Electron/React
shell, Rust backend, authenticated localhost protocol and FFmpeg pipeline remain reference
patterns only.

VivaGo AI Agent is registered as a hosted creative-agent/reference source, including project,
asset, SkillHub, image and video workflow surfaces. Hosted models, service APIs, generated assets
and account/credit behavior are not admitted.

## Exact repository heads observed during intake

- `huggingface/open-r1`: `5b6ff22b3fb7aa069c54866e517f39dfc3160e09`
- `dazeb/openclaw-deepseek-integration`: `b4adbdab3ecf5f1e77c66382015fbd2ecb95cb85`
- `doxdk/deepseek-desktop`: `b2671ed312891ccc30d369764137e49e9d06d612`
- `starryrbs/awesome-ai-tools`: `9bde9809c33e8d492f338754793eb00ad91c09c9`
- `meetpateltech/AI-Infinity`: `070fe5e69ec18da6446f556a241c6fa62ce47894`
- `tesslio/spec-driven-development-tile`: `b8fdff700a5df98386d82d29f1ef3dc783092daf`
- `TheOrcDev/videorc`: `cdd2f9421bbd055a36973bcfe222b6c44db87bec`

Dynamic topic, organization, Hugging Face model-card and hosted-service pages were reviewed as
discovery/reference surfaces; they do not create immutable child snapshots.

## Finalization requirement

This batch must be appended to the running #727 donor-finalization process. Publication is valid
only after:

1. fresh published-main / registry reconciliation;
2. exact source-key, alias and donor-ID deduplication against every batch already included in #727;
3. correction of the pre-existing #727 registry/backfill count drift;
4. regenerated directly dependent donor/reuse/index projections;
5. exact-head required gates PASS;
6. merge followed by fresh-main verification.

Until then these 20 identities are staged, owner-authorized donor references and are **not yet
canonical planning inputs**.
