# FA3 Hierarchical + Hybrid Retrieval Fabric

Canonical root: FA3-KNOWLEDGE-001  
Subprofile: FA3-HIERARCHICAL-HYBRID-RETRIEVAL-001

The mandatory flow is:

RetrievalPlan -> governed provider dispatch -> RetrievalCandidate set -> evidence fusion -> RetrievalTrace -> ContextPassport.

PageIndex Local is the preferred local provider candidate when current-host admitted. It may index and store documents locally, but model calls are routed only through the loopback FA3 Model Router. It receives no PageIndex Cloud API key and owns no model-routing, MCP, policy, Journal or evidence authority.

PageIndex MCP remains the optional cloud-backed provider and keeps its explicit upload-approval and Central MCP Gateway boundary.

OpenKB is retained as an optional compiler/reference pattern for summaries, concepts, entities and cross-links. ConDB is retained as an optional rebuildable tree-search/KV-cache acceleration pattern. Neither is a source authority.

Multimodal inputs are projected into SourceRegion, MediaSegment, TemporalSpan and CrossModalRelation records. Binary image/video/audio artifacts remain in the existing artifact store.

Runtime promotion of PageIndex Local remains PENDING_CURRENT_HOST until a real host test proves the pinned PageIndex SDK, loopback Model Router route, local storage, Central MCP mediation, negative egress tests and evidence lineage.
