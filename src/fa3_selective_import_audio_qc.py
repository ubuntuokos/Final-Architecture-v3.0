"""S4.2 non-effectful per-stem audio QC checklist for the existing FA3 authorities.

Metadata proposals are never independent evidence. Callers cannot mark a track,
model, human review, host, license, quality metric or publication as approved.
"""
from __future__ import annotations

from typing import Any

from fa3_selective_import_stem_plan import stem_plan_preview

SCHEMA = "fa3.selective-audio-qc-plan.v1"
COMMON = (
    "SECURITY_SOURCE_RIGHTS_AND_SCOPE",
    "INDEPENDENT_INSPECTOR_SOURCE_HASH_AND_STREAM_RECEIPT",
    "RATIONAL_SOURCE_TIMING_AND_CHANNEL_PRESERVATION",
    "EXPLICIT_DESTINATION_AND_NO_UNREQUESTED_MEDIA",
    "CANONICAL_EVIDENCE_AND_HUMAN_PUBLICATION_APPROVAL",
)
ORIGINAL = (
    "INDEPENDENT_ORIGINAL_STEM_ATTESTATION",
    "PER_STREAM_SAMPLE_AND_OUTPUT_HASH_QC",
    "TARGET_APPLICATION_FORMAT_AND_CHANNEL_QC",
)
ESTIMATED = (
    "EXPLICIT_OPERATOR_ESTIMATE_OPT_IN",
    "INDEPENDENT_MODEL_AND_CHECKPOINT_LICENSE_ADMISSION",
    "EXACT_ADMITTED_STEM_ONTOLOGY",
    "MODEL_ROUTER_AND_HRB_CURRENT_HOST_ELIGIBILITY",
    "OUTPUT_BLEED_AND_ARTIFACT_OPERATOR_REVIEW",
    "SOURCE_REFERENCE_METRICS_ONLY_WITH_VERIFIED_ISOLATED_REFERENCES",
    "TARGET_APPLICATION_FORMAT_AND_CHANNEL_QC",
)
DENOISE = (
    "SEPARATE_DENOISE_PROVIDER_AND_MODEL_ADMISSION",
    "MODEL_ROUTER_AND_HRB_CURRENT_HOST_ELIGIBILITY",
    "SPEECH_INTELLIGIBILITY_AND_ARTIFACT_REVIEW",
    "PRESERVE_REQUESTED_SOURCE_AMBIENCE_POLICY",
    "DENOISER_RESIDUAL_CANNOT_PROVE_AMBIENCE_OR_SFX",
    "TARGET_APPLICATION_FORMAT_AND_CHANNEL_QC",
)
OBSERVATIONS = (
    "ORIGINAL_OUTPUT_SAMPLE_COUNT_AND_CHANNEL_LAYOUT",
    "OPTIONAL_EBU_R128_LOUDNESS_AND_TRUE_PEAK",
)
FORBIDDEN = (
    "CLASSIFICATION_IS_NOT_WAVEFORM_SEPARATION",
    "FINGERPRINT_IS_NOT_SHA256_FIXITY_OR_STEM_IDENTITY",
    "DENOISER_RESIDUAL_IS_NOT_CLEAN_AMBIENCE",
    "NO_GROUND_TRUTH_METRIC_WITHOUT_ISOLATED_REFERENCE",
    "NO_UNVERIFIED_PHYSICAL_CURRENT_HOST_OR_MODEL_ADMISSION",
)


def audio_qc_plan_preview(
    request: dict[str, Any],
    inventory: dict[str, Any],
    choices: list[dict[str, Any]] | None = None,
    *,
    untrusted_model_candidates: list[dict[str, Any]] | None = None,
    estimate_opt_in_leaf_indices: list[int] | None = None,
) -> dict[str, Any]:
    """Compile QC requirements from validated S1/S2/S4 previews.

    Does not authenticate source attestation, approve a quality measurement,
    inspect a physical host, publish media or run an executable decoder/model.
    """
    stem = stem_plan_preview(
        request, inventory, choices,
        untrusted_model_candidates=untrusted_model_candidates,
        estimate_opt_in_leaf_indices=estimate_opt_in_leaf_indices,
    )
    leaves: list[dict[str, Any]] = []
    for item in stem["outputs"]:
        origin = item["origin"]
        status = item["status"]
        methods = list(OBSERVATIONS)
        if origin == "CLAIMED_ORIGINAL_TRACK":
            requirements = list(COMMON + ORIGINAL)
            methods.append("OPTIONAL_SOURCE_RELINK_FINGERPRINT_ADVISORY_ONLY")
            readiness = "PENDING_INDEPENDENT_ORIGINAL_SOURCE_EVIDENCE"
        elif origin == "PROPOSED_ESTIMATED_STEM":
            requirements = list(COMMON + ESTIMATED)
            methods.append("OPTIONAL_REFERENCE_BASED_STEM_SCORE_IF_GROUND_TRUTH_PRESENT")
            readiness = "PENDING_INDEPENDENT_ESTIMATED_STEM_ADMISSION"
        elif origin == "DENOISE_DERIVATIVE_ONLY":
            requirements = list(COMMON + DENOISE)
            readiness = "PENDING_INDEPENDENT_DENOISE_AND_QUALITY_EVIDENCE"
        else:
            requirements = list(COMMON)
            methods = []
            readiness = ("PENDING_OPERATOR_SOURCE_STREAM_SELECTION"
                         if status == "PENDING_OPERATOR_STREAM_CHOICE"
                         else "UNSUPPORTED_OR_BLOCKED_WITH_CURRENT_METADATA")
        leaves.append({
            "parent_leaf_index": item["parent_leaf_index"],
            "family": item["family"],
            "selector_id": item["selector_id"],
            "requested_stem_class": item["requested_stem_class"],
            "target_application": item["target_application"],
            "origin": origin,
            "original_stem_strategy_status": status,
            "quality_readiness": readiness,
            "source_stream_indices": list(item["source_stream_indices"]),
            "original_timebases": item["original_timebases"],
            "required_independent_evidence_checks": requirements,
            "advisory_measurement_methods": methods,
            "forbidden_inferences": list(FORBIDDEN),
            "independent_evidence_verified": False,
            "human_quality_review_approved": False,
            "quality_metrics_claimed_as_proof": False,
            "publish_audio": False,
            "execution_authorized": False,
        })
    return {
        "schema": SCHEMA,
        "source_ref": stem["source_ref"],
        "source_sha256": stem["source_sha256"],
        "inspector_receipt_ref": stem["inspector_receipt_ref"],
        "status": "QC_REVIEW_PLAN_ONLY",
        "output_count": len(leaves),
        "outputs": leaves,
        "publish_audio": False,
        "execution_authorized": False,
        "authority": False,
        "capability_count": 175,
        "existing_evidence_authority": "FA3-AUTH-OBS-EVIDENCE-001",
        "existing_audio_contract": "FA3-AUDIO-SEPARATION-CONTRACTS-001",
    }
