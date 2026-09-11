# Kdenlive + OpenFX FA3 integration

Kdenlive remains the primary human editorial frontend, OTIO interchange surface and final picture-lock authority. OpenFX is not treated as a native Kdenlive backend.

Kdenlive's native effect path remains MLT with Frei0r and FFmpeg/avfilter surfaces. An OpenFX effect is admitted only through an explicitly selected OpenFX-compatible external host, producing a hash-addressed intermediate artifact that is relinked/imported into Kdenlive. The OpenFX host and plugin do not own timeline semantics, workflow, resource admission, evidence, artifact registry or human editorial approval.

Required handoff metadata includes source and derived artifact hashes, plugin bundle/API/host ABI identity, parameter digest, frame range, FPS/timebase, alpha mode, pixel format, color/OCIO metadata, HRB lease identity when accelerated, FFprobe validation and rollback artifact identity.

Missing host/plugin, ABI mismatch, license/path admission failure, network fetch during render, or incomplete metadata fails closed. Direct external mutation of Kdenlive XML remains forbidden; critical editorial changes require human approval.

The current-host collector is deliberately readiness-only. A real production E2E receipt is still required before runtime admission.
