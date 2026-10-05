# SillyTavern KDE6/Wayland integration

## Canonical decision

`FA3-PROVIDER-SILLYTAVERN-KDE-001` is an optional, replaceable, non-authoritative local conversation desktop client projected only to `CAP-008` (Agent Workspace). It adds no capability and no architectural authority; the canonical capability count remains 143.

The upstream SillyTavern 1.18.0 release already contains an Electron desktop wrapper. Its entrypoint starts the SillyTavern server in the desktop lifecycle, waits for the server-start event, receives the actual URL, and loads that URL into `BrowserWindow`. FA3 therefore uses the upstream Electron wrapper rather than maintaining a second PySide6/QWebEngine browser wrapper.

## Conversation reconciliation

Accepted and normalized:

- KDE6 application-menu integration and an on-demand `systemd --user` service.
- Wayland-first desktop launch, with an explicit exception path rather than an X11 default.
- Optional tray/global-shortcut presentation as user preference, not architectural state.
- Optional push-to-talk only through existing FA3 STT/TTS authorities.
- Read-only CPU/RAM/GPU/runtime telemetry; Host Resource Broker remains placement/admission authority.
- Human-approval presentation for side-effectful actions; policy and tool authorization remain external to this client.

Rejected or reframed:

- BLACKHOLE/SINGULARITY/EVENT HORIZON/ASCENSION as a new AI OS, kernel, global orchestrator or scheduler.
- Prompt-keyword routing or RAM/VRAM-percentage heuristics as canonical model-routing policy.
- Direct GUI spawning/ownership of Oobabooga, KoboldCpp or other model runtimes.
- A second canonical memory/vector-store authority.
- Temporary-file subprocess execution represented as a security sandbox.
- Free-form shell execution or privileged `sudo`, `pkexec`, root `systemctl`, `apt`, `dpkg`, or `nft` actions.
- Fixed `/opt/SillyTavern`, `$HOME/AI`, fixed server port, GPU model or GPU-count assumptions.
- Dependency installation during ordinary desktop launch.

## Upstream pin

The admitted reference is:

- repository: `SillyTavern/SillyTavern`
- release: `1.18.0`
- commit: `51ad27fb86d39a3daca3adaa970375c9670c12df`
- license: `AGPL-3.0`
- Electron entrypoint blob: `6126ef45ca881e30e7fceb134270dfb52d883b4b`
- Electron lockfile blob: `de71cacfc097733f36d79f103bfd9fb2686778a6`

The upstream `src/electron/start.sh` installs dependencies before launch. FA3 intentionally does not use that script as the normal runtime launcher. Dependency preparation is a separate, explicit admission action.

## Installation on a KDE6 host

1. Prepare an exact checkout of SillyTavern at the admitted commit.
2. Install only the FA3 user integration:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --install
   ```

3. Edit `~/.config/fa3/sillytavern-kde.env` and set `SILLYTAVERN_ROOT` to that checkout.
4. Explicitly prepare the lockfile-resolved Electron dependencies:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --prepare-deps
   ```

5. Validate installed integration files:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --check
   ```

6. Start from the KDE application menu (`SillyTavern (FA3 KDE)`) or invoke:

   ```bash
   systemctl --user start sillytavern-kde.service
   ```

The unit has no `[Install]` section and is not enabled at login. A KDE global shortcut may be configured by the user to call `~/.local/libexec/fa3/sillytavern-kde-start`; no canonical fixed key binding is imposed.

## Current-host promotion

Repository/reference conformance is not current-host production evidence. Promotion requires a real KDE6/Wayland E2E receipt proving the pinned source and dependencies, Electron launch, event-derived loopback URL, mutation-free normal start, authority-bypass negative cases, extension denial, optional voice/telemetry delegation where enabled, clean stop and rollback.
