# FA3 step-ca deployment projection

This directory materializes `FA3-PROVIDER-STEP-CA-001`. It is a hardened
deployment projection, not proof that the current host is already admitted.

## Trust topology

1. The FA3 Root CA private key is created and retained **offline**. It MUST NOT
   be copied into the online step-ca host, a systemd credential, or its online
   backup set.
2. The online runtime holds only the issuing intermediate certificate and the
   encrypted intermediate private key.
3. `root_ca.crt` is public trust material distributed through a versioned
   FA3 TrustBundle.
4. Workload TLS certificates default to 12 hours and MUST NOT exceed 24 hours.
5. A certificate authenticates an identity. It does not itself authorize an
   MCP tool, workflow, secret, host resource, or application action.

## Runtime layout

- config: `/etc/fa3/step-ca/ca.json`
- unlock secret: `/etc/fa3/secrets/step-ca-password` (root-only source,
  injected by systemd `LoadCredential=`)
- public root: `/var/lib/fa3-step-ca/certs/root_ca.crt`
- issuing cert: `/var/lib/fa3-step-ca/certs/intermediate_ca.crt`
- encrypted issuing key: `/var/lib/fa3-step-ca/secrets/intermediate_ca_key`
- state/database: `/var/lib/fa3-step-ca/db`
- default listener: `127.0.0.1:9443`

Remote exposure is not enabled by this projection. Multi-host use requires an
explicit network/security admission before changing the bind address.

## Supply-chain admission

Pin step-ca to v0.30.2 / commit `6e8ec61405239cf3f37b2bbf260a587b7d2e4e31`. Verify the selected
architecture's release artifact against `checksums.txt` and its Sigstore bundle
before installation. Floating `latest` or `master` is not promotion evidence.

## Root ceremony

Generate the root key on an offline medium or isolated machine. Create/sign the
issuing intermediate through that root ceremony, then transfer only
`root_ca.crt`, `intermediate_ca.crt`, and the encrypted intermediate key to
the online runtime. Record fingerprints and ceremony evidence, never private key
bytes.

## Promotion

Run `./bin/fa3-enforce trust-pki`.

Reference PASS is static only. Production/current-host promotion additionally
requires ACME issuance/renewal, mTLS, SSH certificate, trust-bundle, and
backup/restore tests from
`canonical/FA3-STEP-CA-RUNTIME-CONFORMANCE-001.json`.
