# FA3 Embedding Fabric

**Profile:** `FA3-EMBEDDING-FABRIC-001`  
**Capability delta:** 0  
**Architectural-authority delta:** 0  
**Canonical capability count:** 143

The Embedding Fabric is a provider-neutral cross-cutting profile. It connects the existing Model Manager, Model Router, Inference Portability, HRB, Knowledge/Retrieval, Evidence, Security, Secret Broker and MCP boundaries. No embedding provider becomes an authority.

## Hardware Audit

- vendor-neutral baseline;
- CPU-only execution is conformant;
- accelerators are optional (0..N) and require HRB-bound admission;
- no CUDA/ROCm/oneAPI/Vulkan backend is globally required;
- provider runtime execution must also satisfy the Provider Runtime and supply-chain admission profiles.

## Embedding space

`EmbeddingSpaceIdentity` is bound to model family, immutable model revision, tokenizer revision, pooling, normalization, query template, document template, dimension, semantic role and modality.

Different space identities **must not** be compared directly. Representation (FP32/FP16/INT8/INT4/BINARY_I1) is a separate concept from semantic space identity.

## Migration

Safe replacement follows:

`old space -> shadow re-embedding -> new index -> dual-query comparison -> quality/performance evidence -> controlled cutover -> old index retirement`.

A projected vector cannot claim `NATIVE` state. Cross-space bridging is explicit and evidence-bound.

## Provider status

TEI, Model2Vec and FlagEmbedding records are materialized as optional providers/projections. Static materialization is not runtime admission. Current-host execution remains pending until real provider/runtime/model/resource receipts exist.

Qxotic/Jinfer remains assessment-only until license, security, supply-chain, performance, coexistence and current-host audits pass.

## GUI

Embedding Inspector and Migration UI are intentionally deferred until the independent GUI physical current-host closure stabilizes. Static contracts may be projected later without invalidating the GUI runtime closure.

## Evidence

A static gate PASS proves only canonical structure and fail-closed regressions. It does not mean `CURRENT_HOST_PASS`, `ADMITTED`, `CONNECTED`, or global promotion.
