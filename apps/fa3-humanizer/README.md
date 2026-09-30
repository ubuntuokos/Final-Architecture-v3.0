# FA3 Humanizer

Qt6/QML standalone consumer of the shared FA3 Humanization & Writing Quality Fabric.

## Current materialization

Implemented:

- shared Humanizer settings service;
- shared QML settings panel;
- shared user/application/module/capability/function scope resolution;
- AI toggle with default AI-OFF behavior;
- deterministic text metrics and formulaic-pattern findings;
- safe whitespace normalization;
- protected number/URL/quotation/citation comparison;
- guarded AI request envelope that requires UAF + Model Router + HRB and never calls a provider directly.

Not claimed:

- physical Current Host PASS;
- direct model execution;
- semantic-equivalence authority;
- AI-authorship detection proof;
- donor runtime admission.

## Build

Requires Qt 6.4+ Core, Quick and QuickControls2.

    cmake -S apps/fa3-humanizer -B build/fa3-humanizer -GNinja
    cmake --build build/fa3-humanizer

The shared settings implementation lives under apps/shared/humanizer and is intended to be embedded by all relevant FA3 applications.
