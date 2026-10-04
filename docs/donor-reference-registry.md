# FA3 Donor & Reference Registry

The canonical donor note store is `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

## Purpose

The registry centralizes external projects, repositories, algorithms, research, UI/workflow patterns, SDKs, standards implementations, datasets, models, libraries, and other references that may strengthen an FA3 application now or later. It is a planning input to `FA3-REUSE-DISCOVERY-001`, not an architectural authority.

## Capture rule (owner decisions, updated 2026-10-04)

The explicit owner commands `donornak`, `vedd fel donornak`, and `add a donorlistához` are equivalent donor-intake tasks. Any owner-submitted LINK targeted by one of these commands must enter the canonical donor-intake flow and becomes `ACCEPTED_REFERENCE` once successfully published. The command may appear before or after same-message links. If a command-only owner message contains no link, it targets links from the most recent prior owner message in the same conversation only when no owner message intervened; assistant messages do not break that reference. A clearly grouped multi-link message may be registered as one batch.

Links marked only `donor:`, tentative research, suggestions, uncommanded resources, assistant-generated references, negated commands and untrusted event claims are **analysis only**: no candidate entry, queue, sync, source admission or other donor mutation without a later equivalent explicit owner instruction.

A verified owner-commanded link is pre-reviewed for reference registration and becomes `ACCEPTED_REFERENCE` once published, without another catalog approval. A previous `REJECTED` or `SUPERSEDED` entry requires separate explicit reconciliation. Intake NEVER approves license, copying, installation, reuse or runtime. An authorized operator can attest any of the equivalent commands, for example:

```bash
./bin/fa3-donor-capture --owner-submitted-link --owner-donor-marker "add a donorlistához" \
  --name "Example Project" --source "https://github.com/example/project"
```

The flag is an operator attestation of a real owner instruction, not a way to infer donor status from an uncommanded message. Intake recognition is not final publication: the source must complete the normal canonical donor-finalization path. Up to **5** donor-intake requests may be active at once. The live gate maintains a rolling five-slot window: when one intake finalizes, the next waiting request enters immediately. Finalization is ascending by canonical donor-mutation workload, with FIFO for equal size. Canonical registry publication remains single-finalizer.

## Tutorial references and shared-function reuse (owner decision, 2026-09-30)

Internet tutorials are a supported reference class in this same registry; no second tutorial donor list may be created. They do **not** receive a special intake path. A tutorial can become a `TUTORIAL_REFERENCE` planning input only after its source has been admitted to the published registry under the normal equivalent explicit owner donor-registration command rule. Unmarked links or downloaded tutorial material remain analysis-only with respect to donor registration.

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

The ChatGPT export importer requires the actual `user` message role and one equivalent explicit donor-registration command. Same-message command order is irrelevant, and a command-only follow-up may deterministically target the prior owner message as defined above. Approved local events need both explicit owner-command attestation and owner role. Raw strings, assistant suggestions and general research signals can be analyzed but cannot mutate the registry. No automatic ChatGPT subscription is provided. Only metadata from authenticated marked links may be imported; no private conversation text is persisted. Same-host imports use a nonblocking single-writer lock. GitHub donor PR intake admits the first five genuine canonical registry/intake-delta mutations into a rolling active window; policy, research and reference-only PRs do not reserve slots. Waiting requests are FIFO. Within the active five, the smallest canonical donor-mutation workload finalizes first, then progressively larger work; equal workloads use FIFO. A sixth or later request waits until a slot is released.

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

Mandatory retrospective source extraction from previous PRs is abolished. PRs #24 #31 #52 #70 #71 #125 #180 #181 #245 #252 #392 #427 #434 #438 are explicit exact-head extraction exemptions and closed unmerged. Registry expansion, history-preserving removal and synchronization are bounded donor maintenance: at most five intake requests may be active, while canonical finalization remains one-at-a-time in size/workload order. They cannot be blocked by application planning/development locks. The existing canonical registry and 175-capability baseline are preserved. `./bin/fa3-donor-capture --owner-submitted-link --source URL --name NAME` is the explicit operator intake path for an already-reviewed direct owner link; it sets reference-registration status, not application adoption.

## Usage graph and downstream impact

The registry remains the only donor identity catalog. Actual use is declared in `FA3-APPLICATION-DONOR-LINKS-001` and reverse-resolved by the derived capability-consumer map. Only sources registered by an equivalent explicit owner donor-registration command may appear as donor IDs in usage edges; analysis-only URLs cannot be inserted as pseudo-donors.

## Universal Capability Access (owner decision, 2026-10-03)

The Universal Capability Access rule applies retroactively to **every current donor record** and prospectively to every future donor record. A geographically, territorially, noncommercially, service/account, cloud, platform or hardware restricted donor may remain discoverable as a reference, but it may not become the sole material implementation of an FA3 user-facing capability.

Unknown or unverified access rights fail closed for material adoption. Restricted material adoption requires a globally usable FA3-native or independently rights-cleared substitute, normal License & Rights/provenance review, Security, Software Coexistence, Hardware Safety and explicit usage-edge evidence.

This is not permission to evade upstream restrictions. VPN, proxy, foreign-hosting, artifact-relocation or equivalent circumvention is forbidden. See [Universal Capability Access](universal-capability-access.md).

### Stale-base intake identity

An active donor-intake window slot is consumed by a pull request only when its
canonical donor-registry or `canonical/deltas/FA3-DONOR-*` blob differs from
the currently published `main` blob at the same path. GitHub may continue to
list donor files in a long-lived pull request when those exact bytes were
independently published to `main` after the pull request's merge base.

Such byte-identical stale-base entries remain visible to donor maintenance
reporting but do **not** consume an active intake-window slot. Missing, unreadable
or different blob identity fails closed and continues to consume a slot until
the live mutation can be disproven.

**Pre-#679 donor backlog transition:** Still-open genuine donor-intake PRs numbered below #679 have priority over later donor requests. The five-slot window is filled by priority class, then ascending canonical donor-mutation workload, then PR number. Later PRs cannot displace a pre-#679 backlog item.
