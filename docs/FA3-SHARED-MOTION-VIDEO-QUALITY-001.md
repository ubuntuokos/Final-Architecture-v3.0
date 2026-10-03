# FA3 Shared Motion Planning, Video Quality & Independent Review

**Profile:** `FA3-SHARED-MOTION-VIDEO-QUALITY-001`  
**Status:** static materialized; physical runtime requalification pending  
**Capability baseline:** 175; delta 0. **Authority delta:** 0.

This is a non-authoritative subprofile of the existing `FA3-VIDEO-001` and existing editorial/render/audio/orchestration authorities. It adds provider-neutral MotionPlan semantics, revision-bound EditProposal projection, deterministic-render evidence rules, profile-specific media quality, isolated component proofs, and independent reviewer/verifier workflow. It does not create a second video editor, timeline, renderer, Engine Selector, Model Router, audio engine, scheduler or evidence store.

The existing `FA3-ENGINE-SELECTION-FABRIC-001` remains preference/compatibility intent only. Render actions consume a non-executing engine-selection intent; actual AI provider/model routing remains Model Router authority and physical CPU/GPU/NPU admission remains HRB authority. MLT and FA3-native engines remain parallel options.

`fa3.motion-plan.v1` binds exact project/timeline revisions and never edits `.fa3video` or `.kdenlive` directly. Mutating `motion.apply` requires a dry-run/diff path, exact revisions and a rollback reference.

Quality is profile- and delivery-target-specific; no single LUFS, pacing or perceptual threshold becomes a universal FA3 constant. Existing FFmpeg/ffprobe, Audio Fabric, VMAF/libvmaf and Evidence/Gate paths are reused.

Builder/producer identity must differ from reviewer identity. Repair verification uses an independent verifier. `NOT_VERIFIABLE` is not PASS and `REGRESSION` blocks delivery.

The external source `https://github.com/echris6/motion-video-kit` informed design analysis only. This change does not register it as a donor, copy source, add a dependency, admit a provider/model, or create a usage edge.

Because this adds an executable structural path, static/unit success cannot promote Current Host. Physical positive/negative/rollback requalification remains required.
