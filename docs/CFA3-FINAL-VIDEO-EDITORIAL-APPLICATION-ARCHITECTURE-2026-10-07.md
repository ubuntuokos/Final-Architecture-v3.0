# CFA3 Final Video / Editorial Application Architecture — 2026-10-07

Status: **OWNER-APPROVED FINAL APPLICATION MODEL / CANONICALIZATION PENDING SHARED RELEASE-PROJECTION WINDOW**

## Final application split

| Application | Final role | Project / authority boundary |
|---|---|---|
| CFA3 Video Editor | **FULL EDIT** — sole full CFA3 NLE | Owns full editorial project state and `project.fa3video` |
| CFA3 OpenCut | **FAST EDIT** — standalone + embeddable QuickClip-style editor | Fast editing surface; never full-NLE authority |
| FA3 QuickClip | **SHORT-FORM AUTOMATION** | Existing short-form automation application; not silently retired or renamed |
| CFA3 OpenVid Shared | **FAST COMPOSE** — shared composition application | Owns `.fa3openvid`; embedded through OpenVid Composer plugin/workspace |
| CFA3 Motion Designer / Animation Studio | **ADVANCED MOTION** — shared motion application | Owns advanced motion semantics, reusable motion graphs/components |
| CFA3 Webdesign | Consumer surface when materialized | Uses OpenCut for fast web-video edit and Motion Designer for web motion; does not own another video core |

## Product flow

```text
CFA3 Video Editor
      FULL EDIT
          |
    +-----+---------------------+
    |                           |
CFA3 OpenCut              CFA3 OpenVid Shared
   FAST EDIT                  FAST COMPOSE
    |                           |
    +------------+--------------+
                 |
        CFA3 Motion Designer
          ADVANCED MOTION
                 |
        +--------+---------+
        |                  |
   CFA3 Webdesign      other CFA3 hosts
```

### OpenCut

CFA3 OpenCut is a standalone and embeddable fast video editor. It is intentionally smaller than CFA3 Video Editor.

Primary scope:
- fast trim/split/move/reframe;
- captions and quick audio adjustments;
- fast preview/export;
- quick variants;
- typed programmable edit operations;
- embedded use by CFA3 Webdesign and compatible CFA3 hosts.

OpenCut is **not**:
- the sole/full NLE;
- a second global timeline authority;
- a second render/resource/model/workflow authority.

The historical OpenCut upstream/provider remains architecture/reference/optional-adapter input. CFA3 OpenCut is the CFA3-native application identity.

### OpenVid Shared

CFA3 OpenVid Shared is the common fast-composition application for:
- screen/demo composition;
- canvas and overlays;
- device/browser mockups;
- picture-in-picture;
- simple camera zoom/pan/tilt/rotate;
- local-first preview/export;
- editable `.fa3openvid` composition references.

OpenCut exposes it through **OpenVid Composer Plugin / embedded workspace**. OpenVid remains the shared owner; it is not absorbed into OpenCut.

Default handoff is an editable composition reference. Flatten/render is explicit.

The historical PolyForm Noncommercial OpenVid upstream remains reference/pattern input only. No vendoring or commercial runtime admission is implied.

### Motion Designer

The existing Animation / Character Motion Studio application identity evolves into **CFA3 Motion Designer / Animation Studio**.

It owns advanced motion semantics:
- deterministic evaluate(t) timeline;
- layer + node composition;
- procedural expressions;
- reusable components/variants;
- state machines;
- responsive motion/layout;
- advanced typography;
- tracking/roto/keying where bound to admitted shared fabrics;
- 2D/3D motion;
- Motion QA and advanced motion handoff.

OpenCut and OpenVid may embed Motion Designer workspaces but do not duplicate its advanced motion engine.

### Webdesign integration

When CFA3 Webdesign is materialized, its video/motion boundary is:

```text
Webdesign
  -> Edit Video -> CFA3 OpenCut
      -> optional OpenVid Composer
      -> optional Advanced Motion -> CFA3 Motion Designer
  -> web-optimized media variants
  -> page/CMS project remains Webdesign authority
```

Webdesign does not create another video editor, FFmpeg core, motion engine, or render authority.

## Shared execution / authority boundaries

- CFA3 Video Editor: sole full NLE.
- `FA3-PROGRAMMABLE-VIDEO-EDITING-001`: shared programmable-editing contract/fabric, not an application.
- OpenTimelineIO: editorial interchange/projection, not native project-state authority.
- MLT + CFA3 Native Media Composition: shared execution engines.
- FFmpeg: CFA3-wide shared media runtime/executor.
- HRB: resource/device authority.
- Model Router: model/provider authority.
- Temporal: durable workflow authority.
- Central MCP Gateway + UAF: effectful operation mediation.
- License & Rights: rights authority.
- SCS: supply-chain authority.
- Evidence: proof/provenance authority.
- Workload Mode Framework: mandatory workload-mode coordination.

## Existing donor usage boundary

This redesign may use only already-published canonical donor/reference records for planning/patterns. No new donor intake is created.

Relevant existing planning inputs include:
- `FA3-DONOR-OPENCUT-001`;
- canonical FFmpeg donor/reference record;
- canonical OpenTimelineIO donor/reference record;
- `FA3-DONOR-OPENIMAGEIO-001`;
- `FA3-DONOR-TESTZEUS-HERCULES-001` for QA/reference patterns.

Donor status is never runtime/code-import permission.

**SDK registration: none.**

## Archived / superseded OpenCut semantics

The following historical semantics remain preserved as lineage/evidence but are **not active target architecture**:

1. PR #45 wording that OpenCut is a required adapter rather than a standalone CFA3 FAST EDIT application.
2. `KDENLIVE_REMAINS_PRIMARY_HUMAN_FINISHING_NLE`.
3. OpenCut as future exclusive/primary CFA3 editor backend.
4. OpenTimelineIO interpreted as native CFA3 project-state authority rather than interchange.
5. Any separate OpenCut SDK workstream.
6. Any plan that creates a second editor authority, second MCP authority, second scheduler, second HRB, second Model Router, or second FFmpeg core.
7. Any OpenVid design that exists only as an OpenCut-owned plugin instead of a shared application.
8. Any OpenVid advanced-motion implementation that duplicates Motion Designer.
9. Any Webdesign-local video editor/motion engine that duplicates OpenCut/OpenVid/Motion Designer.

Historical PRs, immutable upstream pins and evidence are retained; only active semantics are superseded.

## PR lineage redesign requirements

- **#45**: historical OpenCut materialization preserved; active provider/decision/profile semantics must reconcile to this final model when the shared release-projection writer is free.
- **#69**: historical OpenVid evidence preserved; active role becomes CFA3 OpenVid Shared.
- **#422**: editable-video journey must target CFA3 Video Editor as primary editor; Kdenlive is compatibility; OpenVid is optional composition stage.
- **#510**: QuickClip planning keeps short-form automation and removes any duplicate generic compositing/motion core.
- **#613**: generation fabric remains CAP-159/CAP-160 owner; only artifact handoff to OpenVid/OpenCut.
- **#638**: MLT remains execution backend; Kdenlive-owner wording must be reconciled; OpenCut/OpenVid are consumers, not backend authorities.
- **#640**: Motion/Video Quality remains technical motion/render/QC fabric; CFA3 Motion Designer owns advanced motion application semantics.
- **#643**: superseded-pending by #646; must not receive duplicate application records.
- **#646**: sole application-portfolio/entitlement lineage for OpenCut/OpenVid/Motion Designer identities.
- **#668**: GUI governance must support standalone + embedded OpenCut/OpenVid/Motion Designer surfaces after its current review blockers are resolved.

## Current Host boundary

This architecture reconciliation does not attempt Current Host closure, physical requalification or inherited PASS. Current Host remains outside this FIFO application redesign task until the historical blocker chain is resolved.

## Fixed invariants

- capability baseline: **175**
- capability delta: **0**
- architectural authority delta: **0**
- new donor intake: **0**
- SDK registration: **0**
- automatic runtime/provider/model admission: **0**
- historical evidence deletion: **0**
