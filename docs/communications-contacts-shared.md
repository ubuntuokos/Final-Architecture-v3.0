# FA3 Communications & Contacts Shared

This materialization implements the approved provider-neutral communications architecture as a shared FA3 capability with a full standalone Hub and a context-limited embedded surface.

## Runtime status

Static architecture, policy core and GUI projection are materialized. Provider-backed mail/contact execution is **not production admitted**. SMTP, IMAP, JMAP, CardDAV, CalDAV, OAuth/OIDC, certificate validation, Secret Broker credential roundtrip, malware/attachment scanning and physical send/receive/contact roundtrip remain `PENDING_CURRENT_HOST`.

## Access model

The full Hub operates within the authenticated user's effective permissions. Embedded surfaces use the strict intersection of user, role, application, project/workspace, workflow, data-classification and communication permissions. Permission union is forbidden.

## Security

The Python policy core in `src/fa3_communications_contacts.py` is network-free and provider-neutral. It implements deterministic fail-closed admission, AI deny-wins, purpose-bound context, untrusted-message envelopes, attachment disposition, DLP disposition and high-risk agent action checks.

Direct QML/provider/network execution is forbidden. Credentials remain under the existing Secret Broker. AI remains under the Model Router and provider-admission path. Unknown gate/scan/evidence state is denied or quarantined as appropriate.

## Donor status

No external mail/groupware donor is adopted or copied in this change. The committed donor registry snapshot used for entry review is SHA256 `740593d1df5c64bf0ff6e87f7baddbd0d01789e479e840af3f22f1e5d3abf1dd`, 1233 entries. Future source adoption requires owner-marked donor registration plus an explicit canonical adoption decision.

## Verification

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_communications_contacts -v
PYTHONPATH=src python3 src/fa3_communications_contacts_gate.py
./bin/fa3-enforce communications-contacts
```

A PASS is static only. It must never be interpreted as physical provider or Current Host production promotion.
