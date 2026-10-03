# FA3 Platform and Product Family taxonomy

Status: **owner-approved static materialization** (2026-10-03).

## Canonical hierarchy

```text
FA3 Platform
  -> Product Family
    -> Application
      -> Shared / Domain Module
        -> Engine / Provider / Plugin / Extension
```

The hierarchy is classification and dependency context. It is **not** a new execution,
security, model-routing, resource-placement or evidence authority.

The five canonical product families are:

1. **FA3 Creative / Media** — video, image, audio, speech, digital human, animation.
2. **FA3 Studio / Film** — story, screenplay, shot design, virtual production,
   location/set, render and editing.
3. **FA3 AI Workstation** — model management, agent orchestration, RAG, knowledge,
   local/private AI.
4. **FA3 Business / Collaboration** — communication, office, meetings, workflows
   and project functions.
5. **FA3 Enterprise Platform** — deployment, governance, fleet/LAN, audit, rights,
   security and integration control-plane surfaces.

## Existing applications

The existing application inventory remains the single inventory. The product-family
registry supplies placement metadata for every application already emitted by
`src/fa3_application_donor_index.py`. No application is copied or renamed.

A record has exactly one primary product family and may have secondary families.
Secondary membership expresses valid cross-family consumption; it never grants
permissions or provider/model/runtime admission.

## New applications

A newly added application is visible in the existing inventory immediately, but the
inventory validation fails closed with
`UNCLASSIFIED_APPLICATION_PRODUCT_FAMILY` until
`FA3-PRODUCT-FAMILY-REGISTRY-001` contains an explicit placement.

This makes product-family classification part of application admission without
creating a second application registry.

## Shared platform services

Shared runtime/resource, orchestration, security, model/provider, engine registry,
collaboration, plugin/extension, knowledge/data/asset and governance/evidence/update
services remain platform-level facilities. Multi-application functional cores are
implemented once with application-specific adapters under the existing shared-first
policy.

Product-family membership is context only. Model Router, HRB, Secret/Security,
License & Rights, Evidence/Gate and other existing authorities retain their current
scope.

## Engine Selector

`PRODUCT_FAMILY` is an Engine Selector preference scope between `GLOBAL` and
`APPLICATION`. It records an explicit user preference for a family such as
`FA3-FAMILY-CREATIVE-MEDIA-001`; it is not an execution decision and requires a
non-empty scope target ID.

The intended precedence is:

```text
GLOBAL
  -> PRODUCT_FAMILY
    -> APPLICATION
      -> WORKSPACE
        -> PROJECT
          -> SEQUENCE / SCENE
            -> TRACK / CLIP / NODE
              -> TASK
```

Lower-scope explicit selection may override a higher-scope preference, subject to
all normal eligibility gates.

## Capability and authority invariants

This materialization changes neither the active capability count nor architectural
authority count:

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**

A genuinely new top-level capability remains blocked pending a separate explicit
capability-model reconciliation.

## Current Host

The taxonomy and inventory bindings are static. Adding the product-family option to
the Engine Selector GUI is a structural GUI change, so Current Host alignment must
be reassessed before any runtime/global promotion. CI or this document cannot claim
a physical Current Host PASS.
