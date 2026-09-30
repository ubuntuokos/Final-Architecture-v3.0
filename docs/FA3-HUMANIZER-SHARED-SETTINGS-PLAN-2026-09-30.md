# FA3 Humanizer – Shared Settings plan supplement

Status: **OWNER APPROVED / implementation authorized**
Date: 2026-09-30
Capability baseline: **175 fixed**
Primary capability: **CAP-125 — AI Prose Quality, Register-Aware Editing & Anti-Slop**
New architectural authority: **none**
Current-host runtime promotion claim: **none**

## 1. Decision

The Humanizer is materialized as a shared FA3 Humanization & Writing Quality Fabric. The standalone Humanizer application is only one consumer surface.

All Humanizer settings must come from one shared implementation:

- one shared C++ settings service;
- one shared QML settings panel;
- one shared settings namespace and inheritance model;
- application-local code may only provide context, placement and workflow adapters;
- duplicated Humanizer settings logic is forbidden.

## 2. Shared settings scope

Resolution order, most specific first:

1. FUNCTION
2. CAPABILITY
3. MODULE_PLUGIN
4. APPLICATION
5. PROJECT
6. USER
7. canonical defaults

GLOBAL, HOST and USER_ROLE policy layers are authority-controlled and cannot be weakened by the Humanizer UI. The GUI may only create a draft ChangeSet for those layers.

## 3. Shared setting set

The shared panel exposes at minimum:

- Humanizer enabled;
- AI enabled/disabled;
- language;
- register/profile;
- edit budget;
- author voice profile;
- preserve numbers;
- preserve URLs;
- preserve quotations;
- preserve citations;
- preserve terminology/claims;
- semantic validation;
- extension/pack visibility and state;
- effective scope and inherited locks.

AI disabled means no model/provider invocation and no silent fallback.

## 4. Application surfaces

Mandatory consumers are assessed retroactively. The same shared panel is intended for:

- standalone FA3 Humanizer;
- FA3 Control Center settings;
- Story / Screenplay;
- Document Editor;
- Mail / Contacts;
- Marketing;
- Presentation;
- Subtitle Editor;
- Narration;
- Credits / Titles;
- Prompt Editor;
- Knowledge / Documentation surfaces.

A consumer may hide irrelevant options, but it may not fork the settings model.

## 5. Functional core

The first materialization includes an AI-OFF deterministic path:

- text metrics;
- mechanical-pattern findings;
- whitespace-safe normalization;
- number, URL and quotation preservation checks;
- candidate comparison;
- guarded AI rewrite request envelope creation.

The AI request envelope never calls a provider directly. Any AI path requires the existing FA3 Model Router / UAF / HRB admission path.

## 6. Extension model

The Humanizer remains extensible through typed categories:

- AnalyzerPlugin;
- TransformerPlugin;
- ValidatorPlugin;
- LanguagePlugin;
- StylePack;
- RegisterPack;
- GenrePack;
- AuthorVoicePlugin;
- MetricPlugin;
- GrammarPlugin;
- TerminologyPlugin;
- DetectorPlugin;
- DocumentAdapter.

Registry presence or discovery never means installation, activation or runtime admission.

## 7. Protected content

The Humanizer must preserve protected facts and spans. Initial deterministic checks cover:

- numbers;
- URLs;
- quoted text;
- explicit citation-like markers.

Later semantic/claim validators can extend this contract, but may not become independent evidence authority.

## 8. Donor/reuse boundary

Implementation is based on the published main donor registry snapshot only. The active donor-maintenance PR #562 is excluded until merged and requalified.

Published registry snapshot used by this plan:

- registry: FA3-DONOR-REFERENCE-REGISTRY-001
- registry blob SHA: 7e900cac93936d2f319e132def4c172b2a415d4d
- registry SHA-256: 740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd
- donor count: 1233
- main SHA at implementation start: 0240bae4100d0410a11c3026657ba28af508c893

Humanizer-related registry entries are reference/candidate material only. This materialization copies no donor runtime or source code.

## 9. Current Host

This application introduces an executable GUI and shared runtime library, so CAP-125 requires physical Current Host requalification before runtime closure.

Required proof includes:

- AI-OFF deterministic operation;
- shared-settings inheritance;
- protected number/URL/quotation preservation;
- no provider call when AI is disabled;
- Model Router/UAF fail-closed path for AI request;
- rollback;
- Software Coexistence;
- CPU-only operation.

No simulated or repository-only test may claim physical Current Host PASS.

The central Current Host registry is concurrently modified by PR #559. This branch therefore materializes the Humanizer-specific impact/requalification contract and must reconcile the central recipe on the final merged Current Host head rather than overwrite #559.

## 10. Control Center integration

PR #564 concurrently changes Control Center Main.qml, CMakeLists.txt and main.cpp. This branch therefore creates the mandatory shared UI binding contract and the reusable shared panel without parallel replacement of those files.

After the GUI head is reconciled, Control Center must embed the exact shared Humanizer panel. A local duplicate is not acceptable.

## 11. Acceptance

Implementation is acceptable only if:

- 175 capability baseline remains unchanged;
- CAP-125 remains the canonical capability;
- shared settings have one functional implementation;
- standalone and embedded consumers use the same service/panel;
- AI can be disabled independently;
- AI OFF prevents provider/model execution;
- deterministic mode remains available;
- no direct provider endpoint is embedded;
- no silent fallback exists;
- protected content checks are fail-closed;
- Current Host remains PENDING until physical proof;
- user/human acceptance remains final authority for edits.
