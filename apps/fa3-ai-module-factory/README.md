<!-- SPDX-License-Identifier: Apache-2.0 -->
# FA3 AI Module Factory

Qt6/QML workspace for building governed FA3 AI-module drafts from approved work created in FA3 applications.

The application is a consumer/projection of the existing **CAP-095 – Multimodal Generative Model Training & Adaptation Governance** capability. It does not create a new capability or authority and does not execute training providers directly.

## Materialized scope

- source-work selection for the registered FA3 creative applications;
- fail-closed approval/provenance/rights/consent qualification;
- five module strategies: Knowledge, Preference, Skill Adapter, Workflow and Native Model;
- governed module-plan draft generation;
- XDG-namespaced draft persistence;
- explicit Model Router, HRB, License & Rights and Evidence requirements;
- implicit alternate-route substitution is disabled; direct provider execution, direct GPU selection and runtime promotion are also disabled.

Training-capable plans are **drafts only**. Actual training remains behind CAP-095 plus existing approval, Model Router, HRB, License & Rights and evidence gates.

## Build

```bash
cmake -S apps/fa3-ai-module-factory -B build/ai-module-factory
cmake --build build/ai-module-factory
ctest --test-dir build/ai-module-factory --output-on-failure
```

Qt 6.4+ Core, Gui, Quick, QuickControls2 and Test development packages are required. The package manager used to provide these dependencies is distribution-specific; the application itself does not require a particular Linux distribution.

## Current Host

Static application materialization does not claim a physical Current Host PASS. Startup, draft persistence and governed CAP-095 handoff require fresh physical requalification before release promotion.
