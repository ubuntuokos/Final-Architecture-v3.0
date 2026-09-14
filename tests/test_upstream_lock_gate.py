from src.fa3_upstream_lock_gate import validate_registry


def test_registry_rejects_floating_revisions():
    report = validate_registry({
        "policy": {
            "floating_main_allowed_for_runtime": False,
            "floating_main_allowed_for_promotion_evidence": False,
            "immutable_identity_required": True,
        },
        "locks": {
            "bad": {
                "provider_id": "FA3-PROVIDER-TEST-001",
                "kind": "git_commit",
                "revision": "main",
                "update_policy": "CONTROLLED",
            }
        },
        "promotion_pipeline": [
            "RESOLVE_IMMUTABLE_IDENTITY",
            "SECURITY_SCAN",
            "SANDBOX_CONFORMANCE",
            "WRITE_EVIDENCE",
            "REVIEW_LOCK_DIFF",
            "PROMOTE_LOCK",
        ],
    })
    assert report["result"] == "FAIL"


def test_registry_accepts_managed_immutable_revision():
    report = validate_registry({
        "policy": {
            "floating_main_allowed_for_runtime": False,
            "floating_main_allowed_for_promotion_evidence": False,
            "immutable_identity_required": True,
        },
        "locks": {
            "good": {
                "provider_id": "FA3-PROVIDER-TEST-001",
                "kind": "git_commit",
                "revision": "0123456789abcdef0123456789abcdef01234567",
                "update_policy": "CONTROLLED",
            }
        },
        "promotion_pipeline": [
            "RESOLVE_IMMUTABLE_IDENTITY",
            "SECURITY_SCAN",
            "SANDBOX_CONFORMANCE",
            "WRITE_EVIDENCE",
            "REVIEW_LOCK_DIFF",
            "PROMOTE_LOCK",
        ],
    })
    assert report["result"] == "PASS"
