# FA3 Product Entitlement & Application Portfolio — approved implementation plan

Date: 2026-10-03
Status: OWNER_APPROVED_IMMUTABLE_PLAN

## Goal

Materialize the approved FA3 product model without changing the 175-capability baseline or creating a new execution authority.

The product model is:

1. one shared FA3 Platform;
2. one Operating Level selected from MINIMAL, PERSONAL, PROFESSIONAL, STUDIO, BUSINESS, ENTERPRISE;
3. individually selectable user-facing applications;
4. required technical/platform dependencies granted with the selected application but not converted into user-facing application entitlements;
5. optional Domain Packs / bundles that never become technical requirements;
6. optional engine/provider/capacity/support entitlements;
7. continuous retrospective and prospective Application Portfolio classification.

## Required behavior

- A user may select one application and use it at any supported higher Operating Level up to Enterprise.
- Higher Operating Levels increase operating scope, collaboration, deployment and governance; they do not automatically unlock unrelated applications.
- The effective Operating Level is the maximum of selected application minimums and requested infrastructure/governance requirements.
- Runtime/platform dependencies are distinct from product application entitlements.
- Bundle membership never forces bundle purchase and never grants hidden applications.
- Security, License & Rights, Hardware Safety, HRB, Model Router and Evidence boundaries remain authoritative and fail closed.
- Product entitlement may restrict access but may never widen a higher-authority denial.
- Silent engine/provider/device/cloud fallback remains forbidden.
- External optional applications retain upstream rights and are not relicensed by an FA3 entitlement.
- Downgrade must not silently delete project data or claim unsupported compatibility.

## Portfolio lifecycle

Every current, in-progress, planned and future application receives a canonical portfolio record.

Portfolio state is independent of the existing provisioning lifecycle:

- FUTURE
- PLANNED
- IN_PROGRESS
- EXISTING
- RETIRED

Provisioning states in FA3-APP-LIFECYCLE-001 remain unchanged.

Application-class taxonomy distinguishes internal/system/companion/external optional applications from shared modules, platform components, engines, providers, services, GUI surfaces and reference-only records.

## Continuous reconciliation

Portfolio reconciliation is incremental on application, state, domain, operating-level, dependency, engine/provider, donor, rights, security, collaboration or deployment changes. Full reconciliation is required when the Operating Level hierarchy, product-family taxonomy, capability baseline, application-class model or entitlement semantics changes.

No application implementation is considered conforming without a portfolio record. Static classification never creates Current Host PASS or release eligibility.

## Product-family compatibility

FA3-PLATFORM-001 and FA3-PRODUCT-FAMILY-REGISTRY-001 are now canonical published-main inputs. Every portfolio application must have exactly one matching primary Product Family placement; product-family values remain context only and never grant permission or execution authority. The Application Portfolio and the shared Application/Donor inventory are reconciled bidirectionally for governed FA3 applications.

## Donor/reuse

Planning uses only the published main donor registry snapshot. Packaging-oriented donor candidates were reviewed but do not provide a necessary product-entitlement governance implementation. No donor is materially adopted by this change.

## Materialization

Create:

- FA3-APPLICATION-PORTFOLIO-001
- FA3-OPERATING-LEVEL-MODEL-001
- FA3-PRODUCT-CATALOG-001
- FA3-DOMAIN-PACK-REGISTRY-001
- FA3-ENTITLEMENT-POLICY-001
- FA3-APPLICATION-DEPENDENCY-REGISTRY-001
- schemas for the governed records
- product-entitlement resolver and fail-closed gate
- CLI wrapper
- tests and CI
- read-only Control Center My FA3 projection
- mandatory FA3-PRODUCT-ENTITLEMENT-GATESET-001 with portfolio, drift, entitlement and operating-level dependency scopes
- complete retrospective Application/Donor inventory and Product Family placement synchronization
- documentation and REUSE annotations

Capability baseline remains 175. Capability delta is 0. Architectural authority delta is 0. Runtime promotion claim is false.
