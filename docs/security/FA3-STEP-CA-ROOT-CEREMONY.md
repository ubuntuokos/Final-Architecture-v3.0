# FA3 step-ca Root CA ceremony

The FA3 Root CA is offline by **operational role**, not by a mandatory storage device type. The online `fa3-step-ca` issuing service must never load or use the Root private key during normal operation.

For the default single-host FA3 deployment, the Root private key may remain on the same machine when it is:

- strongly encrypted at rest;
- stored outside the FA3 repository, `/etc/fa3`, and `/var/lib/fa3-step-ca`;
- not readable by the `fa3-step-ca` service account;
- protected by an operator-controlled unlock secret;
- backed up redundantly in encrypted form.

Removable media, HSM/YubiKey and an air-gapped ceremony host are optional higher-assurance controls. They are not prerequisites for the default FA3 workflow.

## Default practical layout

Default storage is the mounted FA3 Session Vault image. After FA3 login/unlock, use:

```text
$XDG_RUNTIME_DIR/fa3-state/pki/root/
  root_ca_key
  root-password.txt
  root_ca.crt
  intermediate_ca.csr
  intermediate.ext
```

The online issuing runtime receives only:

- `root_ca.crt`
- `intermediate_ca.crt`
- encrypted `intermediate_ca_key`
- the ceremony receipt

Never copy `root_ca_key` or `root-password.txt` into the repository, evidence tree, `/etc/fa3`, `/var/lib/fa3-step-ca`, or the step-ca runtime backup.

The Root custody backup is a different backup class from the step-ca runtime backup. The preferred backup unit is the **closed LUKS2 Session Vault image itself**, which can be copied as opaque encrypted data to one or more user-selected destinations. Removable media is only one optional destination.

## Recommended current-host ceremony

Run the orchestrated, idempotent ceremony:

```bash
bin/fa3-step-ca-root-ceremony.sh
```

It unlocks the validated FA3 state image interactively, creates or verifies Root/Intermediate material inside the encrypted image, writes the non-secret ceremony receipt, prepares a short-lived online activation bundle under `$XDG_RUNTIME_DIR`, and closes the state image on exit.

The Root private key and Root password are never copied into the activation bundle.

## Manual equivalent

```bash
ROOT_DIR="${FA3_ROOT_CA_DIR:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/fa3-state/pki/root}"
install -d -m0700 "$ROOT_DIR"
cd "$ROOT_DIR"
umask 077

openssl rand -base64 48 > root-password.txt
openssl rand -base64 48 > intermediate-password.txt

openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-384 -aes-256-cbc -pass file:root-password.txt -out root_ca_key

openssl req -new -x509 -sha384 -days 3650   -key root_ca_key   -passin file:root-password.txt   -subj "/CN=FA3 Offline Root CA"   -addext "basicConstraints=critical,CA:TRUE,pathlen:1"   -addext "keyUsage=critical,keyCertSign,cRLSign"   -out root_ca.crt

openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -aes-256-cbc -pass file:intermediate-password.txt -out intermediate_ca_key

openssl req -new -sha256   -key intermediate_ca_key   -passin file:intermediate-password.txt   -subj "/CN=FA3 Issuing Intermediate CA"   -out intermediate_ca.csr

cat > intermediate.ext <<'EOF'
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF

openssl x509 -req -sha256 -days 1095   -in intermediate_ca.csr   -CA root_ca.crt   -CAkey root_ca_key   -passin file:root-password.txt   -CAcreateserial   -extfile intermediate.ext   -out intermediate_ca.crt

openssl verify -CAfile root_ca.crt intermediate_ca.crt
```

Generate the receipt with `evidence/collect-step-ca-root-ceremony.py`. The `--medium-id` argument is optional and exists only as an audit/custody label; it does not imply removable media.

## Higher-assurance options

Operators who need stronger physical separation may instead use:

- removable encrypted cold storage;
- HSM or YubiKey PIV;
- an air-gapped ceremony host;
- geographically separated encrypted Root-key backups.

These options improve resistance to host compromise, but they do not change the FA3 architectural authority or runtime admission model.
