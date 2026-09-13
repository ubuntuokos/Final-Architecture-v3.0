# FA3-RELEASE-EVIDENCE-POLICY-001

Status: CANONICAL_CANDIDATE

## Release capability baseline

The current v3.0 capability count of 143 is a release baseline, not a permanent architectural constant.

Each release SHALL declare its expected capability baseline. Static release gates MUST compare the registry against the active release baseline rather than hard-coding a timeless global count.

Capability removal, addition or semantic change requires explicit release reconciliation.

## Host evidence scope

Canonical support and current-host activation are separate states. FA3 SHALL distinguish at least:

- CANONICAL_SUPPORTED
- HOST_AVAILABLE
- HOST_ENABLED
- HOST_ACTIVE
- PRODUCTION_PROMOTED

Full current-host runtime evidence is required for capabilities that are:

- mandatory on that host; or
- explicitly enabled; or
- production-active.

A supported but disabled optional provider MAY satisfy host evidence with negative assurance, including proof of no unexpected process, port, accelerator allocation, egress or authority.

## Update rings

- LAB: floating upstream permitted in isolation.
- CANDIDATE: resolved source revision required.
- STAGING: immutable source/digest required.
- PRODUCTION: immutable artifact plus provenance/SBOM as applicable.
- CANONICAL: release/evidence/registry reconciliation required.

Production MUST NOT use floating main branches.
