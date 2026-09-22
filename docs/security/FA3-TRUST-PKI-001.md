# FA3-TRUST-PKI-001

## Purpose

FA3-TRUST-PKI-001 provides a provider-neutral trust and machine-identity
contract. Smallstep step-ca is the default internal CA provider, but it does not
become the FA3 security policy, identity, authorization, secret, MCP, HRB,
evidence, or artifact-trust authority.

## Canonical topology

```text
offline FA3 Root CA
        |
        | signs
        v
online issuing Intermediate CA
        |
        +-- step-ca / ACME v2
        +-- server certificates
        +-- client certificates / mTLS
        +-- SSH certificates
        +-- versioned trust bundle
```

The root private key is offline-only. The online runtime contains the public
root certificate and the encrypted issuing-intermediate private key only.

## Identity and authorization

A valid X.509 or SSH certificate proves cryptographic identity according to an
issuance policy. Authorization remains an external FA3 policy decision. Central
MCP Gateway requests therefore still require identity + policy + any applicable
approval/lease. A successful TLS handshake is never sufficient authorization.

## Lifetime and revocation

Machine/workload TLS certificates use 12h by default and 24h maximum.
Compromise handling defaults to deny-renew plus short expiry. CRL/OCSP support,
if deployed, is supplemental and must not be represented as stronger than actual
runtime evidence proves.

## Provider boundary and GUI

`FA3-PROVIDER-STEP-CA-001` may issue and renew credentials under FA3 policy.
It cannot mutate canonical trust policy, approve remote exposure, grant
application permissions, mint FA3 secret leases, or self-promote runtime
evidence. The Control Center projection is read-only until policy-gated backend
issuance/rotation actions are separately admitted.

## Runtime state

Repository/reference integration is canonical. Current-host production runtime
is intentionally `NOT_ADMITTED` until real host evidence is captured.
