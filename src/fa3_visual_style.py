#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence
import argparse
import hashlib
import json
import math
import re


class VisualStyleDenied(ValueError):
    pass


PROFILE_ID = "FA3-VISUAL-STYLE-FABRIC-001"
MODEL_ROUTER_AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
HRB_AUTHORITY = "FA3-AUTH-HOST-RESOURCE-BROKER-001"
EVIDENCE_AUTHORITY = "FA3-AUTH-OBS-EVIDENCE-001"
SUPPORTED_SCOPES = {"PROJECT", "SCENE", "SHOT", "ASSET"}
REQUIRED_UPSTREAM_FIELDS = {"style_name", "style_slug", "prompt_template"}
OPTIONAL_COPY_FIELDS = (
    "style_summary", "category", "environment_variables", "style_fidelity_anchors",
    "source_content_to_avoid", "visual_deconstruction", "composition", "typography",
    "color_palette", "photographic_direction", "design_rules", "do", "avoid",
    "negative_prompt", "examples",
)
TEMPLATE_VARIABLE = re.compile(r"\\{([A-Z][A-Z0-9_]*)\\}")

EXTENDED_FA3_FIELDS = (
    "camera_language", "lens_language", "lighting_language", "material_language",
    "environment_language", "character_language", "motion_language", "animation_language",
    "era", "genre", "weather", "time_of_day", "cultural_context", "production_type",
    "continuity_constraints", "identity_constraints", "shot_constraints",
    "temporal_consistency", "spatial_consistency",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _clean_slug(value: str) -> str:
    slug = str(value).strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise VisualStyleDenied("style_slug must be lowercase kebab-case")
    return slug


def _require_nonempty_string(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise VisualStyleDenied(f"{field} is required")
    return text


def normalize_recipe(
    source: Mapping[str, Any],
    *,
    source_project: str,
    source_revision: str,
    source_license: str,
    attribution: str,
    source_url: str | None = None,
) -> dict[str, Any]:
    missing = sorted(REQUIRED_UPSTREAM_FIELDS - set(source))
    if missing:
        raise VisualStyleDenied("missing required style fields: " + ", ".join(missing))

    license_id = _require_nonempty_string(source_license, "source_license")
    credit = _require_nonempty_string(attribution, "attribution")
    slug = _clean_slug(_require_nonempty_string(source.get("style_slug"), "style_slug"))

    recipe: dict[str, Any] = {
        "schema": "fa3.visual-style-recipe.v1",
        "id": f"fa3.visual-style.{slug}",
        "name": _require_nonempty_string(source.get("style_name"), "style_name"),
        "version": str(source.get("style_version") or source_revision),
        "source_format": "style.json",
        "provider_neutral": True,
        "prompt_template": _require_nonempty_string(source.get("prompt_template"), "prompt_template"),
        "provenance": {
            "source_project": _require_nonempty_string(source_project, "source_project"),
            "source_revision": _require_nonempty_string(source_revision, "source_revision"),
            "source_url": source_url,
            "license": license_id,
            "attribution": credit,
            "source_sha256": digest(source),
            "derived": True,
        },
        "fa3_extensions": {name: source.get(name) for name in EXTENDED_FA3_FIELDS if name in source},
        "runtime": {
            "model_router_authority": MODEL_ROUTER_AUTHORITY,
            "resource_authority": HRB_AUTHORITY,
            "fixed_provider": None,
            "fixed_model": None,
            "fixed_runtime": None,
        },
    }
    for field in OPTIONAL_COPY_FIELDS:
        if field in source:
            recipe[field] = source[field]

    recipe["recipe_sha256"] = digest({k: v for k, v in recipe.items() if k != "recipe_sha256"})
    return recipe


def build_style_dna(components: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not components:
        raise VisualStyleDenied("Style DNA requires at least one component")

    normalized: list[dict[str, Any]] = []
    total = 0.0
    for raw in components:
        recipe_id = _require_nonempty_string(raw.get("recipe_id"), "recipe_id")
        weight = float(raw.get("weight", 0))
        if not math.isfinite(weight) or weight <= 0:
            raise VisualStyleDenied("Style DNA weights must be positive finite numbers")
        total += weight
        normalized.append({"recipe_id": recipe_id, "weight": weight})

    for item in normalized:
        item["weight"] = round(item["weight"] / total, 12)

    return {
        "schema": "fa3.style-dna.v1",
        "components": normalized,
        "normalized": True,
        "dna_sha256": digest(normalized),
    }


def build_visual_intent(
    recipe: Mapping[str, Any],
    *,
    values: Mapping[str, Any] | None = None,
    scope: str = "ASSET",
    target_id: str | None = None,
    continuity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if recipe.get("schema") != "fa3.visual-style-recipe.v1":
        raise VisualStyleDenied("canonical FA3 visual style recipe required")

    scope_norm = str(scope).upper()
    if scope_norm not in SUPPORTED_SCOPES:
        raise VisualStyleDenied("unsupported visual style scope")

    runtime = recipe.get("runtime", {})
    if any(runtime.get(key) for key in ("fixed_provider", "fixed_model", "fixed_runtime")):
        raise VisualStyleDenied("canonical recipes may not pin provider, model or runtime")

    constraints = {
        "style_fidelity_anchors": recipe.get("style_fidelity_anchors", []),
        "source_content_to_avoid": recipe.get("source_content_to_avoid", []),
        "negative_prompt": recipe.get("negative_prompt"),
        "design_rules": recipe.get("design_rules", []),
        "do": recipe.get("do", []),
        "avoid": recipe.get("avoid", []),
        "fa3_extensions": recipe.get("fa3_extensions", {}),
    }

    return {
        "schema": "fa3.visual-intent-ir.v1",
        "style_recipe_id": recipe.get("id"),
        "style_recipe_sha256": recipe.get("recipe_sha256"),
        "scope": scope_norm,
        "target_id": target_id,
        "values": dict(values or {}),
        "constraints": constraints,
        "continuity": dict(continuity or {}),
        "route_request": {
            "route_class": "visual.generation",
            "authority": MODEL_ROUTER_AUTHORITY,
            "resource_authority": HRB_AUTHORITY,
            "provider": None,
            "model": None,
            "runtime": None,
            "silent_fallback_allowed": False,
        },
        "canonical_prompt": False,
        "derived_prompt_required": True,
        "current_host_runtime_promotion_claim": False,
    }



def _constraint_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return _canonical_json(value)


def compile_visual_style(
    recipe: Mapping[str, Any],
    *,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    if recipe.get("schema") != "fa3.visual-style-recipe.v1":
        raise VisualStyleDenied("canonical FA3 visual style recipe required")

    runtime = recipe.get("runtime", {})
    if any(runtime.get(key) for key in ("fixed_provider", "fixed_model", "fixed_runtime")):
        raise VisualStyleDenied("canonical recipes may not pin provider, model or runtime")

    template = _require_nonempty_string(recipe.get("prompt_template"), "prompt_template")
    effective = {str(k): str(v) for k, v in dict(values).items()}
    effective.setdefault(
        "STYLE_FIDELITY_ANCHORS",
        _constraint_text(recipe.get("style_fidelity_anchors", [])),
    )
    effective.setdefault(
        "SOURCE_CONTENT_TO_AVOID",
        _constraint_text(recipe.get("source_content_to_avoid", [])),
    )

    required = sorted(set(TEMPLATE_VARIABLE.findall(template)))
    missing = [name for name in required if not effective.get(name, "").strip()]
    if missing:
        raise VisualStyleDenied("missing template variables: " + ", ".join(missing))

    derived_prompt = TEMPLATE_VARIABLE.sub(lambda match: effective[match.group(1)], template)
    receipt = {
        "schema": "fa3.visual-style-compile-receipt.v1",
        "style_recipe_id": recipe.get("id"),
        "style_recipe_sha256": recipe.get("recipe_sha256"),
        "resolved_variables": {name: effective[name] for name in required},
        "derived_prompt": derived_prompt,
        "negative_prompt": recipe.get("negative_prompt"),
        "prompt_sha256": hashlib.sha256(derived_prompt.encode("utf-8")).hexdigest(),
        "canonical": False,
        "route_request": {
            "route_class": "visual.generation",
            "authority": MODEL_ROUTER_AUTHORITY,
            "resource_authority": HRB_AUTHORITY,
            "provider": None,
            "model": None,
            "runtime": None,
            "silent_fallback_allowed": False,
        },
        "current_host_runtime_promotion_claim": False,
    }
    return receipt

def validate_consumer_binding(binding: Mapping[str, Any]) -> bool:
    if binding.get("status") not in {"MATERIALIZED_REQUIRED", "PLANNED_REQUIRED"}:
        return False
    if binding.get("parallel_style_authority_allowed") is not False:
        return False
    if binding.get("runtime_promoted") is True:
        return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FA3 Visual Style Fabric utility")
    sub = parser.add_subparsers(dest="command", required=True)

    imp = sub.add_parser("import", help="normalize a style.json into canonical FA3 recipe JSON")
    imp.add_argument("--input", required=True)
    imp.add_argument("--source-project", required=True)
    imp.add_argument("--source-revision", required=True)
    imp.add_argument("--source-license", required=True)
    imp.add_argument("--attribution", required=True)
    imp.add_argument("--source-url")

    compile_cmd = sub.add_parser("compile", help="derive a non-canonical provider-neutral prompt receipt")
    compile_cmd.add_argument("--recipe", required=True)
    compile_cmd.add_argument("--values", required=True)

    intent = sub.add_parser("intent", help="build provider-neutral Visual Intent IR")
    intent.add_argument("--recipe", required=True)
    intent.add_argument("--values")
    intent.add_argument("--scope", default="ASSET")
    intent.add_argument("--target-id")

    args = parser.parse_args(argv)
    if args.command == "import":
        source = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = normalize_recipe(
            source,
            source_project=args.source_project,
            source_revision=args.source_revision,
            source_license=args.source_license,
            attribution=args.attribution,
            source_url=args.source_url,
        )
    elif args.command == "compile":
        recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
        values = json.loads(Path(args.values).read_text(encoding="utf-8"))
        result = compile_visual_style(recipe, values=values)
    else:
        recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
        values = json.loads(Path(args.values).read_text(encoding="utf-8")) if args.values else {}
        result = build_visual_intent(recipe, values=values, scope=args.scope, target_id=args.target_id)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
