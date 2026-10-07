# FA3 GUI current-host closure

The Control Center reference/static build is not physical runtime evidence. GUI runtime promotion requires a real local graphical session on the exact `[self-hosted, linux, x64, fa3-current-host]` runner.

The **physical desktop smoke is manual-only** via `workflow_dispatch`. Pull-request and push activity may run materialization/headless checks, but must not launch a visible Control Center window on the operator workstation. A fresh physical run is requested only when current-host GUI requalification evidence is intentionally needed.

The closure is fail-closed:

1. check out the exact PR/source SHA;
2. run as the non-root runner user;
3. discover an active local Wayland or X11 session using the existing desktop-admission substrate;
4. configure and build `apps/fa3-control-center` from that same source SHA without package installation or network-fetch helpers;
5. force the native Qt platform for the proven session (`wayland` or `xcb`); `offscreen` and `minimal` are forbidden;
6. launch the real `fa3-control-center` process for at least five seconds;
7. require the process to remain alive and free of fatal Qt/QML startup markers;
8. terminate and clean up the probe process;
9. emit a secret-free, hashed-host-fingerprint receipt;
10. validate the receipt with `FA3-GUI-CURRENT-HOST-GATESET-001`.

A PASS receipt may promote **FA3 GUI current-host runtime conformance only**. It does not promote the whole FA3 release, create authority, or bypass the 19-criterion global promotion gate.

The canonical receipt path is `evidence/receipts/fa3-gui-current-host.json`. Until a physical PASS receipt is adopted, `FA3-GUI-RUNTIME-CONFORMANCE-001` remains non-production and fail-closed.


## Secret Backend authority separation

Physical Control Center process/runtime proof and Secret Backend admission are separate authority domains.

The GUI current-host receipt requires the Linux/XDG/D-Bus/URI/local graphical-session prerequisites to pass. A full Desktop Admission failure may be scoped out **only when its sole failed required logical capability is `secret_backend`**. The receipt must preserve that failure as `secret_backend_status=FAIL`, record `secret_backend_used_for_gui_runtime_admission=false`, and identify the separate secrets capability owner as `CAP-003`.

This exception does not convert a missing Secret Service or FA3 Vault into PASS. Any GUI operation that requires secret access remains fail-closed behind the existing secrets/session-vault authority and evidence chain. A GUI current-host PASS therefore proves the Control Center can build and execute in the real desktop session; it does not prove or promote Secret Backend availability.

### Tested startup path

The current physical process-smoke is intentionally scoped to
`CONTROL_CENTER_STARTUP_SESSION_VAULT_UNCONFIGURED`. The exact same-source
`fa3-control-center` binary is launched in the real native desktop session, but
`FA3_SESSION_VAULT_IMAGE` is bound to a probe-owned path that is proven absent
before and after the smoke. This exercises the supported `SessionVaultService`
`!configured()` startup branch, which returns before the optional
`secret-tool` lookup.

The receipt therefore records `secret_backend_status` exactly as observed,
`secret_backend_required_for_tested_path=false`,
`secret_backend_authority=AUTH-SECRETS`,
`secret_backend_capability=CAP-003`, and
`secret_backend_pass_claimed=false`. A configured-vault unlock/store path is
outside this GUI process-start proof and remains separately fail-closed behind
the existing Secret Backend / Session Vault evidence chain.

If the Control Center startup implementation changes so that the non-configured
vault path can touch Secret Backend before the guard, the materialization gate
fails and a new physical proof scope is required.
