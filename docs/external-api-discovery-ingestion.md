# FA3 External API Discovery — multi-source offline ingestion core

This materialization implements the offline ingestion boundary for the existing
`FA3-EXTERNAL-API-DISCOVERY-001` profile.

## Boundary

The ingestion core:

- consumes only a local snapshot pinned to a 40-character upstream commit;
- verifies every admitted README surface by SHA-256 and size;
- performs no network fetch;
- treats all upstream metadata as untrusted discovery input;
- removes affiliate/referral/tracking query parameters before identity is computed;
- strips secret-bearing query parameters before any candidate state is persisted;
- produces a derived, rebuildable and non-authoritative candidate store;
- never creates a donor, provider, MCP registration, capability or runtime activation.

The API Mega List upstream reference remains a historical pinned reference. The
candidate store is not a registry and is not canonical state.

## CLI

Create a manifest for a locally acquired pinned snapshot:

```bash
./bin/fa3-external-api-discovery snapshot \
  --snapshot-dir /path/to/API-mega-list-snapshot \
  --source-commit <40-char-commit>
```

Ingest the verified snapshot:

```bash
./bin/fa3-external-api-discovery ingest \
  --snapshot-dir /path/to/API-mega-list-snapshot
```

Validate a derived store or compare two stores:

```bash
./bin/fa3-external-api-discovery check --store candidate-store.json
./bin/fa3-external-api-discovery drift \
  --previous old-candidate-store.json \
  --current new-candidate-store.json
```

Inspect capacity policy action:

```bash
./bin/fa3-external-api-discovery capacity \
  --current-records 9000 \
  --planned-capacity 10000
```

The default state path is under the FA3 XDG state namespace. No default port,
system service, host-global environment variable or upstream uninstall is
claimed.

## Capacity policy

The derived store follows the FA3 volume policy:

- provision with 30% growth headroom;
- at 90% utilization open the next continuation volume and prefer it for new records;
- at 95% utilization rebalance in a controlled way;
- rebalance only until the source volume returns to the original 30% free reserve
  (approximately 70% utilization).

## Explicit non-scope

Reuse Catalog projection, Shared Capability detection, application-impact
projection, donor intake and provider admission are deliberately not performed
by this ingestion core. Those are separate governed stages.
