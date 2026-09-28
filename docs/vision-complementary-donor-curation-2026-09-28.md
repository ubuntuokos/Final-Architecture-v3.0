# Complementary computer-vision donor research — 2026-09-28

## Scope and status

This is selective, non-authoritative research for the existing `CAP-167 Vision Detection, Tracking & Segmentation Fabric` and its FA3 application consumers. It supplements [Nawaf-Rayhan585/YOLO_Projects](https://github.com/Nawaf-Rayhan585/YOLO_Projects) (19 runnable examples, upstream MIT) with 23 source-distinct GitHub candidates. Each source is recorded in the canonical `FA3-DONOR-REFERENCE-REGISTRY-001`; **registry capture is not runtime or model admission**. The source license shown is a reviewed repository declaration, not blanket permission for all weights, datasets or extensions.

Read the existing `FA3-REUSE-DISCOVERY-001` and current application donor index before implementation. Preserve `FA3-AUTH-MODEL-ROUTER-001` for every model-based workload, `FA3-AUTH-HOST-RESOURCE-BROKER-001` for every CPU/GPU/NPU placement, current-host evidence before promotion, and FA3-native media projects / editable non-destructive results. CPU-only remains a mandatory system path; an individual model may be unavailable on CPU as long as it is optional.

## Selective candidates and intended applications

| Upstream | Narrow reusable capability | FA3 targets | Initial disposition |
|---|---|---|---|
| [Supervision](https://github.com/roboflow/supervision) | Model-neutral detection results, annotators, zone counters | CAP-167, Video Editor, QuickClip, Live/Broadcast | MIT, adapter / API reference |
| [Roboflow Trackers](https://github.com/roboflow/trackers) | Interchangeable ByteTrack / BoT-SORT / OC-SORT and camera-motion tracking | CAP-167, Video Editor, Live/Broadcast | Apache-2.0, adapter candidate |
| [Meta SAM 2](https://github.com/facebookresearch/sam2) | Interactive and temporally propagated object masks | Video Editor, QuickClip | Apache-2.0, optional segmentation model |
| [Meta SAM 3/3.1](https://github.com/facebookresearch/sam3) | Text- or exemplar-prompted multi-instance segmentation / tracking | Video Editor, QuickClip | **Research-only until custom SAM License, checkpoint access and published CUDA runtime reviewed** |
| [RF-DETR](https://github.com/roboflow/rf-detr) | Detector alternative and real-time segmentation | CAP-167, Video Editor, Live/Broadcast | **Apache-2.0 core only; Plus and XL/2XL detection variants PML 1.0** |
| [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) | Open-vocabulary text-conditioned bounding boxes | Video Editor, QuickClip, natural-phenomena video | Apache-2.0 upstream; optional CPU path in original demo |
| [RT-DETR](https://github.com/lyuwenyu/RT-DETR) | Replaceable real-time detector and model evaluation | CAP-167, Live/Broadcast | Apache-2.0, optional detector |
| [Anomalib](https://github.com/open-edge-platform/anomalib) | Dataset-calibrated visual anomaly detection / localization | Review, Natural Phenomena | Apache-2.0, advisory output only |
| [MMDetection](https://github.com/open-mmlab/mmdetection) | Modular detector training and benchmark patterns | Model Manager, CAP-167 | Apache-2.0, reference training toolbox |
| [CVAT](https://github.com/cvat-ai/cvat) | Image/video/3D annotation and human label QA | Dataset workspace, Video Editor, Natural Phenomena | MIT Community core; extras independent |
| [FiftyOne](https://github.com/voxel51/fiftyone) | Data exploration, selection, model error triage | Dataset workspace, Model Manager, Review | Apache-2.0, optional tooling |
| [Datumaro](https://github.com/open-edge-platform/datumaro) | Dataset and annotation conversion / integrity checks | Dataset workspace, Model Manager | MIT, adapter candidate |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | OCR, document layout, tables and multilingual document capture | Documents, Video Editor | Apache-2.0, optional OCR provider |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | CPU-first portable runtime and compatible execution providers | Existing Model Router runtime candidate, CAP-167 | MIT, runtime adapter under existing authorities |
| [OpenVINO](https://github.com/openvinotoolkit/openvino) | Compatible Intel CPU/GPU/NPU execution | Existing Model Router runtime candidate, CAP-167 | Apache-2.0, optional hardware-specific adapter |
| [PyroEngine](https://github.com/pyronear/pyro-engine) | Wildfire visual inference and camera calibration patterns | Natural Phenomena, Live/Broadcast | Apache-2.0, advisory image evidence only |
| [Pyro API](https://github.com/pyronear/pyro-api) | Time-window event grouping and camera webhook design | Natural Phenomena, Live/Broadcast | Apache-2.0, reuse event schema patterns, not a new event authority |
| [PyroVision](https://github.com/pyronear/pyro-vision) | Historic wildfire model / ONNX experiments | Natural Phenomena | **Archived upstream**: historical research only |
| [Frigate](https://github.com/blakeblackshear/frigate) | Local multistream review, zoning, retention UX | Live/Broadcast, Natural Phenomena | MIT, selective NVR UX/workflow reference, no mandatory installation |
| [MediaMTX](https://github.com/bluenviron/mediamtx) | RTSP/SRT/WebRTC/RTMP stream input / relay | Live/Broadcast, Natural Phenomena | MIT, optional transport provider |
| [CoTracker3](https://github.com/facebookresearch/co-tracker) | Dense/sparse point tracking reference | Video Editor, Character Studio | **Predominantly CC-BY-NC**; research-only for distributable/commercial FA3 |
| [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) | Single-image depth-assisted compositing and movement cues | Video Editor, Character Studio | Small checkpoint Apache-2.0; Base/Large/Giant CC-BY-NC-4.0 |
| [TorchGeo](https://github.com/torchgeo/torchgeo) | Georeferenced/multispectral satellite data, patch sampling | Natural Phenomena, Model Manager | MIT; each external satellite dataset separately licensed |

## Implementation map (no new capability or authority)

1. **CAP-167 common data contracts.** Typed frame/timebase, detections, segmentation masks, stable tracking IDs, keypoints, quality confidence, frame-to-source transforms, dataset/model identity, privacy classification and provenance. Consumers must never see provider-native objects as canonical state.
2. **CAP-167 model and tracking adapters.** OpenCV CPU-only non-ML baseline; `Supervision` and `Trackers` conventions for detection/track interchange. Independently assess one licensed detector (RT-DETR / RF-DETR core / Grounding DINO) and one segmentation provider (SAM 2) behind governed Model Router routes and approved artifacts. Do not pin YOLO, Ultralytics or a specific GPU as a universal dependency.
3. **Video Editor / QuickClip.** Non-destructive subject mask, temporal mask editing, track-guided reframe, anonymization review, and editable sidecar result attached to `project.fa3video`. Preserve full `.fa3clip` transfer semantics and original media; require human approval for destructive edits.
4. **Character Studio.** Convert detected pose points with explicit coordinates, units, frame rate, skeleton semantics, provenance and confidence to the existing `FA3_HUMAN_MOTION_IR`. No new geometry, DCC or human identity authority.
5. **Data curation and Model Manager.** CVAT / FiftyOne / Datumaro are non-authoritative optional tools for label curation, dataset conversion, sample review, licensing and benchmark evidence. No training or automatic candidate deployment without user-approved, data-rights-verified admission.
6. **Live/Broadcast and Natural Phenomena.** MediaMTX stream transport; Frigate zone/review UX patterns; PyroEngine / Pyro API wildfire advisory evidence; TorchGeo geospatial imagery; Anomalib candidate anomalous-pattern review. Do not conflate vision classifications with certified life-safety, evacuation or enforcement decisions.

## High-risk and excluded-by-default paths

- No automatic suspicion/criminality inference from human poses; raw posture / trajectory analysis requires privacy review, explicit opt-in and qualified human interpretation.
- Face/license-plate processing is privacy-sensitive: minimal retention, explicit authorization, access controls, consent/legal-basis review where relevant and reviewed anonymized exports.
- Fire/fall/smoke outputs are provisional until calibrated against representative data with documented false-negative and false-positive rates, and must not be presented as a certified safety mechanism.
- SAM 3 custom SAM License / gated checkpoint / CUDA-centric setup: research candidate only until explicit legal and hardware review. CoTracker3 is predominantly CC-BY-NC. Depth Anything V2 restricts the larger checkpoints; RF-DETR Plus has a different commercial license; upstream YOLO examples' MIT does not change Ultralytics AGPL-3.0 / Enterprise dependency licensing.
- The older PyroVision repository is archived (reviewed 2026-09-28); use current PyroEngine/Pyro API for integration research.
- All newly captured donors remain CANDIDATE and non-authoritative, even when their repository-level license is known.

## Mandatory Hardware Audit and implementation gates

**Hardware Audit:** vendor-neutral, dynamically discovered CPU and 0..N accelerator topology; CPU-only working baseline, dynamic backend compatibility through existing hardware discovery, HRB sole admission/placement/lease authority, Model Router sole route/provider/model authority, no silent fallback. Display GPU remains display-first; when another GPU and/or NPU exists, its AI use requires explicit app-level assignment to a named model and task. Wayland preferred with X11 supported.

**Reference test plan:** deterministic synthetic CPU frame/zone/mask tests; temporal tracking ID regression; anonymization all-frame adversarial QA; valid/invalid model/license/provider admission; explicit refusal of unavailable requested accelerator; CPU-only and mixed-accelerator runtime evidence; no cloud or unauthorized camera egress; native project roundtrip; real current-host E2E before promotion. CI success for metadata alone never implies runtime admission.

## PR sequence suggested for later implementation

1. Registry / Reuse Discovery capture and targeted application donor-index validation (this draft PR; no runtime changes).
2. Typed CAP-167 interchange and OpenCV CPU-only reference tests.
3. Optional licensed detection / segmentation / tracking adapters under Router and HRB.
4. Non-destructive Video Editor / QuickClip and Character Studio adapters.
5. Dataset tooling, Natural Phenomena and Live/Broadcast adapters with scoped privacy review.
6. Current-host evidence gates per provider / application, with rollback and explicit sign-off.
