# FA3 Awesome OSINT Arsenal — pinned donor catalog integration

**Scope:** existing CAP-053 / CAP-054; zero capability or authority delta. This change materializes the catalog-import portion of the plan only. No runtime OSINT provider is installed, admitted, configured or tested on a production host.

## Source and provenance

- Source: https://github.com/rawfilejson/awesome-osint-arsenal
- Pinned commit: 2c6475a1d5b941cc598b3612419ef22e6d903ce8
- Upstream source Git blob SHA-1: e6a76245dfd5e1e3a345531d32a36f2a543194cc
- Upstream catalog, LICENSE and machine pin: research/external-project-radar/osint/awesome-osint-arsenal/
- Collection license: MIT, copied with the snapshot. **Listed third-party tools do not inherit the collection's MIT license**. Each requires individual licence/provenance/privacy and API terms review.
- Reuses the existing donor FA3-DONOR-RAWFILEJSON-AWESOME-OSINT-ARSENAL-001; no second donor registry.

The pinned source contains **753** raw records, **752** distinct IDs, **26**
normalized categories and **264** raw records without direct source URLs.
The two social-searcher records merge to one metadata record while retaining
both source positions and name aliases, and only the explicit upstream URL.
Never invent an upstream URL from package names or README install examples.

## Offline import

From the FA3 checkout:

    bash bin/fa3-osint-arsenal-import --check --summary
    bash bin/fa3-osint-arsenal-import --output "$TMPDIR/fa3-osint-catalog.json"

The normalized output is an **untrusted metadata projection**, never a provider
registry or list of executable candidates. It never exposes or executes source
installer command text. Source byte changes are blocked by the immutable Git
blob pin; any new pin requires explicit review. No network, root or third-party
Python dependencies. This snapshot is research-only input, not a runtime
distribution dependency.

## Existing ownership

- Donor & Reference Registry: source identity, assessment and donor metadata.
- Reuse Discovery: deterministic assessments scoped to an FA3 application.
- CAP-053 / CAP-054: existing OSINT & Evidence and External Asset Inventory.
- CAP-035 / CAP-051 / CAP-103: optional file metadata, security and web research consumers.
- Existing Security Policy, MCP, Model Router, HRB, Secrets and Evidence authorities remain unchanged.

A catalog record cannot confer execution, network, credential, model,
resource, provider or release-promotion authority. Future investigation
observations require acquisition time, original source, transformation lineage
and uncertainty, bound to the existing FA3 Evidence Envelope.

## Hardware Audit / coexistence

- This importer is CPU-only and vendor-neutral; accelerators 0..N, no probing
  or hardware mutation. It does not use any GPU or model.
- Future accelerated providers require HRB lease and existing display-GPU
  designation/explicit application opt-in; no automatic extra GPU or silent fallback.
- Downstream AI must use central Model Router, without direct model pins.
- Never run upstream install.sh, modify global /opt, use pip
  --break-system-packages, mutate a system Python or claim host-wide ports.
- Future Python adapters require isolated venv and pinned independently verified
  dependencies. Wayland preferred for UI; X11 support required; no new UI here.

## Authorization, safety and admission

Before a downstream tool is callable, require independently verified upstream
locator and immutable version, per-tool license/distribution, supply chain,
software coexistence, privacy/legal basis, purpose and target scope, API terms,
network egress and secret handling, plus negative and current-host testing.
High-risk breach, people/face identification, credential/phishing and
offensive tools remain non-runnable metadata pending a separate explicit
authorization and relevant security review. Never conduct individual-specific
research merely because an item appears in this catalog.

## Planned follow-on stages (not implemented by the catalog PR)

C. Independently assess downstream security, licenses, privacy and API terms;
   unknown or unreviewed tools remain blocked.
D. Reconcile the existing Maigret reference, then implement a small number
   of separately admitted and narrowly scoped metadata/domain adapters.
E. Expose typed observations to the existing Research, Security, Forensics,
   Photo, Video, Documents and Geo/World applications without a second authority.
F. Collect separate current-host execution and rollback evidence for enabled
   adapters, and negative assurance for disabled optional adapters, under
   existing Evidence Registry, Acceptance and Promotion governance.

A/B delivered in the catalog PR: donor reconciliation, immutable offline
upstream snapshot, deterministic normalization, negative tests and CI.

## Validation / claims boundary

    PYTHONPATH=src python3 -m unittest tests.test_osint_arsenal_catalog -v
    bash bin/fa3-osint-arsenal-import --check --summary
    bash bin/fa3-reuse-assess --intent canonical/intents/FA3-OSINT-ARSENAL-CATALOG-APPLICATION-INTENT-001.json
    ./bin/fa3-enforce reuse-discovery
    ./bin/fa3-enforce hardware-portability

Reference CI establishes import/source identity/contract conformance only.
It does not establish current-host runtime execution or production promotion.
