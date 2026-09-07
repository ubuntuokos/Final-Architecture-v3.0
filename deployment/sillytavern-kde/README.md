# FA3 SillyTavern KDE deployment

This directory materializes the optional SillyTavern KDE6/Wayland desktop client projection.

## Boundaries

- SillyTavern remains an optional, replaceable conversation client and is not an FA3 authority.
- The upstream Electron desktop lifecycle owns the SillyTavern server child process; FA3 does not create a second persistent backend service.
- Normal desktop launch never runs `npm install`, `npm i`, `npm ci`, `pip`, `apt`, or other dependency mutation.
- Electron dependencies are prepared only by the explicit `--prepare-deps` installer action after source-pin validation.
- Wayland is canonical; XWayland requires an explicit admitted exception.
- Model routing, MCP/tool execution, memory, durable workflows, voice, resource placement, secrets and evidence remain owned by their existing FA3 authorities.
- Third-party extensions require separate admission and are never auto-installed or auto-updated by this adapter.

## Files

- `bin/sillytavern-kde-launch`: immutable-source and Wayland preflight, then direct Electron launch.
- `bin/sillytavern-kde-start`: starts the on-demand user service.
- `systemd/user/sillytavern-kde.service`: single user-session lifecycle; no install/autostart target.
- `applications/fa3-sillytavern-kde.desktop.in`: KDE application menu entry.
- `sillytavern-kde.env.example`: host-local source-path and presentation preferences.

Current-host runtime promotion is intentionally not claimed by this deployment materialization. It requires the dedicated current-host E2E and rollback evidence defined by `FA3-SILLYTAVERN-KDE-GATESET-001`.
