# FA3 Donor & Reference Registry

The canonical donor note store is `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`.

## Purpose

The registry centralizes external projects, repositories, algorithms, research, UI/workflow patterns, SDKs, standards implementations, datasets, models, libraries, and other references that may strengthen an FA3 application now or later. It is a planning input to `FA3-REUSE-DISCOVERY-001`, not an architectural authority.

## Capture rule

Any source described during FA3 work as potentially useful as a donor or reference is captured immediately as `CANDIDATE`, even when the target application is still only planned. The capture operation records the source once and merges later observations.

```bash
./bin/fa3-donor-capture \
  --name "Example Project" \
  --source "https://github.com/example/project" \
  --domain creative \
  --target "World Generator" \
  --tag workflow \
  --note "Potential donor identified during research."
```

Capture does **not** approve source copying, installation, provider admission, model routing, runtime use, or architectural authority.

## Lifecycle

`CANDIDATE -> ANALYZED -> ACCEPTED_REFERENCE` is the normal positive path. `REJECTED` and `SUPERSEDED` are retained as research history and are excluded from derived planning candidates.

## Planning

Before a new or materially modified FA3 application, capability, or module is implemented, Reuse Discovery queries the registry and the rest of the canonical reuse sources. Matching is deterministic from capability/domain/problem/target/tag metadata. The Decision Fabric may rank already eligible candidates but cannot expand the candidate set.

## Hardware Audit

The registry and its capture/query path are metadata-only, vendor-neutral, CPU-only viable, require zero accelerators, accept accelerator cardinality `0..N`, and do not mutate hardware policy. Runtime resource authority remains `FA3-AUTH-HOST-RESOURCE-BROKER-001`.

## Safety and provenance

Every donor remains non-authoritative. Code or runtime reuse requires separate license, provenance, security, coexistence, distribution and admission review. Unknown or incompatible licenses remain reference-only or blocked for source copying. Runtime/current-host promotion can never be inferred from a registry entry.

## Conversation-adapter contract

A repository-aware FA3 planning/research agent MUST capture a tentative donor signal as soon as it is encountered. A bridge that receives a relevant conversation message can pass it to `./bin/fa3-donor-capture --mention "<message>"`. The parser recognizes explicit Hungarian/English donor cues, extracts one GitHub source or accepts `--name` for an unnamed project, and deliberately stores **only donor metadata**, not the original private conversation text. For multiple source URLs, call capture once for each source. Without a connected bridge, unrelated ChatGPT conversations are not automatically visible to this repository: a declaration in `AGENTS.md` cannot itself subscribe to external conversations.

Identical display names from different source repositories are distinct records; repeat observations with the **same normalized source key** are merged. Newly captured references are always candidates regardless of earlier assessments until explicit normal admission.

## Historical ChatGPT conversation bridge

Use [FA3 ChatGPT donor-history bridge](donor-chat-history-bridge.md) for
privacy-bounded import of user-provided history exports and approved local
conversation-event streams. The event API is ready for an authorized external
source; neither the registry nor agent instructions can independently subscribe
to all ChatGPT conversations. Import remains a non-authoritative candidate
capture path.

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

## Automatic applications and cross-application reuse

The extension described in [Application/donor inventory](application-donor-inventory.md) dynamically indexes every curated AI Studio application, keeps all GUI surfaces distinctly classified, and records separately declared planned internal and reference applications. `bin/fa3-app-donor-index` shows incoming/outgoing proposed reuse relationships and exact-match targeted impact when the donor registry changes. Registration never implies candidate promotion, code import, runtime admission or deployment.

## Awesome OSINT Arsenal catalog source (offline pinned)

The existing donor FA3-DONOR-RAWFILEJSON-AWESOME-OSINT-ARSENAL-001 is reconciled
to the immutable upstream snapshot in
research/external-project-radar/osint/awesome-osint-arsenal/. The catalog
importer is a metadata-only, non-executing projection for existing CAP-053
and CAP-054 planning: 753 raw tools, 752 distinct IDs, 26 categories and 264
missing direct URLs at the reviewed source commit. The collection MIT license
does not confer licenses or admission for any listed third-party tool.

See docs/osint-arsenal-catalog-integration.md for CLI usage, independent
downstream admission stages, mandatory authorization scope and Hardware Audit.

## Maigret independent source review

The existing CAP-053 Maigret reference has now been tied to its verified upstream
source and a new source-unique donor record FA3-DONOR-SOXOJ-MAIGRET-001. The
source license is MIT at the reviewed immutable commit, but transitive
packages, destination website terms, case authorization and runtime admission
remain independent and pending. The typed non-executing case interface and
Maigret plan are described in docs/osint-case-interchange.md.
