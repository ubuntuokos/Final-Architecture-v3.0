# FA3 application/donor inventory and cross-application reuse

This is an extension of the existing FA3 Donor & Reference Registry and Reuse
Discovery, not a second donor list or a new authority.

## Automatic registration and initial coverage

The derived index combines all current and future entries in the canonical AI
Studio curated application catalog, all GUI surface routes (clearly identified
as surfaces, not apps), explicit planned internal apps and external reference
apps in the links manifest, and the existing source-unique donor registry.

Every newly admitted curated application is visible on the next index build.
Every registered application is subject to FA3 development, safety, coexistence,
governance and lifecycle rules even when it is not formally declared as a
dependency of the component being changed. An application does not automatically
become a donor or an approved dependency. Its donor assessment starts at
NOT_AUTOMATICALLY_ASSESSED; existing donor identity is linked only by exact
normalized source key. Actual donor use must also be recorded in
`donor_usage_records`, which provides the canonical reverse donor -> application
impact path.

## Cross-application relationships

The relationship manifest identifies which application offers an artifact or
pattern, which application could consume it, and the human approval and native
project file preservation boundary. Both outgoing and incoming links are
queryable. Initial cases include Video Editor, QuickClip, Story/Screenplay,
Music Studio, Character Studio, Bforartists, Krita and Ardour. All proposed
links require independent license, provenance, security, coexistence, hardware,
fidelity and current-host admission review before real integration.

## Commands

Build the inventory and check its integrity:

    ./bin/fa3-app-donor-index --check --summary

Inspect both directions of an application relationship:

    ./bin/fa3-app-donor-index --app fa3.video-editor

Targeted re-evaluation when the canonical donor registry changes:

    ./bin/fa3-app-donor-index --previous-registry old-registry.json --output impact.json

Every donor-record change triggers an impact record, including provenance,
observation, pin, archival and timestamp metadata changes. Application-specific
reconciliation is derived from explicit donor-usage records and exact normalized
source/target matching. Security-sensitive changes require immediate trust and
security reconciliation. Capability-affecting donor changes require capability
parity/non-regression review. Unmatched donor changes are still processed as
mandatory donor reconciliation rather than being silently ignored.

## Mandatory planning and audit

Before any new or materially modified FA3 application, capability or module,
run existing Reuse Discovery plus an app-index lookup and assess the resulting
eligible donors and cross-app offers. Neither tool can expand an admitted
candidate set or bypass existing architectural authorities.

Hardware Audit: index generation is metadata-only, vendor-neutral and CPU-only
viable with accelerators 0..N. No hardware configuration, device probing,
software installation, provider activation or model choice is performed. HRB
continues as sole resource authority, Model Router as sole model-route authority.
Wayland is preferred for future GUI adapters and X11 remains supported.
No current-host execution PASS is claimed by these static checks.

The separate CI workflow enforces catalog coverage, donor uniqueness, safety
flags, cross-app link integrity, reverse usage records and negative admission
tests on each PR and relevant main-branch change. A scheduled monthly gate checks
that each active donor's capability list is refreshed within 31 days. Donor
security changes do not wait for that cycle. Donor replacement or rematerialization
must preserve application capability unless continued capability has documented,
auditable evidence of risk to an FA3 component. Structural or runtime changes
must also reconcile Current Host obligations. These static checks do not claim
production runtime qualification.
