# FA3 Generative Media Studio

This is the native Qt6/QML materialization of the existing **CAP-111 Generative Media Studio & Creative Workflow Control Surface**.

## What it does

The Studio compiles provider-neutral creative requests for image, video, lip-sync and character-animation workflows. It deliberately does **not** call a provider, pin a model, allocate an accelerator, inject credentials, or claim runtime success.

The compiled request is written atomically below the Qt StateLocation projection:

    fa3/generative-media-studio/requests/<request-id>.json

The request remains PENDING_ADMISSION until downstream FA3 authorities process it.

## Execution boundary

    Studio
      -> UAF authorization/action handoff
      -> Model Router
      -> HRB
      -> admitted provider
      -> validation/evidence
      -> editor/asset handoff

Provider/model labels are read-only downstream projections.

## Shot duration

The self-contained video-shot UI exposes **6..20 seconds**. This is an application interaction range, not a global provider limit. An admitted provider may support a narrower or broader range; projection/admission remains fail-closed.

## Build

    cmake -S apps/fa3-generative-media-studio -B build/fa3-generative-media-studio
    cmake --build build/fa3-generative-media-studio

Requirements: Qt 6.5+ Core, Gui, Qml, Quick and QuickControls2.

## Hardware Audit

The application is vendor-neutral and CPU-only viable as a request compiler. Accelerator inventory is 0..N; the GUI never performs accelerator placement or selection. Any accelerator-backed execution is admitted and leased by HRB downstream.

## Donor policy

The Autom8AI account is used only as discovery input. The canonical donor reference records original upstream repositories and immutable revisions. This implementation does not import donor source code.
