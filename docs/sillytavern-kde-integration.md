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

## Upstream pin and dependency identity

The admitted reference is:

- repository: `SillyTavern/SillyTavern`
- release: `1.18.0`
- commit: `51ad27fb86d39a3daca3adaa970375c9670c12df`
- license: `AGPL-3.0`
- root `package-lock.json` blob: `95b4dbc33c62829e2aff383f286889ebdcc15ffd`
- root `.npmrc` blob: `2143f3df2fc935fce293d1ee5b3c073fd187e135`
- Electron entrypoint blob: `6126ef45ca881e30e7fceb134270dfb52d883b4b`
- Electron lockfile blob: `de71cacfc097733f36d79f103bfd9fb2686778a6`

The root `.npmrc` at the admitted commit sets `ignore-scripts=true` and `min-release-age=7`. The upstream `src/electron/start.sh` installs dependencies before launch; FA3 intentionally does not use that script as the normal runtime launcher.

The explicit `--prepare-deps` admission now prepares **both** dependency surfaces: the root SillyTavern server runtime using the immutable root lockfile and the Electron wrapper using its own immutable lockfile. Normal launch performs no npm installation or update.

## Installation on a KDE6 host

1. Prepare an exact checkout of SillyTavern at the admitted commit.
2. Install the FA3 user integration:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --install
   ```

3. Set `SILLYTAVERN_ROOT` in `~/.config/fa3/sillytavern-kde.env`.
4. Explicitly prepare the admitted server + Electron dependencies:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --prepare-deps
   ```

5. Validate the installed integration:

   ```bash
   bin/fa3-sillytavern-kde-install-user-integration.sh --check
   ```

6. Start from the KDE application menu or invoke:

   ```bash
   systemctl --user start sillytavern-kde.service
   ```

The unit has no `[Install]` section and is not enabled at login.

## Current-host production admission

The current-host gate is `FA3-GATE-SILLYTAVERN-KDE-CURRENT-HOST-001`, with conformance record `FA3-SILLYTAVERN-KDE-RUNTIME-CONFORMANCE-001`. It requires the real `[self-hosted, linux, x64, fa3-current-host]` runner and an active KDE6/Wayland user session.

The executable path is:

```bash
bin/fa3-sillytavern-kde-current-host static
bin/fa3-sillytavern-kde-current-host collect
bin/fa3-sillytavern-kde-current-host verify
```

The collector validates the runner and non-root context, exact source/root-lock/npm-policy/Electron identities, Node.js >=20, explicit dependency preparation, Wayland session/socket, `graphical-session.target`, Electron launch without `--no-sandbox`, dynamic listener discovery without assuming a server port, loopback-only exposure, HTTP SillyTavern UI identity, invalid-source refusal, authority boundaries, clean stop, zero resident service processes, uninstall/reinstall rollback, and an inactive service after the rollback drill.

A successful real run writes `evidence/receipts/sillytavern-kde-current-host.json` with status `CURRENT_HOST_PRODUCTION_E2E_PASS`. Reference CI, synthetic receipts, queued jobs, or a runner lacking any required label cannot promote the provider.
