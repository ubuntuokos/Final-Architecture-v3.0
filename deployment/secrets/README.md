# FA3 encrypted secrets runtime

The FA3 credential-secret store is a separate LUKS2 image at `/var/lib/fa3/state/fa3-machine-state.img`. The external image name is intentionally generic and MUST NOT disclose that credentials are stored inside. It is opened only while `fa3-secrets.target` is active. The raw mount is owned by `fa3-secret-broker`; consumers never receive the full mount.

Only credential secrets belong here: tokens, API keys, OAuth secrets, external-provider login secrets, service/database/SMTP passwords, MCP/provider credentials and equivalent authentication material. Cache, project data, model data, documents, telemetry, general configuration and ordinary application state are out of scope.

Install creates the service identities `fa3-secret-broker`, `fa3-secret-clients`, and `fa3-secret-admin`, installs the units/scripts, initializes the image once with `sudo bin/fa3-secret-vault-init`, and then starts/stops the lifecycle with `sudo systemctl start|stop fa3-secrets.target`.

Policies live in `/etc/fa3/secret-policy.d/*.json` and contain no secret values. Add/update secret values only through `fa3-secretctl put` using an interactive prompt or stdin. Never pass a secret in argv or environment variables.

Machine/service secrets require a dedicated Unix service identity. Same-UID desktop applications share the OS-user trust boundary; FA3 does not claim strong malicious-process isolation between processes running as the same Unix UID.

Podman delivery uses secret file mounts by default; environment-variable secret projection is forbidden unless an explicit non-default exception policy is admitted.

Full FA3 exit must execute `sudo /usr/local/sbin/fa3-secrets-lifecycle exit`. This stops `fa3-secrets.target` and refuses to report a completed exit while the broker or vault service is active, the runtime mount still exists, or the LUKS mapping remains open. Closing a GUI window alone is not the canonical full-FA3 exit signal.


## Operator workflow

After one-time installation, use only the unified operator entry point:

```bash
fa3-secrets-admin help
```

The deterministic lifecycle is:

```text
init -> start -> policy-install -> put/use/rotate/revoke -> exit -> backup/rekey/restore as needed -> assert-closed
```

One-time initialization creates the generic/non-disclosing LUKS2 image and its encrypted systemd unlock credential:

```bash
fa3-secrets-admin init
```

Start and verify the secrets runtime:

```bash
fa3-secrets-admin start
fa3-secrets-admin health
fa3-secrets-admin status
```

Projection policy contains metadata only and may be checked before installation:

```bash
fa3-secrets-admin policy-check provider-policy.json
fa3-secrets-admin policy-install provider-policy.json
```

Store a new token or password interactively; the secret value is entered through the terminal prompt and is never an argv argument:

```bash
fa3-secrets-admin put provider/example --kind API_TOKEN
```

Rotate a stored credential value without changing its classification or secret kind:

```bash
fa3-secrets-admin rotate provider/example
```

Inspect administrative metadata only:

```bash
fa3-secrets-admin metadata provider/example
fa3-secrets-admin list
```

Revoke the active credential:

```bash
fa3-secrets-admin revoke provider/example
```

A backup is permitted only with the vault closed. The default backup image name remains generic and non-disclosing:

```bash
fa3-secrets-admin exit
fa3-secrets-admin assert-closed
fa3-secrets-admin backup
```

Restore validates LUKS2, temporarily starts the restored runtime for broker-health validation, and then closes it again. Successful restore therefore finishes in CLOSED state:

```bash
fa3-secrets-admin restore /var/backups/fa3/fa3-machine-state-YYYYMMDDTHHMMSSZ.img
fa3-secrets-admin assert-closed
```

Bulk secret export does not exist. `list` returns SecretRef metadata only and is administrative. Secret values are retrieved only through an admitted consumer projection.

Exactly one active projection policy may exist for a SecretRef. Duplicate policies fail closed; there is no first-match-wins behavior. Policy filenames are hash-based and do not disclose provider or credential names.

For a machine/service SecretRef, the dedicated provider Unix user must be a member of `fa3-secret-clients`. The consuming provider unit must also use `PartOf=fa3-secrets.target` (in addition to requiring its projection unit) so full FA3 exit stops the provider before the vault is unmounted and the LUKS mapping is closed.


## Unlock-key rotation

The default encrypted systemd unlock credential is created with `systemd-creds --with-key=host`. This is deliberate: the canonical default must not silently become TPM2-bound on hosts where a TPM2 happens to exist. TPM2/FIDO2/PKCS#11 remain explicit optional adapters.

Rekey is a closed-vault operation:

```bash
fa3-secrets-admin exit
fa3-secrets-admin assert-closed
fa3-secrets-admin rekey
fa3-secrets-admin assert-closed
```

The rekey flow adds the new LUKS2 keyslot first, verifies the new encrypted systemd credential, proves a real start/health/exit cycle with the new credential, removes the old keyslot, proves the old key no longer unlocks the image and the new key does, and finishes with the vault closed. Plaintext rekey material exists only transiently under root-only `/run` tmpfs paths and is removed before PASS.
