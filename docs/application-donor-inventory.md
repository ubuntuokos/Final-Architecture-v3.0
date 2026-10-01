# FA3 application/donor inventory and cross-application reuse

This is an extension of the existing FA3 Donor & Reference Registry and Reuse
Discovery, not a second donor list or a new authority.

## Automatic registration and initial coverage

The derived index combines all current and future entries in the canonical AI
Studio curated application catalog, all GUI surface routes (clearly identified
as surfaces, not apps), explicit planned internal apps and external reference
apps in the links manifest, and the existing source-unique donor registry.

Every newly admitted curated application is visible on the next index build.
An application does not automatically become a donor or an approved dependency.
Its donor assessment starts at NOT_AUTOMATICALLY_ASSESSED; existing donor
identity is linked only by exact normalized source key.

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

Validate the tutorial/shared-capability materialization:

    ./bin/fa3-tutorial-reuse-plan --self-check --check

Plan one already-registered tutorial reference without executing tutorial commands:

    ./bin/fa3-tutorial-reuse-plan --tutorial tutorial-reference.json --check --output tutorial-plan.json

Only source-unique, materially changed donors trigger an impact report, and
only exact app aliases and normalized source keys create app-specific review
tasks. Repeated sightings or timestamp-only changes do not cause new reviews.
Unmatched donors stay in the existing registry and remain available to
Reuse Discovery for planning.

## Tutorial-derived functions and shared-capability impact

The application inventory is also the retrospective impact surface for tutorial-derived functions.

- If a registered tutorial describes an existing single-application function, preserve the implementation and adapt the tutorial to that application's real FA3 UI/workflow manual.
- If the function is missing, record a real gap and complete the necessity/placement decision before implementation.
- If two or more FA3 applications can use the same functional core, place that core once in the appropriate shared FA3 layer/component and expose it through stable contracts. Consumer applications retain only UI/workflow adapters and context-specific behavior unless an explicit reviewed exception justifies duplication.
- Impact discovery must include planned, in-progress and materialized applications. A new shared layer is never future-only.
- Migration from application-local implementations must preserve verified behavior, native project/data compatibility and capability coverage. If direct replacement cannot yet be proven safe, keep a compatibility adapter and leave migration pending rather than reducing capability.
- Every affected application's manual receives its own UI-specific projection. Shared technical documentation does not replace per-application user documentation.
- A structural/runtime shared-layer change also triggers Current Host alignment and requires the normal physical evidence before runtime promotion.

The declaration manifest exposes a `shared_capabilities` collection. Every concrete shared capability must name one owner layer and at least two known consumer applications, require retrospective review and manual updates, forbid capability loss, and remain non-authoritative until separately admitted.

An empty `shared_capabilities` collection means that the placement policy is enforced but no concrete shared runtime capability has yet been admitted by this change.

## Shared capability consumer projection

FA3-native shared components use a separate derived
`fa3.shared-capability-consumer-map.v1` projection. This avoids conflating
native shared composition with donor adoption.

For a materialized shared component:

- capability IDs are derived only from its canonical profile/contract
  `capability_bindings`; manual CAP-ID declaration is rejected;
- application consumers and existing GUI surface projections are reverse
  queryable;
- materialized components must declare Current Host impact;
- `NO_RUNTIME_IMPACT` is valid only while no executable service, provider,
  package/runtime, credential, host-resource or mutating action path is added;
- the 175 baseline remains unchanged unless an explicit capability-model
  reconciliation separately changes it.

The donor `capability_consumer_map` remains unchanged and continues to describe
registered donor usage only. The two derived views can be queried together by
capability/consumer without turning FA3-native shared components into donors.

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
flags, cross-app link integrity, and negative admission tests on each PR and
relevant main-branch change. It does not claim production runtime qualification.

## Donor lifecycle and capability-consumer reverse traceability

Every donor-record change is processed. Actual donor adoption/use requires an explicit usage edge tied to a registered donor and a primary application. The same edge may name additional shared-module, profile, authority, GUI, test and Current Host consumers. `src/fa3_application_donor_index.py` derives capability IDs only from canonical profile/contract `capability_bindings` and emits all three reverse projections. Monthly capability refresh remains 31 days; security changes are immediate; donor-driven capability regression is forbidden except for documented auditable FA3 risk.


## P0 donor usage traceability repair (2026-10-01)

The canonical donor registry capture metadata now matches the effective owner rule:
unmarked or merely suggested links remain analysis-only, while only an explicit
owner `donornak` marker may create a registry reference. The obsolete embedded
automatic-CANDIDATE capture flag is no longer retained as contradictory metadata.

Actual donor use is different from donor/reference registration. The
`donor_usage_records` list accepts either the existing application primary
consumer or a typed primary consumer, so shared profiles, contracts and providers
do not need to be misrepresented as applications. Existing application-scoped
usage remains backward compatible.

The index discovers explicit canonical donor-use evidence from provider
`donor_registry_id` bindings and License & Rights
`boundaries.donor_pattern_source` declarations. Every such declaration must
have a matching active usage edge with the evidence path recorded in provenance,
or CI fails closed. This rule does not infer adoption from names, target hints,
pattern catalogues, research notes or a Reuse Assessment that explicitly says
adoption is not authorized.

The initial evidence-backed backfill contains only the currently proven uses:
System One Harness pattern use by the two FA3-native System One provider
surfaces, and the Terax donor/reference binding by the canonical Terax provider.
Further historical edges are added only when equivalent canonical evidence
exists.

Shared-capability rules remain separate but coupled: a multi-application
functional core must live in one shared FA3 layer, and a donor-derived shared
capability requires an explicit donor usage edge before donor adoption can be
claimed. Reference-only pattern candidates do not create usage edges by
themselves.
