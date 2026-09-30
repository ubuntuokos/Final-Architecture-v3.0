# FA3 Donor ↔ Capability ↔ Consumer Usage Graph

The capability map is a **derived projection**, not a new FA3 authority and not a
second donor registry. Its single declaration source is
`canonical/FA3-APPLICATION-DONOR-LINKS-001.json::donor_usage_records`.

## Purpose

The graph answers three update questions without manual archaeology:

1. **Donor → Capability → Consumer:** which FA3 capabilities and consumers use a
   donor-derived pattern, algorithm, workflow, code/runtime dependency or
   reference binding?
2. **Capability → Donors + Consumers:** which registered donors contribute to a
   capability and which applications/modules/surfaces consume it?
3. **Consumer → Capabilities + Donors:** which donor-derived capabilities are
   used by one application, shared module, profile, authority projection, GUI
   surface, test harness or Current Host path?

The reverse views are generated from one edge list. They must never become
independent hand-maintained `used_by` or `uses` authorities.

## Capability identity

A usage edge stores `fa3_binding_refs`, never hand-written capability IDs.
`src/fa3_capability_usage_graph.py` resolves those references against canonical
profiles/contracts and derives only their declared `capability_bindings`.

If no canonical binding can be resolved, the edge is
`UNRESOLVED_CAPABILITY_BINDING`. Active donor use that requires a capability
binding fails closed. A contributor must not infer a CAP number from a feature
name.

The fixed release baseline remains **175** and this graph creates neither a new
capability nor a new architectural authority.

## Consumer types

Supported consumer kinds are:

- `APPLICATION`
- `SHARED_MODULE`
- `PROFILE`
- `AUTHORITY`
- `GUI_SURFACE`
- `TEST_HARNESS`
- `CURRENT_HOST_PATH`

Relationships are explicit: `DIRECT`, `INDIRECT_SHARED`, `OPTIONAL`,
`GUI_PROJECTION`, `TEST_ONLY`, or `ENFORCEMENT_OWNER`.

## Current Host

Every new usage edge must classify its Current Host impact as one of:

- `NO_RUNTIME_IMPACT`
- `STRUCTURAL_REASSESSMENT_REQUIRED`
- `RUNTIME_REQUALIFICATION_REQUIRED`

This field is only an impact declaration. It does not create a Current Host
authority and cannot create a PASS. Structural/runtime enforcement stays with
the existing Current Host policy/gates, including the structural-impact rule
when that canonical policy is active. Historical evidence is never promoted by
the map.

## Update impact

When a previous donor registry snapshot is supplied, every changed donor record
is joined with active usage edges and produces:

- affected FA3 capability IDs;
- affected typed consumers;
- application-specific reconciliation inherited from the application/donor
  index;
- capability-binding revalidation;
- Current Host reconciliation requirement when the declared edge classification
  requires it.

Security-sensitive donor changes retain the existing immediate reconciliation
rules. Capability regression remains forbidden except for documented,
auditable FA3 safety risk.

## Commands

Validate and print a summary:

```bash
./bin/fa3-capability-map --check --summary
```

Write the complete derived graph:

```bash
./bin/fa3-capability-map --check --output capability-usage-graph.json
```

Reverse lookup examples:

```bash
./bin/fa3-capability-map --donor FA3-DONOR-EXAMPLE-001
./bin/fa3-capability-map --capability CAP-005
./bin/fa3-capability-map --consumer APPLICATION:fa3.video-editor
```

Donor-update impact:

```bash
./bin/fa3-capability-map \
  --previous-registry old-registry.json \
  --check --output capability-update-impact.json
```

Only donor IDs present in the canonical published Donor & Reference Registry can
appear on canonical usage edges. Unmarked research URLs remain analysis-only and
cannot be inserted into this graph as donor identities.
