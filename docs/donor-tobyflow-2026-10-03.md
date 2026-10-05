# FA3 TobyFlow donor intake — 2026-10-03

**Authority:** owner-explicit `donornak` registration.
**Source:** https://labs.toby.vn/tobyflow
**Scope:** canonical donor/reference registration only; no extension, browser-automation runtime, provider, model, account, credential, remote-control channel or paid-service admission.

## Upstream identity and observed behavior

TobyFlow is presented by TobyLabs as a Chrome/Chromium browser automation layer for existing Google Flow, ChatGPT and Grok accounts. Its documentation exposes visual DAG workflows, batch prompt execution, retry/progress handling, reusable workflow and prompt templates, reference-asset handoff, Telegram-triggered remote workflow execution and MCP-trigger patterns.

The Chrome Web Store listing observed during intake reports version **1.2.56**, updated **2026-09-09**, offered by **Ly Quang Thien**. These observations are provenance context only; the Chrome Web Store listing is not separately admitted as a donor source by this intake.

No open-source code/source license has been verified for the TobyFlow product or extension. Direct code copying, redistribution or embedding therefore remains fail-closed.

## Selective FA3 reuse

TobyFlow is useful as a pattern source for:

- visual node/DAG workflow composition;
- multi-provider workflow chaining;
- batch prompt queues and controlled concurrency;
- explicit handoff of one provider/stage output to the next;
- reusable workflow/task/prompt templates;
- retry, progress and queue-state UX;
- reference-asset/albums style handoff;
- remote workflow dispatch patterns;
- MCP-triggered generation/task initiation.

These patterns may strengthen existing FA3 components, especially Orchestration & Workflow Fabric, Model/Provider Router, Engine/Provider Selector, Task Inbox/Queue, Shared Plugin & Extension Fabric, Inter-App Handoff and creative/media applications.

## Authority and safety boundary

This intake does **not** make TobyFlow a replacement for Temporal or Model Router. Temporal remains the sole global durable workflow authority; Model Router remains the provider/model authority.

The intake also does not authorize:

- installing or bundling the TobyFlow extension;
- browser automation against third-party services;
- accessing browser cookies or credentials;
- signing into external accounts;
- enabling Telegram or other remote command channels;
- requiring a TobyFlow paid plan or cloud service;
- admitting Google Flow, ChatGPT, Grok or any other provider/model through TobyFlow;
- creating a donor usage edge;
- changing Current Host evidence.

Any material adoption requires a fresh Reuse Assessment against the published donor registry, an explicit typed usage edge, and all applicable License & Rights, provenance, security, privacy, Software Coexistence, Hardware Safety, provider/runtime and Current Host gates.

## Canonical delta

Parent published main: `33f230096ea8bd3a37dedb3cbce29b9a3a4b7b24`
Parent registry blob: `4d7641a6caf194db50162cbb3a25ef3930c4ad0b`
Parent donor count: **1425**
Proposed donor count: **1426**
Capability baseline: **175**
Capability delta: **0**
Authority delta: **0**

## Serialization

The rolling donor window allows at most five active canonical intake requests. This PR may exist as a FIFO waiting intake, but it must not finalize unless the live donor-readiness gate admits it into the active window and all earlier finalization priorities are respected.
