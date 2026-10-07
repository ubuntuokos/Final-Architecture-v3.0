# CFA3 donor L0-L5 Source Graph and fast-access index

Status: owner-approved materialization, 2026-10-07.

This layer extends the published Registry v2 identity/index architecture without creating a second donor authority. The canonical donor registry remains the registration source; the source graph records discovery and provenance.

## Three independent dimensions

- discovery_depth: L0-L5 provenance only;
- strategic_value: CRITICAL/HIGH/MEDIUM/LOW/HISTORICAL;
- integration_priority: P0-P4 current-phase accessibility.

Depth never lowers strategic value or integration accessibility. An L5 SDK may be CRITICAL and P0/P1.

## Fast path

SDKs, skills, codecs, plugins, agents, their SDK/framework variants, protocols, interoperability toolkits, shared libraries and reference implementations are classified as soon as discovered. P0/P1 is a visibility/review index only. Unknown rights keep a strategically critical SDK in P1 review rather than silently making it usable.

## Identity and provenance

One normalized source key maps to one graph node. Every parent/root path remains an edge. If a discovered source already exists in the canonical donor registry, the existing donor identity is reused. Otherwise it remains DISCOVERED_UNREGISTERED.

## Safety

Discovery does not register a donor, copy code, install dependencies, admit providers/models, activate runtimes or modify the 175-capability baseline. Private/local addresses are not crawled. Rights, security and admission reviews remain fail-closed.

## Commands

Seed the graph from all published canonical donors:

    ./bin/cfa3-donor-source-graph seed --output /tmp/cfa3-source-graph

Run network discovery recursively through exactly five levels:

    GITHUB_TOKEN=... ./bin/cfa3-donor-source-graph crawl --output /tmp/cfa3-source-graph

The network crawl emits source-graph.json plus integration-priority, strategic-value, relation-type and depth indexes. The P0/P1 index exists to make high-value building blocks rapidly visible during the current CFA3 planning phase.
