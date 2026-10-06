#!/usr/bin/env python3
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = Path("canonical/FA3-FUTURE-APPLICATION-COMMUNICATION-BASELINE-20261006.json")
REGISTRY_PATH = Path("canonical/FA3-APPLICATION-COMMUNICATION-READINESS-REGISTRY-001.json")
ADAPTER_ID = "FA3-SHARED-APPLICATION-AGENT-ADAPTER-001"

class ApplicationCommunicationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason: str

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ApplicationCommunicationError("FAC-JSON-OBJECT-REQUIRED", str(path))
    return value

def validate_identity(identity: dict[str, Any], application_id: str) -> None:
    required = ("application_id", "identity_revision", "application_class", "provenance_refs")
    missing = [key for key in required if not identity.get(key)]
    if missing:
        raise ApplicationCommunicationError("FAC-IDENTITY-MISSING", ",".join(missing))
    if identity["application_id"] != application_id:
        raise ApplicationCommunicationError("FAC-IDENTITY-MISMATCH", application_id)
    if not isinstance(identity.get("provenance_refs"), list) or not identity["provenance_refs"]:
        raise ApplicationCommunicationError("FAC-IDENTITY-PROVENANCE-MISSING", application_id)

def validate_operation_descriptor(descriptor: dict[str, Any], application_id: str) -> None:
    if descriptor.get("schema") != "fa3.application-operation-descriptor.v1":
        raise ApplicationCommunicationError("FAC-OP-DESCRIPTOR-SCHEMA", application_id)
    if descriptor.get("application_id") != application_id:
        raise ApplicationCommunicationError("FAC-OP-DESCRIPTOR-IDENTITY", application_id)
    if not descriptor.get("descriptor_revision") or not isinstance(descriptor.get("provenance_refs"), list) or not descriptor["provenance_refs"]:
        raise ApplicationCommunicationError("FAC-OP-DESCRIPTOR-PROVENANCE", application_id)
    operations = descriptor.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ApplicationCommunicationError("FAC-OP-DESCRIPTOR-EMPTY", application_id)
    seen: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            raise ApplicationCommunicationError("FAC-OPERATION-INVALID", application_id)
        ref = operation.get("operation_ref")
        if not isinstance(ref, str) or not ref or ref in seen:
            raise ApplicationCommunicationError("FAC-OPERATION-REF", application_id)
        seen.add(ref)
        if operation.get("direction") not in {"SEND", "RECEIVE", "BIDIRECTIONAL", "LOCAL"}:
            raise ApplicationCommunicationError("FAC-OPERATION-DIRECTION", ref)
        if not isinstance(operation.get("effectful"), bool):
            raise ApplicationCommunicationError("FAC-OPERATION-EFFECTFUL", ref)
        if not isinstance(operation.get("capability_refs"), list):
            raise ApplicationCommunicationError("FAC-OPERATION-CAPABILITIES", ref)
        if operation["effectful"] and not operation.get("uaf_action_ref"):
            raise ApplicationCommunicationError("FAC-EFFECTFUL-UAF-REF", ref)

def validate_application_entry(entry: dict[str, Any]) -> None:
    application_id = entry.get("application_id")
    if not isinstance(application_id, str) or not application_id:
        raise ApplicationCommunicationError("FAC-APPLICATION-ID", "missing application_id")
    validate_identity(entry.get("canonical_identity") or {}, application_id)
    validate_operation_descriptor(entry.get("operation_descriptor") or {}, application_id)
    if (entry.get("agent_adapter") or {}).get("adapter_id") != ADAPTER_ID:
        raise ApplicationCommunicationError("FAC-SHARED-ADAPTER-REQUIRED", application_id)
    admission = entry.get("self_communication_admission") or {}
    for key in ("sender", "receiver", "round_trip", "result"):
        if admission.get(key) != "PASS":
            raise ApplicationCommunicationError("FAC-SELF-ADMISSION-NOT-PASS", f"{application_id}:{key}")
    if not isinstance(admission.get("evidence_refs"), list) or not admission["evidence_refs"]:
        raise ApplicationCommunicationError("FAC-SELF-ADMISSION-EVIDENCE", application_id)

def validate_relationship(relationship: dict[str, Any]) -> None:
    a = relationship.get("application_a")
    b = relationship.get("application_b")
    if not isinstance(a, str) or not a or not isinstance(b, str) or not b or a == b:
        raise ApplicationCommunicationError("FAC-RELATIONSHIP-IDENTITY", "application_a/application_b")
    for key in ("a_to_b", "b_to_a"):
        direction = relationship.get(key) or {}
        if direction.get("sender_admission") != "PASS" or direction.get("receiver_admission") != "PASS":
            raise ApplicationCommunicationError("FAC-DIRECTIONAL-ADMISSION-NOT-PASS", key)
    round_trip = relationship.get("round_trip") or {}
    if round_trip.get("result") != "PASS":
        raise ApplicationCommunicationError("FAC-ROUND-TRIP-NOT-PASS", f"{a}<->{b}")
    if not isinstance(round_trip.get("evidence_refs"), list) or not round_trip["evidence_refs"]:
        raise ApplicationCommunicationError("FAC-ROUND-TRIP-EVIDENCE", f"{a}<->{b}")
    if relationship.get("result") != "PASS":
        raise ApplicationCommunicationError("FAC-RELATIONSHIP-NOT-PASS", f"{a}<->{b}")

def application_ready_admission(application_id: str, *, root: Path | None = None) -> AdmissionDecision:
    base = (root or ROOT).resolve()
    try:
        baseline = _load(base / BASELINE_PATH)
        registry = _load(base / REGISTRY_PATH)
    except (OSError, json.JSONDecodeError, ApplicationCommunicationError) as exc:
        return AdmissionDecision(False, "registry_unavailable:" + str(exc))
    if application_id in set(baseline.get("grandfathered_application_ids") or []):
        return AdmissionDecision(True, "POLICY_EPOCH_BASELINE_APPLICATION")
    entries = [row for row in registry.get("applications", []) if isinstance(row, dict) and row.get("application_id") == application_id]
    if len(entries) != 1:
        return AdmissionDecision(False, "future_application_readiness_entry_required")
    try:
        validate_application_entry(entries[0])
    except ApplicationCommunicationError as exc:
        return AdmissionDecision(False, exc.code)
    return AdmissionDecision(True, "PASS")

class SharedApplicationAgentAdapter:
    def __init__(self, entry: dict[str, Any]):
        validate_application_entry(entry)
        self.application_id = entry["application_id"]
        self.operations = {row["operation_ref"]: row for row in entry["operation_descriptor"]["operations"]}

    def prepare_handoff(self, operation_ref: str, target_application: str, *, correlation_id: str, work_context_ref: str, capability_grant_ref: str, provenance_refs: list[str]) -> dict[str, Any]:
        operation = self.operations.get(operation_ref)
        if operation is None:
            raise ApplicationCommunicationError("FAC-UNDECLARED-OPERATION", operation_ref)
        return {"kind":"OPERATION_REQUEST","source_application":self.application_id,"target_application":target_application,"correlation_id":correlation_id,"operation_ref":operation_ref,"work_context_ref":work_context_ref,"capability_grant_ref":capability_grant_ref,"provenance_refs":provenance_refs,"uaf_action_ref":operation.get("uaf_action_ref"),"adapter_id":ADAPTER_ID,"authorization_granted":False,"execution_started":False}
