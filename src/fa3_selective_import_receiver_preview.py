"""S6 bounded application/host receiver *claim* matching for S5 deliverables.

No host discovery, API calls, file IO, asset publication, UAF execution or
authorization. Receiver inventories and chosen placements are untrusted input.
Independent FA3 application-registration, machine-role, Security, UAF, Logistics,
Evidence and (when used) HRB/Temporal gates remain mandatory.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from fa3_selective_import_preview import ALL, DELIVERY_TYPES, TARGETS

SCHEMA = "fa3.selective-receiver-handoff-preview.v1"
INVENTORY_SCHEMA = "fa3.receiver-capability-claims.v1"
_REF = re.compile(r"^ref:[A-Za-z0-9][A-Za-z0-9_.-]{0,247}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_FORMAT = re.compile(r"^[A-Za-z][A-Za-z0-9.+/\-]{0,119}$")
_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.+\-]{0,63}$")
_CONTENT = {"TEXT", "AUDIO", "VIDEO", "AUDIO_VIDEO"}
# Exact S5 intent classes. No external claim can reclassify a TEXT-only,
# AUDIO-only or silent-picture request into a different published payload.
_ALLOWED_PUBLICATION = {
    **{("TEXT", s): {"TEXT"} for s in ALL["TEXT"]},
    **{("AUDIO", s): ({"TEXT"} if s == "TRANSCRIPT_ONLY" else {"AUDIO"})
       for s in ALL["AUDIO"]},
    **{("VIDEO", s): (
        {"AUDIO_VIDEO", "VIDEO"} if s == "FULL_VIDEO" else
        {"TEXT"} if s == "TRANSCRIPT_ONLY" else
        {"AUDIO"} if s in {"FULL_AUDIO_ONLY", "MUSIC_OR_INSTRUMENTAL_ONLY",
                            "AMBIENCE_AND_SFX_ONLY"} else {"VIDEO"}
    ) for s in ALL["VIDEO"]},
}
_REQUIRED_GATES = (
    "EXISTING_APPLICATION_REGISTRY_AND_RECEIVER_VERSION",
    "EXISTING_MACHINE_ROLE_AND_HOST_IDENTITY",
    "EXISTING_SECURITY_RIGHTS_AND_HOST_NONINTERFERENCE",
    "EXISTING_UAF_CROSS_APPLICATION_DELIVERY_APPROVAL",
    "EXISTING_LOGISTICS_ASSET_STAGING_AND_PROVENANCE",
    "CANONICAL_EVIDENCE_AUTHENTICATED_RECEIVER_HANDSHAKE",
    "PER_DELIVERABLE_USER_PUBLICATION_APPROVAL",
)
_ROUNDTRIP = "EXACT_FORMAT_PAIR_VERSION_AND_FEATURE_ROUNDTRIP"


def _ref(value: Any, name: str) -> None:
    if not isinstance(value, str) or _REF.fullmatch(value) is None:
        raise ValueError(f"{name}: opaque ref required, no URL or raw credential")


def _format(value: Any, name: str, pattern: re.Pattern[str]) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name}: invalid identifier")


def _publication(value: Any) -> str:
    if not isinstance(value, dict) or set(value) != {"text", "audio", "video"}:
        raise ValueError("exact requested publication flags required")
    if any(type(item) is not bool for item in value.values()):
        raise ValueError("publication flags must be bool")
    if not any(value.values()):
        raise ValueError("cannot create an empty publish intent")
    if value["text"] and (value["audio"] or value["video"]):
        raise ValueError("text/transcript derivative must not leak AV")
    if value["text"]:
        return "TEXT"
    if value["audio"] and value["video"]:
        return "AUDIO_VIDEO"
    return "AUDIO" if value["audio"] else "VIDEO"


def _receiver_inventory(inventory: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    if not isinstance(inventory, dict) or set(inventory) != {
        "schema", "inventory_claim_ref", "receivers",
    } or inventory["schema"] != INVENTORY_SCHEMA:
        raise ValueError("invalid, untrusted receiver inventory claim")
    _ref(inventory["inventory_claim_ref"], "inventory_claim_ref")
    rows = inventory["receivers"]
    if not isinstance(rows, list) or len(rows) > 256:
        raise ValueError("at most 256 bounded receiver claims allowed")
    by_route: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in rows:
        if not isinstance(entry, dict) or set(entry) != {
            "application", "host_ref", "machine_role_ref", "app_version",
            "receiver_claim_ref", "advertised_formats",
        }:
            raise ValueError("malformed receiver claim")
        app = entry["application"]
        if not isinstance(app, str) or app not in TARGETS:
            raise ValueError("receiver may only name an existing known FA3 target")
        for field in ("host_ref", "machine_role_ref", "receiver_claim_ref"):
            _ref(entry[field], field)
        _format(entry["app_version"], "app_version", _VERSION)
        route = (app, entry["host_ref"])
        if route in by_route:
            raise ValueError("same application/host advertised twice")
        specs = entry["advertised_formats"]
        if not isinstance(specs, list) or len(specs) > 256:
            raise ValueError("receiver format claims exceed budget")
        seen_specs: set[tuple[str, ...]] = set()
        for spec in specs:
            if not isinstance(spec, dict) or set(spec) != {
                "family", "selector_id", "delivery_class", "content_kind",
                "format_id", "format_version", "editable_roundtrip_claim",
            }:
                raise ValueError("malformed per-format receiver claim")
            family, selector = spec["family"], spec["selector_id"]
            if family not in ALL or selector not in ALL[family]:
                raise ValueError("receiver cannot advertise noncanonical selector")
            if spec["delivery_class"] not in DELIVERY_TYPES or spec["content_kind"] not in _CONTENT:
                raise ValueError("receiver delivery/content class invalid")
            _format(spec["format_id"], "format_id", _FORMAT)
            _format(spec["format_version"], "format_version", _VERSION)
            if type(spec["editable_roundtrip_claim"]) is not bool:
                raise ValueError("roundtrip advertisement must be bool")
            key = (family, selector, spec["delivery_class"], spec["content_kind"],
                   spec["format_id"], spec["format_version"])
            if key in seen_specs:
                raise ValueError("duplicated receiver format claim")
            seen_specs.add(key)
        by_route[route] = entry
    return by_route


def receiver_handoff_preview(
    s5: dict[str, Any],
    inventory: dict[str, Any],
    placements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Preflight exact target-app/host/version/format choices. Always no-execution."""
    if not isinstance(s5, dict) or s5.get("schema") != "fa3.selective-delivery-preview.v1" \
            or s5.get("state") != "SELECTIVE_DELIVERY_PREVIEW_ONLY" \
            or s5.get("capability_count") != 175 or s5.get("authority") is not False:
        raise ValueError("only intact S5 no-authority delivery previews accepted")
    if s5.get("execution_authorized") is not False or any(
        s5.get("publish_" + kind) is not False for kind in ("text", "audio", "video")
    ):
        raise ValueError("S5 must not be authorized or published")
    for field in ("source_ref", "production_ref", "inspector_receipt_ref"):
        _ref(s5.get(field), field)
    _format(s5.get("source_sha256"), "source_sha256", _SHA)
    leaves = s5.get("deliverables")
    if not isinstance(leaves, list) or not (1 <= len(leaves) <= 1024) \
            or s5.get("planned_deliverable_count") != len(leaves):
        raise ValueError("invalid or incomplete S5 leaves")
    receiver_by_route = _receiver_inventory(inventory)
    if not isinstance(placements, list) or len(placements) > 1024:
        raise ValueError("bounded explicit receiver placements required")
    choices: dict[str, dict[str, Any]] = {}
    for item in placements:
        if not isinstance(item, dict) or set(item) != {
            "deliverable_ref", "target_host_ref", "format_id", "format_version",
        } or not isinstance(item["deliverable_ref"], str):
            raise ValueError("invalid explicit placement")
        _ref(item["target_host_ref"], "target_host_ref")
        _format(item["format_id"], "format_id", _FORMAT)
        _format(item["format_version"], "format_version", _VERSION)
        if item["deliverable_ref"] in choices:
            raise ValueError("duplicate receiver placement for a deliverable")
        choices[item["deliverable_ref"]] = item
    expected_refs: set[str] = set()
    outcome: list[dict[str, Any]] = []
    for leaf in leaves:
        if not isinstance(leaf, dict):
            raise ValueError("S5 deliverable must be an object")
        name, family, selector = leaf.get("deliverable_ref"), leaf.get("family"), leaf.get("selector_id")
        if not isinstance(name, str) or not name or name in expected_refs:
            raise ValueError("missing or duplicate S5 deliverable reference")
        expected_refs.add(name)
        if family not in ALL or selector not in ALL[family] or leaf.get("target_application") not in TARGETS:
            raise ValueError("S5 deliverable has an unknown family/target")
        if leaf.get("execution_authorized") is not False or any(
            leaf.get("publish_" + kind) is not False for kind in ("text", "audio", "video")
        ) or leaf.get("independent_evidence_verified") is not False \
                or leaf.get("editable_project_verified") is not False:
            raise ValueError("S5 deliverable contains forged execution or evidence claims")
        content = _publication(leaf.get("requested_publication"))
        if content not in _ALLOWED_PUBLICATION[(family, selector)]:
            raise ValueError("S5 publication intent contradicts the exact canonical selector")
        if (family == "TEXT" or selector == "TRANSCRIPT_ONLY") and content != "TEXT":
            raise ValueError("text/transcript-only leaf cannot request AV output")
        if family == "AUDIO" and content != "AUDIO" and selector != "TRANSCRIPT_ONLY":
            raise ValueError("audio source leaf cannot publish video")
        app = leaf["target_application"]
        delivery_class = leaf.get("delivery_class")
        if delivery_class not in DELIVERY_TYPES:
            raise ValueError("invalid delivery class")
        chosen = choices.get(name)
        target_host = chosen["target_host_ref"] if chosen else None
        receiver = receiver_by_route.get((app, target_host)) if target_host else None
        status = "PENDING_EXPLICIT_HOST_AND_FORMAT_CHOICE"
        if chosen and not receiver:
            status = "BLOCKED_RECEIVER_NOT_ADVERTISED_FOR_EXACT_APP_AND_HOST"
        if chosen and receiver:
            matching = [s for s in receiver["advertised_formats"] if (
                s["family"] == family and s["selector_id"] == selector and
                s["delivery_class"] == delivery_class and s["content_kind"] == content and
                s["format_id"] == chosen["format_id"] and
                s["format_version"] == chosen["format_version"]
            )]
            if not matching:
                status = "BLOCKED_EXACT_FORMAT_SELECTOR_OR_CONTENT_NOT_ADVERTISED"
            elif delivery_class == "COPY_EDITABLE_IF_ADMITTED" and not matching[0]["editable_roundtrip_claim"]:
                status = "BLOCKED_EDITABLE_ROUNDTRIP_NOT_ADVERTISED"
            else:
                status = "PENDING_INDEPENDENT_RECEIVER_HANDSHAKE_AND_ADMISSION"
        if isinstance(leaf.get("status"), str) and (
            leaf["status"].startswith("BLOCKED_") or
            leaf["status"].startswith("UNSUPPORTED") or
            "UNSUPPORTED" in leaf["status"] or
            leaf["status"] == "PENDING_DUPLICATE_DESTINATION_REVIEW"
        ):
            status = "BLOCKED_UPSTREAM_DELIVERY_OR_REQUIRES_DUPLICATE_REVIEW"
        extra = list(_REQUIRED_GATES)
        if delivery_class == "COPY_EDITABLE_IF_ADMITTED":
            extra.append(_ROUNDTRIP)
        if target_host:
            extra.extend(["EXISTING_HRB_HOST_LEASE_IF_EXECUTING",
                          "EXISTING_TEMPORAL_WORKFLOW_AND_CAP150_WHEN_REMOTE"])
        base_checks = leaf.get("required_independent_checks")
        if not isinstance(base_checks, list) or not base_checks or any(
            not isinstance(c, str) or not c for c in base_checks
        ):
            raise ValueError("S5 independent evidence checklist missing")
        fingerprint = {
            "source_sha256": s5["source_sha256"], "deliverable_ref": name,
            "target_application": app, "target_host_ref": target_host,
            "format_id": chosen["format_id"] if chosen else None,
            "format_version": chosen["format_version"] if chosen else None,
        }
        outcome.append({
            "deliverable_ref": name, "parent_leaf_index": leaf["parent_leaf_index"],
            "family": family, "selector_id": selector, "target_application": app,
            "source_sha256": s5["source_sha256"],
            "source_stream_indices": leaf["source_stream_indices"],
            "source_timebases": leaf["source_timebases"],
            "source_range": leaf["source_range"],
            "source_binding_group": leaf["source_binding_group"],
            "target_locale": leaf["target_locale"],
            "variant": leaf["variant"],
            "requested_publication": dict(leaf["requested_publication"]),
            "target_host_ref": target_host,
            "machine_role_claim_ref": receiver["machine_role_ref"] if receiver else None,
            "receiver_claim_ref": receiver["receiver_claim_ref"] if receiver else None,
            "app_version_claim": receiver["app_version"] if receiver else None,
            "format_id": chosen["format_id"] if chosen else None,
            "format_version": chosen["format_version"] if chosen else None,
            "idempotency_intent_key": hashlib.sha256(
                json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "status": status, "required_independent_checks": list(dict.fromkeys(base_checks + extra)),
            "receiver_verified": False, "format_verified": False,
            "editable_project_verified": False,
            "publish_text": False, "publish_audio": False, "publish_video": False,
            "execution_authorized": False,
        })
    if set(choices) - expected_refs:
        raise ValueError("placement points to unrequested deliverable")
    return {
        "schema": SCHEMA, "state": "RECEIVER_HANDOFF_PREVIEW_ONLY",
        "production_ref": s5["production_ref"], "source_ref": s5["source_ref"],
        "source_sha256": s5["source_sha256"],
        "inspector_receipt_ref": s5["inspector_receipt_ref"],
        "receiver_inventory_claim_ref": inventory["inventory_claim_ref"],
        "deliverable_count": len(outcome),
        "pending_receiver_count": sum(
            x["status"] == "PENDING_INDEPENDENT_RECEIVER_HANDSHAKE_AND_ADMISSION" for x in outcome
        ),
        "blocked_or_unplaced_count": sum(
            x["status"] != "PENDING_INDEPENDENT_RECEIVER_HANDSHAKE_AND_ADMISSION" for x in outcome
        ),
        "deliverables": outcome,
        "execution_authorized": False, "publish_text": False,
        "publish_audio": False, "publish_video": False,
        "authority": False, "capability_count": 175,
        "existing_owners": [
            "FA3-FILE-CONVERSION-001", "FA3-UNIFIED-ACTION-FABRIC-001",
            "FA3-CREATIVE-PROJECT-WORKFLOW-CONTRACTS-001",
            "FA3-AUTH-OBS-EVIDENCE-001", "FA3-AUTH-HOST-RESOURCE-BROKER-001",
            "FA3-LOGISTICS", "FA3-DIRECTOR-WORKFORCE",
        ],
    }
