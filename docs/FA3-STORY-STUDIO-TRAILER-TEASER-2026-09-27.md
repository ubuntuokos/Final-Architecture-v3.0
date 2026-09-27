# FA3 Story Studio — Script-to-Teaser / Trailer Derivative

Date: 2026-09-27

## Purpose

The Story Studio can derive a video teaser/trailer plan from an explicitly selected screenplay revision and narrative branch without mutating canonical Story state.

This is distinct from the text-only Spoiler / Recap derivative.

## Source modes

### SCRIPT_ONLY_CONCEPT
Used before filmed material exists.

Story / Screenplay -> Trailer Plan -> FA3-MMG-CONTEXT-IR-001 -> FA3-VIDEO-001 -> OTIO editorial handoff.

Generated visuals are previs/concept material and MUST remain visibly distinguishable from photographed source footage.

### SCRIPT_PLUS_EXISTING_ASSETS
Uses available source media where possible and may request generated/previs gaps through the existing MMG/Video path.

Every sourced shot keeps media lineage. Every generated shot is explicitly labeled.

### FINISHED_FILM_CUT
Builds trailer/editorial intent from existing filmed/final source media.

Story provides narrative lineage and spoiler constraints; editorial mutation is expressed through canonical OTIO handoff. Generated previs cannot be silently inserted.

## Output types

- Teaser
- Trailer
- TV spot
- Social teaser
- Character trailer
- Episode promo
- Season promo
- Custom promo

Target duration is 6..180 seconds or a user-specified value within the admitted range.

## Trailer semantics

A Trailer Plan may contain Hook, Setup, Escalation, Turn, Montage, Emotional Beat, Button, Title Card and CTA roles.

Each shot selection binds to one or more selected Story nodes. The plan also carries source screenplay revision digest, branch, spoiler ceiling, target duration, aspect ratio and target audience.

## Spoiler boundary

A trailer always has an explicit spoiler ceiling:

NONE / LIGHT / PARTIAL / FULL / ENDING

The selected branch is mandatory. Cross-branch detail mixing is forbidden. A trailer compiler must not reveal a Story node that is outside the selected source set or violates the approved spoiler ceiling.

## Dialogue and marketing copy

Quoted screenplay dialogue requires exact source reference.

Generated title-card copy, narration or marketing copy is a separate derivative field and MUST NOT be represented as if it were canonical screenplay dialogue.

## Handoffs and authority

- Story authority: FA3-STORY-001
- Generation context: FA3-MMG-CONTEXT-IR-001
- Video generation/edit semantics: FA3-VIDEO-001
- Voice identity/synthesis: FA3-VOICE-001
- Editorial handoff: canonical OTIO -> FA3 Video Editor / compatible editorial provider
- Provider selection: FA3-AUTH-MODEL-ROUTER-001
- Resource admission: FA3-AUTH-HOST-RESOURCE-BROKER-001
- Final trailer cut: human editorial approval

No trailer derivative becomes canonical Story authority.

## Hardware Audit

The planning layer is CPU-only viable, vendor-neutral and requires 0 accelerators. Any local generative video execution is separately admitted by HRB, with 0..N accelerator topology. The Story Studio does not mutate CPU/GPU/memory/storage hardware parameters.

## Evidence boundary

Static materialization, reference tests and CI do not constitute physical current-host generative-video or final editorial PASS. Real current-host promotion remains fail-closed.
