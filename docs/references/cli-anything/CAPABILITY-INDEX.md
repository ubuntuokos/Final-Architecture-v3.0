# CLI-Anything Reference Capability Index

Canonical reference: `FA3-REFERENCE-CLI-ANYTHING-001`

This index is a retrieval aid, not an FA3 capability claim. It identifies areas in the controlled CLI-Anything fork that should be consulted when an FA3 design task intersects the same problem class.

## Application-control methodology

Consult for:

- GUI-to-CLI decomposition and mapping of GUI actions to backend/API calls.
- Native project/data-model manipulation followed by execution through the real application/backend.
- One-shot subcommand and stateful REPL interaction models.
- Introspection-first command surfaces (`info`, `list`, `status`).
- Machine-readable JSON output contracts for agents.
- Undo/redo and persistent session-state patterns.

Primary reference material in the source repository includes the CLI-Anything harness methodology (`cli-anything-plugin/HARNESS.md`).

## Agent discovery and tool contracts

Consult for:

- `SKILL.md` generation and self-describing CLI surfaces.
- Capability discovery for agents.
- Command examples intended for machine use.
- Separation of human-readable and JSON/machine-readable output.
- Registry/hub discovery patterns.

FA3 rule: skill or registry metadata is descriptive only and never grants execution, admission, canonical, security, or resource authority.

## Native backend and MCP patterns

Consult for:

- Native CLI/scripting backends.
- MCP-backed application control when no suitable native CLI exists.
- Backend executable resolution and subprocess wrapping.
- Error reporting that permits an agent to self-correct.
- Native-renderer-first execution instead of reimplementing the target application.

FA3 rule: any executing adapter remains below FA3 policy/admission/security/resource boundaries.

## Media, DCC, and desktop-application examples

Known directly relevant harness families include:

- Krita
- Kdenlive
- Blender
- GIMP
- Inkscape
- LibreOffice
- FreeCAD
- QGIS
- OBS-related control patterns
- n8n/workflow-control patterns

These examples are comparison material. Their presence does not imply FA3 adoption or conformance.

## Kdenlive/editorial patterns

Consult for:

- media-bin import and inspection;
- track/timeline manipulation;
- trim/split/move operations;
- effects and transitions;
- guide/marker handling;
- MLT/Kdenlive project generation;
- JSON state and undo/redo;
- installed-CLI and real-render E2E testing.

Compare with existing FA3 editorial canonical profiles before adopting any behavior.

## Preview, live preview, and trajectory

Consult for:

- immutable preview-bundle concepts;
- separation of preview producer and read-only viewer/consumer;
- mutable live-session head versus immutable history;
- append-only command-to-preview trajectory;
- agent-cheap status/introspection responses;
- truthfulness requirements for previews generated from real application state.

FA3 rule: preview state is evidence/inspection state, not execution authority.

## Validation and real-backend E2E

Consult for:

- unit tests for deterministic data-layer behavior;
- real-file/native-format tests;
- tests invoking the installed CLI as an external user would;
- true backend execution using the real target application;
- output verification beyond exit status, including file signatures, structure, duration, image/video/audio properties, or other artifact-specific checks;
- round-trip tests through the real application where applicable.

FA3 rule: if a CLI-Anything-derived runtime component is materialized, it must receive its own FA3 conformance/evidence path. Reference review alone is not runtime evidence.

## Security patterns

Consult for:

- subprocess argument allowlisting;
- avoiding `shell=True`;
- script-language escaping;
- XML/SVG/structured-content escaping;
- path normalization and traversal resistance;
- secret/credential handling;
- agent-generated command threat modeling.

FA3 rule: these patterns complement but do not replace FA3 SCS, security validation, HRB, admission, or accelerator/resource authorization controls.

## Retrieval rule

When an FA3 task matches one or more sections above:

1. Inspect the pinned controlled fork first.
2. Compare the reference pattern with existing FA3 canonical semantics.
3. Record `ADOPT`, `ADAPT`, `REJECT`, or `NOT_APPLICABLE` when the comparison materially affects the design.
4. Do not import or execute source code directly from the reference repository.
5. If runtime use becomes desirable, materialize an explicit FA3 provider/runtime contract and corresponding conformance/evidence.
