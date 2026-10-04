# Implementation plan — implementation-planning donor exception

**Date:** 2026-10-04  
**Scope:** FA3 development workflow and donor-governance enforcement only.

## Goal

Permit donor search, technical analysis and substantive planning-time processing before registry admission when producing an implementation plan, but only inside the originating planning conversation and its direct continuations. After owner approval of that implementation plan, every donor that was substantively processed must be published to the canonical Donor & Reference Registry before implementation execution may continue.

## Delta

1. Canonicalize the bounded planning exception without weakening the ordinary `donornak` capture rule.
2. Treat approval of the exact processed-donor set as a narrow donor-registration authorization, so a second per-link `donornak` marker is not required for that exact approved set.
3. Add a `plan` readiness phase that allows unregistered processed donors only with explicit conversation-lineage scope metadata and never grants execution.
4. Add an `execute` readiness phase that requires an approved plan and blocks until all processed planning donors are visible in the verified published canonical registry.
5. Keep `entry` compatible as a readiness preflight but remove execution authority from it; `finalize` remains exact-head and owner-review gated.
6. Extend the canonical registry writer with a plan-approved registration path that validates the approval record and exact normalized donor key.
7. Add regression coverage for bounded planning analysis, fail-closed execution, plan-approved capture, ordinary marker preservation, and the fixed 175 capability baseline.

## Donor impact

The existing canonical donor registry and donor-governance implementation were consulted. No new external donor was substantively processed for this policy implementation, so this change does not itself require a donor-registry intake mutation.

## Closure criteria

- Canonical decision and operator documentation agree.
- Planning can analyze an unregistered processed donor only under the bounded conversation-lineage exception.
- Execution fails closed while any processed donor is unregistered.
- An approved plan can authorize registration only for its exact processed donor keys.
- Ordinary unmarked links remain analysis-only outside this exception.
- Tests and protected checks pass.
- Capability baseline remains 175 and architectural-authority delta remains 0.
