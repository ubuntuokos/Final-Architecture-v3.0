# HPC, MCP and Microsoft donor curation — 2026-09-29

**Scope:** Seven user-supplied organization/profile/topic links and 17 individually checked repositories. Candidate metadata only, recorded in the existing `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. Base `main` at `cb3e5b34da3e0f4002f8fb82b4d1c0ae05375194`: 592 records → 616 on this branch; concurrent donor PRs require exact-head reconciliation before merge. FA3 capability baseline remains **175**.

## User-submitted discovery indexes

| Submitted source | Role | Selected FA3 targets |
| --- | --- | --- |
| [hpc](https://github.com/hpc) | HPC upstream repository index | Storage Fabric, Host Federation, Hardware Audit |
| [hpc-systems topic — JavaScript filter](https://github.com/topics/hpc-systems?l=javascript&o=asc&s=updated) | Dynamic discovery index, one JavaScript repository observed | Orchestrator, Agent Workload Runtime |
| [hpc-uk](https://github.com/hpc-uk) | UK HPC build/benchmark learning index | Generic Linux installer, Hardware Audit |
| [hpc-social](https://github.com/hpc-social) | HPC community and research-discovery index, *not an execution dependency* | Research and Reuse Discovery |
| [modelcontextprotocol](https://github.com/modelcontextprotocol) | Official MCP project/SDK discovery index | Existing FA3 MCP Gateway, Skill Fabric |
| [punkpeye](https://github.com/punkpeye) | Community MCP references, not an official specification | Existing FA3 MCP Gateway, Reuse Discovery |
| [microsoft](https://github.com/microsoft) | Large multi-domain discovery index; no blanket admission | Import/Migration, Inference, testing |

All seven are non-code **DISCOVERY_INDEX** candidates. The language-filtered topic URL is retained in provenance; the canonical source identity is the unfiltered topic, preventing duplicates from sorting and pagination variants. Do not automatically import every repository under an organization or indexed topic.

## Separately verified project candidates

The below project identities were checked through the GitHub repository metadata on 2026-09-29. Licenses in this table are *GitHub metadata declarations*, not complete source-level, transitive dependency, patent, or distribution clearance.

| Upstream | GitHub-reported license | Scoped use for FA3 |
| --- | --- | --- |
| [hpc/ior](https://github.com/hpc/ior) | NOASSERTION | I/O and metadata benchmark methods, controlled Storage/Hardware Audit tests |
| [hpc/mpifileutils](https://github.com/hpc/mpifileutils) | BSD-3-Clause | Distributed file traversal/copy; Host Federation and Migration patterns |
| [hpc/dcp](https://github.com/hpc/dcp) | NOASSERTION | Decentralized distributed copy; historical 2019 reference |
| [hpc/pavilion2](https://github.com/hpc/pavilion2) | NOASSERTION | Multi-host test planning and evidence collection |
| [hpc-uk/build-instructions](https://github.com/hpc-uk/build-instructions) | GPL-3.0 | Portable Linux build/configuration recipes; no automatic host mutation |
| [hpc-uk/mpi-performance](https://github.com/hpc-uk/mpi-performance) | GPL-3.0 | MPI performance-measurement methods; 2019 historical reference |
| [alice-viola/dora](https://github.com/alice-viola/dora) | MIT | Older AI/HPC cluster orchestration UX/workflow research; topic-derived |
| [modelcontextprotocol/modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | NOASSERTION | Protocol/specification compatibility and version negotiation |
| [modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk) | MIT | Python server/client adapter and interoperability patterns |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | NOASSERTION | MCP protocol conformance and visual debugging |
| [modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry) | NOASSERTION | Registry schema *interoperability only*; no second FA3 donor registry |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | NOASSERTION | Server example/test fixtures; individual server vetting required |
| [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) | MIT | Community discovery catalog only; linked projects require separate vetting |
| [punkpeye/mcp-proxy](https://github.com/punkpeye/mcp-proxy) | MIT | stdio / HTTP / SSE transport bridging patterns in existing MCP Gateway |
| [microsoft/markitdown](https://github.com/microsoft/markitdown) | MIT | File-to-Markdown patterns in existing Production Import & Migration Fabric |
| [microsoft/onnxruntime](https://github.com/microsoft/onnxruntime) | MIT | Optional inference-backend interfaces beneath central Model Router |
| [microsoft/playwright](https://github.com/microsoft/playwright) | Apache-2.0 | Multi-browser test and automation patterns; Browser Skill and Evidence/Gate |

Already registered `microsoft/mcp-gateway` remains untouched as an existing **ACCEPTED_REFERENCE**; this curation does not re-add or promote it.

## Required FA3 boundaries

- **No new authority:** use existing MCP Gateway, Model Router, Host Resource Broker, Reuse Discovery, Donor & Reference Registry, evidence/gates and multi-host orchestration. Upstream `modelcontextprotocol/registry` and MCP proxy patterns may inform interoperable adapters, never create competing FA3 authorities.
- **Hardware Audit:** metadata-only, CPU-only viable, vendor-neutral, 0..N discovered accelerators. Optional HPC/MPI, GPU or inference use must obey HRB, Hardware Safety Envelope, protected display-GPU rules, current-host physical evidence and explicit model/task routing. No automatic tuning or unsafe benchmarks.
- **Software Coexistence:** no upstream replacement of installed runtimes, no global service/port/path/socket/env/model-cache collisions, no mandatory Conda/Mamba, no automatic external workload execution. Generic Linux and Wayland-first/X11 fallback remain intact.
- **Governed network and file movement:** path safety, source provenance, cross-host authorization, secure transport, bounded resource use, retry/idempotence and exact source/output hashes for future migration or MCP transports.
- **Admission separation:** each repository needs exact revision, independent license and provenance audit, security and dependency review, Software Coexistence and prospective source/runtime tests. An organization/topic page is never a code donor.
- **No unsupported release status:** no code import, install, provider/model admission, architectural changes, CI PASS or current-host PASS are claimed by this capture.

## Validation and concurrency

Registry construction used the original `main` JSON byte-for-byte apart from the appended candidate metadata, count, sorting and capture note. All seven supplied sources are covered; all 24 new sources have unique normalized keys and donor IDs, status `CANDIDATE` and authority/automatic-install/fetch/code-import/model-selection/provider-admission flags disabled. The already-existing `microsoft/mcp-gateway` record was preserved. This validation concerns only captured metadata and is **not** runtime qualification.

Other open donor PRs modify the same canonical JSON. Reconcile this branch against the latest exact head before merging, without overwriting any concurrent candidate records.
