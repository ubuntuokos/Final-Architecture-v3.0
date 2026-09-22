# FA3 current-host runner control plane

`FA3-CURRENT-HOST-RUNNER-CONFORMANCE-001` is the shared execution substrate for real workstation evidence jobs requiring:

```text
[self-hosted, linux, x64, fa3-current-host]
```

It is not an architectural authority and does not promote any capability by itself. A runner doctor PASS only proves that GitHub can see an online, correctly labeled, non-root current-host runner; each provider still needs its own real E2E receipt.

## Pinned runner

- upstream: `actions/runner`
- version: `2.337.0`
- Linux x64 asset: `actions-runner-linux-x64-2.337.0.tar.gz`
- SHA-256: `70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613`
- auto-update: disabled; updates require a new reviewed immutable pin

The bootstrap downloads the archive to a temporary file, validates the exact digest, and only then extracts it. Direct remote-to-shell installation is forbidden.

## Host prerequisites

The runner user must be non-root and have `curl`, `tar`, `sha256sum`, `python3`, `systemctl`, and preferably an authenticated `gh` CLI with permission to create/read repository self-hosted runners. The 429-capability closure additionally requires locally admitted runtime prerequisites for every registered executor; CAP-028 currently requires `wasmtime` for real WASM/WASI sandbox execution. Missing executor prerequisites are fail-closed and must not be replaced by hosted CI or synthetic receipts. The runner itself is installed under:

```text
$HOME/.local/share/fa3/actions-runner
```

The long-running listener is managed by the user service `fa3-github-runner.service`. Boot-persistent execution after logout/reboot requires systemd user linger; the bootstrap now enables and verifies it fail-closed:

```bash
sudo loginctl enable-linger "$USER"
```

## Bootstrap

From a checked-out repository branch containing this materialization:

```bash
chmod +x bin/fa3-current-host-runner-bootstrap.sh bin/fa3-current-host-runner-doctor
./bin/fa3-current-host-runner-bootstrap.sh
```

If `gh` is authenticated with sufficient permission, the bootstrap obtains an ephemeral registration token itself. Otherwise supply a short-lived registration token only for the command invocation:

```bash
FA3_GITHUB_RUNNER_TOKEN='...' ./bin/fa3-current-host-runner-bootstrap.sh
```

The token is never written to a repository file or evidence receipt and is unset when bootstrap exits.

## Doctor

Run:

```bash
./bin/fa3-current-host-runner-doctor
```

The doctor fails closed unless all of these are true:

- systemd user linger is enabled for the runner user;

- the local runner is exactly version `2.337.0`;
- `fa3-github-runner.service` is active;
- the repository runner inventory contains the local runner name;
- GitHub reports the runner `online`;
- `self-hosted`, `linux`, `x64`, and `fa3-current-host` labels are present.

The secret-free receipt is written to:

```text
.fa3-current-host/runner/doctor.json
```

## Repository smoke test

After registration, dispatch **FA3 Current Host Runner Control Plane** with `execute_current_host=true`. The `current-host-runner / real-smoke` job can start only if GitHub can actually assign the required label set.

Once that smoke test passes, re-run the previously cancelled provider jobs, beginning with PR #91 X-CMD `xcmd-current-host / production-e2e`. A provider PASS remains separate from global 143-capability Evidence Registry closure and from the 19-point promotion gate.


## Secret Broker privileged bridge

The current-host runner itself remains non-root. Secret Broker tests require LUKS2, mount, systemd and rekey operations that need root privileges, so the runner bootstrap installs a separate exact-command bridge.

Run the normal bootstrap from the intended checked-out commit:

```bash
./bin/fa3-current-host-runner-bootstrap.sh
```

If the Secret Broker bridge is missing or source-stale, bootstrap requests sudo once and runs:

```text
bin/fa3-install-secret-broker-current-host-bridge.sh
```

The resulting sudoers entry authorizes only:

```text
/usr/local/libexec/fa3-secret-broker-current-host-root
```

with no arguments. General passwordless sudo is not granted. The root helper executes only the root-owned package installed from the bound Git commit. The workflow invokes the non-root client:

```bash
FA3_REPO_ROOT="$PWD" /usr/local/bin/fa3-secret-broker-current-host-bridge doctor
FA3_REPO_ROOT="$PWD" /usr/local/bin/fa3-secret-broker-current-host-bridge run
```

If the checkout and installed source binding differ, the bridge fails closed.
