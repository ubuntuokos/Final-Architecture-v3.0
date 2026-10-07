# FA3 Application Portfolio, Operating Level and Entitlement Plan — 2026-10-03

Status: OWNER APPROVED FOR MATERIALIZATION

FA3 uses one 175-capability platform. Operating levels are MINIMAL, PERSONAL, PROFESSIONAL, STUDIO, BUSINESS and ENTERPRISE; they describe operating scale and governance, not application count.

User-facing applications are independently entitleable by default through Enterprise. Domain packs are optional bundles only. Required platform/shared dependencies are activated with an entitled application but never grant another user-facing application.

Canonical example: Story/Screenplay + Render Manager resolves to PROFESSIONAL because Render Manager requires it. Required 3D/render platform dependencies are included without granting the 3D/DCC Studio application.

Every existing, in-progress, planned and future FA3 application is registered in one portfolio. Portfolio state is separate from FA3-APP-LIFECYCLE-001 provisioning state and is incrementally reconciled on relevant application, package, domain, dependency, donor, rights, security, engine/provider and deployment changes.

Invariants: capability baseline 175; capability delta 0; no new architectural authority; Security, License & Rights, HRB, Model Router, Secrets and Evidence remain authoritative; deny wins; no silent fallback; CPU-only remains globally valid; bundles are never technical dependencies; runtime dependency is not application entitlement; no silent project-data loss; no Current Host PASS or release-eligibility claim.

Owner approval basis: final plan approved in the 2026-10-03 FA3 conversation, followed by explicit instruction: "Készítsd el!".

## 2026-10-07 final video application architecture

The application portfolio now records the owner-approved final video/editorial application split:

- **CFA3 Video Editor** is the sole full NLE and owns `project.fa3video`.
- **CFA3 OpenCut Fast Editor** is a standalone and embeddable FAST EDIT / QuickClip-style application. It is not a second full NLE.
- **CFA3 OpenVid Shared Composer** is a shared FAST COMPOSE application. OpenCut hosts it through an OpenVid Composer plugin/embedded workspace; editable `.fa3openvid` references are preferred over flattening.
- **CFA3 Motion Designer / Animation Studio** is the shared ADVANCED MOTION application consumed from OpenCut, OpenVid, Video Editor and future Webdesign surfaces.
- **FA3 QuickClip** remains a separate short-form automation application; this change does not silently retire or rename it.
- Existing shared MLT/FFmpeg/OTIO, HRB, Model Router, Temporal, UAF/MCP, License & Rights and Evidence authorities remain unchanged.

No donor-registry mutation, SDK registration, provider admission or Current Host promotion is created by this portfolio reconciliation.
