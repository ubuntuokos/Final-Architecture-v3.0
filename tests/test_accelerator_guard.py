from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fa3_accelerator_guard import (  # noqa: E402
    AcceleratorSnapshot,
    ClientUsage,
    DecisionAction,
    GuardMode,
    Origin,
    SavedPolicy,
    WorkloadRequest,
    action_plan,
    evaluate_request,
    resolve_actor,
    submit_decision,
)
from fa3_accelerator_guard_gate import run_gate  # noqa: E402


GIB = 1024 ** 3


def test_preexisting_external_usage_requires_user_decision():
    snap = AcceleratorSnapshot(
        "gpu-1", "GPU", 24 * GIB,
        clients=(ClientUsage(100, "blender", Origin.EXTERNAL_KNOWN, 18 * GIB, 0.7),),
        safety_headroom_bytes=1 * GIB,
    )
    request = WorkloadRequest("fa3-comfy", 10 * GIB, "GPU")
    conflict = evaluate_request(snap, request, conflict_id="startup")
    assert conflict is not None
    assert conflict.workload_state.value == "PENDING_USER_DECISION"
    actor, policy = resolve_actor(conflict, GuardMode.RECOMMEND, ())
    assert actor == "USER"
    assert policy is None


def test_unaffected_fit_does_not_create_false_conflict():
    snap = AcceleratorSnapshot(
        "gpu-0", "GPU", 24 * GIB,
        clients=(ClientUsage(50, "kwin_wayland", Origin.SYSTEM_TRUSTED, 1 * GIB, 0.05),),
        safety_headroom_bytes=1 * GIB,
    )
    request = WorkloadRequest("fa3-small", 8 * GIB, "GPU")
    assert evaluate_request(snap, request) is None


def test_alternative_accelerator_is_recommended_but_not_applied():
    busy = AcceleratorSnapshot(
        "gpu-1", "GPU", 24 * GIB,
        clients=(ClientUsage(100, "python", Origin.EXTERNAL_UNKNOWN, 20 * GIB, 0.9),),
        safety_headroom_bytes=1 * GIB,
    )
    free = AcceleratorSnapshot("gpu-2", "GPU", 24 * GIB, safety_headroom_bytes=1 * GIB)
    request = WorkloadRequest("fa3-llm", 12 * GIB, "GPU")
    conflict = evaluate_request(busy, request, candidates=(free,), conflict_id="runtime")
    assert conflict is not None
    assert conflict.recommendation.action == DecisionAction.MOVE_FA3
    assert conflict.recommendation.target_accelerator_id == "gpu-2"
    assert conflict.recommendation.action_taken is False


def test_alternative_must_match_execution_path_requirement():
    requirement = {
        "acceptable_execution_paths": [
            {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"},
        ],
        "allow_translation": False,
    }
    busy = AcceleratorSnapshot(
        "gpu-busy", "GPU", 24 * GIB,
        clients=(ClientUsage(100, "python", Origin.EXTERNAL_UNKNOWN, 20 * GIB, 0.9),),
        safety_headroom_bytes=1 * GIB,
        execution_paths=({
            "accelerator_id": "gpu-busy",
            "backend": "cuda",
            "backend_class": "native",
            "framework_backend": "pytorch-cuda",
            "available": True,
            "health": "READY",
        },),
    )
    rocm_free = AcceleratorSnapshot(
        "gpu-rocm", "GPU", 24 * GIB,
        safety_headroom_bytes=1 * GIB,
        execution_paths=({
            "accelerator_id": "gpu-rocm",
            "backend": "rocm",
            "backend_class": "native",
            "framework_backend": "pytorch-rocm",
            "available": True,
            "health": "READY",
        },),
    )
    cuda_free = AcceleratorSnapshot(
        "gpu-cuda", "GPU", 16 * GIB,
        safety_headroom_bytes=1 * GIB,
        execution_paths=({
            "accelerator_id": "gpu-cuda",
            "backend": "cuda",
            "backend_class": "native",
            "framework_backend": "pytorch-cuda",
            "available": True,
            "health": "READY",
        },),
    )
    request = WorkloadRequest("fa3-cuda-job", 8 * GIB, "GPU", execution_requirement=requirement)
    conflict = evaluate_request(
        busy,
        request,
        candidates=(rocm_free, cuda_free),
        conflict_id="backend-aware",
    )
    assert conflict is not None
    assert conflict.recommendation.action == DecisionAction.MOVE_FA3
    assert conflict.recommendation.target_accelerator_id == "gpu-cuda"


def test_incompatible_current_device_never_silently_falls_back():
    requirement = {
        "acceptable_execution_paths": [
            {"backend": "cuda", "backend_class": "native", "framework_backend": "pytorch-cuda"},
        ],
        "allow_translation": False,
    }
    rocm = AcceleratorSnapshot(
        "gpu-rocm", "GPU", 24 * GIB,
        execution_paths=({
            "accelerator_id": "gpu-rocm",
            "backend": "rocm",
            "backend_class": "native",
            "framework_backend": "pytorch-rocm",
            "available": True,
            "health": "READY",
        },),
    )
    request = WorkloadRequest("fa3-cuda-job", 4 * GIB, "GPU", execution_requirement=requirement)
    conflict = evaluate_request(rocm, request, conflict_id="no-silent-fallback")
    assert conflict is not None
    assert conflict.recommendation.action == DecisionAction.WAIT
    assert "incompatible" in conflict.assessment.reason


def test_only_explicit_saved_policy_can_decide_automatically():
    busy = AcceleratorSnapshot(
        "gpu-1", "GPU", 24 * GIB,
        clients=(ClientUsage(100, "blender", Origin.EXTERNAL_KNOWN, 20 * GIB, 0.9),),
        safety_headroom_bytes=1 * GIB,
    )
    conflict = evaluate_request(
        busy, WorkloadRequest("fa3-comfy-42", 10 * GIB, "GPU"), conflict_id="policy"
    )
    assert conflict is not None

    implicit = SavedPolicy(
        "implicit", "blender", "fa3-comfy", DecisionAction.KEEP_EXTERNAL,
        explicit_user_created=False,
    )
    assert resolve_actor(conflict, GuardMode.POLICY, (implicit,))[0] == "USER"

    explicit = SavedPolicy(
        "user-rule-1", "blender", "fa3-comfy", DecisionAction.KEEP_EXTERNAL,
        explicit_user_created=True,
    )
    actor, policy = resolve_actor(conflict, GuardMode.POLICY, (explicit,))
    assert actor == "POLICY"
    assert policy == explicit


def test_action_plan_never_force_kills_by_default():
    snap = AcceleratorSnapshot(
        "gpu-1", "GPU", 8 * GIB,
        clients=(ClientUsage(100, "external", Origin.EXTERNAL_UNKNOWN, 7 * GIB, 0.7),),
    )
    conflict = evaluate_request(
        snap, WorkloadRequest("fa3-job", 4 * GIB, "GPU"), conflict_id="decision"
    )
    assert conflict is not None
    submit_decision(conflict, DecisionAction.PREFER_FA3, actor="USER")
    plan = action_plan(conflict)
    assert plan["force_terminate_external"] is False
    assert plan["requires_hrb_execution"] is True


def test_canonical_gate():
    assert run_gate(ROOT) == []
