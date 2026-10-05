# NNStreamer, ONNX, AOMedia and A11yance — donor capture (2026-09-29)

**Authority:** candidate-only references in `canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json`. 175 capability baseline unchanged. No runtime/code/model/provider/hardware admission or dependency adoption.

The user supplied nine URLs representing **eight distinct discovery/project sources**: NNStreamer core and its organization; ONNX organization; Mozilla AOM branch; GitHub aom topic filtered to Shell and Rust; AOMediaCodec organization with its repositories-listing alias; A11yance organization. Six additional individually verified repositories provide scoped, actionable references, producing 14 unique evaluated candidate sources in this curation.

| Captured source | Role / potential FA3 reuse | License declaration / caution |
| --- | --- | --- |
| [NNStreamer core](https://github.com/nnstreamer/nnstreamer) | streaming-neural-inference, gstreamer-tensor-pipelines, tensor-mux-demux | LGPL-2.1 |
| [NNStreamer organization index](https://github.com/nnstreamer) | Discovery index only | NOT_APPLICABLE |
| [ONNX organization index](https://github.com/onnx) | Discovery index only | NOT_APPLICABLE |
| [ONNX open model format](https://github.com/onnx/onnx) | onnx-model-graph-interchange, opset-versioning, model-validation | Apache-2.0 |
| [Mozilla AOM codec branch](https://github.com/mozilla/aom) | av1-codec-reference, media-codec-compatibility | BSD-2-Clause |
| [GitHub aom Shell-filtered topic](https://github.com/topics/aom?l=shell) | Discovery index only | NOT_APPLICABLE |
| [GitHub aom Rust-filtered topic](https://github.com/topics/aom?l=rust) | Discovery index only | NOT_APPLICABLE |
| [Alliance for Open Media organization index](https://github.com/AOMediaCodec) | Discovery index only | NOT_APPLICABLE |
| [Alliance for Open Media libavif](https://github.com/AOMediaCodec/libavif) | avif-encode-decode, codec-backend-abstraction | UNKNOWN (GitHub API NOASSERTION) |
| [Alliance for Open Media AVM](https://github.com/AOMediaCodec/avm) | av2-reference-software, emerging-codec-analysis | BSD-3-Clause-Clear |
| [A11yance accessibility organization index](https://github.com/A11yance) | Discovery index only | NOT_APPLICABLE |
| [A11yance aria-query](https://github.com/A11yance/aria-query) | aria-semantics-lookup, accessibility-validation | Apache-2.0 |
| [A11yance axobject-query](https://github.com/A11yance/axobject-query) | axobject-model-lookup, accessible-role-validation | Apache-2.0 |
| [NNStreamer Edge](https://github.com/nnstreamer/nnstreamer-edge) | distributed-stream-source-patterns, remote-tensor-stream-ingest | Apache-2.0 |

**AOM disambiguation:** AOMediaCodec and Mozilla/aom relate to Alliance for Open Media codecs; A11yance relates to the *Accessibility Object Model*. The GitHub aom topic pages are dynamic, language-filtered indexes and can contain unrelated repositories; no automatic bulk import. `https://github.com/orgs/AOMediaCodec/repositories` is an alias/list view of `https://github.com/AOMediaCodec`, not a second organization donor.

**Source evidence:** GitHub upstream repository metadata and organization/topic pages checked 2026-09-29. GitHub license fields are upstream metadata **not** source-file, transitive-dependency, binary, patent or distribution clearance. The Mozilla AOM repository had its latest observed push on 2019-04-01; treat as a historical reference until independently updated.

**FA3 admission boundaries:** This capture is metadata only. NNStreamer pipeline ideas must not introduce another Model Router, resource scheduler or silent provider fallback; ONNX defines interchange, not automatic model admission. Streaming and network patterns must use FA3's existing addressing, secure transport, evidence and Software Coexistence controls. Any eventual codec/component integration requires provenance, dependency and license review, existing application reuse assessment, and separately verified current-host evidence. Vendor-neutral CPU-only operation, 0..N accelerators, HRB hardware authority, Hardware Safety Envelope and protected display-GPU rules remain unchanged. Qt6 accessibility remains a native FA3 GUI responsibility; ARIA/AXObject tooling is a reference rather than a React runtime dependency.

**Concurrent registry PRs:** Other active donor PRs modify this same canonical file. Rebase/reconcile at exact head before merge; never overwrite their entries or convert metadata-only checks into physical PASS.
