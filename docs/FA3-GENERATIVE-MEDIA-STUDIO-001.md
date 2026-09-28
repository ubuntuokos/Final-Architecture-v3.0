# FA3 Generative Media Studio

`FA3-GENERATIVE-MEDIA-STUDIO-001` is the native application materialization of the existing **CAP-111 Generative Media Studio & Creative Workflow Control Surface**. It adds no capability and no architectural authority.

## Scope

The first materialized application surface supports provider-neutral requests for:

- text-to-image and image-to-image;
- text-to-video, image-to-video and text/image-to-video;
- speech/audio-driven video;
- lip sync;
- character animation.

The standalone Qt6/QML application lives under `apps/fa3-generative-media-studio`.

## Authority flow

The Studio is a request compiler, not an execution authority:

```text
FA3 Generative Media Studio
  -> Unified Action Fabric authorization/action handoff
  -> FA3 Central Model Router
  -> Host Resource Broker
  -> admitted provider/runtime/model
  -> result validation and Evidence receipt
  -> asset / FA3 Video Editor handoff
```

The GUI cannot pin a physical provider or model, allocate an accelerator, inject a credential, install provider extensions, or claim runtime success.

## Video shot control

The standalone-shot control exposes **6 to 20 seconds**. This is an application interaction range only. Provider capabilities are discovered downstream and may be narrower or broader. Unsupported projection fails closed; no silent fallback is allowed.

## Request artifact

The application atomically writes `fa3.generative-media-studio-request.v1` requests beneath:

```text
$XDG_STATE_HOME/fa3/generative-media-studio/requests/
```

or `~/.local/state/fa3/generative-media-studio/requests/` when `XDG_STATE_HOME` is unset.

The request starts in `PENDING_ADMISSION`. Static application conformance does not promote it.

## Hardware Audit

- vendor-neutral;
- CPU-only request compilation is supported;
- accelerator cardinality is `0..N`;
- no global GPU vendor, SKU, ordinal, runtime or topology is required;
- HRB remains the only resource admission, placement, reservation and lease authority;
- a display accelerator is never silently reused as compute.

## Donor provenance

Autom8AI is treated only as discovery input. The canonical reference set is `FA3-AUTOM8AI-DONOR-REFERENCE-2026-09-28`, which records original upstream repositories and immutable commits.

No third-party donor code is imported by this materialization. Any later code intake requires its own file-level license, security, dependency and distribution admission.

## Verification

Static gate:

```bash
./bin/fa3-generative-media-studio-gate
```

or, when wired through permanent enforcement:

```bash
./bin/fa3-enforce generative-media-studio
```

A static PASS proves only repository/application contract conformance. It does **not** prove a current-host Qt build, provider execution, accelerator execution, or production promotion.
