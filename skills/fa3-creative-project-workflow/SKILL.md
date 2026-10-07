---
name: fa3-creative-project-workflow
description: Task-scoped creative project workflow for story, storyboard, media binding, revision planning and editorial handoff.
version: 1.0.0
trigger: creative.project.workflow
---

# FA3 Creative Project Workflow

## use_when
Use for a bounded film/video project task that spans project specification, story or screenplay context, storyboard/shot planning, media generation or binding, review, scoped revision, or editorial handoff.

## inputs
- A bounded creative project state or selected project nodes.
- Applicable story, shot, character, environment, media and editorial constraints.
- User documents, AI-authored notes and imported references with origin/provenance retained.
- The requested task scope and any human approval state.

## procedure
1. Validate the project graph and preserve the distinction between user-authored documents, AI-authored notes and imported references.
2. Select the smallest deterministic eligible Skill Fabric context for the task; do not load the whole project corpus by default.
3. Build or update explicit story, shot, storyboard-card and media bindings without inventing hidden relationships.
4. Express model-backed generation as typed UAF intent. Model/provider selection remains with Model Router and host resource admission remains with HRB.
5. Before any revision, identify explicitly changed nodes and compute downstream invalidation only through dependency edges marked as revision-impacting.
6. Preserve unaffected nodes, frozen constraints and native editable artifacts by default.
7. If an affected node is locked or already human-approved, require the applicable approval before execution.
8. Project editorial changes through OpenTimelineIO or the FA3 Video Editor/admitted editorial command surface; never mutate native editor files directly.
9. Require explicit acknowledgement before billable remote generation or rendering.
10. Emit revision, decision, action, provenance and evidence receipts needed by the existing authorities.

## guardrails
- This skill is declarative task context, not an execution, workflow, model-routing, resource, security, evidence or human-approval authority.
- Direct provider invocation is forbidden; do not directly invoke a provider, model endpoint, shell command, secret, external account or paid service.
- Silent provider or backend fallback is forbidden.
- Do not inject the full project corpus when a bounded context slice is sufficient.
- Do not silently rewrite dialogue, visible text, identity, voice, approved story state or locked assets.
- Direct .kdenlive XML or other native-project mutation is forbidden outside an admitted application/editorial surface.
- External creative platforms are reference-only pattern sources unless separately admitted.
- A static or reference PASS never proves current-host production execution.

## pitfalls
- Treating a workflow skill as an autonomous creative authority.
- Regenerating the full project after a local change.
- Invalidating nodes without an explicit dependency edge.
- Flattening editable native artifacts into generated outputs.
- Letting a convenient provider choice bypass Model Router or HRB.
- Treating generated media as automatically bound to a shot or storyboard card.

## acceptance_checks
- Project graph validation passes.
- A bounded revision has an explicit invalidation plan and preserves unrelated nodes.
- Locked or human-approved affected nodes have an approval boundary.
- Model/provider and host-resource decisions remain outside the skill.
- Editorial projection uses OTIO or an admitted FA3 editor command surface.
- Native project round-trip semantics remain intact.
- Provenance/evidence is emitted without claiming unexecuted current-host runtime.
