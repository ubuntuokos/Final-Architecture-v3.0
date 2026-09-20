# step-ca current-host closure

1. Normal user: `bin/fa3-step-ca-bootstrap.sh prepare`.
2. Explicit root install: `sudo FA3_REPO_ROOT="$PWD" FA3_STEP_CA_BOOTSTRAP_STATE="$PWD/.fa3-current-host/step-ca/bootstrap" bin/fa3-step-ca-bootstrap.sh install`. No CA key is created and the service is not started.
3. Perform `docs/security/FA3-STEP-CA-ROOT-CEREMONY.md`.
4. Activate with `bin/fa3-step-ca-activate.sh` and the approved transfer bundle plus external password files.
5. Run `bin/fa3-step-ca-current-host.sh preflight`.
6. Run privileged ACME/mTLS/SSH E2E: `sudo FA3_REPO_ROOT="$PWD" bin/fa3-step-ca-e2e.sh`.
7. Run recovery drill: `sudo FA3_REPO_ROOT="$PWD" FA3_STEP_CA_MAINTENANCE_ACK=YES bin/fa3-step-ca-backup-restore-drill.sh`.
8. Final gate: `bin/fa3-step-ca-current-host.sh collect`.

The E2E harness is root only for ACME http-01 port 80. The CA daemon remains unprivileged. The recovery drill uses a short maintenance stop, restores a shadow instance on 127.0.0.1:9445, and proves post-restore issuance. Root private key and password/unlock files are excluded from backup evidence. A PASS can promote only the step-ca provider runtime, never global FA3.
