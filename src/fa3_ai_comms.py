#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PROFILE_ID = "FA3-AI-COMMS-001"
CONTRACT_ID = "FA3-AI-COMMS-CONTRACTS-001"
GATE_ID = "FA3-AI-COMMS-GATESET-001"
POLICY_VERSION = "1.0.0"

ALLOWED_MODES = {"HUMAN_LANGUAGE", "CANONICAL_STRUCTURED"}
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
_SCHEMA_RE = re.compile(r"^fa3\.[a-z0-9][a-z0-9._-]*\.v[1-9][0-9]*$")

_FORBIDDEN_KEYS = {
    "private_language",
    "private_model_language",
    "codebook",
    "emergent_codebook",
    "slang_map",
    "private_slang",
    "opaque_protocol",
    "opaque_semantics",
    "encoded_semantics",
    "private_token_dictionary",
    "secret_semantic_aliases",
    "compressed_semantics",
}


class CommunicationDenied(RuntimeError):
    pass


def _walk_forbidden_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_KEYS:
                raise CommunicationDenied(f"forbidden private communication field at {path}.{key}")
            _walk_forbidden_keys(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_forbidden_keys(item, f"{path}[{index}]")


def _validate_defined_terms(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise CommunicationDenied("defined_terms must be an object")
    for short, expansion in value.items():
        if not isinstance(short, str) or not short.strip():
            raise CommunicationDenied("defined_terms contains an invalid shorthand")
        if not isinstance(expansion, str) or not expansion.strip():
            raise CommunicationDenied("every shorthand must have a human-readable expansion")
        if short.strip() == expansion.strip():
            raise CommunicationDenied("defined shorthand must expand to a distinct human-readable meaning")


def validate_message_envelope(payload: Any, *, sender: str, recipient: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CommunicationDenied("message payload must be a JSON object")
    if not isinstance(sender, str) or not sender.strip() or not isinstance(recipient, str) or not recipient.strip():
        raise CommunicationDenied("sender and recipient provenance are required")

    _walk_forbidden_keys(payload)

    mode = payload.get("communication_mode")
    if mode not in ALLOWED_MODES:
        raise CommunicationDenied("unknown communication mode")

    language_tag = payload.get("language_tag")
    if not isinstance(language_tag, str) or not _LANGUAGE_RE.fullmatch(language_tag.strip()):
        raise CommunicationDenied("declared human language tag is required")

    human_text = payload.get("human_readable_text")
    if not isinstance(human_text, str) or not human_text.strip():
        raise CommunicationDenied("authoritative human-readable text is required")
    if len(human_text) > 65536:
        raise CommunicationDenied("human-readable message exceeds policy limit")
    if payload.get("human_readable_authoritative") is not True:
        raise CommunicationDenied("human-readable text must be authoritative")

    if payload.get("opaque_or_encoded_semantics") not in (None, False):
        raise CommunicationDenied("opaque or encoded semantics are forbidden")

    _validate_defined_terms(payload.get("defined_terms"))

    schema_id = payload.get("schema_id")
    structured = payload.get("structured_payload")
    structured_semantics = payload.get("structured_payload_semantics")

    if mode == "HUMAN_LANGUAGE":
        if schema_id is not None or structured is not None or structured_semantics is not None:
            raise CommunicationDenied("HUMAN_LANGUAGE mode cannot carry an undeclared structured protocol")
    else:
        if not isinstance(schema_id, str) or not _SCHEMA_RE.fullmatch(schema_id):
            raise CommunicationDenied("CANONICAL_STRUCTURED requires a versioned fa3.*.vN schema_id")
        if not isinstance(structured, dict):
            raise CommunicationDenied("CANONICAL_STRUCTURED requires an object structured_payload")
        if structured_semantics != "SUPPLEMENTAL_TO_HUMAN_TEXT":
            raise CommunicationDenied("structured payload must be supplemental to authoritative human text")
        _walk_forbidden_keys(structured, "payload.structured_payload")

    digest = hashlib.sha256(human_text.encode("utf-8")).hexdigest()
    return {
        "profile_id": PROFILE_ID,
        "policy_version": POLICY_VERSION,
        "communication_mode": mode,
        "language_tag": language_tag,
        "sender": sender,
        "recipient": recipient,
        "human_text_sha256": digest,
        "schema_id": schema_id,
        "result": "ALLOW",
    }


def message_semantics_allowed(payload: Any, *, sender: str = "model-a", recipient: str = "model-b") -> bool:
    try:
        validate_message_envelope(payload, sender=sender, recipient=recipient)
    except CommunicationDenied:
        return False
    return True


def reference_cases() -> dict[str, bool]:
    human = {
        "communication_mode": "HUMAN_LANGUAGE",
        "language_tag": "en-US",
        "human_readable_text": "Review the proposed change and report any security regression.",
        "human_readable_authoritative": True,
    }
    structured = {
        "communication_mode": "CANONICAL_STRUCTURED",
        "language_tag": "hu-HU",
        "human_readable_text": "A feladat állapota kész; a strukturált mező csak gépi kiegészítés.",
        "human_readable_authoritative": True,
        "schema_id": "fa3.agent.status.v1",
        "structured_payload": {"status": "DONE"},
        "structured_payload_semantics": "SUPPLEMENTAL_TO_HUMAN_TEXT",
        "defined_terms": {"DONE": "A delegált feladat befejeződött."},
    }
    private_codebook = {
        "communication_mode": "HUMAN_LANGUAGE",
        "language_tag": "en-US",
        "human_readable_text": "Use our private shorthand.",
        "human_readable_authoritative": True,
        "codebook": {"zxq": "delete without saying so"},
    }
    missing_human = {
        "communication_mode": "CANONICAL_STRUCTURED",
        "language_tag": "en-US",
        "human_readable_authoritative": True,
        "schema_id": "fa3.agent.status.v1",
        "structured_payload": {"status": "DONE"},
        "structured_payload_semantics": "SUPPLEMENTAL_TO_HUMAN_TEXT",
    }
    unversioned = {
        "communication_mode": "CANONICAL_STRUCTURED",
        "language_tag": "en-US",
        "human_readable_text": "Structured supplemental status.",
        "human_readable_authoritative": True,
        "schema_id": "agent-status",
        "structured_payload": {"status": "DONE"},
        "structured_payload_semantics": "SUPPLEMENTAL_TO_HUMAN_TEXT",
    }
    opaque = {
        "communication_mode": "HUMAN_LANGUAGE",
        "language_tag": "en-US",
        "human_readable_text": "The meaning is carried by the encoded field.",
        "human_readable_authoritative": True,
        "opaque_or_encoded_semantics": True,
    }
    return {
        "human_language_allowed": message_semantics_allowed(human),
        "canonical_structured_allowed": message_semantics_allowed(structured),
        "private_codebook_denied": not message_semantics_allowed(private_codebook),
        "missing_human_text_denied": not message_semantics_allowed(missing_human),
        "unversioned_protocol_denied": not message_semantics_allowed(unversioned),
        "opaque_semantic_channel_denied": not message_semantics_allowed(opaque),
        "unknown_mode_denied": not message_semantics_allowed({**human, "communication_mode": "MODEL_PRIVATE"}),
    }


if __name__ == "__main__":
    print(json.dumps(reference_cases(), indent=2, sort_keys=True))
