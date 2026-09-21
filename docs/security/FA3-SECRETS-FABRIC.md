# FA3 Encrypted Secrets Vault + Secret Broker

## Decision

FA3 tokens, API keys, OAuth secrets, external-provider login secrets, service/database/SMTP passwords, MCP/provider credentials and equivalent authentication material use the P0/MUST profile `FA3-SECRET-BROKER-001`. The canonical local store is a separate LUKS2 image at the intentionally generic, non-disclosing path `/var/lib/fa3/state/fa3-machine-state.img`. Its external name MUST NOT reveal that it contains credentials. It is not the user Session Vault and it does not create a new secrets, identity, authorization, orchestration or evidence authority.

The existing `FA3-SESSION-VAULT-001` remains user-session custody for the offline Root CA and session state. New raw machine/application credentials must not be stored in that user-mounted image.

The vault content scope is **credential secrets only**. Cache data, model data, project files, documents, telemetry, general configuration and ordinary application state are forbidden. Non-secret identity metadata such as provider name or username belongs in normal provider/application configuration; only the sensitive credential value belongs in the encrypted vault.

## Lifecycle

`fa3-secrets.target` is the lifecycle projection. Start order: encrypted credential materialization → LUKS2 open → hardened ext4 mount → unprivileged broker → secret-dependent providers. Stop order is reversed. If open, mount, policy admission or broker access fails, secret-dependent providers fail closed. There is no plaintext config, `.env`, command-line or silent fallback.

The default machine-state unlock source is `LoadCredentialEncrypted=fa3-machine-state-key:...`. TPM2, FIDO2/PKCS#11 and removable recovery mechanisms are optional higher-assurance choices, not global hardware requirements.

## Access model

Consumers use `SecretReference`; they never receive the full vault mount. The broker listens only on a local Unix domain socket and verifies Linux peer credentials using `SO_PEERCRED`. Each secret has an explicit policy binding consumer identity, Unix service identity and optional executable/systemd-unit constraints to allowed projection types.

Machine/service secrets require dedicated service identities. Processes running under the same desktop Unix UID share the OS-user trust boundary; FA3 must not claim strong isolation against a malicious same-UID process. Human-managed credentials may remain in an admitted human credential-vault provider such as Vaultwarden, but that provider is not the machine secret broker.

## Delivery

File/FD-based delivery is the default. systemd credentials are supported. Rootless Podman integration uses `type=mount` secret delivery by default. Secret-to-environment projection is forbidden by the canonical default. Bulk export and full-vault bind mounts are forbidden. Infisical remains an optional backend provider under the same broker boundary: targeted secret retrieval only, never a parallel secrets authority. Podman is a delivery adapter; its default secret store is not described as RAM-only unless separate current-host evidence proves that property.

The broker audit contains only operation metadata and a SHA-256 of the SecretRef identifier. Raw values are excluded from Git, canonical records, Journal, telemetry, logs and evidence.

## Backup and recovery

The closed LUKS2 image can be copied opaquely to user-selected backup storage. Recovery is not PASS until a copy is independently opened read-only and the restored broker health check succeeds. The unlock secret is never stored in the same image.

## Vault service capability boundary

The privileged vault service retains only the Linux capabilities required by its existing mechanics: `CAP_SYS_ADMIN` for dm-crypt/mount operations, `CAP_CHOWN` for assigning the mounted vault root to the broker identity, and `CAP_FOWNER` for enforcing the vault-root mode after ownership assignment. Broader capability sets are forbidden. The unprivileged broker service retains an empty capability bounding set.

Current-host systemd lifecycle failures are fail-closed and self-diagnosing: the E2E prints bounded `systemctl status` output and at most 120 relevant journal entries for the vault and broker units before cleanup. No raw secret values are intentionally emitted by these diagnostics.

## Hardware and desktop audit

No NVIDIA, CUDA, GPU, NPU, accelerator SKU or topology is required. The core is headless-capable and has no canonical KDE, GNOME, Wayland, X11 or other desktop/display-server dependency. Any desktop unlock or management UI is an optional adapter and cannot become a prerequisite for the secrets core.

## Promotion boundary

Repository/reference PASS does not promote production runtime. Promotion requires a real current-host receipt proving LUKS2, mount flags, unprivileged broker execution, authorized access, unauthorized denial, no argv/environment/audit leakage, explicit cleanup, and backup/restore broker health. Provider/runtime PASS does not imply global FA3 promotion.

## FA3 exit semantics

A teljes FA3 kilépés nem azonos egy GUI-ablak bezárásával. A secrets lifecycle lezárását a `/usr/local/sbin/fa3-secrets-lifecycle exit` művelet végzi: leállítja a `fa3-secrets.target` egységet, majd fail-closed módon ellenőrzi, hogy maga a target, a broker és a vault service is inaktív, a `/run/fa3/machine-state` mount eltűnt, és a `fa3-machine-state` LUKS mapper bezárult. Az FA3 csak ezen postconditionök teljesülése után tekinthető teljesen kilépett állapotúnak.

A `fa3-secret-vault.service` külön `ExecStopPost` ellenőrzést is futtat. Ha az unmount vagy a LUKS close nem teljesül, a shutdown nem kaphat PASS állapotot.


## Operator operations

The only documented administrative entry point is `fa3-secrets-admin`. It covers initialization, start/status/health, credential put/rotate/revoke, metadata-only listing, policy validation/install/remove/show/list, opaque backup/restore, and fail-closed exit/assert-closed.

Rotation preserves the existing classification and secret kind by default; a rotation cannot silently change either. Revocation removes the active secret object before removing its index entry. Bulk secret export does not exist. Administrative listing exposes only SecretRef metadata and never raw values.

Exactly one active projection policy is permitted per SecretRef. Duplicate policy definitions deny access fail-closed. Policy filenames are SHA-256-derived and non-disclosing.

Backup requires the secrets lifecycle to be CLOSED. Restore validates LUKS2, starts the restored runtime only long enough to prove broker health, then executes the normal FA3 secrets exit path and finishes in CLOSED state. A failed restore rolls back the previous encrypted image and remains closed.


## Unlock credential and rekey

The canonical automatic unlock credential uses `systemd-creds --with-key=host`. The default must not use implicit `auto` TPM2 binding, because hardware discovery may not silently alter the canonical portability contract. TPM2, FIDO2 and PKCS#11/HSM unlock mechanisms remain explicit optional higher-assurance adapters.

The LUKS2 unlock passphrase can be rotated through `fa3-secrets-admin rekey`. Rekey requires the secrets lifecycle to be CLOSED. It uses a two-phase keyslot transition: add and verify the new key, materialize and verify the new encrypted systemd credential, prove start/health/exit, then remove the old key and verify that it no longer unlocks the image. A successful rekey always ends in CLOSED state. Current-host promotion requires real evidence of this sequence.

Cross-host disaster recovery is not implied by an encrypted image backup alone. With the canonical `systemd-creds --with-key=host` default, automatic restore is scoped to the same systemd host-credential domain. Cross-host DR requires a separate explicitly admitted recovery-credential adapter; that recovery credential must remain outside the encrypted image.


## Current-host privileged bridge

The GitHub Actions current-host runner remains non-root. The Secret Broker physical LUKS2/systemd closure must not call general `sudo` from a workflow.

The supported boundary is:

```text
non-root fa3-current-host runner
        |
        v
/usr/local/bin/fa3-secret-broker-current-host-bridge
        |
        | sudo -n, exact command only, no arguments
        v
/usr/local/libexec/fa3-secret-broker-current-host-root
        |
        v
root-owned immutable package
/usr/local/lib/fa3/current-host-secret-broker
```

The installer writes a sudoers rule for exactly one root-owned helper and explicitly forbids general passwordless sudo. The helper accepts no arguments. The installed E2E package is produced from a Git archive of one exact commit and records that commit in `SOURCE_COMMIT`.

The non-root bridge client compares the current checkout commit with the installed source binding before any privileged execution. Physical evidence contains `bridge_source_commit` and the `current_host_privileged_bridge_source_binding_pass` check. Source drift therefore fails closed and requires rerunning the current-host runner bootstrap from the intended commit.

The privileged helper writes only sanitized current-host evidence to the fixed runtime handoff directory `/run/fa3/current-host-secret-broker`. It does not expose raw token/password values or provide a general-purpose privileged execution interface.


## Dedicated current-host admin probe

The physical Secret Broker E2E does not rely on a root peer being interpreted as broker admin over the Unix socket. Broker mutations are exercised through a dedicated temporary non-root identity named `fa3-sb-admin-probe`.

The test creates that identity only when it does not already exist, requires membership in both `fa3-secret-admin` and `fa3-secret-clients`, performs the administrative put/rotate/revoke/metadata operations through that identity, and executes the credential-scope negative probe through the same authorized admin identity.

A pre-existing `fa3-sb-admin-probe` causes fail-closed termination. The probe identity is removed before the PASS receipt is written, and the current-host receipt requires both `non_root_admin_authorization_pass` and `ephemeral_admin_probe_removed_pass`.

This preserves the separation between the root-only host mechanics needed for LUKS2/systemd tests and the broker's own SO_PEERCRED/group-based administration boundary.
