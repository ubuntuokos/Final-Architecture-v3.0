# FA3-PAID-PROVIDER-POLICY-001

Status: CANONICAL_CANDIDATE
Default: FAIL_CLOSED

## Policy

FA3 MAY integrate paid remote providers, but paid execution is disabled by default.

Paid provider execution is permitted only when all of the following are true:

1. `paid_services.enabled == true` globally;
2. the specific provider is enabled;
3. valid credentials are available through the approved secret mechanism;
4. cost/budget policy permits the operation;
5. the requested capability is authorized for remote execution;
6. an ExternalServiceExecutionLease is granted.

A provider being present in the catalog MUST NOT imply permission to spend money.

## GUI requirements

FA3 System Settings SHALL expose a dedicated External Services / Paid Services policy surface with:

- global paid-services OFF/ON switch;
- per-provider OFF/ON switches;
- credential status (never secret value disclosure);
- monthly/provider budget controls where supported;
- execution preference: Local first / Lowest cost / Fastest / Best quality / Manual selection;
- clear indication of FREE REMOTE versus PAID REMOTE providers.

The global switch MUST default to OFF.

## Provider classes

- LOCAL
- REMOTE_FREE
- REMOTE_PAID

Remote paid providers MUST remain discoverable when disabled if catalog policy permits, but execution controls MUST remain unavailable until policy requirements are satisfied.
