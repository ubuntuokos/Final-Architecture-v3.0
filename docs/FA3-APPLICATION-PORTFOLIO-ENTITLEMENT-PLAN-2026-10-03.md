# FA3 Application Portfolio, Operating Level and Entitlement Plan — 2026-10-03

Status: OWNER APPROVED FOR MATERIALIZATION

FA3 uses one 175-capability platform. Operating levels are MINIMAL, PERSONAL, PROFESSIONAL, STUDIO, BUSINESS and ENTERPRISE; they describe operating scale and governance, not application count.

User-facing applications are independently entitleable by default through Enterprise. Domain packs are optional bundles only. Required platform/shared dependencies are activated with an entitled application but never grant another user-facing application.

Canonical example: Story/Screenplay + Render Manager resolves to PROFESSIONAL because Render Manager requires it. Required 3D/render platform dependencies are included without granting the 3D/DCC Studio application.

Every existing, in-progress, planned and future FA3 application is registered in one portfolio. Portfolio state is separate from FA3-APP-LIFECYCLE-001 provisioning state and is incrementally reconciled on relevant application, package, domain, dependency, donor, rights, security, engine/provider and deployment changes.

Invariants: capability baseline 175; capability delta 0; no new architectural authority; Security, License & Rights, HRB, Model Router, Secrets and Evidence remain authoritative; deny wins; no silent fallback; CPU-only remains globally valid; bundles are never technical dependencies; runtime dependency is not application entitlement; no silent project-data loss; no Current Host PASS or release-eligibility claim.

Owner approval basis: final plan approved in the 2026-10-03 FA3 conversation, followed by explicit instruction: "Készítsd el!".
