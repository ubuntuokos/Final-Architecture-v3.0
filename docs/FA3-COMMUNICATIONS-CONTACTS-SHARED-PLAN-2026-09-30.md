# FA3 Communications & Contacts Shared - approved immutable plan

Date: 2026-09-30
Owner approval: explicit in conversation before materialization.
Capability baseline: 175. Capability delta: 0. Architectural authority delta: 0.

## Purpose

Materialize one shared FA3 communications and contact system with two projections over one canonical backend:

1. FA3 Communications Hub - standalone, full-featured mail, contacts, shared inbox and team-collaboration surface within the authenticated user's effective permissions.
2. Communications Shared Surface - embedded in FA3 applications and restricted to the intersection of user, role, application, project, workflow, data-classification and communication permissions.

The embedded surface MUST NOT expose the global mailbox or global contact set merely because the user can access those resources elsewhere.

## Canonical fabrics

The system materializes provider-neutral Mail, Thread, Shared Inbox, Contact, Organization, Collaboration, Communication History and Communication Relation fabrics. External mail/groupware implementations are not architectural authorities and are not adopted by this change.

The system reuses the existing Shared Capability Fabric, UAF, Security Governance, Secret Broker, Model Router, HRB, Evidence authority, Layer/Scope guards, Hardware Safety Envelope and Software Coexistence rules. No parallel authority is introduced.

## Standalone behaviour

The Communications Hub provides mailbox/thread navigation, compose/reply/forward, shared mailbox workflow, assignment, internal notes, contact and organization management, communication history, context linking and policy-controlled AI assistance. Provider-backed network execution remains unavailable until separately admitted and proven on the current host.

## Embedded behaviour

Embedded use is context-limited. Effective access is the INTERSECTION of authenticated user permissions, role permissions, application permissions, project/workspace permissions, workflow permissions, data classification and communication permissions.

Administration, global mailbox enumeration, global address-book enumeration, account/provider configuration, global export and permission administration are denied from embedded surfaces unless a separately authorized full-hub transition is performed. Opening the full hub never expands permissions.

## Security

Every operation runs through all applicable FA3 gates and fails closed. The communications security chain includes identity, authentication, authorization, context/scope, Layer Guard, application boundary, data classification/privacy, Secret Broker, communication security, attachment/content security, anti-abuse/phishing, AI permission, AI context isolation, prompt-injection/tool-use control, Model Router/provider admission, HRB, plugin/extension security, Software Coexistence, Hardware Safety, audit/evidence and Current Host gates.

UNKNOWN, ERROR, TIMEOUT, missing evidence or policy conflict => DENY.

Email and external message bodies are UNTRUSTED INPUT. They cannot become system instructions. Attachments are type/MIME/policy/malware/archive/active-content/safe-preview/DLP gated. Outbound communication is DLP and recipient-policy gated.

Credentials never enter prompts, project files, plaintext config, logs or uncontrolled donor stores; Secret Broker remains the credential authority.

## AI

AI is optional and separately controllable at global, application, module, capability and operation level. AI-off means no model/provider/background AI use and no silent fallback. The non-AI path remains functional.

AI capabilities include summarization, draft reply, translation, classification, task/contact extraction, priority assistance, phishing assistance, thread summary, contact deduplication/enrichment and semantic search. AI receives only purpose-bound minimized context. External provider use requires Model Router selection, provider admission, data-egress permission and normal security gates.

Agents cannot directly send, delete, bulk-export, alter permissions, administer mailboxes or access credentials without the corresponding explicit action authorization.

## Protocol and current-host boundary

Target protocol bridges: SMTP, IMAP, JMAP, CardDAV, CalDAV and OAuth/OIDC where applicable. This change does not claim physical provider admission. TLS/certificate checks, protocol reachability, Secret Broker integration, attachment/malware scanning, notification integration, offline cache and provider-specific E2E proof remain PENDING_CURRENT_HOST until physically verified.

## Shared and retroactive integration

The capability applies to planned, in-progress and materialized FA3 applications when functionally relevant. Existing local contact, recipient, participant, email-send or communication-history implementations must be assessed for adapter/migration to the shared fabric without losing verified capabilities.

## Donor boundary

The live committed donor registry snapshot is reviewed for this materialization. No external donor is adopted or copied by this change. External groupware candidates discussed during planning require explicit owner-marked donor registration and a separate approved adoption decision before source/pattern adoption.

## Final invariants

- fixed capability baseline 175;
- capability delta 0;
- authority delta 0;
- provider-neutral;
- CPU-only viable;
- 0..N accelerators;
- no hardware mutation;
- no silent fallback;
- no permission union;
- no hidden background send;
- no direct UI/provider bypass;
- fail closed;
- document-only runtime promotion forbidden;
- physical Current Host proof required before production promotion.
