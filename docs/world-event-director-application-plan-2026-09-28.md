# FA3 World & Event Director — application implementation plan (2026-09-28)

**Status:** proposed application plan, architecture and acceptance criteria only. This document does **not** assert a functioning GUI, create a canonical capability, select any unadmitted donor, change the current studio timeline authority or claim current-host evidence. This plan complements [Environmental & Natural Phenomena Fabric discovery](environmental-natural-phenomena-discovery-2026-09-28.md) on the same pull request.

## Product and scope

**Working title:** FA3 World & Event Director (WED).
**Form:** independently launchable Qt 6/QML application, also accessible from FA3 Control Center > Create > World & Environment. WED is a **user-facing authoring surface**, not a competing world/simulation/model/resource/data authority.

**Core task:** an author provides a screenplay or a scene proposal; WED resolves optional location, date, time, period and environment evidence, then authors consistent 3D-ready environments, events and consequences for film and animation. A story may contain a cloned dinosaur in 1976 Budapest, an alien occupation, a fabricated meteorological event or a wholly invented planet. The underlying geographic and astronomical anchor remains correct for the real place and instant by default **regardless of story genre**. Only an explicit planetary/world-rule decision can replace the baseline physics or astronomy.

**Audiences:** screenwriter, scene/shot designer, production designer, VFX artist, animation director and video editor. **First production scope:** previsualization and authored effects, not operational hazard forecasts or certified structural/fire/flood analysis.

### Product invariants

1. **Narrative autonomy:** story determines actors, events, vehicles, occupations, crowds, destruction, anomalies and intended visual style. Neither a historical date nor a realism preset vetoes a fictional screenplay; a locked historical layer can be overridden deliberately with reversible provenance.
2. **Earth anchor is independent:** real coordinates, cardinal directions, hemisphere, season, dated timezone rules and astronomical solar trajectory stay anchored to Earth by default. A UFO shadow changes *effective* illumination but not the Sun's underlying ephemeris; color grading changes the image but not its geospatial facts.
3. **Explicit world rules:** two actual suns, another planet, modified orbital mechanics, reversed planet rotation or modified gravity require `WorldRuleOverride` and explicit human confirmation. A drawn second sun or artificial projector may instead be a scene-only visual-lighting effect. Do not conflate visual appearance with new physical law.
4. **Two orthogonal choices:** `world_mode` = HISTORICAL / ALTERNATE_HISTORY / FICTIONAL / HYBRID; `simulation_mode` = ART_DIRECTED / PHYSICS_INFORMED / DATA_GUIDED. A narrative event's invention is independent of the fidelity of the city, daypart, climate and physical approximation.
5. **Visible epistemics:** separate `OBSERVED`, `HISTORICAL_RECORD`, `REANALYSIS`, `DERIVED`, `AUTHOR_INVENTED` and `UNKNOWN`. Per-layer source, interval, coverage, acquisition date, rights, uncertainty and authored deviations remain inspectable. Photorealistic rendering is not evidence.
6. **Native and non-destructive:** keep immutable baseline snapshots, layered creative branches, reproducible seeds, command-bus undo/redo, external asset references and shot-time impact deltas. Preserve existing FA3 project ownership, including `project.fa3video`, `.fa3clip`, `.kra`, `.kdenlive` and audio-native sessions.

## Screen and interaction architecture

**One window, four areas plus a status strip** (an embedded FA3 Control Center view may reflow as panels):

| Area | Intended interaction |
| --- | --- |
| Top context bar | Project title, Earth/custom world switch, resolved place with geographic-precision badge, calendar/date, optional historical local clock and timezone version, season/daypart, world mode, simulation mode, branch name. Controls with unavailable data must display `UNKNOWN`, never invent precision. |
| Left story/branches navigator | Screenplay scene/shot list, location anchors, branch tree (history / alien occupation / dinosaur incident), authored actors/events and multi-scene continuity map. Highlight which story decisions inherited from Story/Screenplay vs locally authored. |
| Center workspace | Linked geographic map + 3D/2D CPU-capable scene preview with north arrow, cardinal axes, camera compass, Sun path, sky/weather, layer visibility and four nested scale levels: wilderness/region, settlement/street, building vicinity and interior. |
| Right world inspector | Tabbed Reality Anchor, Historic Baseline, Narrative Overrides, World Rules, Phenomena/Impacts and Sources. Every rule exposes lock state, author, dependent shots and source truth. A rules change first produces a dependency preview, not a destructive rewrite. |
| Bottom event/shot timeline | Separate synchronized tracks for solar/clock, authored narrative events, weather and disaster events, traffic/crowd states, persistent damage, ambient sound, camera/shot binding and exports. This is an **authoring projection**, not a second authoritative video editorial timeline. |
| Status/approval strip | Source/licensing gaps, unknown data, current HRB admission and CPU/optional accelerator mode, stale caches, simulation validity, approval queue and export/provenance warnings. |

### Key workflows

**A. Script-first: Budapest, 1976-07-23, Kossuth tér, cloned T-Rex.** Import selected screenplay beats. Resolve **a precisely selected point** in Kossuth tér if requested, retain historical date and verify local time rules if a clock time is supplied. Use dated streets/transport/vehicles/buildings and seasonal lighting only where evidenced; label inferred crowds and unknown hourly rain. Add the dinosaur as `NarrativeEvent` with timing, movement bounds, avoidance intent, crowd reaction, potential damage, camera and sound cues. Sun orientation and geographic north do not change. If the dinosaur shades a façade, the effective lighting does. Only an explicitly staged override may change global astronomy or physics.

**B. Script-first: an alien occupation of Budapest in 1976.** Fork the baseline at a chosen divergence date; attach extraordinary technology, road closures, nonhistorical aircraft and crowd behavior as authored layers. A projected artificial sun is a localized light source; a truly changed star system instead requires world-rule override and recomputation of seasonal/daylight consequences.

**C. Event-first: storm across four scales.** Region-wide cloud/rain/wind event -> city runoff/drainage and traffic -> roof/facade, tree and gutter exposure -> interior leak, smoke or power loss as separately evidenced or scripted. One event ID and reversible impact deltas persist across every shot; physical simulation fidelity can be raised separately from rendering LOD.

**D. Fully fictional setting.** No false requirement for an Earth GPS point. User declares invented terrain, planet rules, solar cycle, climate, settlement and narrative laws; source-of-truth tags distinguish authored canon from measured Earth data.

### Project wizard and guardrails

1. Create/import screenplay scene or start from an empty world; specify a story synopsis, location/date/time if desired, and the initial world mode. Display historical source coverage *before* claiming reconstruction.
2. Show a generated **World Bible**: immutable facts/selected sources, author-declared canon, unknowns, conflicting evidence, environment rules and branch divergence timeline. This is a versioned project document visible to Story/Screenplay, not an AI-created authority.
3. Ask only for controls that materially affect a shot: exact street/camera for building geometry, specific clock for instantaneous Sun direction, world-rule approval for different physical law. Otherwise permit a rough draft with UNKNOWN badges and bounded defaults labeled as fictional art-direction.
4. Make per-layer toggles (geography, period buildings, transport, vegetation, daypart/astronomy, meteorology, hazards, population/crowds, wardrobe, building/interior, sound) and per-shot overrides available. Users can restore any layer to its original baseline.
5. Export preview, edit assets or hand off to FA3 Video Editor. Do not synchronize speculative traffic counts or narrative storms into historical observational datasets.

## Modules and implementation ownership

| Module | Responsibility | Required existing FA3 integration |
| --- | --- | --- |
| WED GUI / Project Wizard | Qt 6/QML authoring panels, branch compare, map/3D preview, evidence badges | Control Center stable route; standalone desktop entry; Common GUI/Command Bus |
| Geo & Historical Resolver | Optional date/time/place/GPS, as-of place names and street validity, CRSs, hemisphere, region, sourced population and transport periods | Existing Weather & Geo data-provider category, Knowledge/Asset provenance and cache |
| Geo-Solar & Seasonal Adapter | Solar ephemerides, cardinal directions, dated timezone rules, hemisphere and region-aware seasons, object orientation, natural vs effective light | pvlib/Astral/timezonefinder donors **after** Reuse Discovery and independent admission; CPU deterministic fallback |
| Historical Baseline & World Bible | Versioned source snapshot; historical buildings, people/transport era, unknown/estimated labels and evidence/rights | Existing source/asset graph and Story/Screenplay artifacts |
| Narrative Event & Branch Graph | Story events, cloned animals, fictional tech, invasions, divergences; shot inheritance, causal dependencies and reversible changes | Existing Story/Screenplay and shot/scene contracts; no new model authority |
| World Rule Policy | Planet/Earth selection, explicit alternate astronomy/gravity/season rules, approval and invariant guardrails | Existing approval/audit/decision controls; no hidden provider selection |
| Phenomena & Impact Scheduler | Weather, water, geological/fire/heat and secondary event propagation; four geographic/interior spatial scopes, deterministic seed, bounded simulation jobs | Environmental & Natural Phenomena Fabric, VFX, existing HRB and approved simulation adapters |
| Crowd & Mobility Planner | Optional era-qualified fleets, dated street networks, pedestrian density bands, scripted escape paths and congestion consequences | Asset graph and optional SUMO/Mesa donors; CPU simple authored paths by default |
| Shots / Deliverables | Save native project reference, camera/time/sky/effect/auditory metadata and per-shot `ImpactDelta`; no replacing the video editor | Bforartists primary DCC, OpenUSD/glTF exchange where admitted; VFX, FA3 Video Editor, QuickClip, Ardour-compatible audio, OTIO as approved interchange candidate |
| Sources & Verification | Fetch/label/attribute optional observations, reanalysis and archival images, missing/fictitious-data checks, reproducible snapshot hashes | Donor Registry + Reuse Discovery, security/rights and existing FA3 evidence systems |

**Adapter integration:** source and geometry imports use narrow normalized contracts, not direct writes into an editor's own native project. Bforartists is the primary DCC interaction; Blender can be a compatibility/reference path. Stage temporal scene exchanges through already admitted FA3 interchange; file import/export must preserve shot IDs, source flags, event lineage and editable materials.

## Draft data contracts (proposal, not new canonical authorities)

- `WorldProject`: stable ID; schema version; human-readable name; scene/shot IDs; selected scenario branch and World Bible ID; versioned local `.fa3world` manifest; optional external asset references; hash manifest; reversible change journal. `.fa3world` is a **proposed new native sidecar container**, not yet approved or implemented.
- `RealityAnchor`: `anchor_kind` (EARTH / AUTHORED_WORLD), precise WGS84 point or bounded locality with precision, valid historical date/calendar, optional local time, named timezone and tzdb version, north reference, latitude/elevation/hemisphere, Earth ephemeris ID and region-dependent season scheme.
- `HistoricalBaseline`: immutable as-of source snapshot refs; asset/town/route valid-time intervals; population measures and geographic scope; dated meteorological observation/reanalysis; source attribution and rights; known and unresolved fields. Never derive a street crowd directly from a city population.
- `NarrativeEvent`: stable ID; screenplay scene and shot refs; event kind (FICTIONAL_ENTITY / DISASTER / SOCIETAL_CHANGE / VEHICLE / CROWD / LIGHT / OTHER); origin; authored time window and footprint; causal inputs and reversible impact IDs; affected assets; degree of creative override.
- `WorldRuleOverride`: scope (LOCAL_PRESENTATION / LOCAL_PHYSICS / PLANETARY); explicit user approval ID; modified physics/astronomy fields; time validity; baseline comparator; recompute dependencies; fail closed if the result would silently invalidate an unchanged Earth anchor.
- `ExposureContext`: per-asset position/normal/facade compass, roof, slope, windward/leeward, surface materials, portals, artificial occluders, direct and effective sunlight.
- `PhenomenonEvent` / `ImpactDelta`: inherit and extend the existing environmental proposal; regional parameter profiles, canonical event ID, clock time, actual coverage, affected geometry and material-state changes, user-authored vs simulated classification, undo and cache invalidation.
- `ShotWorldBinding`: project/scene/shot refs, historical anchor, story branch and event revision, frame/time conversion, source snapshot hashes, render LOD vs simulation-fidelity profile, camera/lighting/audio references and approved handoff receipt.
- `SourceEvidence`: source type, publisher, URI/record key, observed vs reconstructed vs authored status, spatial/temporal resolution, source right and attribution, retrieved timestamp, fixed content hash and uncertainty.

**Logical data flow:** `Story/Screenplay -> Scene intent -> optional Geo/Historical evidence -> Earth/Custom World anchor -> Narrative branch -> Explicit WorldRuleOverride (only if approved) -> Phenomenon/Impact graph -> Four-scale scene state -> shot previews/3D/FX/audio -> FA3 native project handoff`. External input is **data**, not a self-authorizing instruction to an agent.

## Donor and Reuse Discovery matrix

Before materialization run the canonical `FA3-REUSE-DISCOVERY-001` assessment for this application intent. Existing donor registry search was reviewed for cross-scale weather, geo-solar, building response and scene interchange; the three extra candidates below fill traffic/crowd and editorial-interchange gaps. These are non-authoritative candidates, not code or runtime admission.

| Existing / newly captured donor | Selective contribution | Adoption constraint |
| --- | --- | --- |
| Pixar OpenUSD (existing) | layered stage/asset/scene/shot interchange, not a duplicate authoritative world graph | already in registry; source/third-party/license review remains required |
| OpenVDB, Blender/Bforartists compatibility (existing) | sparse volumetric effects, procedural effects patterns, DCC exchange | no silent GPL code import or automatic accelerator requirement |
| CityJSON, historical map/date plugin (existing) | city models, dated map layers, building/street as-of filtering | underlying GIS/map/photo sources independently licensed and often incomplete |
| pvlib, Astral, timezonefinder (existing) | solar/daypart physics, twilight, coordinate-to-IANA-zone lookup | **contemporary zone geometry is not historical clock law**; pin dated timezone rules |
| NOAA/Open-Meteo, USGS, FDS/SWMM/ANUGA/OpenFOAM (existing) | evidence/context and *optional* domain-scoped simulation | observed, reanalysis, artistic and forecast data never silently mixed; no certified life-safety claim |
| **Eclipse SUMO (new candidate)** | optional street-traffic, pedestrian and route responses for period network after explicit calibration | EPL-2.0 with separately reviewed subcomponents; fictional occupancy and population inputs marked as authored/estimated |
| **Mesa agent-based modeling (new candidate)** | optional coarse crowd/social-interaction behavioral reference | Apache-2.0; not evidence of historically accurate individual behavior or emergency evacuation suitability |
| **OpenTimelineIO (new candidate)** | edit/shot interchange of clip timing, transitions and metadata | Apache-2.0; not a media container and never a replacement for `project.fa3video` |

**Khronos required review:** existing FA3 Khronos adapter registry is the mandatory first stop. glTF-Validator and KTX-Software are `MATCHED` to optional asset/texture interchange. Vulkan/ANARI are `MATCHED` only as selectively admitted optional render abstraction; no baseline Vulkan requirement. OpenXR is `REVIEWED_NO_MATCH` for the initial 2D desktop MVP, while optional future immersive projection remains separate. Reuse OpenUSD alongside existing Khronos interchange rather than inventing a competing interchange layer.

## Delivery plan and acceptance gates

**Phase W0 — design and admission prerequisites (this PR):** publish this app plan, extend central donor metadata, record reuse/Khronos gap analysis and hardware audit. Do not claim implementation, runtime promotion or a new CAP. A subsequent implementation change must satisfy the canonical application-intent and reuse-assessment gate.

**Phase W1 — CPU-only creative MVP:** standalone Qt/QML shell with scripted scene wizard; optional real Budapest anchor/date/local clock; historic-vs-fictional mode; north arrow, reproducible sun position where the time is known; user-authored dinosaur actor on a simple period-labeled square; reversible narrative event layers; baseline evidence/UNKNOWN labels and `.fa3world` **proposed** manifest behind existing FA3 project/asset controls. Stubbed map/vehicle data must be visibly synthetic.

**Phase W2 — continuity across applications:** import Story/Screenplay scene and scene constraints; World Bible branch comparison and inherited locks; shot preview handoff to Bforartists, VFX and native Video Editor; synchronize weather, dust, cast-shadow and sound cue IDs. For any chosen place/time, cardinal orientation and solar angle survive every shot cut and narrative branch unless there is an explicit world-rule change.

**Phase W3 — spatial and regional phenomena:** CPU deterministic seasonal/weather preview; causal rain/wind/damage chain across landscape, street, roof and interior; north/south hemisphere and polar/equatorial regional tests; asset/camera LOD independent of simulation fidelity. Scope any external FDS/SWMM/CFD job to independently admitted optional adapters.

**Phase W4 — dated history and mobility:** source adapters and rights, historic street/transport validity, population time-series with source scope, optional SUMO and Mesa research integration after individual reviews. Compare evidence-backed city population with scenario-authored local crowd: no false historical precision.

**Phase W5 — world-law fiction and QA:** explicitly approved planetary rule overrides, custom orbits and calendars where declared, AI prompt inheritance via the **existing** Model Router, crowd/impact branch replay, cache invalidation and entire project round-trip/undo/screenshot fidelity.

### Must-pass acceptance tests

| ID | Test / pass condition |
| --- | --- |
| A01 | `Budapest, 1976-07-23` at city/date-only precision resolves northern-hemisphere summer; exact street, hour, Sun direction and pedestrian count stay unknown until supplied or evidenced. |
| A02 | `Kossuth tér, 1976-07-23` with a selected historical local clock computes reproducible geographic north and Sun position using a pinned historical timezone source. |
| A03 | Add a fictional dinosaur without any world-rule override: underlying Sun ephemeris, compass, season and selected history snapshot hash **remain identical**; local cast shadows, traffic and crowd cues may change. |
| A04 | Alien ship obscures the Sun or casts artificial light: change effective scene lighting only, not the astronomical position. |
| A05 | "Two genuine suns" without explicit approved planetary rule change is blocked as a physical statement; visual-only second light can be authored without changing global astronomy if clearly labeled. |
| A06 | A historical building is fictionally destroyed: non-destructive baseline, modified story branch, damage and downstream shots differ; undo restores the baseline byte-identically. |
| A07 | Changing real-world location to Cape Town on the same July date reverses hemispheric seasonal interpretation and recomputes exposure; local regional climate is source-scoped, not continent templated. |
| A08 | Fictitious planet with custom seasons/day cycle renders without an Earth GPS value; cannot be mislabeled as geodetically or historically observed. |
| A09 | A regional storm causes consistent street/runoff, façade/roof and interior wetness/damage; deterministic input/seed reproduces impact hashes; moving camera changes render LOD, not the event's factual state. |
| A10 | Population from dated city statistics does **not** silently turn into a measured Kossuth square crowd or an exact route timetable. |
| A11 | Native creative project round-trip retains world/shot/event provenance and editable layers; no automatic hidden copy into upstream project formats. |
| A12 | Offline CPU-only mode with `0` accelerators can open/save/play a bounded storyboard and deterministically recompute time/orientation; accelerated profiles remain optional and HRB admitted. |
| A13 | Missing hourly observations, blocked licensed images, unknown historical street geometry, absent simulation provider and incompatible schema each produce explicit fail-closed/UNKNOWN outcomes, never unlabelled fabrication or automatic unsafe runtime substitution. |

## Mandatory Hardware Audit / release boundary

- Vendor-neutral and CPU-only deterministic preview remain mandatory for the application shell, geometry metadata, scripted branch graph and orientation/daypart calculation; accelerators are optional `0..N`. Discover actual available physical/logical CPU cores and GPU/NPU capabilities through existing host audit; place budgets via **HRB only**. Never pin a fixed GPU vendor, device index, toolkit or provider.
- Qt6/QML GUI, standalone and Control Center projections must support Wayland as preferred and X11 as an alternate without KDE-only assumptions. No global environment changes, upstream uninstalls, default port claims or new runtime resource/model authorities.
- Scoped coexistence namespaces proposed: app `fa3-world-event-director`, `$XDG_DATA_HOME/fa3/world-event-director`, `$XDG_CACHE_HOME/fa3/world-event-director`, `$XDG_CONFIG_HOME/fa3/world-event-director`; runtime paths and sockets namespaced under existing FA3 session context. Secrets only via the existing session vault/broker, never embedded in `.fa3world`.
- Independent source-data licensing, third-party provenance, threat review, version pins, admission and actual current-host runtime evidence required before copying code or enabling external simulators. No operational disaster-warning, hazard-response or certified engineering prediction claim.
- No excluded proprietary real-time 3D engine as installed/runtime/GUI/workflow dependency. Native FA3 timeline and Bforartists-primary DCC remain unchanged.

## Explicit decisions and pending implementation work

Accepted **design proposals**: standalone Qt6/QML authoring UI integrated with World & Environment; story controls narrative, Earth anchor is stable until explicitly overruled; per-layer historical/fictional overrides; source truth badges; CPU-only creative baseline; non-destructive branches; mandatory donor/Khronos discovery.

Not yet decided/implemented: final app/capability identity, canonical `.fa3world` file schema and binary packaging, actual historical GIS/weather sources for any selected scene, crowd and traffic runtime, per-provider resource budgets, real GUI, production DCC/video handoff and current-host proof. Each requires its own authorized approval and normal FA3 gates.
