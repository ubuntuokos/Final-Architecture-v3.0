# FA3 Shared Web Acquisition State

`FA3-SHARED-WEB-ACQUISITION-STATE-001` is a zero-authority shared child of the existing Web AI profile. It hardens durable acquisition state without creating a Crawlee, Crawl4AI, Apify, browser, resource, model, MCP or knowledge authority.

## State model

Requests carry stable request identity, dedupe identity, backend, policy revision and provenance. Claims are lease-bound. Expired claims are requeued with an explicit recovery receipt. Retry waits and terminal states are explicit. A deterministic JSON snapshot allows restart/recovery testing without depending on wall-clock time.

HTTP and browser-backed acquisition use the same request/result binding. Browser mutation and verification remain the responsibility of `FA3-BROWSER-ACTION-RUNTIME-001`; this layer does not click, type, launch a browser or select a browser provider.

## Crash-consistent persistence

The reference core can persist a deterministic snapshot through a same-directory temporary file, file flush + `fsync`, and atomic `os.replace`. If replacement fails, the previously committed snapshot remains unchanged and the temporary file is cleaned up. Corrupt/unreadable snapshots fail closed.

## Origin and session policy

An origin policy must explicitly permit robots access and satisfy the configured politeness interval before a request can be claimed. Concurrency values are advisory only. Session replacement is allowed only after the predecessor session is retired or blocked, preventing silent session substitution.

## HRB boundary

The reference core exposes only a load observation with `advisory_only=true` and `may_change_concurrency=false`. `FA3-AUTH-HOST-RESOURCE-BROKER-001` remains the sole physical placement/reservation/lease authority.

## Apify donor boundary

The published planning snapshot contains only the organization-level `FA3-DONOR-APIFY-ORG-001` reference. The reviewed child repositories remain analysis-only. This materialization copies no upstream source, installs no package, enables no Apify Cloud/Actor/MCP/Skill runtime, creates no child donor record, and creates no donor usage edge.

Future material adoption of a child repository requires explicit owner `donornak` registration, exact revision/provenance, License & Rights, security, Software Coexistence, Hardware Safety, Reuse Assessment, explicit adoption approval and a canonical usage edge.

## Verification

Run:

```bash
python -m unittest tests.test_shared_web_acquisition_state -v
python src/fa3_shared_web_acquisition_state_gate.py --root .
```

The materialization is static/reference-library scope only. It makes no physical Current Host PASS or runtime-promotion claim.
