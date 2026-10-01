# FA3 Shared Capability Fabric

**Status:** canonical design and executable policy materialized; physical Current Host qualification pending.

The Shared Capability Fabric (SCF) exposes common FA3 functions through one context-filtered service layer. It does **not** create architectural authority and does not change the fixed 175-capability baseline.

## Core rule

An application receives only shared capability slices relevant to its application, module, project, selected object, workflow, role and authority context. A slice can be `ACTIVE`, `VISIBLE_DISABLED`, `HIDDEN`, `DENIED` or `UNAVAILABLE`. `HIDDEN` and `DENIED` slices must not execute in the background.

The canonical registry is `canonical/FA3-SHARED-CAPABILITY-FABRIC-001.json`; it contains **45** slices.

## Shared families

- **Content & Project:** import, export, print, share, archive, file/project management.
- **Media, Capture & Production:** video/image resize, audio/camera settings, A/V recording, lighting, color management, texture management and rendering.
- **Assistance:** Assistant, Coach, Mentor, Manager and Dramaturg surfaces.
- **Work, Collaboration & Business:** app-to-app chat, task inbox/delegation, time tracking, deadline log, meetings, expense submission/request/settlement, RFQ, purchase order and email management.
- **Plugin & Extension:** common manager with application/context applicability filtering.
- **Runtime & Distribution:** Model Manager, Download Manager and Update System.
- **Knowledge & Documentation:** help, manual reader and table-of-contents builder.
- **Language:** dictionaries, spelling and synonym services.
- **Search & Research:** web search and source/reference management.
- **Knowledge Navigation:** Mind Map access.

## Email from every FA3 application

### UI Component Fabric projection

The universal send entry is projected through `FA3-UI-COMPONENT-FABRIC-001`. Every FA3 application receives the same shared action surface and emits the typed `email.send` UAF intent. The UI component cannot send directly, access secrets, or bypass authorization/provider admission.


Every FA3 application exposes the same shared **Email küldése** / `email.send` surface. The application may project its current context into the composer, including a document, render, export, report, project reference or task reference where the underlying capability allows it.

This does **not** turn every application into a full mail client. Full mailbox/thread/read/reply surfaces remain context filtered. Sending is a mutation: it requires an explicit user or authorized workflow intent, admitted provider/connector path and normal policy checks. Silent background send is forbidden.

## Hobby projects and external services

Hobby is **not** an external-service denial profile. A Hobby project may explicitly use an admitted external service such as a render farm. Business/admin surfaces may stay hidden by default, but RFQ, purchase-order and cost slices may become relevant for that selected external-service workflow. Purchase or cost commitment is never silent: explicit authorization and normal policy/authority gates are required.

## Plugin and extension projection

The global manager may inspect the admitted catalog. An application-embedded manager view must show only packages applicable to that application/capability/context or installable/temporarily unavailable for that same context. `NOT_APPLICABLE` and incompatible packages stay out of the normal application view. Shared package installation does not imply enablement in every consumer application.

## Existing capability mapping

Every SCF slice references only existing CAP-001..CAP-175 identifiers. Source management maps to CAP-154/CAP-155; rendering to CAP-161/CAP-162/CAP-163; textures to existing Media/Asset/Scene/Round-trip capabilities; email to existing Integration/Gateway/Messaging capabilities. New capability claims fail closed rather than being hidden behind a shared-module label.

## Current Host

This is a structural FA3 change, so Current Host alignment is mandatory. Static materialization is not physical runtime proof. Production promotion remains blocked until fresh real-host evidence covers context filtering, hidden/denied no-background execution, plugin applicability, universal email send surface, Hobby external-service flow, explicit purchase authorization, coexistence, hardware safety and AI-off behavior.
