# LynxHub integration

`FA3-PROVIDER-LYNXHUB-001` is an optional, replaceable Creative Operations Dashboard projected only to `CAP-057`. It is a local presentation and approved-launch surface; it is not an orchestrator, MCP gateway, model manager, package manager, service authority, database or secrets store.

## Immutable baseline

- LynxHub: `V3.5.8`, source commit `96129c218b8bd4337fd3e4cf220aa97a46c486a5`
- Debian artifact: `LynxHub-V3.5.8-linux_amd64.deb`
- SHA-256: `b13882eb5d0443b84bd8c2488c659a149c5b16e15f22fad93aa6ad3c5f33a435`
- Debian identity: package `lynxhub`, version `3.5.8`, executable `/opt/LynxHub/lynxhub`
- Custom Actions when action cards are used: `v0.4.4`, commit `418be2f8d2488f67f8c6f7728729161577f4c90e`, artifact SHA-256 `125c3382393ef32bde5d1eae415a7a7829493e0d77504f02e6f72fc85bb6ef83`

The current-host Debian installation is user-reported. Static conformance does not independently verify that installation and does not promote the provider runtime.

## Canonical boundaries

The normative path is:

```text
LynxHub dashboard
  -> approved fixed action ID
  -> version-controlled FA3 wrapper
  -> approved local UI or enumerated systemd --user unit
  -> Open WebUI / Goose / Orchestrator
  -> Temporal
  -> policy-mediated MCP and workers
```

Direct LynxHub-to-MCP tools, direct Ollama agent execution, arbitrary shell actions, `sudo`/`su`/`pkexec`, root `systemctl`, `apt`/`dpkg`/`nft`, secret or database access and Stability Matrix package management are denied.

Ownership remains unchanged:

| Concern | Authority |
| --- | --- |
| Host and platform services | systemd and existing FA3 lifecycle authority |
| ComfyUI/InvokeAI/Forge/Wan2GP packages | Stability Matrix |
| Human LLM and agent clients | Open WebUI and Goose |
| Workflow execution and durability | FA3 Orchestrator and Temporal |
| Tools and MCP policy | Central MCP/Capability Gateway |
| Logs, receipts and promotion evidence | Unified Observability/Evidence |
| Dashboard cards and approved launch requests | LynxHub adapter only |

LynxHub's `lowdb` content is application state only. It is never canonical workflow, memory, evidence or registry state.

## Debian-package hardening correction

The upstream `V3.5.8` Debian desktop entry invokes `/opt/LynxHub/lynxhub --no-sandbox %U`. FA3 does not modify the vendor package payload, but installs a higher-precedence per-user desktop entry that starts `lynxhub.service`. The service executes the FA3 launcher without `--no-sandbox`, with `NoNewPrivileges=yes` and systemd hardening. A current-host runtime PASS is forbidden if the effective launcher or running process still contains `--no-sandbox`.

There is one named on-demand user unit: `lynxhub.service`. It is associated with `ai-creative-ops.target` but deliberately has no `[Install]` section, so it cannot become a second automatic startup path. KDE-generated `app-lynxhub@*.service` instances and desktop autostart entries must not run in parallel.

## Materialized user integration

Install or reconcile the user-scoped adapter without changing the Debian package:

```bash
./bin/fa3-lynxhub-install-user-integration.sh --install
./bin/fa3-lynxhub-install-user-integration.sh --check
```

The installer does not start or enable LynxHub. It installs three fixed wrappers, two user-unit files, a per-user desktop override and a non-secret loopback URL example. Configure only loopback URLs in `~/.config/fa3/lynxhub-actions.env`.

Custom Actions cards may call only:

```text
~/.local/libexec/fa3/lynxhub-action open-webui
~/.local/libexec/fa3/lynxhub-action open-comfyui
~/.local/libexec/fa3/lynxhub-action open-invokeai
~/.local/libexec/fa3/lynxhub-action open-omnivoice
~/.local/libexec/fa3/lynxhub-action start-goose
~/.local/libexec/fa3/lynxhub-action start-creative-stack
~/.local/libexec/fa3/lynxhub-action platform-status
```

Unknown action IDs and non-loopback URLs fail closed. Do not embed shell pipelines or package/update commands in LynxHub cards.

## Plugin disposition

| Plugin | Disposition |
| --- | --- |
| Custom Actions | Pinned and required only when action cards are used |
| Hardware Monitor | Optional presentation; never observability authority |
| Python Toolkit | Disabled by default |
| Local AI Collection | Disabled; Stability Matrix remains package owner |
| Skills Manager | Separately admitted pilot only |
| Automatic plugin updates | Disabled |

## Verification and promotion

Static/reference checks:

```bash
./bin/fa3-enforce lynxhub
PYTHONPATH=src python -m unittest tests.test_lynxhub_gate -v
```

Current-host evidence collection is read-only and must run in the real Wayland session. Supply the original `.deb` and pinned Custom Actions archive when available:

```bash
python evidence/collect-lynxhub-current-host.py \
  --deb /path/to/LynxHub-V3.5.8-linux_amd64.deb \
  --custom-actions /path/to/0.4.4.7z \
  --output evidence/current-host/lynxhub-current-host.json
```

The collector does not install, start, stop or reconfigure anything. Runtime promotion also requires a human-observed Wayland UI/action smoke, bypass-negative results, OpenSnitch/default-deny evidence, clean stop and rollback receipt.

Rollback of the FA3 user adapter preserves the Debian package and LynxHub data:

```bash
./bin/fa3-lynxhub-install-user-integration.sh --uninstall
```
