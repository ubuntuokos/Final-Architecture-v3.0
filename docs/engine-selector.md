# FA3 Unified Engine Registry & Engine/Provider Selector

## Purpose

The Engine Selection Fabric gives users a broad, shared choice of established upstream engines, FA3-native engines, admitted providers and custom/plugin engines without making the selector an execution authority.

The governing rule is: **the project belongs to FA3; engines are selectable execution implementations of existing capabilities.**

## Permanent coexistence

MLT and future FA3-native media composition are parallel options. MLT is not deprecated by the existence of an FA3-native engine. The same pattern applies to Digital Human: the FA3-native engine may coexist with admitted external providers.

Selection can be scoped at global, application, workspace, project, sequence, scene, track, clip, node or task level. Lower-level explicit user intent may override a broader preference.

## Authority boundaries

- Engine Selector: records user preference, filters, compatibility and policy only.
- Model Router: exclusive AI provider/model/refiner routing authority.
- Host Resource Broker: CPU/GPU/NPU admission, placement, reservation and leases.
- Secret Broker: credentials and secret projection.
- License & Rights / Security: eligibility and fail-closed policy.
- Current Host evidence: runtime promotion.

The selector never directly executes a provider, chooses a physical GPU, stores raw credentials or substitutes another engine without the user's declared fallback policy.

Decision Fabric applicability is currently `NOT_APPLICABLE`: eligibility filtering and explicit user selection are deterministic. A future advisory auto-ranking mode would require a fresh applicability assessment before Decision Fabric could rank an already-eligible set.

## Registry

`canonical/FA3-ENGINE-REGISTRY-001.json` contains stable engine records plus projection rules over existing canonical provider profiles. It intentionally includes planned/not-yet-admitted entries so the GUI can show the full architecture without misrepresenting runtime readiness.

Initial explicit records include MLT, Kdenlive, FFmpeg, FA3 Native Media Composition, FA3 Motion & Video Generation, FA3 Video Refinement and FA3 Native Digital Human. Additional providers are projected from already-canonical profiles and may be added only through normal provider/admission flows.

## Compatibility

Grades are:

`NATIVE`, `LOSSLESS`, `ADAPTED`, `BAKE_REQUIRED`, `PARTIAL`, `UNSUPPORTED`.

No conversion or semantic loss is silent.

## Fallback

Fallback modes are `OFF`, `ASK` and `APPROVED_ONLY`.

`OFF` is the default. `APPROVED_ONLY` requires a user-owned engine allowlist. Even then, this static selector produces candidate intent; it does not bypass Model Router, HRB, Security, License & Rights or Current Host gates.

## Shared GUI

`apps/shared/engine-selector/qml/EngineSelectorPanel.qml` provides a reusable surface with:

- text/capability search;
- engine-class filtering;
- Local/LAN/Cloud filters;
- unavailable/planned visibility;
- scope selection;
- status/capability/execution details;
- fallback policy;
- compare selection;
- explicit preference setting.

Application adapters supply a controller that exposes the canonical catalog and converts GUI actions into `fa3.engine-selection-intent.v1` objects.

## Reference implementation

`src/fa3_engine_selector.py` can list the static catalog and produce non-executing selection intents.

Examples:

```bash
python3 src/fa3_engine_selector.py list --class DIGITAL_HUMAN
python3 src/fa3_engine_selector.py list --capability CAP-159
python3 src/fa3_engine_selector.py select --engine FA3-ENGINE-MLT-001 --scope PROJECT --capability CAP-121
```

Static materialization does **not** claim physical Current Host runtime promotion for any engine.
