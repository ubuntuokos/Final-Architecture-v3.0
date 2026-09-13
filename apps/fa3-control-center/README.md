# FA3 Control Center

Native Qt 6/QML reference GUI for FINAL ARCHITECTURE v3.0.

The application is deliberately a **projection and intent surface**, not a new FA3 authority. It reads canonical/evidence state, shows host telemetry, maintains the local Unified Journal, and can create local `DRAFT_NOT_SUBMITTED` typed ChangeSet JSON files. It does not execute privileged system changes or mutate the canonical repository.

## Views

Command Center; Projects & Workspaces; AI Studio; Agents & Workflows; Models & Providers; Architecture Explorer; Resources; Security & Approvals; Observability; **Napló / Journal**; Evidence; Integrations; System.

AI Studio includes Image, Video, Animation, 3D/VFX, Audio, Music, and Story/Screenplay projections.

## Unified Journal and Archive

Control Center 0.2.0 adds the `FA3-JOURNAL-001` GUI projection and `FA3-JOURNAL-ARCHIVE-001` archive surface:

- system, conversation, project, evidence, security and audit event domains;
- active, closed and planned-project lifecycle views;
- Markdown/JSON/HTML export, print, e-mail composer and configurable chat-adapter/export fallback;
- append-only active journal with tombstone-based soft deletion;
- manual and policy-driven journal rotation;
- SEALED archive bundles with SHA-256 payload integrity;
- verification-gated restore with original event ID provenance;
- archive retirement to retention trash rather than direct GUI purge.

The local journal is **not** a replacement for canonical registry, security policy, Host Resource Broker, execution, or evidence/promotion authorities. Archive-integrity PASS is not production runtime admission.

## Build

```bash
cmake -S apps/fa3-control-center -B build/fa3-control-center -GNinja -DCMAKE_BUILD_TYPE=Release
cmake --build build/fa3-control-center
FA3_REPO_ROOT="$PWD" ./build/fa3-control-center/fa3-control-center
```

For Kubuntu/Ubuntu use `deployment/fa3-gui/install.sh`.

## Authority boundary

Mutating privileged intent is expressed as a draft typed ChangeSet and must be submitted through an existing FA3 adapter/approval path. The GUI must never bypass identity, policy, MCP/tool mediation, workflow durability, model routing, Host Resource Broker admission, systemd/cgroup enforcement, evidence/provenance, secrets, or promotion authorities.
