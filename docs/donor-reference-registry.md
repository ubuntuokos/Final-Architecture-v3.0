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
