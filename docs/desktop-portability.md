# FA3 Generic Linux desktop portability

## Canonical decision

FA3 uses KDE Plasma on Wayland as its Tier-1 reference desktop, but Plasma is not a core runtime dependency. Portable FA3 desktop code must target the Generic Linux boundary defined by `FA3-DESKTOP-BASE-001`.

The portable boundary is based on XDG paths, the D-Bus session bus, XDG Desktop Portal where available, Secret Service or the approved FA3 vault fallback, and XDG/portal URI opening. Direct KWallet, KIO, KWin private API, or Plasma-private D-Bus dependencies are forbidden in portable core code. Plasma-specific behavior belongs behind an enhancement adapter.

## Support tiers

| Tier | Environments | Semantics |
| --- | --- | --- |
| 1 | KDE Plasma / Wayland | Reference and most deeply validated environment |
| 2 | COSMIC / Wayland, GNOME / Wayland, Cinnamon, XFCE, LXQt | Supported targets through the Generic XDG boundary |
| 3 | Sway, Hyprland, MATE, other XDG-compatible environments | Compatible when the baseline admission probe passes |
| Headless | Linux without a local GUI | Supported when the requested workflow does not require a local GUI |

Wayland is preferred. X11 is a supported compatibility path and must not fail admission solely because the session is X11.

## Required versus optional integration

When a local GUI is required, the admission baseline fails closed if the host lacks Linux, an XDG runtime, a D-Bus session, a URI-opening path, a secret backend, or a local GUI session.

XDG Desktop Portal, notifications, clipboard integration, power inhibition, system tray, global shortcuts, and screen-capture portal support are reported independently. Their absence can reduce integration quality but must not silently disable the FA3 core. In particular, the full FA3 control surface must remain usable without a system tray, and a compositor that does not expose global shortcuts must not make the application unusable.

## Secret handling

Providers must use the FA3 secret broker boundary. A Secret Service implementation such as KWallet or GNOME Keyring may satisfy that boundary. The approved FA3 vault may be used as a fallback. Providers must not bind directly to a desktop-specific wallet API.

For the Tier-1 Plasma reference desktop, FA3 may use a **reference-only D-Bus activation hint** when the installed Secret Service implementation is packaged under a compatibility activation name rather than directly under `org.freedesktop.secrets`. The hint may start the provider, but it cannot satisfy admission by itself: FA3 must subsequently prove the standard `org.freedesktop.secrets` bus name and `org.freedesktop.Secret.Service` interface. The activation hint is not a portable-core dependency, architectural authority, or provider API.

## Appearance

Breeze is the reference Plasma appearance, not a runtime dependency. FA3-owned design tokens define spacing, typography, scaling, icon/control sizing, and light/dark behavior so the UI remains coherent under other desktops and themes.

## Executable checks

Run the deterministic architecture regression gate:

```bash
python3 ./bin/fa3-desktop-admission --self-test --json
```

Probe the current desktop without requiring a GUI:

```bash
python3 ./bin/fa3-desktop-admission --json
```

Require a local GUI baseline and fail closed otherwise:

```bash
python3 ./bin/fa3-desktop-admission --require-gui --json
```

A CI self-test proves the policy and deterministic compatibility cases only. It is not current-host evidence for Plasma, COSMIC, GNOME, or another desktop. A real host support claim requires a runtime probe receipt from that host.
