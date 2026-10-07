# FA3 CLI-Anything Reference Capability Index

Canonical reference: `FA3-REFERENCE-CLI-ANYTHING-001`

This index exists so FA3 work can quickly determine whether the controlled CLI-Anything fork contains a relevant pattern before designing a new implementation from scratch.

## Application-control patterns

- GUI-to-CLI methodology
- Native backend wrapping
- Existing CLI wrapping
- MCP backend wrapping
- REST/WebSocket-style application control patterns
- Stateful command models
- Project/session persistence
- Undo/redo/history/status patterns

## Agent-facing interface patterns

- Human-readable plus machine-readable JSON output
- Introspection commands such as `info`, `list`, and `status`
- Stateful REPL and one-shot subcommands
- `SKILL.md` capability discovery
- Agent-oriented command documentation
- Error contracts designed for agent self-correction

## Preview and trajectory patterns

- Static preview publication
- Live preview sessions
- Immutable preview bundles
- Mutable session head
- Append-only trajectory history
- Producer/consumer separation
- Cheap JSON status/introspection calls
- Truthful preview generation through real backends or native inspection paths

## Validation patterns

- Unit tests
- Native/intermediate format validation
- True backend E2E tests
- Installed CLI subprocess E2E tests
- Real artifact generation
- Output verification beyond exit status
- Image/video/audio/document format verification
- Round-trip workflows
- Agent-only operation tests

## Security patterns

- No `shell=True` subprocess execution
- Subprocess argument allowlisting
- Script/string escaping
- Structured-data escaping
- Path normalization and traversal resistance
- Credential handling and non-disclosure
- Security review for untrusted agent-controlled input

These patterns are useful references only. FA3 security, SCS, admission, HRB, resource authorization, Accelerator Guard, canonical action contracts, evidence rules, and conformance gates remain authoritative.

## Known FA3-relevant application areas

The controlled source includes or documents patterns/harnesses relevant to areas such as:

- Kdenlive / MLT video editing
- Krita digital painting
- Blender and related DCC workflows
- GIMP
- Inkscape
- LibreOffice
- FreeCAD
- QGIS
- OBS
- n8n
- Godot
- other desktop, media, DCC, automation, and agent-facing software

This list is intentionally non-exhaustive. The complete controlled fork is the reference corpus.

## Consultation rule

Consult this reference when a new FA3 task materially concerns any of the following:

1. agent-to-application control;
2. GUI automation without screen-scraping;
3. new CLI or harness design;
4. MCP/native/CLI backend selection;
5. `SKILL.md` or comparable capability discovery;
6. preview, live-preview, state, session, or trajectory design;
7. real-backend E2E testing or artifact verification;
8. application-control security patterns.

Consultation does not imply adoption. Any selected pattern must go through the FA3 adoption process in `ADOPTION-RULES.md`.
