# FA3 Environmental & Natural Phenomena Fabric — discovery and design scope (2026-09-28)

**Status:** proposed, documentation and donor-candidate capture only. This document neither creates a canonical capability nor admits a runtime/provider or certifies an engineering model.

## Purpose and existing boundaries

Provide one cross-application scenario and effects contract for weather, ordinary natural phenomena, environmental change and disasters across **wilderness, settlements, building exteriors and surroundings, and building interiors**. Extend the existing World & Environment Studio, VFX Studio, Weather & Geo real-time-data category, Story/Screenplay context and creative workflows. Do not start an independent rendering engine, model router, timeline, resource scheduler or competing scene authority.

Prior to implementation, run FA3 Reuse Discovery against the central `FA3-DONOR-REFERENCE-REGISTRY-001` (including Pixar OpenUSD, pre-existing Khronos reuse and the new 2026-09-28 environmental candidates). Do not interpret donor capture as adoption.

## Phenomena taxonomy

| Family | Examples | Environmental effects |
| --- | --- | --- |
| Atmosphere/weather | cloud, rain, snow, hail, lightning, wind, severe convection, tornado, fog | precipitation, wetness, visibility, vegetation sway, surface deposition, sound, lighting |
| Hydrological/coastal | river flow, flood, flash flood, storm surge, waves, tsunami | channel routing, streets and basements inundated, shoreline and debris change |
| Geological | earthquakes, volcanoes, ash, rockfalls, landslides, subsidence | ground motion/displacement, dust, building and infrastructure damage |
| Fire/heat | wildfire, urban fire, building fire, smoke, ash, heat waves | flame/smoke, material scorching, heat, evacuation-story conditions |
| Cryosphere | blizzard, ice storm, avalanche, ice and snow melt | accumulated snow/ice, slippery surfaces, vegetation loads |
| Atmospheric dust and landscape change | dust and sand storms, erosion, drought | reduced visibility, deposition, soil and vegetation changes |
| Optical/astronomical | sunrise/sunset, rainbow, aurora, eclipses | sky illumination, reflections, ambient light, mood |
| Cascading/secondary | falling trees, blocked culverts, roof leaks, burst water mains, power outage | persistent object state, indoor damage, lighting and sound transitions |

Distinguish a **phenomenon** (e.g. rainfall), an **event** (time/region/intensity), an **interaction** (rain hits a roof), a **consequence** (gutter overflow), a **state change** (basement flooded), and a **visual/audio presentation**. Reuse the same event across every scale. Events can be scripted or guided by external data, without implying a certified hazard prediction.

## Four nested spatial scopes

1. **Natural landscape:** terrain, forest, desert, ocean, river, mountain, cave, snow and ice. Include ecological and terrain state as needed.
2. **Settlement:** roads, transport, buildings, bridges, green space, public utilities, drainage networks and crowds. Geospatial imports are optional.
3. **Building vicinity and exterior:** façades, roofs, gutters, patios, yards, vegetation, nearby trees, fences, nearby utilities and ground drainage.
4. **Building interior:** windows, rooms, corridors, ventilation, basements, industrial spaces, utility systems, interior water/smoke/dust ingress and material response.

Require *bidirectional spatial context*: the same exterior event causes plausible, authored or physically guided interior consequences. Outdoor volume simulations need not be recomputed inside every room; exchange bounded physical boundary conditions and event-state deltas instead.

## Proposed layered architecture

1. **Scenario/World binding:** coordinates and CRS if geospatial, scene/shot, time range, asset IDs, geometry references, surface/material labels, building envelope, indoor/outdoor portals. Keep FA3-native scene/project/timeline authority; OpenUSD and CityJSON are interoperability references only.
2. **Phenomenon & dependency graph:** event ID, type, region, temporal envelope, intensity with physical units where relevant, seed, authored controls, source type (synthetic/observed/forecast), uncertainty and cascades. Guard against cyclic cascade explosions and unbounded expansion.
3. **Simulation adapter fabric:** a lightweight deterministic CPU preview baseline, then selectively admitted external adapters for sparse volumes, CFD, runoff/flood, fire/smoke and structural response. Adapters are sandboxed versioned jobs, not baseline dependencies; choose per scene and resource admission.
4. **Persistent impact state:** wetness, standing water, snow depth, scorch, soot, broken assets, ground displacement and infrastructure status. Non-destructive, reversible scene deltas with provenance and user approval for destructive edits. Report differences between aesthetic simplification and simulation output.
5. **Presentation:** scene geometry, particles, sparse volumes, materials, lighting, camera-relative LOD, sound, compositing and timelines. Deliver to Bforartists first-class DCC integration, VFX Studio, FA3 Video Editor and QuickClip imports through each application's existing native project model.
6. **Optional observed-data ingestion:** time-stamped Weather & Geo provider adapters, source licensing and attribution, coverage, resolution, confidence and offline snapshot. Observed/forecast data never silently becomes a simulated local outcome or an official alert.
7. **AI:** only already designated models through the canonical Model Router -> HRB -> admitted runtime/provider -> model. AI suggests scene parameters/prompts or maps screenplay beats to events; human approval policy is explicit (automatic, approval-only, mixed). No new self-appointed model.

### Proposed interoperable contracts, not yet canonical

- `EnvironmentScenario`: scenario ID, coordinate reference/timezone, scene/shot refs, spatial extents, operating mode, provenance manifest.
- `PhenomenonEvent`: event ID and taxonomy, origin (synthetic/observation/forecast), start/end, bounded region, intensity and units, random seed, spatial/temporal accuracy and uncertainty.
- `AffectedAsset`: stable asset and material IDs; exterior/interior region; topology, inlet/outlet and exposure metadata. Do not require BIM-level detail for a simple film scene.
- `ImpactDelta`: affected asset, precondition, change, validity interval, dependency IDs, severity/uncertainty, author/solver provenance, reversible application.
- `SimulationJob`: adapter, input schema/version, model/data license, resource requirements, execution admission, source snapshot hashes, timeout, deterministic seed, resulting cache references.
- `RenderPresentation`: volumetric/mesh/particle layers, LOD budget, artistic overrides and exports into existing studio workflows.

Modes: **ART_DIRECTED** (explicitly fictional/visual), **PHYSICS_INFORMED** (bounded simulation for creative coherence), **DATA_GUIDED** (observations/forecasts interpreted with source limits). Scientific/engineering output is **not** certified merely by selecting an upstream solver; any validated engineering use requires its own documented validation, domain expertise, provenance and independent review.

## Cross-scale reference story / end-to-end acceptance scene

*A storm travels from mountain watershed through a settlement to a residential building:*

- Upstream thunderstorm: cloud/rain/wind/lightning and landscape response; rainfall advances runoff in the watershed.
- Settlement: drainage receives runoff; water pools in a street; vegetation moves and one authored tree falls; a power-outage event changes road and house lighting.
- Building vicinity: rain strikes roof/façade; gutter overflow reaches the foundation, causes a persistent muddy puddle and enters a basement window.
- Interior: water trickles into basement; damp wall and floor material changes persist; rain and thunder remain spatially coherent in sound and through windows.
- Editorial: shot-specific level-of-detail and camera cuts preserve event timeline and material changes; exports remain editable in FA3-native scene, video, audio and VFX workflows.

A second targeted acceptance case should cover an earthquake and aftereffects; a third should cover fire/smoke across an indoor/outdoor boundary. Neither scenario is an emergency response forecast.

## LOD and execution boundaries

Maintain two **independent** concepts: rendering/particle LOD and physical-model fidelity. The first may be camera driven; the second is governed by purpose, event extent, source quality and tolerances, not by camera distance alone. Suggested visualization levels: regional sky/landscape, district/street, building/vicinity, interior/material contact. Share physical event identity and persistent impact deltas across all levels.

Cache event-state deltas and generated simulation outputs by scenario inputs, solver version, geometry/data snapshot, seed and profile. Invalidate selectively when precipitation, roof topology, runoff route, time window or material exposure changes. Bound all jobs; no unbounded scene-wide CFD/flood/fire computation on the default UI path.

## Reuse Discovery / donor candidate roster

The **canonical registry** is the source of truth. The table documents intended selective roles, **not** source copying or runtime admission.

| Source | Specific possible contribution | Adoption boundary |
| --- | --- | --- |
| [Academy OpenVDB/NanoVDB](https://github.com/AcademySoftwareFoundation/openvdb) | sparse smoke/fire/fog/volume storage and interchange | Apache-2.0 declaration; GPU use optional, CPU path required |
| [Blender](https://github.com/blender/blender) | fluid/smoke/particles/scene-processing reference for Bforartists DCC interoperability | GPL-3.0: reference or externally admitted compatible workflow; do not casually embed |
| [OpenFOAM](https://github.com/OpenFOAM/OpenFOAM-dev) | outdoor wind and physically guided fluid computations | GPL-3.0; optional external scientific adapter |
| [NIST FDS](https://github.com/firemodels/fds) | fire/smoke/heat simulation, especially interiors | public-domain NIST code; check bundled parts and solver validation |
| [US EPA SWMM](https://github.com/USEPA/Stormwater-Management-Model) | urban runoff and drainage, rain-to-flood cascades | public-domain EPA solver; not a complete 3D visual flood renderer |
| [ANUGA](https://github.com/anuga-community/anuga_core) | shallow-water flooding, tsunami and inundation profiles | Apache-2.0; optional, preserve model limitations |
| [LISFLOOD-FP BMI](https://github.com/openearth/lisflood-fp-bmi) | floodplain and basic-model-interface design patterns | this older branch GPL-3.0 and not latest upstream |
| [OpenSees](https://github.com/OpenSees/OpenSees) | structural/geotechnical response research for earthquake, wind and other loads | verify exact licensing and model validity before use |
| [CityJSON](https://github.com/cityjson/specs) | 3D city, structures, roads and spatial LOD interchange | CC0 specification; tools/data are separately licensed |
| [EnergyPlus](https://github.com/NatLabRockies/EnergyPlus) | building thermal state and indoor-environment research | upstream custom permissive license has attribution and trademark/name conditions; independent dependency review pending |
| [NOAA NOMADS/GFS](https://nomads.ncep.noaa.gov/) | gridded meteorological boundary conditions | optional data provider; evaluate coverage, latency and terms |
| [USGS Earthquake API](https://earthquake.usgs.gov/fdsnws/event/1/) | historical/recorded seismic event metadata | observation, not local building-damage prediction |
| [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/) | satellite hotspot data for wildfire scene research | not for life/property protection; detection != exact fire perimeter |
| [Open-Meteo](https://open-meteo.com/en/docs/) | forecast/historical weather adapter shape | distinguish noncommercial/commercial/self-hosted access terms |
| Existing [Pixar OpenUSD donor](https://github.com/PixarAnimationStudios/OpenUSD) | layered environment/asset scene interchange, no second scene authority | extend existing registry record, not a duplicate donor |

## Hardware Audit (mandatory before implementation or promotion)

- CPU-only viable preview and offline authored mode are mandatory. No GPU, NVIDIA, CUDA, ROCm, oneAPI, Vulkan or fixed accelerator is a global prerequisite; optional backends require vendor-neutral feature detection and admission.
- Accelerator count is `0..N`; discover Intel/AMD/NVIDIA/other accelerators and physical versus logical CPU cores with current host evidence. HRB is the **only** compute-resource authority; keep time/memory/CPU/GPU budgets workload scoped.
- GUI must be toolkit/desktop neutral: Wayland preferred, X11 supported; avoid KDE-only assumptions even when the primary FA3 GUI is Qt6/QML.
- Simulators, codecs, model providers, dataset connectors and source copying require **independent** licensing, supply-chain/security, environment coexistence and current-host checks. No silent fallback from absent scientific solver to an unlabelled invented result.
- Keep current studio formats (`.kra`, `.kdenlive`, Ardour sessions, `project.fa3video`, `.fa3clip`) intact. No excluded proprietary game-engine installation, runtime, workflow or hidden application duplication.

## Delivery slices and completion gates

**D0 — Discovery (this PR):** capture distinct donor candidates, link pre-existing OpenUSD and publish scope/contract proposal. No implementation/promotion claim.

**D1 — Core creative vertical slice:** implement the event/impact contracts, a CPU-only deterministic rain-and-wind preview, authored 4-scale storm case and persistent wetness/inundation deltas. Require unit tests on event causality, spatial scope, reproducible seed, cache invalidation and human approval.

**D2 — Existing studio handoff:** Bforartists scene interchange; VFX layered volumes/particles; FA3 Video Editor shot/timeline handoff; sound and light causal consistency; QuickClip import preserving provenance; round-trip native project tests.

**D3 — Optional scientific and data adapters:** select by Reuse Discovery and independent license/security/provider admission. Start with SWMM urban drainage and selected recorded weather; add FDS, ANUGA, OpenFOAM and structural models only when a use case and validation criteria exist.

**D4 — QA/acceptance:** offline CPU-only and admitted optional acceleration on current host, no fixed GPU/runtime/model, Wayland+X11, bounded jobs, failure injection, licensing inventory, donor deduplication, exact-source attribution, synthetic vs real-data labeling, visual shot continuity, no automatic life-safety claim.

**Out of scope without separate decisions:** public warning or operational disaster-response service, certified risk estimates, fully coupled city-scale multi-physics solver, a new monolithic DCC/editor, source-copy approvals or automatic downloading of donor software.
