# FA3 Change-History specification donor intake — 2026-10-02

**Authority:** owner-explicit `donornak` registration.  
**Scope:** reference metadata only; no code, dependency, provider, model or runtime admission.

This intake adds four exact specification pages to the existing `FA3-DONOR-REFERENCE-REGISTRY-001` as `ACCEPTED_REFERENCE` records:

- SLSA Build Provenance — https://slsa.dev/spec/v1.2/build-provenance
- in-toto specifications — https://in-toto.io/docs/specs/
- OpenTelemetry semantic conventions for events — https://opentelemetry.io/docs/specs/semconv/general/events/
- OpenLineage Lineage Job Facet — https://openlineage.io/docs/spec/facets/job-facets/lineage/

## Intended FA3 planning value

These sources are registered because the approved `FA3-CHANGE-HISTORY-INTELLIGENCE-001` design needs strong reference patterns for:

- artifact/build provenance and verifiable source-to-output statements;
- attestation subject/predicate separation;
- structured event naming, attributes and correlation;
- explicit source-to-target lineage without manufacturing all-to-all edges.

They are planning/reference inputs only. The FA3 Journal, Evidence, Canonical Registry, Security, License & Rights, Model Router, HRB, MCP Gateway and workflow authorities remain unchanged.

## Admission boundary

This intake does **not**:

- copy or vendor specification implementation code;
- create a package/runtime dependency;
- admit an observability or lineage service;
- add a provider/model;
- create an MCP connector;
- activate cloud/network access;
- create a donor usage edge;
- change the fixed capability baseline of 175;
- create an architectural authority;
- claim Current Host PASS.

The registry records reference-page license metadata as `UNKNOWN / UNVERIFIED_REFERENCE_PAGE`. Public availability is not source-copy permission. Any later material reuse remains subject to the normal License & Rights/provenance, security, Software Coexistence, Hardware Safety and distribution checks.

## CHIF handoff

If these references are selected by the fresh CHIF Reuse Assessment after publication, each actual pattern use must receive an explicit canonical donor usage edge. Reference registration alone is not adoption.

Parent published main: `9a9768a98e07b4961c460b2e6f3f2e00ad927c93`  
Parent donor count: **1340**  
Proposed donor count: **1344**  
Capability baseline: **175**  
Capability delta: **0**  
Authority delta: **0**
