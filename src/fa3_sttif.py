#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from typing import Any


class STTIFDenied(ValueError):
    pass


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise STTIFDenied(f"{name} must be a positive integer")
    return value


def _fraction(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise STTIFDenied(f"{name} must be numeric")
    value = float(value)
    if not 0.0 <= value < 1.0:
        raise STTIFDenied(f"{name} must be in [0, 1)")
    return value


def _aligned_floor(value: int, alignment: int) -> int:
    return max(alignment, (value // alignment) * alignment)


def _axis_starts(total: int, tile: int, overlap_fraction: float, alignment: int) -> list[int]:
    if tile >= total:
        return [0]
    raw_step = max(1, int(tile * (1.0 - overlap_fraction)))
    step = max(alignment, _aligned_floor(raw_step, alignment))
    if step >= tile:
        raise STTIFDenied("overlap produces a gap between spatial tiles")
    starts = [0]
    while starts[-1] + tile < total:
        candidate = starts[-1] + step
        last = total - tile
        if candidate >= last:
            if last != starts[-1]:
                starts.append(last)
            break
        starts.append(candidate)
    previous_end = 0
    for start in starts:
        if start > previous_end:
            raise STTIFDenied("spatial plan contains an uncovered gap")
        previous_end = max(previous_end, start + tile)
    if previous_end < total:
        raise STTIFDenied("spatial plan does not cover target axis")
    return starts


def _shrink_to_budget(width: int, height: int, alignment: int, max_pixels: int | None) -> tuple[int, int]:
    if max_pixels is None:
        return width, height
    max_pixels = _positive_int(max_pixels, "max_pixels_per_tile")
    w, h = width, height
    while w * h > max_pixels:
        if w >= h and w > alignment:
            w -= alignment
        elif h > alignment:
            h -= alignment
        else:
            raise STTIFDenied("declared resource budget cannot fit one aligned tile")
    return w, h


def _validate_temporal_shape(window: int, constraints: dict[str, Any]) -> None:
    modulus = constraints.get("temporal_modulus")
    offset = constraints.get("temporal_offset")
    if modulus is None and offset is None:
        return
    modulus = _positive_int(modulus, "temporal_modulus")
    if not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset < modulus:
        raise STTIFDenied("temporal_offset must be an integer in [0, temporal_modulus)")
    if window % modulus != offset:
        raise STTIFDenied("temporal window violates model shape rule")


def plan_spatial(
    target_width: int,
    target_height: int,
    tile_width: int,
    tile_height: int,
    overlap_fraction: float,
    alignment: int,
) -> dict[str, Any]:
    target_width = _positive_int(target_width, "target_width")
    target_height = _positive_int(target_height, "target_height")
    alignment = _positive_int(alignment, "spatial_alignment")
    overlap_fraction = _fraction(overlap_fraction, "overlap_fraction")
    tile_width = min(target_width, _positive_int(tile_width, "tile_width"))
    tile_height = min(target_height, _positive_int(tile_height, "tile_height"))
    if target_width > tile_width and tile_width % alignment:
        raise STTIFDenied("tile_width violates spatial alignment")
    if target_height > tile_height and tile_height % alignment:
        raise STTIFDenied("tile_height violates spatial alignment")

    xs = _axis_starts(target_width, tile_width, overlap_fraction, alignment)
    ys = _axis_starts(target_height, tile_height, overlap_fraction, alignment)
    tiles = []
    index = 0
    for y in ys:
        for x in xs:
            tiles.append({
                "index": index,
                "x": x,
                "y": y,
                "width": min(tile_width, target_width - x),
                "height": min(tile_height, target_height - y),
            })
            index += 1
    return {
        "target_width": target_width,
        "target_height": target_height,
        "tile_width": tile_width,
        "tile_height": tile_height,
        "overlap_fraction": overlap_fraction,
        "alignment": alignment,
        "grid": {"columns": len(xs), "rows": len(ys)},
        "tiles": tiles,
        "coverage_complete": True,
    }


def plan_temporal(frame_count: int, window_frames: int, overlap_frames: int, constraints: dict[str, Any]) -> dict[str, Any]:
    frame_count = _positive_int(frame_count, "frame_count")
    window_frames = min(frame_count, _positive_int(window_frames, "temporal_window_frames"))
    overlap_frames = int(overlap_frames)
    if overlap_frames < 0 or overlap_frames >= window_frames:
        raise STTIFDenied("temporal_overlap_frames must be >= 0 and smaller than temporal_window_frames")
    _validate_temporal_shape(window_frames, constraints)
    if frame_count <= window_frames:
        starts = [0]
    else:
        step = window_frames - overlap_frames
        starts = [0]
        while starts[-1] + window_frames < frame_count:
            candidate = starts[-1] + step
            last = frame_count - window_frames
            if candidate >= last:
                if last != starts[-1]:
                    starts.append(last)
                break
            starts.append(candidate)
    windows = [
        {"index": i, "start_frame": start, "end_frame_exclusive": min(frame_count, start + window_frames)}
        for i, start in enumerate(starts)
    ]
    previous_end = 0
    for window in windows:
        if window["start_frame"] > previous_end:
            raise STTIFDenied("temporal plan contains an uncovered gap")
        previous_end = max(previous_end, window["end_frame_exclusive"])
    if previous_end < frame_count:
        raise STTIFDenied("temporal plan does not cover requested frames")
    return {
        "frame_count": frame_count,
        "window_frames": window_frames,
        "overlap_frames": overlap_frames,
        "windows": windows,
        "coverage_complete": True,
    }


def plan_inference(request: dict[str, Any], constraints: dict[str, Any], resource_budget: dict[str, Any] | None = None) -> dict[str, Any]:
    if request.get("schema") != "fa3.tiled-inference-request.v1":
        raise STTIFDenied("unsupported request schema")
    if constraints.get("schema") != "fa3.model-window-descriptor.v1":
        raise STTIFDenied("unsupported model constraint schema")

    sampler = request.get("sampler")
    supported = constraints.get("supported_samplers")
    if not isinstance(sampler, str) or not sampler:
        raise STTIFDenied("sampler is required")
    if not isinstance(supported, list) or not supported or sampler not in supported:
        raise STTIFDenied("requested sampler is not explicitly supported; silent substitution is forbidden")

    overlap = _fraction(request.get("spatial_overlap_fraction", constraints.get("minimum_overlap_fraction", 0.0)), "spatial_overlap_fraction")
    minimum_overlap = _fraction(constraints.get("minimum_overlap_fraction", 0.0), "minimum_overlap_fraction")
    if overlap < minimum_overlap:
        raise STTIFDenied("requested spatial overlap is below the model constraint")

    alignment = _positive_int(constraints.get("spatial_alignment", 1), "spatial_alignment")
    max_w = _positive_int(constraints.get("max_tile_width"), "max_tile_width")
    max_h = _positive_int(constraints.get("max_tile_height"), "max_tile_height")
    requested_w = min(max_w, _positive_int(request.get("tile_width", max_w), "tile_width"))
    requested_h = min(max_h, _positive_int(request.get("tile_height", max_h), "tile_height"))
    requested_w = _aligned_floor(requested_w, alignment)
    requested_h = _aligned_floor(requested_h, alignment)

    budget = resource_budget or {}
    if budget and budget.get("schema") != "fa3.resource-budget.v1":
        raise STTIFDenied("unsupported resource budget schema")
    tile_w, tile_h = _shrink_to_budget(requested_w, requested_h, alignment, budget.get("max_pixels_per_tile"))

    spatial = plan_spatial(
        request.get("target_width"),
        request.get("target_height"),
        tile_w,
        tile_h,
        overlap,
        alignment,
    )

    frame_count = _positive_int(request.get("frame_count", 1), "frame_count")
    window_frames = _positive_int(
        request.get("temporal_window_frames", constraints.get("temporal_window_frames", frame_count)),
        "temporal_window_frames",
    )
    temporal_overlap = request.get("temporal_overlap_frames", constraints.get("temporal_overlap_frames", 0))
    temporal = plan_temporal(frame_count, window_frames, temporal_overlap, constraints)

    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise STTIFDenied("request_id is required")
    seed = request.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise STTIFDenied("seed must be a non-negative integer")

    plan = {
        "schema": "fa3.tiled-inference-execution-plan.v1",
        "request_id": request_id,
        "provider_neutral": True,
        "physical_device_selected": False,
        "provider_selected": False,
        "model_selected": False,
        "sampler": sampler,
        "spatial": spatial,
        "temporal": temporal,
        "latent_canvas": {
            "logical_canvas_id": f"{request_id}:latent",
            "shared_across_spatial_tiles": True,
        },
        "noise_trajectory": {
            "trajectory_id": f"{request_id}:noise:{seed}",
            "seed": seed,
            "shared_across_spatial_tiles": True,
            "shared_across_temporal_windows": request.get("share_noise_across_temporal_windows", True) is True,
        },
        "fusion": {
            "policy": "NORMALIZED_EDGE_WEIGHTED_OVERLAP",
            "per_denoise_step": True,
            "independent_tile_stitching": False,
        },
        "resource_budget": {
            "authority": "EXTERNAL_INPUT_ONLY",
            "hrb_authority_preserved": True,
            "max_pixels_per_tile": budget.get("max_pixels_per_tile"),
            "physical_device_authorized": False,
        },
        "silent_fallback_used": False,
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode("utf-8")
    plan["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    return plan
