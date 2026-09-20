# FA3 encrypted secrets runtime

The FA3 credential-secret store is a separate LUKS2 image at `/var/lib/fa3/state/fa3-machine-state.img`. The external image name is intentionally generic and MUST NOT disclose that credentials are stored inside. It is opened only while `fa3-secrets.target` is active. The raw mount is owned by `fa3-secret-broker`; consumers never receive the full mount.

Only credential secrets belong here: tokens, API keys, OAuth secrets, external-provider login secrets, service/database/SMTP passwords, MCP/provider credentials and equivalent authentication material. Cache, project data, model data, documents, telemetry, general configuration and ordinary application state are out of scope.

Install creates the service identities `fa3-secret-broker`, `fa3-secret-clients`, and `fa3-secret-admin`, installs the units/scripts, initializes the image once with `sudo bin/fa3-secret-vault-init`, and then starts/stops the lifecycle with `sudo systemctl start|stop fa3-secrets.target`.

Policies live in `/etc/fa3/secret-policy.d/*.json` and contain no secret values. Add/update secret values only through `fa3-secretctl put` using an interactive prompt or stdin. Never pass a secret in argv or environment variables.

Machine/service secrets require a dedicated Unix service identity. Same-UID desktop applications share the OS-user trust boundary; FA3 does not claim strong malicious-process isolation between processes running as the same Unix UID.

Podman delivery uses secret file mounts by default; environment-variable secret projection is forbidden unless an explicit non-default exception policy is admitted.
