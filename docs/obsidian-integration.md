# Obsidian FA3 integration

## Canonical role

Obsidian is an optional, replaceable, human-facing local Markdown knowledge workspace provider under `FA3-HUMAN-KNOWLEDGE-WORKSPACE-001`. It projects only to `CAP-010` and `CAP-018`; it adds no capability and no architectural authority. The canonical capability count remains 143.

The local Markdown note plus admitted attachments are the human workspace source. Git provides reviewable promoted-content history. Obsidian's metadata cache, Bases, Canvas, search results, chunks and embeddings are rebuildable or view-only projections. They are not the FA3 registry, database, workflow or memory authority.

Obsidian does not replace the Unified Memory Gateway, PostgreSQL/pgvector, the Central MCP/Capability Gateway, Temporal, NATS, the identity/policy/secrets authorities, or the evidence system. Obsidian failure must not block inference, orchestration or canonical memory.

## Vault boundary

The provider-neutral contract uses a user-configured, canonicalized `approved_root`; it does not encode one workstation path as a global constant. The current-host preferred layout remains:

```text
/Dokumentumok/Obsidian/
├── AI-Platform/   # approved human knowledge workspace
└── Private/       # excluded from watcher, indexer and agent routes
```

`/Dokumentumok/Obsidian/AI-Platform/` is current-host evidence/configuration, not a portable architectural path. Nested vaults, home/root-wide scopes and symlink escapes are denied.

Recommended workspace layout:

```text
00-Inbox/
10-Architecture/
20-Projects/
30-Research/
40-Runbooks/
50-Decisions/
60-Prompts/
70-Agent-Workspace/
80-References/
90-Archive/
_agent-inbox/<proposal_id>/
_templates/
_attachments/
```

Models, checkpoints, renders and large media stay in their governed artifact stores; notes contain references and metadata only.

## Note admission

Every indexable note requires stable `id`, `type`, `status`, `owner`, `visibility`, `index`, `source`, `created`, `updated` and `tags` properties. Only `status: approved`, `index: true`, `visibility: agent-read` notes are eligible for agent retrieval. Unknown or malformed metadata fails closed.

```yaml
---
id: "a-stable-uuid"
type: architecture
status: approved
owner: human
visibility: agent-read
index: true
source: human
created: 2026-09-07
updated: 2026-09-07
tags:
  - architecture
  - obsidian
---
```

The watcher is only a low-latency trigger. Periodic full reconciliation is mandatory so missed events are recovered. Indexing records the canonical note ID, path, content hash, frontmatter, chunk/embedding lineage and tombstones. The entire derived index must be rebuildable from admitted source files and Git provenance.

## Agent access and writes

Agents receive only policy-scoped `knowledge.search` and `knowledge.read` through the Central MCP/Capability Gateway and Unified Memory Gateway. Direct vault filesystem access, direct Obsidian MCP access and direct PostgreSQL/pgvector access are denied.

An agent cannot overwrite a curated note. It emits a typed proposal under `_agent-inbox/<proposal_id>/` with a target note ID, base content hash, patch, reason and policy receipt. Human review creates the promotion receipt. Promotion uses atomic compare-and-swap against the base hash; conflict requires review against the new base. Delete, move and rename remain denied by default. Promoted changes require a Git commit and rollback path.

## Desktop, CLI and hosted services

The pinned Linux desktop reference is Obsidian `1.13.7`, package `obsidian_1.13.7_amd64.deb`, SHA-256 `17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0`. It runs manually as a non-root process in the KDE Wayland user session; it is not a system service and autostart is not required.

The Obsidian CLI controls the desktop application and exposes broad commands. It is operator-only by default; agents cannot execute commands, evaluate JavaScript or manage plugins through it. Obsidian Headless remains an optional open-beta service client, not an FA3 core runtime. Sync and Publish are optional, consent/egress-gated services and do not replace Git or backup authorities.

## Local REST API/MCP adapter

`FA3-PROVIDER-OBSIDIAN-LOCAL-REST-API-001` pins `coddingtonbear/obsidian-local-rest-api` `5.1.0` at commit `2e255200a4d8f68e49a4f7f8fd46b4abf736c4eb`. It remains disabled by default because an Obsidian community plugin inherits the application's process access and lacks a reliable native fine-grained permission boundary.

Separate admission requires an independently audited pinned bundle, a dedicated non-private vault, verified TLS on loopback, bearer material from the FA3 secrets authority, and Central MCP/Capability Gateway mediation with an operation allowlist. Plaintext HTTP, insecure TLS bypass, direct endpoint disclosure, command execution, evaluation, plugin configuration, curated-note overwrite, delete, move, rename and private-vault access are denied.

## Evidence and status

Run the canonical gate with:

```bash
./bin/fa3-enforce obsidian-knowledge-workspace
```

The reference gate proves 32 positive/negative fail-closed rules and authority separation. It does not claim installed desktop, vault/indexer, plugin or current-host production E2E conformance. Runtime remains `NOT_PROMOTED_PENDING_CURRENT_HOST_KNOWLEDGE_WORKSPACE_CONFORMANCE`.

Upstream references: [Obsidian data storage](https://obsidian.md/help/data-storage), [Properties](https://obsidian.md/help/properties), [Bases](https://obsidian.md/help/bases), [plugin security](https://obsidian.md/help/plugin-security), [CLI](https://obsidian.md/help/cli), [Headless](https://obsidian.md/help/headless), [license overview](https://obsidian.md/license), [desktop releases](https://github.com/obsidianmd/obsidian-releases/releases), and [Local REST API/MCP releases](https://github.com/coddingtonbear/obsidian-local-rest-api/releases).
