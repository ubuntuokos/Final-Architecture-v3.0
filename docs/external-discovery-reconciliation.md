# FA3 External Discovery Reconciliation

`FA3-EXTERNAL-DISCOVERY-RECONCILIATION-001` connects the derived External API
Discovery Candidate Store to the existing FA3 reuse, donor, provider, shared
capability and application inventories.

It is a **projection**, not a registry and not an admission path.

## Data flow

```text
Derived Candidate Store
        |
        +--> Reuse Catalog query
        +--> Donor Registry query
        +--> canonical provider query
        +--> Shared Module Pattern query
        +--> Application/Donor Index query
        |
        v
Derived reconciliation projection
```

No branch of this flow grants runtime authority.

## Match strength

### Exact source identity

Only exact canonical source identity can produce:

- `EXISTING_DONOR`;
- `EXISTING_PROVIDER`;
- confirmed existing CAP bindings when that exact matched canonical record
  already exposes explicit CAP bindings.

### Review-only matching

Deterministic token overlap can produce:

- `POSSIBLE_EXISTING_DONOR_REVIEW`;
- `POSSIBLE_EXISTING_PROVIDER_REVIEW`;
- `EXISTING_CAPABILITY_SUBFUNCTION_REVIEW`;
- reuse/shared pattern review suggestions.

A token match never becomes a canonical relationship automatically.

## Donor rule

A discovery candidate that is not already represented by a canonical donor is
**not** inserted into the Donor Registry. New donor intake still requires the
explicit owner donor marker and the existing serialized donor intake workflow.

No donor usage edge is created from discovery alone.

## Provider rule

A discovery candidate may be classified as
`NEW_PROVIDER_CANDIDATE_REQUIRES_ADMISSION`, but no provider record, MCP
registration, network permission or runtime activation is created.

## Capability rule

Reconciliation can return:

- `EXACT_EXISTING_CAPABILITY`;
- `EXISTING_CAPABILITY_SUBFUNCTION_REVIEW`;
- `UNMAPPED_FUNCTIONAL_GAP_REVIEW`.

The last state does **not** create CAP-176 or any other new CAP identifier.
The canonical baseline remains 175.

## Shared capability and retrospective impact

For every candidate, the reconciler:

1. checks existing shared capability consumer edges;
2. checks shared-module reuse patterns;
3. evaluates known capability consumers;
4. scans every registered application name/alias for deterministic relevance;
5. records the total number of applications scanned.

If an existing shared binding is found, it is preferred. If there is no
existing shared binding but at least two affected applications are identified,
the result is `SHARED_REUSE_CANDIDATE`. That result is proposal-only and
cannot materialize a shared module.

## CLI

```bash
./bin/fa3-external-discovery-reconcile reconcile \
  --store /path/to/candidate-store.json \
  --output /path/to/reconciliation.json

./bin/fa3-external-discovery-reconcile check \
  --projection /path/to/reconciliation.json

./bin/fa3-external-discovery-reconcile candidate \
  --projection /path/to/reconciliation.json \
  --candidate-id EXTDISC-...
```

## Current Host

This is a structural metadata/reconciliation change. It does not add a runtime
provider and does not change the 175-capability baseline or the existing
current-host obligation count. Runtime or structural changes proposed later
from this projection remain subject to their normal Current Host gates.
