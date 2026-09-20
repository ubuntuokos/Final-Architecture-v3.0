# FA3 step-ca offline Root CA ceremony

The Root CA is **offline by role and custody**: its private key is not installed in, exposed to, or used by the online `step-ca` issuing runtime. The Root key must remain encrypted on separate cold-storage/removable media and is connected only when a Root signing operation is intentionally performed.

Network isolation during the ceremony is a recommended high-assurance control, but it is **not** a PASS, admission, or promotion requirement. A default route does not invalidate the ceremony.

## Preconditions

- Generate and retain `root_ca_key` and `root-password.txt` directly on dedicated Root cold-storage media; do not place them in the FA3 repository, evidence tree, `/etc/fa3`, or `/var/lib/fa3-step-ca`.
- Keep Root and Intermediate password files outside Git and evidence.
- Use a separate transfer medium/bundle for the online issuing runtime. Never copy the Root private key or Root password to it.
- Air-gap or disconnect networking when practical for higher-assurance ceremonies; this is recommended, not mandatory.

## Root and Intermediate

Run the following **from the dedicated Root media directory**:

```bash
umask 077
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-384 -aes-256-cbc -pass file:root-password.txt -out root_ca_key
openssl req -new -x509 -sha384 -days 3650 -key root_ca_key -passin file:root-password.txt -subj "/CN=FA3 Offline Root CA" -addext "basicConstraints=critical,CA:TRUE,pathlen:1" -addext "keyUsage=critical,keyCertSign,cRLSign" -out root_ca.crt
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -aes-256-cbc -pass file:intermediate-password.txt -out intermediate_ca_key
openssl req -new -sha256 -key intermediate_ca_key -passin file:intermediate-password.txt -subj "/CN=FA3 Issuing Intermediate CA" -out intermediate_ca.csr
cat > intermediate.ext <<'EOF'
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF
openssl x509 -req -sha256 -days 1095 -in intermediate_ca.csr -CA root_ca.crt -CAkey root_ca_key -passin file:root-password.txt -CAcreateserial -extfile intermediate.ext -out intermediate_ca.crt
openssl verify -CAfile root_ca.crt intermediate_ca.crt
```

Generate the receipt with `evidence/collect-step-ca-root-ceremony.py`. The receipt may record whether a default route was present, but that value is observational only.

Transfer to the online issuing runtime only:

- `root_ca.crt`
- `intermediate_ca.crt`
- encrypted `intermediate_ca_key`
- the ceremony receipt

Never transfer `root_ca_key` or `root-password.txt`. After signing the Intermediate, unmount/remove the Root cold-storage media when it is not needed.
