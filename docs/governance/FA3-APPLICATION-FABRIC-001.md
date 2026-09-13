# FA3-APPLICATION-FABRIC-001

Status: CANONICAL_CANDIDATE

## Decision

FA3 SHALL provide its own canonical application lifecycle fabric. External meta-launchers/application managers MUST NOT be canonical dependencies, default-install components or required GUI surfaces.

The following components are removed from canonical/default FA3 scope:

- LynxHub
- Stability Matrix
- Pinokio

Their useful patterns MAY be reimplemented natively in FA3, but their runtime/application-manager authority MUST NOT remain in canonical FA3.

## Native FA3 responsibilities

The Application Fabric owns:

- application discovery and catalog presentation
- provider manifests
- installation and dependency bootstrap
- update policy integration
- application start/stop lifecycle
- runtime isolation and resource-lease integration
- application status and health
- uninstall/cleanup semantics
- GUI presentation through the FA3 Control Center

## Boundary

Model/content/asset sources are not meta-launchers. Hugging Face, CivitAI and OpenModelDB MAY remain or become native FA3 providers subject to provider policy and evidence requirements.

## Migration rule

References to LynxHub, Stability Matrix and Pinokio MUST be classified as one of:

1. obsolete canonical dependency -> remove;
2. provider-independent useful pattern -> migrate to FA3 native capability;
3. historical evidence/documentation -> retain only when explicitly marked historical;
4. current-host installation/runtime -> remove during host reconciliation.
