# LynxHub user-session deployment assets

These files materialize `FA3-PROVIDER-LYNXHUB-001` around an existing verified `lynxhub` Debian installation.

- `systemd/user/lynxhub.service`: single on-demand dashboard unit; not enableable.
- `systemd/user/ai-creative-ops.target`: optional desktop-session grouping target.
- `bin/lynxhub-launch`: Wayland-first, sandbox-preserving Electron launcher.
- `bin/lynxhub-start`: argument-free desktop entry bridge.
- `bin/lynxhub-action`: fixed action-ID allowlist; no free-form shell.
- `applications/*.desktop.in`: per-user effective launcher overriding the vendor `--no-sandbox` entry.
- `lynxhub-actions.env.example`: non-secret loopback dashboard URLs only.

Use `bin/fa3-lynxhub-install-user-integration.sh` from the repository root. Full policy, verification and rollback instructions are in `docs/lynxhub-integration.md`.
