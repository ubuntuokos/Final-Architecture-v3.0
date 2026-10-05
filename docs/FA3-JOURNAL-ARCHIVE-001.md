# FA3 Unified Journal & Journal Archive

Canonical profiles: `FA3-JOURNAL-001`, `FA3-JOURNAL-ARCHIVE-001`  
Provider: `FA3-PROVIDER-JOURNAL-LOCAL-001`  
Gate: `FA3-JOURNAL-GATESET-001`

## Purpose

The Unified Journal is the FA3 work-history projection for system/runtime events, conversations and decisions, project lifecycle, evidence links, security events and audit actions. It does not replace any existing canonical authority.

The Journal Archive is the mandatory retention layer for rotated journal data. It creates a self-describing archive manifest with an event count and SHA-256 digest over the archived payload. A restore operation is fail-closed unless the digest verifies.

## GUI

`FA3 Control Center 0.2.0` exposes **Napló / Journal** in the primary navigation. The view provides:

- Overview
- System
- Conversations
- Projects: Active / Closed / Planned / All
- Events
- Archive

Actions available from the GUI:

- save/export to Markdown, JSON and printable HTML;
- print through `lp` when present, otherwise print-preview via the default desktop handler;
- e-mail handoff through `xdg-email` with an attached export;
- chat handoff through a configured `FA3_CHAT_SHARE_URL`, otherwise an explicit export-bundle fallback;
- tombstone-based soft delete of active events;
- manual and policy archive rotation;
- archive SHA-256 verification;
- verification-gated archive restore;
- archive retirement to retention trash.

## Storage model

The reference provider uses the platform `QStandardPaths::AppLocalDataLocation` and stores journal state beneath `journal/`:

```text
journal/
├── events/
│   └── active.jsonl
├── archives/
│   └── FA3-JOURNAL-ARCHIVE-*.fa3journal.json
├── exports/
└── trash/
```

The active log is append-only. Soft deletion adds a `TOMBSTONE` event rather than rewriting history. Archive retirement moves a sealed bundle into retention trash; physical purge is intentionally not available as an ordinary GUI action.

## Reference archive policy

- maximum active event count: 5000;
- maximum active age: 30 days;
- archive digest: SHA-256;
- restore: digest PASS required;
- restore emits an audit event and creates fresh event IDs while preserving `original_event_id` and `restored_from` provenance;
- archive retirement and physical purge are separate lifecycle transitions.

These are reference defaults. Canonical retention/evidence policy can impose longer retention or legal/operational hold.

## Authority boundaries

The Journal provider is not:

- the Canonical Registry;
- the security authority;
- the Host Resource Broker;
- the MCP/tool execution authority;
- the workflow authority;
- the evidence/promotion authority.

An archive integrity PASS proves only that the archive payload matches its manifest digest. It does **not** prove current-host runtime conformance or production admission.

## Evidence state

Repository materialization is present. Current-host build, GUI launch, archive/verify/restore E2E and print/share evidence remain `PENDING_CURRENT_HOST` until produced by the designated current-host execution path.
