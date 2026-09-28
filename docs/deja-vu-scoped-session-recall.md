# FA3 scoped deja-vu session recall

Status: **implemented read-only adapter and offline negative tests; production runtime
PENDING_CURRENT_HOST**. This extends the existing FA3 Knowledge / Agent Memory
contracts and the existing fa3.memory.retrieve MCP capability. It is neither a
new architectural authority nor a standalone FA3 application.

## What exists in this change

- Pinned upstream: vshulcz/deja-vu at immutable commit
  73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8. The upstream LICENSE
  at this commit declares MIT; its license blob is pinned in the provider record.
  No upstream implementation code is copied into FA3 by this PR.
- Provider and CLI JSON v2 read adapter: src/fa3_deja_vu_recall.py.
- Existing central MCP capability: fa3.memory.retrieve. New binding is
  **PENDING_CURRENT_HOST** and requires an external policy resolver.
- Static gate, offline isolated-CLI fixture and MCP negative tests, and CI.
- Source transcript snippets are untrusted retrieved data, never tool instructions.
- Search only. No automatic import, raw transcript scrubbing, persistent memory
  promotion, network sync, provider self-authorization, agent hook installation,
  host-wide indexing or automatic model/accelerator use.

## Trust boundary and dataflow

1. A consumer (Developer Tools, SUB-Agents, Decision Fabric in advisory mode,
   Agent Memory) sends a typed fa3.memory.retrieve request through the existing
   central stateless MCP Gateway.
2. The existing external FA3 policy resolver verifies the caller and produces
   an ALLOW decision scoped to an explicit project_id, purpose, and decision ID.
   The Gateway enforces that decision *before* calling this provider. A client-
   asserted policy cannot enable the deja binding.
3. The adapter resolves the project ID in a trusted deployment manifest. Each
   project has a private (0700), separately indexed partition INSIDE an FA3
   approved encrypted-at-rest store. Only already-approved Claude/Codex source
   snapshots in that partition may be present.
4. A SHA-256-pinned deja executable runs with an isolated HOME/XDG,
   DEJA_INDEX_DIR, DEJA_STORES and exact approved source roots. The upstream
   CLI's substring --project filter is deliberately NOT treated as ACL.
5. JSON schema_version=2 is mandatory. Results are checked AGAIN for exact
   allowed project aliases, harness and source-root containment, then reduced
   to bounded, redacted snippets and stable opaque source references.
   Relevance-tier near-misses without strict=true are excluded, and semantic
   retrieval is not admitted.
6. The Gateway writes a mandatory local receipt through the adapter's audit
   handler. No raw query or snippet is copied into the audit stream.
   Canonical evidence ownership remains FA3-AUTH-OBS-EVIDENCE-001.

The source Journal and original project files remain authoritative. Search hits
are rebuildable derived data. Do not promote them to durable L1/L2/L3 memory
without existing typed FA3 consent, lineage, versioning and authorization.

## Explicit deployment configuration (not supplied or activated by this PR)

Only a separately admitted administrator-controlled runtime may set
FA3_MCP_ADAPTER_FACTORIES=fa3_deja_vu_recall:factory together with
FA3_DEJA_RUNTIME_MANIFEST pointing to an owner-private 0600 JSON file:

~~~json
{
  "schema": "fa3.deja.scoped-runtime.v1",
  "upstream_sha": "73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8",
  "admission_status": "RUNTIME_ADMITTED",
  "binary_path": "/approved/bin/deja",
  "binary_sha256": "REPLACE_WITH_REAL_64_CHAR_LOWERCASE_SHA256",
  "partition_root": "/approved/encrypted/fa3/deja",
  "projects": {
    "PROJECT_ID": {
      "partition_dir": "/approved/encrypted/fa3/deja/PROJECT_ID",
      "stores": {
        "claude": "/approved/encrypted/fa3/deja/PROJECT_ID/claude",
        "codex": "/approved/encrypted/fa3/deja/PROJECT_ID/codex"
      },
      "exact_project_aliases": ["PROJECT_ID"]
    }
  }
}
~~~

These are **illustrative paths and NOT an admission receipt**. Create
partition, index and home directories at mode 0700, and stage only explicit
user-approved source snapshots. Claude root points at a scoped projects tree;
Codex root points at a scoped CLI store including its sessions/ tree. Do not
copy a complete unreviewed home directory. In particular, raw source
transcripts may still contain secrets even when deja's index redacts them.

The upstream CLI and its JSON v2 contract are documented in:
https://github.com/vshulcz/deja-vu/blob/73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8/docs/INTEGRATING.md
and
https://github.com/vshulcz/deja-vu/blob/73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8/docs/json-output.md

Go upstream declares go 1.25. A separately controlled build can install
github.com/vshulcz/deja-vu/cmd/deja@73ad34e5fdc2b0c245a0fb69b65a17f3cbb123c8
and record its exact built binary SHA-256, provenance and retained MIT notices.
Do not run deja install --auto, update, sync, embed, or expose deja mcp directly.

**Never** edit canonical/mcp-capability-registry.json to CONNECTED on the
strength of the illustrative manifest, this PR, or hosted CI alone.

## Static and isolated tests

~~~
PYTHONPATH=src python3 src/fa3_deja_vu_gate.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_fa3_deja_vu_recall.py' -v
~~~

Offline tests use a fake executable in a private temporary partition and a
temporary registry overlay that simulates CONNECTED for ONLY the local test.
The committed binding remains PENDING_CURRENT_HOST. Tests cover exact scope,
out-of-partition source denial, redaction, schema drift, unsupported semantic
tier, relevance fallback, invalid budgets, upstream digest mismatch, manifest
permissions, external policy scope denial and redaction-safe audit.

## GUI and application mapping

The existing Knowledge / Control Center UI is the home for a future "Session
History" panel. Planned fields: project, query, exact provenance, lifecycle
state, source inspection request, status and revocation, all via a policy-gated
backend. Never call deja from QML or show fabricated CONNECTED/PASS.

- P0 integration consumers: SUB-Agents / Agent Execution, Developer Tools,
  Decision Fabric (advisory only), MCP Gateway and Agent Memory.
- Subsequent consumers: Knowledge/PageIndex context selection, Donor Registry,
  Model Manager, OSINT Intelligence & Evidence.
- FA3-native event adapters later: Video Editor, QuickClip, Story/Screenplay,
  Bforartists, Krita, Music Studio, Ardour, Character Studio and scientific
  observations. Native project files remain untouched.

## Independent rollout blockers

1. Approve exact upstream binary/build provenance and the security/privacy
   handling of source transcripts; verify the staged import is revocable.
2. Prove a real private, per-user AND per-project storage partition on the
   target host, including deletion/tombstone propagation to the index.
3. Exercise real v2 JSON search on the current host with external policy and
   effective identity / project scope, plus adversarial negative cases.
4. Prove current-host performance, timeout, audit failure, resource/NUMA
   placement, rollback, cleanup and zero-residency when disabled.
5. Complete the GUI backend and real native FA3 event producers separately.
   Neither hosted CI nor a valid runtime manifest is production admission.

## Hardware Audit

The metadata, isolated CLI search and static gate are CPU-only viable,
vendor-neutral and allow 0..N accelerators. No accelerator is required or
automatically selected; the display GPU is never enlisted. Optional later
semantic-model work must route through FA3-AUTH-MODEL-ROUTER-001 and the HRB,
and has its own separate current-host admission. Wayland is preferred and
X11 supported for the eventual Qt6 GUI, without KDE-specific requirements.
