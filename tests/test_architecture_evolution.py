from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fa3_compute_profile import evaluate_workload, validate_profile
from fa3_dependency_qualification import authorize_promotion, staging_receipt, transition, validate_identity

_spec = importlib.util.spec_from_file_location("render_p3d", ROOT / "tools/render_pytorch3d_quadlet.py")
_render_mod = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_render_mod)
render = _render_mod.render


def identity():
    return {"selected_version":"1.2.3","source_commit":"a"*40,"source_sha256":"b"*64,"artifact_sha256":"c"*64,"sbom_sha256":"d"*64,"provenance_sha256":"e"*64}


def profile(**metrics):
    base={"gpu.vram_gib":24,"gpu.fp16_score":9.5,"pcie.h2d_gbps":24.0,"numa.remote_latency_p95_ns":190}
    base.update(metrics)
    return {"schema":"fa3.compute-profile.v1","host_attestation_sha256":"f"*64,"metrics":base,"diagnostic_aggregates":{"cu":37.4,"tu":123.0}}


class ComputeProfileTests(unittest.TestCase):
    def test_vector_positive(self):
        env={"schema":"fa3.workload-resource-envelope.v1","requirements":[{"metric":"gpu.vram_gib","operator":">=","value":24},{"metric":"pcie.h2d_gbps","operator":">=","value":20},{"metric":"numa.remote_latency_p95_ns","operator":"<=","value":250}]}
        self.assertEqual(evaluate_workload(profile(),env)["result"],"PASS")

    def test_vram_shortfall_not_compensated_by_compute(self):
        p=profile(**{"gpu.vram_gib":12,"gpu.fp16_score":9999})
        env={"schema":"fa3.workload-resource-envelope.v1","requirements":[{"metric":"gpu.vram_gib","operator":">=","value":24},{"metric":"gpu.fp16_score","operator":">=","value":2}]}
        result=evaluate_workload(p,env)
        self.assertEqual(result["result"],"FAIL")
        self.assertFalse(result["cross_metric_compensation"])

    def test_missing_metric_fails_closed(self):
        env={"schema":"fa3.workload-resource-envelope.v1","requirements":[{"metric":"gpu.bf16_score","operator":">=","value":1}]}
        self.assertEqual(evaluate_workload(profile(),env)["result"],"FAIL")

    def test_cu_tu_allowed_only_as_diagnostic(self):
        self.assertEqual(validate_profile(profile())["result"],"PASS")
        bad=profile(); bad["metrics"]["tu"]=123
        self.assertEqual(validate_profile(bad)["result"],"FAIL")


class DependencyQualificationTests(unittest.TestCase):
    def test_identity_requires_immutable_digests(self):
        self.assertEqual(validate_identity(identity())["result"],"PASS")
        bad=identity(); bad["artifact_sha256"]="latest"
        self.assertEqual(validate_identity(bad)["result"],"FAIL")

    def test_staging_has_no_authority(self):
        r=staging_receipt(identity(),True)
        self.assertEqual(r["state"],"STAGING_QUALIFIED")
        self.assertFalse(r["may_claim_current_host"])
        self.assertFalse(r["may_promote"])
        self.assertFalse(r["production_authority"])

    def test_illegal_state_jump_rejected(self):
        with self.assertRaises(ValueError):
            transition("STAGING_QUALIFIED","PRODUCTION_PROMOTED")

    def test_auto_still_requires_current_host(self):
        q={"state":"ACCEPTANCE_PASS","current_host_qualified":False,"host_attestation_sha256":"f"*64,"identity":identity()}
        self.assertEqual(authorize_promotion(q,"AUTO",[])["result"],"FAIL")

    def test_review_requires_approval(self):
        q={"state":"ACCEPTANCE_PASS","current_host_qualified":True,"host_attestation_sha256":"f"*64,"identity":identity()}
        self.assertEqual(authorize_promotion(q,"REVIEW",[])["result"],"FAIL")
        self.assertEqual(authorize_promotion(q,"REVIEW",["maintainer-a"])["result"],"PASS")

    def test_critical_requires_two_distinct_approvals(self):
        q={"state":"ACCEPTANCE_PASS","current_host_qualified":True,"host_attestation_sha256":"f"*64,"identity":identity()}
        self.assertEqual(authorize_promotion(q,"CRITICAL",["a"])["result"],"FAIL")
        self.assertEqual(authorize_promotion(q,"CRITICAL",["a","b"])["result"],"PASS")


class QuadletTests(unittest.TestCase):
    def test_digest_pin_required(self):
        template="Image=@IMAGE_REF@\nNetwork=none\n"
        with self.assertRaises(ValueError):
            render(template,"registry/pytorch3d:latest")
        out=render(template,"registry/pytorch3d@sha256:"+"a"*64)
        self.assertIn("@sha256:",out)


class ContainerSupplyChainTests(unittest.TestCase):
    def test_source_archive_digest_is_actually_verified(self):
        text=(ROOT/"deployment/containers/pytorch3d.Containerfile").read_text(encoding="utf-8")
        self.assertIn("COPY pytorch3d-source.tar",text)
        self.assertIn("sha256sum -c -",text)
        self.assertNotIn("git rev-parse HEAD 2>/dev/null ||",text)

    def test_runtime_install_cannot_fetch_dependencies(self):
        text=(ROOT/"deployment/containers/pytorch3d.Containerfile").read_text(encoding="utf-8")
        self.assertIn("--no-index",text)


if __name__ == "__main__":
    unittest.main()
