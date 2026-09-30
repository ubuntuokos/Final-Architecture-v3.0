# FA3 Donor & Reference Registry

The canonical donor note store is `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

## Purpose

The registry centralizes external projects, repositories, algorithms, research, UI/workflow patterns, SDKs, standards implementations, datasets, models, libraries, and other references that may strengthen an FA3 application now or later. It is a planning input to `FA3-REUSE-DISCOVERY-001`, not an architectural authority.

## Capture rule (owner decision, 2026-09-29)

Only a LINK explicitly preceded by the user's `donornak` marker (with or without a colon) may enter this registry. A marker can introduce one clearly grouped batch of links. Links marked `donor:`, tentative research, suggestions, unmarked resources, and assistant-generated references are **analysis only**: no candidate entry, queue, sync, source admission or other donor mutation without subsequent explicit owner direction.

A verified owner-marked link is pre-reviewed for reference registration and becomes `ACCEPTED_REFERENCE` once published, without another catalog approval. A previous `REJECTED` or `SUPERSEDED` entry requires a separate explicit reconciliation. Intake NEVER approves license, copying, installation, reuse or runtime. To register a directly marked source, an authorized operator can use:

```bash
./bin/fa3-donor-capture --owner-submitted-link --owner-donor-marker donornak \\
  --name "Example Project" --source "https://github.com/example/project"
```

This command requires a real prior user marker; the flag is an operator attestation, not a way to infer donor status from an unmarked message. Only one donor intake conversation is allowed at a time; GitHub publication must pass the exclusive live intake gate.

## Tutorial references and shared-function reuse (owner decision, 2026-09-30)

Internet tutorials are a supported reference class in this same registry; no second tutorial donor list may be created. They do **not** receive a special intake path. A tutorial can become a `TUTORIAL_REFERENCE` planning input only after its source has been admitted to the published registry under the normal explicit owner `donornak` rule. Unmarked links or downloaded tutorial material remain analysis-only with respect to donor registration.

Tutorial intake does not approve text/code/asset copying, dependency installation, provider admission, model selection or runtime promotion. Provenance and rights/licensing must be classified before reuse; unknown or incompatible rights permit factual/functional analysis and clean FA3-native re-expression only.

Each registered tutorial is decomposed into functional units and matched against the existing capability model and application inventory. If a function already exists, the existing FA3 implementation is preserved and the tutorial is adapted to the actual FA3 UI/workflow in the affected application's manual. If the function is absent, a necessity assessment and normal Reuse Discovery precede any implementation proposal.

When a tutorial-derived function is useful to multiple FA3 applications, its functional core must be implemented once in a shared FA3 layer with stable contracts and application-specific adapters. The impact analysis is retroactive: planned, in-progress and materialized applications must all be checked for manual-only changes, adapter work, local-to-shared migration, regression revalidation and current-host requalification. The 175-capability baseline cannot be silently increased.

See [FA3 Tutorial → Shared Capability → Application Manual plan](FA3-TUTORIAL-SHARED-CAPABILITY-PLAN-001.md).

## Lifecycle

`CANDIDATE -> ANALYZED -> ACCEPTED_REFERENCE` is the normal research path. Direct, pre-reviewed owner-submitted links enter `ACCEPTED_REFERENCE` upon capture for catalog inclusion only. `REJECTED` and `SUPERSEDED` are retained as research history and are excluded from derived planning candidates.

## Planning

Before a new or materially modified FA3 application, capability, or module is implemented, Reuse Discovery queries the registry and the rest of the canonical reuse sources. Matching is deterministic from capability/domain/problem/target/tag metadata. The Decision Fabric may rank already eligible candidates but cannot expand the candidate set.

## Hardware Audit

The registry and its capture/query path are metadata-only, vendor-neutral, CPU-only viable, require zero accelerators, accept accelerator cardinality `0..N`, and do not mutate hardware policy. Runtime resource authority remains `FA3-AUTH-HOST-RESOURCE-BROKER-001`.

## Safety and provenance

Every donor remains non-authoritative. Code or runtime reuse requires separate license, provenance, security, coexistence, distribution and admission review. Unknown or incompatible licenses remain reference-only or blocked for source copying. Runtime/current-host promotion can never be inferred from a registry entry.

## Conversation-adapter contract

The ChatGPT export importer requires the actual `user` message role and an explicit `donornak` label, with or without a colon, before any imported link. Approved local events need both explicit owner-marker attestation and owner role. Raw strings, assistant suggestions and general research signals can be analyzed but cannot mutate the registry. No automatic ChatGPT subscription is provided. Only metadata from authenticated marked links may be imported; no private conversation text is persisted. Same-host imports use a nonblocking lock. GitHub donor PR intake uses the oldest open PR actually changing the canonical registry or canonical donor-intake delta, plus a globally serialized Actions check; policy, research and reference-only PRs do not reserve the slot. A later competing conversation must stop and report the active PR rather than create competing donor changes.

Planning, verification and finalization during maintenance use ONLY the last exact, verified, published main snapshot. Pending PR donor entries are invisible. A new published donor batch does not automatically restart an earlier approved workflow.

## Historical ChatGPT conversation bridge

Use [FA3 ChatGPT donor-history bridge](donor-chat-history-bridge.md) for
privacy-bounded import of user-provided history exports and approved local
conversation-event streams. The event API is ready for an authorized external
source; neither the registry nor agent instructions can independently subscribe
to all ChatGPT conversations. Import remains non-authoritative and owner-marker-only; unmarked references are analysis only.

## Historical selective reuse review

The [archived Architecture v1/v2/v3 review](donor-historical-selective-review.md)
labels selected capabilities, partial implementation patterns and intended
current or future FA3 application targets without adopting entire upstream
applications or changing FA3 runtime, provider, hardware or model authorities.
Historical `REF`/`REQ` designations are not present-day admission approvals.

## NVIDIA GitHub donor curation

The [selective NVIDIA upstream reference index](nvidia-github-donor-curation-2026-09-28.md) records 39 individually checked NVIDIA repositories plus the organization-level discovery source. Entries remain non-authoritative; NVIDIA-specific paths do not replace the CPU-only and vendor-neutral hardware baseline.

## Pixar GitHub donor curation

The [Pixar upstream reference index](pixar-github-donor-curation-2026-09-28.md) inventories the official organization and records five individually checked repositories plus a discovery index as metadata-only donor candidates. It links OpenUSD/Hydra, OpenSubdiv and USD proposals to current or planned creative applications while preserving FA3-native projects, CPU-only viability, existing Khronos reuse, and all independent admission gates.

## Intel and oneAPI GitHub donor curation

[Curated source and admission-boundary notes](donor-intel-github-ecosystem-2026-09-28.md). Donor references are candidate-only; runtime/provider admission and hardware safety remain separately gated.

## Pixar OpenUSD donor curation

[Curated source and admission-boundary notes](donor-openusd-2026-09-28.md). Donor references are candidate-only; runtime/provider admission and hardware safety remain separately gated.

## Adobe donor curation

[Curated source and admission-boundary notes](adobe-github-donor-curation-2026-09-28.md). Donor references are candidate-only; runtime/provider admission and hardware safety remain separately gated.

## AMD ROCm donor curation

[Curated source and admission-boundary notes](donor-amd-rocm-curation.md). Donor references are candidate-only; runtime/provider admission and hardware safety remain separately gated.

## OSPRay donor curation

[Curated source and admission-boundary notes](donor-ospray-renderkit-ecosystem-2026-09-28.md). Donor references are candidate-only; runtime/provider admission and hardware safety remain separately gated.

## Shell-filtered AI orchestration donor discovery (2026-09-29)

The [GitHub AI-orchestration Shell topic](https://github.com/topics/ai-orchestration?l=shell) is a dynamic discovery index, not an application, provider or approved dependency. Nine distinct upstream repositories are recorded as candidate-only references. See [AI-orchestration Shell donor curation](donor-ai-orchestration-shell-2026-09-29.md). License, provenance, security, Software Coexistence, Hardware Audit, Reuse Discovery and current-host gates remain separate.

## Automatic applications and cross-application reuse

The extension described in [Application/donor inventory](application-donor-inventory.md) dynamically indexes every curated AI Studio application, keeps all GUI surfaces distinctly classified, and records separately declared planned internal and reference applications. `bin/fa3-app-donor-index` shows incoming/outgoing proposed reuse relationships and exact-match targeted impact when the donor registry changes. Registration never implies candidate promotion, code import, runtime admission or deployment.

## Reconciled donor research references (2026-09-29, candidate-only)

The following imported upstream curation reports are historical/research references for the serialized donor repair #538. Their presence does not approve any donor or application plan.

- [donors-office-3d-animation-2026-09-29.md](donors-office-3d-animation-2026-09-29.md)
- [donor-oracle-ubuntu-kubuntu-2026-09-29.md](donor-oracle-ubuntu-kubuntu-2026-09-29.md)
- [donor-opensuse-novel-writing-2026-09-29.md](donor-opensuse-novel-writing-2026-09-29.md)
- [donor-hpc-mcp-microsoft-2026-09-29.md](donor-hpc-mcp-microsoft-2026-09-29.md)
- [donor-multimedia-video-render-mcp-2026-09-29.md](donor-multimedia-video-render-mcp-2026-09-29.md)
- [donor-openal-openmax-heif-2026-09-29.md](donor-openal-openmax-heif-2026-09-29.md)
- [donor-nnstreamer-onnx-aom-a11y-2026-09-29.md](donor-nnstreamer-onnx-aom-a11y-2026-09-29.md)
- [FA3-ORCHESTRATOR-FUNCTIONAL-DONOR-EXPANSION-2026-09-29.md](FA3-ORCHESTRATOR-FUNCTIONAL-DONOR-EXPANSION-2026-09-29.md)
- [donor-ai-orchestrator-topic-2026-09-29.md](donor-ai-orchestrator-topic-2026-09-29.md)
- [godotengine-github-donor-curation-2026-09-29.md](godotengine-github-donor-curation-2026-09-29.md)
- [beadboard-agent-coordination-donor-review-2026-09-28.md](beadboard-agent-coordination-donor-review-2026-09-28.md)
- [beat-tracking-donor-curation-2026-09-28.md](beat-tracking-donor-curation-2026-09-28.md)
- [storygen-atelier-donor-review-2026-09-28.md](storygen-atelier-donor-review-2026-09-28.md)
- [three-storyboard-donor-curation-2026-09-28.md](three-storyboard-donor-curation-2026-09-28.md)
- [creative-writing-donor-curation-2026-09-28.md](creative-writing-donor-curation-2026-09-28.md)
- [storyboard-donor-curation-2026-09-28.md](storyboard-donor-curation-2026-09-28.md)
- [daw-music-generation-donor-curation-2026-09-28.md](daw-music-generation-donor-curation-2026-09-28.md)
- [github-video-editor-and-clip-donor-curation-2026-09-28.md](github-video-editor-and-clip-donor-curation-2026-09-28.md)
- [ai-video-editor-video-generation-donor-curation-2026-09-28.md](ai-video-editor-video-generation-donor-curation-2026-09-28.md)
- [video-generator-donor-curation-2026-09-28.md](video-generator-donor-curation-2026-09-28.md)
- [3dcoat-donor-curation-2026-09-28.md](3dcoat-donor-curation-2026-09-28.md)
- [vision-complementary-donor-curation-2026-09-28.md](vision-complementary-donor-curation-2026-09-28.md)
- [github-actions-runner-images-donor-curation-2026-09-28.md](github-actions-runner-images-donor-curation-2026-09-28.md)
- [chip-huyen-ml-systems-donor-curation-2026-09-28.md](chip-huyen-ml-systems-donor-curation-2026-09-28.md)
- [adaptive-representation-donor-curation-2026-09-28.md](adaptive-representation-donor-curation-2026-09-28.md)

## 2026-09-29 prospective-only donor intake

Mandatory retrospective source extraction from previous PRs is abolished. PRs #24 #31 #52 #70 #71 #125 #180 #181 #245 #252 #392 #427 #434 #438 are explicit exact-head extraction exemptions and closed unmerged. Registry expansion, history-preserving removal and synchronization are serialized donor maintenance and cannot be blocked by application planning/development locks. The existing canonical registry and 175-capability baseline are preserved. `./bin/fa3-donor-capture --owner-submitted-link --source URL --name NAME` is the explicit operator intake path for an already-reviewed direct owner link; it sets reference-registration status, not application adoption.

## Usage graph and downstream impact

The registry remains the only donor identity catalog. Actual use is declared in `FA3-APPLICATION-DONOR-LINKS-001` and reverse-resolved by the derived capability-consumer map. Only owner-`donornak` registered sources may appear as donor IDs in usage edges; analysis-only URLs cannot be inserted as pseudo-donors.
