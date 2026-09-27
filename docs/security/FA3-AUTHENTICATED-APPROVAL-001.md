# Authenticated approval receipts

FA3 release acceptance no longer treats boolean fields such as `signed=true`, `approved=true`, or `independent=true` as authority evidence for criteria 4, 18, or 19.

The trust chain is intentionally split:

1. **FA3 Trust PKI** proves signer identity with an X.509 certificate and URI SAN.
2. **FA3 Security Governance** separately signs a role grant authorizing that certificate identity for an approval role.
3. The signer signs the canonical approval receipt content.
4. Acceptance verifies source commit, content digest, expiry, certificate chain, identity, role grant and receipt signature.
5. Promotion consumes release-decision receipt IDs in a replay-protection ledger.

Certificate issuance alone never grants an approval role.

## Verification key installation

Security Governance's approval **public** key is installed explicitly:

```bash
sudo bash bin/fa3-install-security-governance-approval-key.sh /path/to/security-governance-approval.pub
```

This installs only:

```text
/etc/fa3/trust/security-governance-approval.pub
```

The installer does not generate, read, copy or store any private key.

## Issue a role grant

Run from an authorized offline/administrative context:

```bash
python tools/fa3_approval_tool.py grant \
  --identity spiffe://fa3.example/reviewer/alice \
  --identity-class HUMAN \
  --certificate /path/to/alice.crt \
  --role INDEPENDENT_REVIEWER \
  --receipt-type INDEPENDENT_REVIEW \
  --security-governance-private-key /secure/path/security-governance.key \
  --output /secure/path/alice-review-grant.json
```

The private key path is an explicit input. FA3 does not persist the key.

## Issue a receipt

Prepare a JSON payload describing the exact approved/reviewed content, including the producer identity for independent review. Then:

```bash
python tools/fa3_approval_tool.py receipt \
  --identity spiffe://fa3.example/reviewer/alice \
  --certificate /path/to/alice.crt \
  --private-key /secure/path/alice.key \
  --signed-grant /secure/path/alice-review-grant.json \
  --receipt-type INDEPENDENT_REVIEW \
  --receipt-id APR-20260927-0001 \
  --source-commit "$(git rev-parse HEAD)" \
  --nonce 8nYw_Mc5aX0JqP2Zr7Ls \
  --payload /path/to/review-payload.json \
  --output evidence/receipts/independent-review.json
```

Equivalent receipt types and roles are used for release integrity and human promotion. Promotion receipts are single-use for a new source revision.

## Independence

For `INDEPENDENT_REVIEW`, the signed payload must contain `producer_identity`. The verifier compares the authenticated reviewer identity against that producer identity. A self-declared `independent=true` field has no effect.

## Fail-closed behavior

Missing trust root, missing Security Governance verification key, expired receipt/grant, source-commit mismatch, modified payload, invalid signature, wrong role, certificate mismatch, non-human promoter, or replayed promotion receipt all block acceptance/promotion.
