# FA3 OSINT case interchange (existing CAP-053 / CAP-054)

This follow-on materializes **reference contracts, pure structural checks and
non-executable provider plans**, not a new OSINT application, authorization
service, or production runtime. Stacked on the pinned Awesome OSINT Arsenal
catalog PR; merge the catalog base first.

## Scope and lineage

- Existing source donor: FA3-DONOR-RAWFILEJSON-AWESOME-OSINT-ARSENAL-001.
- Independently reviewed Maigret source: https://github.com/soxoj/maigret
  pinned to b6642744988e7e6c2d21f75db60ec3093019ba25.
- Maigret upstream repository LICENSE is MIT. Its transitive dependencies
  and target websites have separate license, security, privacy and API/ToS
  obligations. No Maigret executable or dependency is installed.
- Typed contracts: canonical/contracts/FA3-OSINT-CASE-INTERCHANGE-001.json.
- Case-bound pure checks: src/fa3_osint_case.py. Negative tests:
  tests/test_osint_case.py.

## Consumer contract

An InvestigationRequest carries the case ID, purpose, explicit target scope,
data classes, expiry, existing Security Policy receipt reference and
authorization/human review references when applicable.

A structurally valid request returns PENDING_INDEPENDENT_SECURITY_AUTHORITY_VERIFICATION.
It never grants authority by itself. The existing Security/MCP authority MUST
authenticate the externally issued references and verify action-specific scope
again before any real provider is called.

A candidate review evaluates source URL, immutable version, independently
verified per-tool license, supply chain, privacy/terms, host coexistence and
network egress. Even all-true metadata flags only yield
PENDING_SEPARATE_PROVIDER_ADMISSION; no user-provided flags can self-admit
a provider. Sensitive sources require an additional independent review.

A typed ObservationProjection carries case scope, source/tool provenance,
acquisition time, SHA-256 of original artifact bytes, extracted structured
data, uncertainties and separate interpretation semantics. It is **not** an
Evidence Registry entry: an authorized host-side collector must submit it via
FA3-EVIDENCE-ENVELOPE-001 to the existing Evidence authority.

The Maigret mapping is currently an explicit NON_EXECUTABLE_PLAN with no
shell command and no network request. It requires AUTHORIZED_SUBJECT scope,
literal username in the case allowlist, and independent real admission prior
to any future execution.

## Hardware Audit

CPU-only, zero mandatory accelerators, 0..N accelerator inventory, vendor
neutral; pure Python code has no GPU, model, network or background tasks.
Future runtime must use HRB for all resource decisions; display GPU remains
subject to existing explicit application-level rules. Future AI uses only
the single central Model Router, no direct model pins or automatic fallback.
No global Python installation, host default port or forced upstream uninstall.

## Future runtime and current-host evidence: NOT DONE

1. Verify actual Security/MCP receipts using existing trusted services
   and implement authorization-specific, fail-closed invocation handoff.
2. Review an immutable Maigret release with complete dependency lock/SBOM,
   target-site terms, privacy and purpose scope and isolated venv.
3. Add a replaceable Maigret runtime adapter under the existing CAP-053 and
   formal FA3 admission; other candidates remain independently queued.
4. Bind approved typed observations into existing application consumers.
5. Run exact current-host positive/negative tests, audit egress, secrets,
   CPU/accelerator leases, rollback and evidence/promotion gates.

Local reference regression:

    PYTHONPATH=src python3 -m unittest tests.test_osint_case tests.test_osint_arsenal_catalog -v
    bash bin/fa3-reuse-assess --intent canonical/intents/FA3-OSINT-CASE-APPLICATION-INTENT-001.json
    ./bin/fa3-enforce reuse-discovery
    ./bin/fa3-enforce hardware-portability

Reference CI has no right to claim live provider installation, execution,
current-host PASS or production promotion.
