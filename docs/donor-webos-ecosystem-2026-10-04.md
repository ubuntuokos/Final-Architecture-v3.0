# FA3 webOS / web-based OS donor intake — 2026-10-04

## Owner marker

The owner explicitly requested `vedd fel donornak` for these four submitted URLs:

1. https://github.com/webosose
2. https://github.com/topics/webos
3. https://github.com/topics/web-based-os
4. https://github.com/topics/webos-application?o=asc&s=updated

This request is treated as an explicit donor-intake instruction. All four exact URLs are preserved as provenance.

## Duplicate and normalization check

Published-main duplicate search at `9e795a2a6bf3417b60bc52179edcd31d8e53d8a9` found no matching canonical or pending normalized identities for:

- `github:webosose`
- `github:topics/webos`
- `github:topics/web-based-os`
- `github:topics/webos-application`

The query parameters on the submitted `webos-application` URL are preserved in provenance but do not create a separate canonical topic identity.

Planned identities:

1. `FA3-DONOR-WEBOSOSE-ORG-001`
2. `FA3-DONOR-GITHUB-TOPIC-WEBOS-001`
3. `FA3-DONOR-GITHUB-TOPIC-WEB-BASED-OS-001`
4. `FA3-DONOR-GITHUB-TOPIC-WEBOS-APPLICATION-001`

All four are `ACCEPTED_REFERENCE` / `DISCOVERY_INDEX` records only.

## Upstream observation

The public `webosose` GitHub organization resolves as **webOS Open Source Edition**. Its public repository index currently exposes system/build, application-management, browser/web-app, service-bus, media and UI-related projects. Representative visible repositories include `build-webos`, `meta-webosose`, `sam`, `ls2-helpers`, `samples` and `com.webos.app.enactbrowser`.

The three GitHub topic URLs also resolve and are treated solely as discovery indexes. Their linked repositories are not recursively admitted.

## FA3 reference value

Reference-only areas worth consulting in later FA3 planning include:

- application and process/service lifecycle patterns;
- app-to-service and service-bus messaging;
- web-application runtime/container separation;
- surface/window/workspace management;
- app packaging, installation, deployment and developer tooling;
- notification/media-service orchestration;
- web-based desktop/workspace/shell patterns;
- webOS application ecosystem and cross-device UI/runtime examples.

These records do not create a new FA3 operating system, shell authority, application authority, runtime authority or provider authority.

## Safety, rights and authority boundaries

This intake does **not**:

- recursively register repositories found under an organization or topic page;
- copy or import upstream code;
- install packages or services;
- admit an engine, provider, model, SDK or runtime;
- create a donor usage edge;
- change Current Host evidence;
- change the fixed capability baseline of **175**;
- change any existing FA3 architectural authority.

Any concrete repository later selected for material reuse requires separate provenance, License & Rights, security, Software Coexistence and applicable Hardware Safety/model-runtime review, plus explicit usage-edge registration.

## FIFO waiting state

Published parent main: `9e795a2a6bf3417b60bc52179edcd31d8e53d8a9`

Parent donor registry blob: `1362d75186c6da74e5cf947fdf0b8867d462636a`

Parent donor count: **1427**

Parent-relative proposed count: **1431**

The live intake inventory exceeds the repository's rolling five-slot donor-maintenance window. The currently observed earliest canonical-registry mutators are #651, #657, #663, #664 and #671; later donor intakes are already queued.

Therefore this PR is deliberately staged as **draft / FIFO waiting**:

- the four owner-marked sources are recorded;
- the canonical registry on this branch is not modified yet;
- these identities are not yet canonical planning inputs;
- when a slot is available, the branch must be rebased/reconciled against then-current published main, duplicates rechecked, the four identities materialized into the canonical registry, and exact-head donor gates rerun.

No canonical admission or PASS is claimed before that step.
