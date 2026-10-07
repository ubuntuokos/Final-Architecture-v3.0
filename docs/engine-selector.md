# FA3 Unified Engine Registry & Engine/Provider Selector

## Purpose

The Engine Selection Fabric gives users a shared choice of preserved upstream engines, FA3-native engines, canonical provider projections and admitted custom/plugin engines without creating a second execution authority.

The governing rule is: **the project belongs to FA3; engines are selectable implementations of existing capabilities.**

## Permanent coexistence

MLT and future FA3-native media composition remain parallel options. MLT is not deprecated by the existence of an FA3-native engine. The same pattern applies to Digital Human: the FA3-native engine may coexist with admitted external providers.

Selection can be scoped at global, product-family, application, workspace, project, sequence, scene, track, clip, node or task level. `PRODUCT_FAMILY` is a context/preference scope backed by `FA3-PRODUCT-FAMILY-REGISTRY-001`; it grants no execution or permission authority. Every non-global selection carries an explicit `scope_target_id`, so two project/clip/node preferences cannot collapse into the same serialized intent.

## Authority boundaries

- Engine Selector: records user preference, filters, compatibility and policy only.
- Model Router: exclusive AI provider/model/refiner routing authority.
- Host Resource Broker: CPU/GPU/NPU admission, placement, reservation and leases.
- Secret Broker: credentials and secret projection.
- License & Rights / Security: eligibility and fail-closed policy.
- Current Host evidence: runtime promotion.

The selector never directly executes a provider, chooses a physical GPU, stores raw credentials or substitutes another engine without the user's declared fallback policy. Unknown, reference-only, disabled, pending or otherwise non-admitted projected providers are visible only as unavailable; they cannot produce a selectable preference intent.

Decision Fabric applicability is currently `NOT_APPLICABLE`: eligibility filtering and explicit user selection are deterministic. A future advisory auto-ranking mode requires a fresh applicability assessment before Decision Fabric may rank an already-eligible set.

## Registry and provider projection

`canonical/FA3-ENGINE-REGISTRY-001.json` contains stable engine records plus projection rules over existing canonical provider profiles.

Projection is fail-closed:

- a required provider record that is missing aborts materialization;
- explicit engine records win over provider projections by `provider_record`, preventing Kdenlive/FFmpeg duplicates;
- provider capability metadata is normalized across `capability_projection`, `capability_bindings` and `capabilities`;
- Local/LAN/Remote/Cloud/Hybrid execution modes are normalized from explicit topology/mode/classification metadata;
- provider admission state is conservative: unrecognized state is not selectable.

CAP-162 is intentionally **not** claimed as materialized by this selector change because no admitted External Render Service engine/provider binding is materialized here. The capability remains in the global 175 baseline and can be added to the selector when its engine/provider binding is admitted.

## Compatibility

The materialized deterministic compatibility report uses declared capability projection:

- `NATIVE`: all requested capabilities are declared;
- `PARTIAL`: some but not all are declared;
- `UNSUPPORTED`: none are declared.

`LOSSLESS`, `ADAPTED` and `BAKE_REQUIRED` remain schema vocabulary but require explicit evidence-backed transform metadata; the selector will not infer them. Runtime eligibility is reported separately from semantic compatibility.

## Fallback

Fallback modes are `OFF`, `ASK` and `APPROVED_ONLY`.

`OFF` is the default. `APPROVED_ONLY` requires a user-owned engine allowlist. The CLI accepts repeated `--approved-fallback-engine` arguments; the GUI uses the visible comparison selection as the explicit allowlist. Candidates must be execution-eligible and satisfy every required capability.

## Shared GUI

`apps/shared/engine-selector/qml/EngineSelectorPanel.qml` provides:

- text/capability search;
- engine-class filtering;
- Local/LAN/Cloud-Remote filters;
- unavailable/planned visibility;
- scope + explicit target ID;
- required-capability input;
- status/capability/execution details;
- explicit compatibility report;
- fallback policy;
- retained compare selection across filter/model refresh;
- explicit preference setting.

Compact/advanced modes and privacy/cost/license/hardware filters are not claimed as materialized in this change.

The first concrete adapter is `EngineSelectorService` in FA3 Control Center at `models.engines`. It loads the canonical registry plus provider projections and produces non-executing selection intents.

## Reference implementation

Examples:

```bash
python3 src/fa3_engine_selector.py list --class DIGITAL_HUMAN
python3 src/fa3_engine_selector.py list --capability CAP-159
python3 src/fa3_engine_selector.py select --engine FA3-ENGINE-MLT-001 --scope PROJECT --scope-target project:alpha --capability CAP-121
python3 src/fa3_engine_selector.py select --engine FA3-ENGINE-MLT-001 --scope PROJECT --scope-target project:alpha --capability CAP-121 --fallback APPROVED_ONLY --approved-fallback-engine FA3-ENGINE-KDENLIVE-001
python3 src/fa3_engine_selector.py compare --engine FA3-ENGINE-MLT-001 --engine FA3-ENGINE-KDENLIVE-001 --capability CAP-121
```

The Reuse Assessment donor snapshot is revalidated against the checked-out live donor registry and its declared published-main commit/blob/count/SHA-256. Static materialization does **not** claim physical Current Host runtime promotion for any engine.
