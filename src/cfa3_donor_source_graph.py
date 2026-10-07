#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import os
import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

REGISTRY_REL = "canonical/FA3-DONOR-REFERENCE-REGISTRY-001.json"
MAX_DEPTH = 5

FOUNDATIONAL_RELATIONS = {
    "SDK", "AGENT_SDK", "PLUGIN_SDK", "ENGINE_SDK", "HARDWARE_SDK", "API_SDK",
    "SKILL", "SKILL_FRAMEWORK", "AGENT", "AGENT_FRAMEWORK", "PLUGIN",
    "PLUGIN_FRAMEWORK", "CODEC", "MEDIA_FRAMEWORK", "PROTOCOL",
    "INTEROPERABILITY_TOOLKIT", "SHARED_LIBRARY", "REFERENCE_IMPLEMENTATION",
}
HIGH_RELATIONS = FOUNDATIONAL_RELATIONS | {
    "TOOLKIT", "LIBRARY", "FRAMEWORK", "API", "ENGINE", "EXTENSION", "UPSTREAM",
}
REFERENCE_RELATIONS = {
    "DOCUMENTATION", "SPECIFICATION", "RESEARCH", "ORGANIZATION_INDEX",
    "TOPIC_INDEX", "DISCOVERY_INDEX", "EXAMPLE", "SAMPLE", "RELATED_PROJECT",
}
UNKNOWN_RIGHTS = {"NOASSERTION", "NONE", "UNKNOWN", ""}
URL_RE = re.compile(r"""https?://[^\s<>\]\[()"']+""", re.I)
GITHUB_REPO_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/#?]+?)(?:\.git)?/?$", re.I)
GITHUB_ORG_RE = re.compile(r"^https?://github\.com/([^/]+)/?$", re.I)
GITHUB_TOPIC_RE = re.compile(r"^https?://github\.com/topics/([^/?#]+)/?$", re.I)

RELATION_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("AGENT_SDK", ("agent sdk", "agents sdk")),
    ("PLUGIN_SDK", ("plugin sdk", "extension sdk")),
    ("ENGINE_SDK", ("engine sdk",)),
    ("HARDWARE_SDK", ("hardware sdk", "gpu sdk", "npu sdk")),
    ("API_SDK", ("api sdk", "client sdk")),
    ("SKILL_FRAMEWORK", ("skill framework", "skills framework")),
    ("AGENT_FRAMEWORK", ("agent framework", "multi-agent framework", "agentic framework")),
    ("PLUGIN_FRAMEWORK", ("plugin framework", "extension framework")),
    ("MEDIA_FRAMEWORK", ("media framework", "multimedia framework")),
    ("INTEROPERABILITY_TOOLKIT", ("interop toolkit", "interoperability toolkit")),
    ("REFERENCE_IMPLEMENTATION", ("reference implementation",)),
    ("SHARED_LIBRARY", ("shared library",)),
    ("SDK", (" sdk", "sdk ", "software development kit")),
    ("SKILL", ("skill", "skills")),
    ("AGENT", ("agent", "agentic")),
    ("PLUGIN", ("plugin", "plug-in", "extension")),
    ("CODEC", ("codec", "encoder", "decoder")),
    ("PROTOCOL", ("protocol", "specification")),
    ("TOOLKIT", ("toolkit", "tool kit")),
    ("FRAMEWORK", ("framework",)),
    ("LIBRARY", ("library",)),
    ("API", (" api", "api ")),
    ("ENGINE", ("engine",)),
    ("EXAMPLE", ("example",)),
    ("SAMPLE", ("sample",)),
    ("DOCUMENTATION", ("docs", "documentation", "guide")),
    ("RESEARCH", ("paper", "research")),
]

def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EXPECTED_JSON_OBJECT:" + str(path))
    return value

def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def normalize_url(url: str) -> str:
    value = url.strip().rstrip(".,;:")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("UNSUPPORTED_URL_SCHEME")
    host = (parsed.hostname or "").casefold()
    if not host:
        raise ValueError("URL_HOST_MISSING")
    path = re.sub(r"/+", "/", parsed.path or "/")
    if host == "github.com":
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2 and parts[0].casefold() != "topics":
            path = "/" + parts[0] + "/" + parts[1].removesuffix(".git")
        elif len(parts) == 1:
            path = "/" + parts[0]
        elif len(parts) >= 2 and parts[0].casefold() == "topics":
            path = "/topics/" + parts[1]
    query = parsed.query if host != "github.com" else ""
    return urllib.parse.urlunsplit((parsed.scheme.lower(), host, path.rstrip("/") or "/", query, ""))

def normalized_key(url: str) -> str:
    value = normalize_url(url)
    m = GITHUB_TOPIC_RE.match(value)
    if m:
        return "github:topics/" + m.group(1).casefold()
    m = GITHUB_REPO_RE.match(value)
    if m:
        return "github:" + m.group(1).casefold() + "/" + m.group(2).casefold()
    m = GITHUB_ORG_RE.match(value)
    if m:
        return "github:" + m.group(1).casefold()
    return value

def source_kind(url: str) -> str:
    value = normalize_url(url)
    if GITHUB_TOPIC_RE.match(value):
        return "GITHUB_TOPIC"
    if GITHUB_REPO_RE.match(value):
        return "GITHUB_REPOSITORY"
    if GITHUB_ORG_RE.match(value):
        return "GITHUB_ORGANIZATION_OR_PROFILE"
    return "WEBSITE"

def classify_relation(context: str, url: str) -> str:
    text = " " + context.casefold() + " "
    for relation, patterns in RELATION_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return relation
    kind = source_kind(url)
    if kind == "GITHUB_TOPIC":
        return "TOPIC_INDEX"
    if kind == "GITHUB_ORGANIZATION_OR_PROFILE":
        return "ORGANIZATION_INDEX"
    return "RELATED_PROJECT"

def classify_priority(
    relation_type: str,
    *,
    license_spdx: str | None = None,
    archived: bool = False,
    security_blocked: bool = False,
    current_phase_relevant: bool = True,
) -> dict[str, Any]:
    relation = relation_type.upper()
    lic = (license_spdx or "UNKNOWN").upper()
    blockers: list[str] = []
    if archived:
        blockers.append("UPSTREAM_ARCHIVED")
    if security_blocked:
        blockers.append("SECURITY_BLOCK")
    if lic in UNKNOWN_RIGHTS:
        blockers.append("RIGHTS_REVIEW_REQUIRED")

    if relation in FOUNDATIONAL_RELATIONS:
        strategic = "CRITICAL" if relation in {
            "SDK", "AGENT_SDK", "PLUGIN_SDK", "ENGINE_SDK", "HARDWARE_SDK",
            "API_SDK", "CODEC", "SKILL", "AGENT_FRAMEWORK", "PLUGIN_FRAMEWORK",
        } else "HIGH"
        priority = "P0" if current_phase_relevant else "P1"
    elif relation in HIGH_RELATIONS:
        strategic = "HIGH"
        priority = "P1" if current_phase_relevant else "P2"
    elif relation in REFERENCE_RELATIONS:
        strategic = "MEDIUM"
        priority = "P3"
    else:
        strategic = "LOW"
        priority = "P3"

    if security_blocked:
        priority = "P4"
    elif archived and priority in {"P0", "P1"}:
        priority = "P2"
    elif lic in UNKNOWN_RIGHTS and priority == "P0":
        priority = "P1"

    return {
        "strategic_value": strategic,
        "integration_priority": priority,
        "blockers": blockers,
        "depth_is_ranking_factor": False,
    }

def _safe_public_http_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        host = parsed.hostname.casefold()
        if host in {"localhost", "localhost.localdomain"}:
            return False
        try:
            ip = ipaddress.ip_address(host)
            return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
        except ValueError:
            return True
    except Exception:
        return False

def extract_links(text: str) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for match in URL_RE.finditer(text):
        raw = match.group(0).rstrip("`*_")
        if not _safe_public_http_url(raw):
            continue
        try:
            url = normalize_url(raw)
            key = normalized_key(url)
        except ValueError:
            continue
        if key in seen:
            continue
        seen.add(key)
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 120)
        context = re.sub(r"\\s+", " ", text[start:end])
        result.append({"url": url, "normalized_key": key, "context": context})
    return result

def registry_identity_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in registry.get("entries", []):
        if not isinstance(row, dict) or not isinstance(row.get("source"), dict):
            continue
        key = row["source"].get("normalized_key")
        if isinstance(key, str) and key:
            if key in out:
                raise ValueError("DUPLICATE_CANONICAL_SOURCE_KEY:" + key)
            out[key] = row
    return out

def root_queue_priority(row: dict[str, Any]) -> int:
    source = row.get("source", {}) if isinstance(row.get("source"), dict) else {}
    text = " ".join(
        [str(row.get("name", "")), str(source.get("kind", ""))]
        + [str(x) for key in ("tags", "capability_hints", "domain_hints", "target_hints") for x in (row.get(key, []) if isinstance(row.get(key), list) else [])]
    ).casefold()
    if any(token in text for token in ("sdk", "skill", "codec", "plugin", "agent", "toolkit", "framework")):
        return 0
    if (
        source.get("kind") in {"GITHUB_TOPIC", "GITHUB_ORGANIZATION", "GITHUB_PROFILE", "DISCOVERY_INDEX", "RESEARCH_DISCOVERY_INDEX", "GITHUB_CATALOG", "GIST", "GITHUB_ORG"}
        or bool(source.get("discovery_urls"))
        or bool(row.get("upstream_repository_references"))
        or any(token in text for token in ("discovery", "catalog", "index", "awesome", "ecosystem"))
    ):
        return 1
    if str(source.get("kind", "")).startswith("GITHUB"):
        return 2
    return 3

def seed_graph(registry: dict[str, Any]) -> dict[str, Any]:
    identities = registry_identity_map(registry)
    nodes: dict[str, dict[str, Any]] = {}
    queue: list[dict[str, Any]] = []
    for key, row in sorted(identities.items()):
        source = row["source"]
        locator = source.get("locator")
        nodes[key] = {
            "source_id": "src-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
            "normalized_key": key,
            "locator": locator,
            "source_kind": source.get("kind"),
            "min_depth": 0,
            "canonical_donor_id": row.get("donor_id"),
            "canonical_lifecycle": row.get("status"),
            "registration_state": "CANONICAL_DONOR",
            "root_donor_ids": [row.get("donor_id")],
            "relation_types": ["ROOT_DONOR"],
            "assessment": {
                "strategic_value": "UNASSESSED",
                "integration_priority": "UNASSESSED",
                "depth_is_ranking_factor": False,
            },
        }
        if isinstance(locator, str) and locator.startswith(("http://", "https://")) and _safe_public_http_url(locator):
            queue.append({"normalized_key": key, "url": locator, "depth": 0, "root_donor_id": row.get("donor_id"), "priority": root_queue_priority(row)})
    queue.sort(key=lambda item: (item["priority"], item["normalized_key"]))
    return {
        "schema": "cfa3.donor-source-graph.v1",
        "authority": False,
        "capability_baseline": 175,
        "capability_delta": 0,
        "architectural_authority_delta": 0,
        "max_depth": MAX_DEPTH,
        "nodes": nodes,
        "edges": [],
        "queue": queue,
    }

def add_discovery(
    graph: dict[str, Any],
    *,
    parent_key: str,
    child_url: str,
    depth: int,
    relation_type: str,
    root_donor_id: str,
    evidence: dict[str, Any],
    canonical_record: dict[str, Any] | None = None,
) -> bool:
    if depth < 1 or depth > MAX_DEPTH:
        raise ValueError("DISCOVERY_DEPTH_OUT_OF_RANGE")
    child_key = normalized_key(child_url)
    if child_key == parent_key:
        return False
    nodes = graph["nodes"]
    priority = classify_priority(relation_type)
    node = nodes.get(child_key)
    created = node is None
    if node is None:
        nodes[child_key] = {
            "source_id": "src-" + hashlib.sha256(child_key.encode("utf-8")).hexdigest()[:16],
            "normalized_key": child_key,
            "locator": normalize_url(child_url),
            "source_kind": source_kind(child_url),
            "min_depth": depth,
            "canonical_donor_id": canonical_record.get("donor_id") if canonical_record else None,
            "canonical_lifecycle": canonical_record.get("status") if canonical_record else None,
            "registration_state": "CANONICAL_DONOR" if canonical_record else "DISCOVERED_UNREGISTERED",
            "root_donor_ids": [root_donor_id],
            "relation_types": [relation_type],
            "assessment": priority,
            "upstream_observation": {
                "license_spdx": None,
                "archived": None,
                "updated_at": None,
                "pushed_at": None,
                "security_review": "REQUIRED",
                "code_reuse_policy": "REFERENCE_ONLY_PENDING_RIGHTS",
                "runtime_provider_model_admission": "NOT_GRANTED",
            },
        }
    else:
        node["min_depth"] = min(int(node.get("min_depth", depth)), depth)
        if root_donor_id not in node["root_donor_ids"]:
            node["root_donor_ids"].append(root_donor_id)
            node["root_donor_ids"].sort()
        if relation_type not in node["relation_types"]:
            node["relation_types"].append(relation_type)
            node["relation_types"].sort()
        rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "UNASSESSED": 9}
        old = node.get("assessment", {})
        if rank.get(priority["integration_priority"], 9) < rank.get(old.get("integration_priority"), 9):
            node["assessment"] = priority

    edge = {
        "parent_key": parent_key,
        "child_key": child_key,
        "depth": depth,
        "relation_type": relation_type,
        "root_donor_id": root_donor_id,
        "evidence": evidence,
    }
    fingerprint = json.dumps(edge, sort_keys=True, ensure_ascii=False)
    existing = {json.dumps(row, sort_keys=True, ensure_ascii=False) for row in graph["edges"]}
    if fingerprint not in existing:
        graph["edges"].append(edge)
    return created

def update_node_observation(node: dict[str, Any], metadata: dict[str, Any]) -> None:
    relation = next((x for x in node.get("relation_types", []) if x != "ROOT_DONOR"), "RELATED_PROJECT")
    if node.get("relation_types") != ["ROOT_DONOR"]:
        node["assessment"] = classify_priority(
            relation,
            license_spdx=metadata.get("license_spdx"),
            archived=bool(metadata.get("archived")),
            security_blocked=bool(metadata.get("security_blocked")),
        )
    node["upstream_observation"] = {
        "license_spdx": metadata.get("license_spdx"),
        "archived": metadata.get("archived"),
        "updated_at": metadata.get("updated_at"),
        "pushed_at": metadata.get("pushed_at"),
        "security_review": "REQUIRED",
        "code_reuse_policy": (
            "REFERENCE_ONLY_PENDING_RIGHTS"
            if (metadata.get("license_spdx") or "UNKNOWN").upper() in UNKNOWN_RIGHTS
            else "LICENSE_RIGHTS_SECURITY_REVIEW_REQUIRED"
        ),
        "runtime_provider_model_admission": "NOT_GRANTED",
    }

def build_indexes(graph: dict[str, Any]) -> dict[str, Any]:
    priority: dict[str, list[str]] = {p: [] for p in ("P0", "P1", "P2", "P3", "P4", "UNASSESSED")}
    strategic: dict[str, list[str]] = {p: [] for p in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "HISTORICAL", "UNASSESSED")}
    relation: dict[str, list[str]] = {}
    depth: dict[str, list[str]] = {f"L{i}": [] for i in range(0, MAX_DEPTH + 1)}
    for key, node in graph["nodes"].items():
        assessment = node.get("assessment", {})
        priority.setdefault(assessment.get("integration_priority", "UNASSESSED"), []).append(key)
        strategic.setdefault(assessment.get("strategic_value", "UNASSESSED"), []).append(key)
        depth.setdefault("L" + str(node.get("min_depth", 0)), []).append(key)
        for rel in node.get("relation_types", []):
            relation.setdefault(rel, []).append(key)
    for mapping in (priority, strategic, relation, depth):
        for values in mapping.values():
            values.sort()
    return {
        "integration_priority": priority,
        "strategic_value": strategic,
        "relation_type": relation,
        "discovery_depth": depth,
        "fast_access_p0_p1": sorted(set(priority.get("P0", []) + priority.get("P1", []))),
    }

def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, dict) or not isinstance(edges, list):
        return {"result": "FAIL", "findings": ["GRAPH_SHAPE_INVALID"]}
    if graph.get("capability_baseline") != 175:
        findings.append("CAPABILITY_BASELINE_NOT_175")
    if graph.get("capability_delta") != 0:
        findings.append("CAPABILITY_DELTA_NOT_ZERO")
    if graph.get("architectural_authority_delta") != 0:
        findings.append("AUTHORITY_DELTA_NOT_ZERO")
    for key, node in nodes.items():
        if node.get("normalized_key") != key:
            findings.append("NODE_KEY_DRIFT:" + key)
        depth = node.get("min_depth")
        if not isinstance(depth, int) or not 0 <= depth <= MAX_DEPTH:
            findings.append("NODE_DEPTH_INVALID:" + key)
        if node.get("assessment", {}).get("depth_is_ranking_factor") is not False:
            findings.append("DEPTH_USED_AS_RANKING:" + key)
    for i, edge in enumerate(edges):
        if edge.get("parent_key") not in nodes or edge.get("child_key") not in nodes:
            findings.append("BROKEN_EDGE:" + str(i))
        if not isinstance(edge.get("depth"), int) or not 1 <= edge["depth"] <= MAX_DEPTH:
            findings.append("EDGE_DEPTH_INVALID:" + str(i))
    return {"result": "PASS" if not findings else "FAIL", "node_count": len(nodes), "edge_count": len(edges), "findings": findings}

def _http_timeout() -> float:
    raw = os.getenv("CFA3_SOURCE_GRAPH_HTTP_TIMEOUT", "8")
    try:
        return max(1.0, min(float(raw), 30.0))
    except ValueError:
        return 8.0

def _request_json(url: str, token: str | None = None) -> Any:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "CFA3-Donor-Source-Graph/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=_http_timeout()) as response:
        return json.loads(response.read(2_000_000).decode("utf-8"))

def _request_text(url: str) -> str:
    if not _safe_public_http_url(url):
        raise ValueError("UNSAFE_OR_NONPUBLIC_URL")
    req = urllib.request.Request(url, headers={"User-Agent": "CFA3-Donor-Source-Graph/1"})
    with urllib.request.urlopen(req, timeout=_http_timeout()) as response:
        ctype = response.headers.get("Content-Type", "")
        if not any(x in ctype for x in ("text/", "json", "xml", "markdown", "html")):
            return ""
        return response.read(2_000_000).decode("utf-8", errors="replace")

def _github_repo(url: str) -> tuple[str, str] | None:
    m = GITHUB_REPO_RE.match(normalize_url(url))
    return (m.group(1), m.group(2)) if m else None

def _github_raw_readme_links(owner: str, repo: str) -> list[dict[str, str]]:
    for name in ("README.md", "README.MD", "README.rst", "README"):
        raw = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{name}"
        try:
            text = _request_text(raw)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            continue
        if text:
            return extract_links(text)
    return []

def discover_github_repo(url: str, token: str | None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    parsed = _github_repo(url)
    if not parsed:
        return [], {}
    owner, repo = parsed
    metadata_enabled = os.getenv("CFA3_SOURCE_GRAPH_GITHUB_METADATA", "1") != "0"
    meta: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
    if metadata_enabled:
        try:
            value = _request_json(f"https://api.github.com/repos/{owner}/{repo}", token)
            if isinstance(value, dict):
                meta = value
                metadata = {
                    "license_spdx": ((meta.get("license") or {}).get("spdx_id")),
                    "archived": bool(meta.get("archived")),
                    "updated_at": meta.get("updated_at"),
                    "pushed_at": meta.get("pushed_at"),
                }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            metadata = {}

    links: list[dict[str, str]] = []
    if metadata_enabled:
        try:
            readme = _request_json(f"https://api.github.com/repos/{owner}/{repo}/readme", token)
            if isinstance(readme, dict) and readme.get("download_url"):
                links = extract_links(_request_text(readme["download_url"]))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            pass
    if not links:
        links = _github_raw_readme_links(owner, repo)

    homepage = meta.get("homepage") if meta else None
    if isinstance(homepage, str) and homepage.startswith(("http://", "https://")) and _safe_public_http_url(homepage):
        try:
            key = normalized_key(homepage)
            if all(row["normalized_key"] != key for row in links):
                links.append({"url": normalize_url(homepage), "normalized_key": key, "context": "repository homepage"})
        except ValueError:
            pass
    return links, metadata

def discover_github_index(url: str, token: str | None) -> list[dict[str, str]]:
    normalized = normalize_url(url)
    topic = GITHUB_TOPIC_RE.match(normalized)
    rows: list[dict[str, str]] = []
    if topic:
        q = urllib.parse.quote("topic:" + topic.group(1))
        for page in range(1, 11):
            data = _request_json(
                f"https://api.github.com/search/repositories?q={q}&sort=updated&order=desc&per_page=100&page={page}", token
            )
            items = data.get("items", []) if isinstance(data, dict) else []
            for item in items:
                html = item.get("html_url")
                if isinstance(html, str):
                    rows.append({"url": normalize_url(html), "normalized_key": normalized_key(html), "context": "GitHub topic member"})
            if len(items) < 100:
                break
        return rows
    org = GITHUB_ORG_RE.match(normalized)
    if org:
        owner = org.group(1)
        for endpoint in ("orgs", "users"):
            try:
                for page in range(1, 21):
                    data = _request_json(
                        f"https://api.github.com/{endpoint}/{owner}/repos?type=public&sort=updated&per_page=100&page={page}", token
                    )
                    if not isinstance(data, list):
                        break
                    for item in data:
                        html = item.get("html_url")
                        if isinstance(html, str):
                            rows.append({"url": normalize_url(html), "normalized_key": normalized_key(html), "context": "GitHub organization/profile member"})
                    if len(data) < 100:
                        break
                if rows:
                    return rows
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise
    return rows

def discover_url(url: str, token: str | None) -> tuple[list[dict[str, str]], dict[str, Any]]:
    if _github_repo(url):
        return discover_github_repo(url, token)
    normalized = normalize_url(url)
    if GITHUB_TOPIC_RE.match(normalized) or GITHUB_ORG_RE.match(normalized):
        return discover_github_index(url, token), {}
    return extract_links(_request_text(url)), {}

def crawl(
    registry: dict[str, Any],
    *,
    token: str | None = None,
    max_nodes: int = 0,
    workers: int = 24,
    root_shard_index: int = 0,
    root_shard_count: int = 1,
) -> dict[str, Any]:
    graph = seed_graph(registry)
    identities = registry_identity_map(registry)
    queue_items = graph.pop("queue")
    if root_shard_count < 1:
        raise ValueError("ROOT_SHARD_COUNT_INVALID")
    if not 0 <= root_shard_index < root_shard_count:
        raise ValueError("ROOT_SHARD_INDEX_INVALID")
    queue = deque(
        item for index, item in enumerate(queue_items)
        if index % root_shard_count == root_shard_index
    )
    root_count = len(queue)
    expanded: set[tuple[str, str]] = set()
    errors: list[dict[str, Any]] = []
    stopped_by_limit = False
    worker_count = max(1, min(int(workers), 64))
    batch_size = max(worker_count, worker_count * 2)

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        while queue:
            batch: list[dict[str, Any]] = []
            while queue and len(batch) < batch_size:
                item = queue.popleft()
                parent_key = item["normalized_key"]
                parent_depth = int(item["depth"])
                root = item["root_donor_id"]
                if parent_depth >= MAX_DEPTH:
                    continue
                marker = (parent_key, root)
                if marker in expanded:
                    continue
                expanded.add(marker)
                batch.append(item)

            if not batch:
                continue

            futures = [executor.submit(discover_url, item["url"], token) for item in batch]
            for item, future in zip(batch, futures):
                parent_key = item["normalized_key"]
                url = item["url"]
                parent_depth = int(item["depth"])
                root = item["root_donor_id"]
                try:
                    children, metadata = future.result()
                    update_node_observation(graph["nodes"][parent_key], metadata)
                except Exception as exc:
                    errors.append({
                        "source_key": parent_key,
                        "url": url,
                        "error": type(exc).__name__ + ":" + str(exc)[:300],
                    })
                    continue

                for child in children:
                    child_key = child["normalized_key"]
                    if child_key == parent_key:
                        continue
                    relation = classify_relation(child.get("context", ""), child["url"])
                    child_depth = parent_depth + 1
                    created = add_discovery(
                        graph,
                        parent_key=parent_key,
                        child_url=child["url"],
                        depth=child_depth,
                        relation_type=relation,
                        root_donor_id=root,
                        evidence={
                            "source_url": url,
                            "context": child.get("context", "")[:500],
                            "observed_at": dt.date.today().isoformat(),
                        },
                        canonical_record=identities.get(child_key),
                    )
                    if child_depth < MAX_DEPTH and (created or (child_key, root) not in expanded):
                        queue.append({
                            "normalized_key": child_key,
                            "url": child["url"],
                            "depth": child_depth,
                            "root_donor_id": root,
                            "priority": item.get("priority", 3),
                        })
                    if max_nodes and len(graph["nodes"]) >= max_nodes:
                        stopped_by_limit = True
                        queue.clear()
                        break
                if stopped_by_limit:
                    break

            if len(expanded) % 100 < batch_size:
                print(json.dumps({
                    "source_graph_progress": {
                        "expanded_parent_root_pairs": len(expanded),
                        "nodes": len(graph["nodes"]),
                        "edges": len(graph["edges"]),
                        "queue": len(queue),
                        "errors": len(errors),
                    }
                }), flush=True)
            if stopped_by_limit:
                break

    graph["indexes"] = build_indexes(graph)
    graph["crawl"] = {
        "max_depth": MAX_DEPTH,
        "workers": worker_count,
        "root_shard_index": root_shard_index,
        "root_shard_count": root_shard_count,
        "root_count": root_count,
        "expanded_parent_root_pairs": len(expanded),
        "errors": errors,
        "complete": not stopped_by_limit,
        "stopped_by_limit": stopped_by_limit,
        "network_discovery_does_not_register_donors": True,
    }
    graph["validation"] = validate_graph(graph)
    return graph

def merge_graphs(graphs: list[dict[str, Any]], *, expected_shards: int) -> dict[str, Any]:
    if expected_shards < 1:
        raise ValueError("EXPECTED_SHARDS_INVALID")
    if not graphs:
        raise ValueError("NO_SOURCE_GRAPHS")

    ordered = sorted(graphs, key=lambda value: int(value.get("crawl", {}).get("root_shard_index", -1)))
    shard_indexes = [int(value.get("crawl", {}).get("root_shard_index", -1)) for value in ordered]
    if len(set(shard_indexes)) != len(shard_indexes):
        raise ValueError("DUPLICATE_ROOT_SHARD")
    expected_indexes = list(range(expected_shards))

    merged: dict[str, Any] = {
        "schema": "cfa3.donor-source-graph.v1",
        "authority": False,
        "capability_baseline": 175,
        "capability_delta": 0,
        "architectural_authority_delta": 0,
        "max_depth": MAX_DEPTH,
        "nodes": {},
        "edges": [],
    }
    priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4, "UNASSESSED": 9}
    strategic_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "HISTORICAL": 4, "UNASSESSED": 9}

    def copy_value(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False))

    for graph in ordered:
        if graph.get("capability_baseline") != 175 or graph.get("capability_delta") != 0:
            raise ValueError("SHARD_CAPABILITY_INVARIANT_DRIFT")
        if graph.get("architectural_authority_delta") != 0 or graph.get("max_depth") != MAX_DEPTH:
            raise ValueError("SHARD_AUTHORITY_OR_DEPTH_DRIFT")
        crawl_info = graph.get("crawl", {})
        if int(crawl_info.get("root_shard_count", -1)) != expected_shards:
            raise ValueError("SHARD_COUNT_DRIFT")

        for key, incoming in graph.get("nodes", {}).items():
            existing = merged["nodes"].get(key)
            if existing is None:
                merged["nodes"][key] = copy_value(incoming)
                continue
            old_id = existing.get("canonical_donor_id")
            new_id = incoming.get("canonical_donor_id")
            if old_id and new_id and old_id != new_id:
                raise ValueError("CANONICAL_DONOR_IDENTITY_CONFLICT:" + key)
            if not old_id and new_id:
                existing["canonical_donor_id"] = new_id
                existing["canonical_lifecycle"] = incoming.get("canonical_lifecycle")
                existing["registration_state"] = "CANONICAL_DONOR"
            existing["min_depth"] = min(int(existing.get("min_depth", MAX_DEPTH)), int(incoming.get("min_depth", MAX_DEPTH)))
            existing["root_donor_ids"] = sorted(set(existing.get("root_donor_ids", [])) | set(incoming.get("root_donor_ids", [])))
            existing["relation_types"] = sorted(set(existing.get("relation_types", [])) | set(incoming.get("relation_types", [])))

            old_assessment = existing.get("assessment", {})
            new_assessment = incoming.get("assessment", {})
            old_key = (
                priority_rank.get(old_assessment.get("integration_priority"), 9),
                strategic_rank.get(old_assessment.get("strategic_value"), 9),
            )
            new_key = (
                priority_rank.get(new_assessment.get("integration_priority"), 9),
                strategic_rank.get(new_assessment.get("strategic_value"), 9),
            )
            if new_key < old_key:
                existing["assessment"] = copy_value(new_assessment)

            old_obs = existing.setdefault("upstream_observation", {})
            new_obs = incoming.get("upstream_observation", {})
            for field in ("license_spdx", "archived", "updated_at", "pushed_at"):
                if old_obs.get(field) in (None, "", "UNKNOWN") and new_obs.get(field) not in (None, "", "UNKNOWN"):
                    old_obs[field] = new_obs.get(field)

    edge_map: dict[str, dict[str, Any]] = {}
    error_map: dict[str, dict[str, Any]] = {}
    all_complete = True
    any_stopped = False
    for graph in ordered:
        for edge in graph.get("edges", []):
            fingerprint = json.dumps(edge, sort_keys=True, ensure_ascii=False)
            edge_map[fingerprint] = copy_value(edge)
        crawl_info = graph.get("crawl", {})
        shard = crawl_info.get("root_shard_index")
        all_complete = all_complete and crawl_info.get("complete") is True
        any_stopped = any_stopped or crawl_info.get("stopped_by_limit") is True
        for error in crawl_info.get("errors", []):
            row = copy_value(error)
            row["root_shard_index"] = shard
            fingerprint = json.dumps(row, sort_keys=True, ensure_ascii=False)
            error_map[fingerprint] = row

    merged["edges"] = [edge_map[key] for key in sorted(edge_map)]
    merged["indexes"] = build_indexes(merged)
    missing_shards = sorted(set(expected_indexes) - set(shard_indexes))
    merged["crawl"] = {
        "max_depth": MAX_DEPTH,
        "root_shard_count": expected_shards,
        "root_shards_merged": shard_indexes,
        "missing_root_shards": missing_shards,
        "expanded_parent_root_pairs": sum(int(g.get("crawl", {}).get("expanded_parent_root_pairs", 0)) for g in ordered),
        "errors": [error_map[key] for key in sorted(error_map)],
        "complete": all_complete and not any_stopped and not missing_shards and len(shard_indexes) == expected_shards,
        "stopped_by_limit": any_stopped,
        "network_discovery_does_not_register_donors": True,
    }
    validation = validate_graph(merged)
    if missing_shards or len(shard_indexes) != expected_shards:
        validation["result"] = "FAIL"
        validation.setdefault("findings", []).append("ROOT_SHARDS_INCOMPLETE")
    merged["validation"] = validation
    return merged

def write_outputs(graph: dict[str, Any], output: Path) -> None:
    output = output.resolve()
    _write(output / "source-graph.json", graph)
    indexes = graph.get("indexes") or build_indexes(graph)
    _write(output / "indexes/integration-priority-index.json", {
        "schema": "cfa3.integration-priority-index.v1",
        "authority": False,
        "P0": indexes["integration_priority"].get("P0", []),
        "P1": indexes["integration_priority"].get("P1", []),
        "fast_access_p0_p1": indexes["fast_access_p0_p1"],
        "note": "Visibility/availability index only; not donor registration or admission.",
    })
    _write(output / "indexes/strategic-value-index.json", indexes["strategic_value"])
    _write(output / "indexes/relation-type-index.json", indexes["relation_type"])
    _write(output / "indexes/depth-index.json", indexes["discovery_depth"])
    _write(output / "reports/validation.json", graph.get("validation") or validate_graph(graph))

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    seed_p = sub.add_parser("seed")
    seed_p.add_argument("--root", default=".")
    seed_p.add_argument("--output", required=True)
    crawl_p = sub.add_parser("crawl")
    crawl_p.add_argument("--root", default=".")
    crawl_p.add_argument("--output", required=True)
    crawl_p.add_argument("--max-depth", type=int, default=5, choices=[5])
    crawl_p.add_argument("--max-nodes", type=int, default=0)
    crawl_p.add_argument("--workers", type=int, default=24)
    crawl_p.add_argument("--root-shard-index", type=int, default=0)
    crawl_p.add_argument("--root-shard-count", type=int, default=1)
    merge_p = sub.add_parser("merge")
    merge_p.add_argument("--root", default=".")
    merge_p.add_argument("--input-root", required=True)
    merge_p.add_argument("--expected-shards", type=int, required=True)
    merge_p.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "merge":
        graph_paths = sorted(Path(args.input_root).resolve().rglob("source-graph.json"))
        graphs = [_load(path) for path in graph_paths]
        graph = merge_graphs(graphs, expected_shards=args.expected_shards)
        write_outputs(graph, Path(args.output))
        return 0 if graph["validation"]["result"] == "PASS" else 1

    registry = _load(root / REGISTRY_REL)
    if args.command == "seed":
        graph = seed_graph(registry)
        graph.pop("queue", None)
        graph["indexes"] = build_indexes(graph)
        graph["validation"] = validate_graph(graph)
        write_outputs(graph, Path(args.output))
        return 0 if graph["validation"]["result"] == "PASS" else 1
    graph = crawl(
        registry,
        token=os.getenv("GITHUB_TOKEN"),
        max_nodes=args.max_nodes,
        workers=args.workers,
        root_shard_index=args.root_shard_index,
        root_shard_count=args.root_shard_count,
    )
    write_outputs(graph, Path(args.output))
    return 0 if graph["validation"]["result"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
