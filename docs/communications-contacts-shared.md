# FA3 Communications & Contacts Shared

Status: **static materialization in progress; physical Current Host runtime promotion remains pending**.

The system has one provider-neutral backend contract and two presentation modes:

- **FA3 Communications Hub** — full standalone mail, contacts, shared-inbox and collaboration surface within the signed-in user's authorization.
- **CommunicationsSurface** — embedded, context-limited surface. Its effective scope is the intersection of user, role, application, context and data permissions. Embedding never grants global mailbox or global directory access.

## Security

All applicable gates fail closed. Base runtime gates cover identity, authentication, authorization, context/scope, Layer Guard, application boundary, data classification, privacy, Secret Broker, communication security, audit/evidence, Software Coexistence, Hardware Safety and physical Current Host qualification. Attachments, external messages, egress/export and AI add their own mandatory gates.

Email/message content is untrusted external input. It cannot become an AI system instruction or grant tool authority. AI is optional at global, application, module, capability and operation levels. Disabled at any level means no model/provider execution. Model Router, provider admission, HRB, context minimization, prompt-injection checks, PII/secret filtering and output validation remain mandatory when AI is used. Silent provider/model/device/cloud fallback is forbidden.

## Donor/Re-use boundary

The implementation is FA3-native. The groupware products discussed during design were not present in the verified published-main Donor & Reference Registry snapshot and therefore are **not** imported, installed, registered or adopted by this materialization. The Reuse Assessment is bound to registry blob `7e900cac93936d2f319e132def4c172b2a415d4d`, SHA-256 `740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd`, 1233 entries, and records `REVIEWED_NO_MATCH`.

## Current Host

`src/fa3_communications_contacts_current_host_gate.py` accepts only a physical, non-simulated receipt. Missing evidence is `PENDING_CURRENT_HOST`, never PASS. Static/CI success cannot promote runtime operation.

## Embedded consumer contract

Every affected FA3 application may host `CommunicationsSurface`, but must provide a non-empty context ID and a narrowed permission set. Administrative/global operations are unavailable through the embedded surface. The standalone Hub can expose broader functionality only through the same security and authorization backend.
