#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from typing import Any

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SKILL_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

SECURITY_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "PROMPT_INJECTION": (
        re.compile(r"\bignore\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior)\s+instructions\b", re.I),
        re.compile(r"\bdisregard\s+(?:the\s+)?(?:system|developer)\s+(?:message|instructions)\b", re.I),
    ),
    "INSTRUCTION_OVERRIDE": (
        re.compile(r"\boverride\s+(?:the\s+)?(?:system|developer|policy|guardrail)", re.I),
    ),
    "SECRET_OR_CREDENTIAL_ACCESS": (
        re.compile(r"\b(?:read|print|dump|steal|exfiltrate)\b.{0,48}\b(?:api[-_ ]?key|token|password|secret|credential)\b", re.I | re.S),
    ),
    "DATA_EXFILTRATION": (
        re.compile(r"\b(?:upload|send|post|forward)\b.{0,64}\b(?:secret|credential|token|private\s+data|user\s+data)\b", re.I | re.S),
    ),
    "PRIVILEGE_ESCALATION": (
        re.compile(r"\bsudo\b", re.I),
        re.compile(r"\bsetcap\b", re.I),
        re.compile(r"\bchmod\s+777\b", re.I),
    ),
    "UNBOUNDED_SHELL_EXECUTION": (
        re.compile(r"\b(?:bash|sh)\s+-c\b", re.I),
        re.compile(r"\beval\s+\$", re.I),
    ),
    "NETWORK_BOOTSTRAP": (
        re.compile(r"\bcurl\b.{0,160}\|\s*(?:sh|bash)\b", re.I | re.S),
        re.compile(r"\bwget\b.{0,160}\|\s*(?:sh|bash)\b", re.I | re.S),
        re.compile(r"\bnpx\s+", re.I),
    ),
    "PATH_ESCAPE": (
        re.compile(r"(?:^|[\s'\"\`])\.\./", re.M),
    ),
    "MCP_TOOL_POISONING": (
        re.compile(r"\btrust\s+(?:this\s+)?tool\b.{0,64}\b(?:without|skip|bypass)\b.{0,32}\b(?:check|approval|authorization|validation)\b", re.I | re.S),
    ),
    "MEMORY_POISONING": (
        re.compile(r"\b(?:store|remember)\b.{0,80}\b(?:permanently|across\s+sessions)\b.{0,80}\b(?:ignore|override|bypass)\b", re.I | re.S),
    ),
    "OBFUSCATED_EXECUTION": (
        re.compile(r"\bbase64\s+(?:-d|--decode)\b.{0,160}\|\s*(?:sh|bash)\b", re.I | re.S),
        re.compile(r"\bexec\s*\(.{0,80}base64", re.I | re.S),
    ),
    "SELF_MODIFYING_AGENT_INSTRUCTIONS": (
        re.compile(r"\b(?:modify|rewrite|append\s+to|overwrite)\b.{0,64}\b(?:AGENTS\.md|SKILL\.md|system\s+prompt)\b", re.I | re.S),
    ),
}


def _scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_skill_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not isinstance(text, str) or not text.startswith("---\n"):
        raise ValueError("SKILL.md YAML frontmatter required")
    lines = text.splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("unterminated SKILL.md frontmatter") from exc
    meta: dict[str, Any] = {}
    current_map: str | None = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")):
            if current_map is None or ":" not in raw:
                raise ValueError("unsupported nested frontmatter")
            key, value = raw.strip().split(":", 1)
            bucket = meta.setdefault(current_map, {})
            if not isinstance(bucket, dict):
                raise ValueError("invalid mapping frontmatter")
            bucket[key.strip()] = _scalar(value)
            continue
        if ":" not in raw:
            raise ValueError("unsupported frontmatter line")
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError("empty frontmatter key")
        if value == "":
            meta[key] = {}
            current_map = key
        else:
            meta[key] = _scalar(value)
            current_map = None
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


def normalize_agent_skill(
    text: str,
    *,
    source_repository: str,
    source_commit: str,
    source_path: str = "SKILL.md",
    skill_dir_name: str | None = None,
) -> dict[str, Any]:
    try:
        meta, body = parse_skill_frontmatter(text)
    except ValueError as exc:
        return {"status": "REJECTED_PARSE", "compatible_parse": False, "reason": str(exc)}
    name = str(meta.get("name", ""))
    description = str(meta.get("description", ""))
    name_ok = bool(SKILL_NAME.fullmatch(name)) and "--" not in name
    description_ok = 1 <= len(description) <= 1024
    commit_ok = bool(SHA40.fullmatch(source_commit))
    directory_ok = skill_dir_name is None or skill_dir_name == name
    compatible = name_ok and description_ok and commit_ok and directory_ok
    return {
        "schema": "fa3.external-skill-normalization-candidate.v1",
        "status": "UNTRUSTED_CANDIDATE" if compatible else "REJECTED_COMPATIBILITY",
        "compatible_parse": compatible,
        "source": {
            "repository": source_repository,
            "commit": source_commit,
            "path": source_path,
            "immutable": commit_ok,
        },
        "upstream_metadata": meta,
        "body": body,
        "original_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "allowed_tools_authority": False,
        "scripts_inert": True,
        "direct_admission": False,
        "direct_activation": False,
        "fa3_required_additions": [
            "version",
            "trigger",
            "guardrails",
            "acceptance_checks",
            "permissions",
            "dependency_graph",
            "distribution_classification",
            "security_inspection",
            "behavioral_and_routing_evaluation",
        ],
    }


def security_inspection(text: str) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for category, patterns in SECURITY_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            findings.append({"category": category, "severity": "BLOCKING_FOR_ADMISSION"})
    return {
        "schema": "fa3.skill-security-inspection.v1",
        "result": "PASS" if not findings else "REVIEW_REQUIRED",
        "findings": findings,
        "authority": False,
        "execution_performed": False,
    }


def routing_eval(cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for row in cases:
        eligible = list(dict.fromkeys(row.get("eligible", [])))
        selected = list(dict.fromkeys(row.get("selected", [])))
        expected = list(dict.fromkeys(row.get("expected", [])))
        subset_ok = set(selected).issubset(set(eligible))
        exact_ok = set(selected) == set(expected) and len(selected) == len(expected)
        ok = subset_ok and exact_ok
        results.append({"case_id": row.get("case_id"), "status": "PASS" if ok else "FAIL", "subset_ok": subset_ok, "exact_ok": exact_ok})
    return {
        "schema": "fa3.skill-routing-eval.v1",
        "result": "PASS" if results and all(x["status"] == "PASS" for x in results) else "FAIL",
        "cases": results,
        "candidate_expansion": any(not x["subset_ok"] for x in results),
    }


def improvement_candidate_allowed(record: dict[str, Any]) -> bool:
    try:
        source = record["source"]
        candidate = record["candidate"]
        if record.get("source_admission_status") != "ADMITTED":
            return False
        if not SHA256.fullmatch(str(source.get("content_sha256", ""))):
            return False
        if not SHA256.fullmatch(str(candidate.get("content_sha256", ""))):
            return False
        if source.get("version") == candidate.get("version") and source.get("content_sha256") == candidate.get("content_sha256"):
            return False
        if record.get("offline") is not True or record.get("live_self_modification") is not False:
            return False
        if record.get("auto_promote") is not False or record.get("new_admission_required") is not True:
            return False
        if record.get("regression_eval") != "PASS" or record.get("held_out_validation") != "PASS" or record.get("security_reinspection") != "PASS":
            return False
        if record.get("optimizer_model_used"):
            if record.get("model_router") != "FA3-AUTH-MODEL-ROUTER-001" or record.get("resource_authority") != "FA3-AUTH-HOST-RESOURCE-BROKER-001":
                return False
        return True
    except (KeyError, TypeError, AttributeError):
        return False
