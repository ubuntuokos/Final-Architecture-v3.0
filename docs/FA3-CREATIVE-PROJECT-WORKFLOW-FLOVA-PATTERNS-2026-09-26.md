# FA3 Creative Project Workflow — Flova-derived pattern materialization

Date: 2026-09-26

## Decision

FA3 reuses selected workflow patterns observed in Flova public documentation without adopting Flova as a runtime, provider, account dependency, credential dependency, architectural authority, or imported skill/code source.

The implementation is an overlay on existing FA3 layers:

- Skill Fabric owns reusable task-scoped workflow guidance.
- FA3 Video + MMG Context IR own provider-neutral creative project context and context-aware regeneration semantics.
- UAF owns typed action execution.
- Model Router owns model/provider selection.
- HRB owns host resource admission and placement.
- AUTH-HUMAN owns approval/sign-off.
- Evidence owns receipts/provenance.
- OTIO / FA3 Video Editor or another separately admitted editorial surface owns timeline mutation.

## Adopted patterns

1. Persistent project-scoped specification and provenance-aware documents.
2. Explicit story / shot / storyboard / media relationship graph.
3. Reusable creative workflow skill.
4. Dependency-aware scoped revision with preservation of unaffected nodes.
5. Human approval boundary when a local change reaches locked or approved state.
6. Editorial handoff via canonical OTIO or FA3 Video Editor command surface.
7. Parallel planning/context work without granting execution authority to the skill.

## Explicit non-adoption

- No Flova runtime, API, account, credential or provider dependency.
- No direct provider invocation from the creative skill.
- No global project-corpus auto-injection.
- No silent whole-project regeneration.
- No direct .kdenlive/native editor file mutation.
- No static/reference evidence is promoted to current-host runtime evidence.

## Hardware Audit

Planning and validation are CPU-only viable. Accelerator cardinality is 0..N. Any accelerated execution remains HRB-admitted. Any hardware parameter mutation remains inside the FA3 Hardware Safety Envelope.

## Evidence boundary

The bundled reference evidence proves only static contracts and deterministic reference regressions. Physical generation/editor execution and current-host production promotion remain separate obligations.
