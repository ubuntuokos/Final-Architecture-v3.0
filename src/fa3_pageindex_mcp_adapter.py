#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import queue
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fa3_mcp_gateway import Adapter, GatewayDenied
from fa3_asset_egress_policy import validate_decision

PROVIDER_ID = "FA3-PROVIDER-PAGEINDEX-MCP-001"
INDEX_ADAPTER_ID = "fa3.adapter.pageindex.index"
RETRIEVE_ADAPTER_ID = "fa3.adapter.pageindex.retrieve"
UPSTREAM_VERSION = "1.8.2"
UPSTREAM_COMMIT = "bda946b4b6fffaaf6926aa8809bc62e0098f30e8"
MCPB_SHA256 = "972705b6991a5291112db368fafccf2ce89926a8a0318601cba89bff4adc5de2"
REQUIRED_TOOLS = {"process_document", "get_document", "get_document_structure", "get_page_content"}
EXPECTED_REQUIRED_FIELDS = {
    "process_document": {"url"},
    "get_document": {"doc_name"},
    "get_document_structure": {"doc_name"},
    "get_page_content": {"doc_name", "pages"},
}
RETRIEVE_TOOL_MAP = {"metadata": "get_document", "structure": "get_document_structure", "pages": "get_page_content"}
SECRET_KEY_FRAGMENTS = ("token", "authorization", "credential", "secret", "api_key", "apikey")


@dataclass(frozen=True)
class PageIndexAdapterConfig:
    command: tuple[str, ...]
    oauth_home: Path
    source_root: Path | None = None
    allowed_roots: tuple[Path, ...] = ()
    allowed_remote_hosts: tuple[str, ...] = ()
    timeout_seconds: float = 30.0
    strict_supply_chain: bool = True
    source_commit: str = UPSTREAM_COMMIT
    release_sha256: str = MCPB_SHA256

    def validate(self) -> None:
        if not self.command:
            raise GatewayDenied("PAGEINDEX_COMMAND_MISSING", "PageIndex MCP command is required")
        if not self.oauth_home.is_absolute():
            raise GatewayDenied("PAGEINDEX_OAUTH_HOME_INVALID", "OAuth home must be absolute")
        token_file = self.oauth_home / ".pageindex-mcp" / "oauth-tokens.json"
        if not token_file.is_file():
            raise GatewayDenied("PAGEINDEX_SECRET_MATERIALIZATION_MISSING", "Ephemeral PageIndex OAuth materialization is missing")
        if token_file.stat().st_mode & 0o077:
            raise GatewayDenied("PAGEINDEX_SECRET_PERMISSIONS", "OAuth materialization must not be group/world accessible")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise GatewayDenied("PAGEINDEX_TIMEOUT_INVALID", "PageIndex timeout must be in (0, 300] seconds")
        for root in self.allowed_roots:
            if not root.is_absolute():
                raise GatewayDenied("PAGEINDEX_SCOPE_INVALID", "Allowed local roots must be absolute")
        if self.strict_supply_chain:
            if self.source_commit != UPSTREAM_COMMIT or self.release_sha256 != MCPB_SHA256:
                raise GatewayDenied("PAGEINDEX_SUPPLY_CHAIN_MISMATCH", "PageIndex supply-chain proof does not match canonical pin")
            if self.source_root is None or not self.source_root.is_absolute() or not self.source_root.is_dir():
                raise GatewayDenied("PAGEINDEX_SOURCE_ROOT_REQUIRED", "Pinned PageIndex source root is required")
            try:
                head = subprocess.run(
                    ["git", "-C", str(self.source_root), "rev-parse", "HEAD"],
                    check=True, text=True, capture_output=True, timeout=5,
                ).stdout.strip()
                dirty = subprocess.run(
                    ["git", "-C", str(self.source_root), "diff", "--quiet"],
                    check=False, timeout=5,
                ).returncode
                cached_dirty = subprocess.run(
                    ["git", "-C", str(self.source_root), "diff", "--cached", "--quiet"],
                    check=False, timeout=5,
                ).returncode
            except Exception as exc:
                raise GatewayDenied("PAGEINDEX_SOURCE_PROOF_FAILED", f"Unable to verify pinned source tree: {type(exc).__name__}") from exc
            if head != UPSTREAM_COMMIT or dirty != 0 or cached_dirty != 0:
                raise GatewayDenied("PAGEINDEX_SOURCE_PROOF_FAILED", "PageIndex source tree is not the clean canonical commit")
            package_path = self.source_root / "package.json"
            build_path = (self.source_root / "build" / "index.js").resolve()
            try:
                package = json.loads(package_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise GatewayDenied("PAGEINDEX_BUILD_PROOF_FAILED", "PageIndex package metadata is unreadable") from exc
            if package.get("name") != "@pageindex/mcp" or package.get("version") != UPSTREAM_VERSION or not build_path.is_file():
                raise GatewayDenied("PAGEINDEX_BUILD_PROOF_FAILED", "PageIndex build/package does not match canonical version")
            if len(self.command) != 2 or Path(self.command[0]).name != "node" or Path(self.command[1]).resolve() != build_path:
                raise GatewayDenied("PAGEINDEX_COMMAND_NOT_CANONICAL", "Production PageIndex command must be node <pinned-source>/build/index.js")


class JsonRpcStdioSession:
    def __init__(self, config: PageIndexAdapterConfig):
        self.config = config
        self.proc: subprocess.Popen[str] | None = None
        self.responses: queue.Queue[dict[str, Any]] = queue.Queue()
        self.request_id = 0
        self.server_info: dict[str, Any] = {}

    def start(self) -> None:
        if self.proc is not None:
            return
        self.config.validate()
        env = os.environ.copy()
        env["HOME"] = str(self.config.oauth_home)
        env["BROWSER"] = "/bin/false"
        env["FA3_MANAGED_MCP_PROVIDER"] = "1"
        self.proc = subprocess.Popen(
            list(self.config.command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
            shell=False,
        )
        threading.Thread(target=self._reader, daemon=True).start()
        init = self.request(
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fa3-pageindex-adapter", "version": "1"}},
        )
        self.server_info = init.get("serverInfo") if isinstance(init.get("serverInfo"), dict) else {}
        self.notify("notifications/initialized", {})

    def _reader(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict):
                self.responses.put(msg)

    def _write(self, payload: dict[str, Any]) -> None:
        if self.proc is None or self.proc.stdin is None or self.proc.poll() is not None:
            raise GatewayDenied("PAGEINDEX_PROCESS_UNAVAILABLE", "PageIndex MCP process is unavailable")
        self.proc.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.request_id += 1
        rid = self.request_id
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + self.config.timeout_seconds
        deferred: list[dict[str, Any]] = []
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise GatewayDenied("PAGEINDEX_TIMEOUT", f"Timed out waiting for {method}")
                try:
                    msg = self.responses.get(timeout=min(remaining, 0.25))
                except queue.Empty:
                    if self.proc is not None and self.proc.poll() is not None:
                        raise GatewayDenied("PAGEINDEX_PROCESS_EXITED", f"PageIndex MCP exited during {method}")
                    continue
                if msg.get("id") != rid:
                    deferred.append(msg)
                    continue
                if "error" in msg:
                    raise GatewayDenied("PAGEINDEX_MCP_ERROR", json.dumps(msg["error"], ensure_ascii=False)[:1000])
                result = msg.get("result", {})
                if not isinstance(result, dict):
                    raise GatewayDenied("PAGEINDEX_RESULT_SCHEMA", "MCP result must be an object")
                return result
        finally:
            for msg in deferred:
                self.responses.put(msg)

    def list_tools(self) -> dict[str, dict[str, Any]]:
        result = self.request("tools/list", {})
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise GatewayDenied("PAGEINDEX_TOOLS_SCHEMA", "tools/list did not return an array")
        return {item["name"]: item for item in tools if isinstance(item, dict) and isinstance(item.get("name"), str)}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.proc is None:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None


def contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lk = str(key).lower()
            if any(fragment in lk for fragment in SECRET_KEY_FRAGMENTS):
                return True
            if contains_secret_key(item):
                return True
    elif isinstance(value, list):
        return any(contains_secret_key(item) for item in value)
    return False


def extract_json_text(result: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    content = result.get("content", [])
    if not isinstance(content, list):
        return out
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "text" or not isinstance(item.get("text"), str):
            continue
        text = item["text"]
        try:
            out.append(json.loads(text))
        except json.JSONDecodeError:
            out.append(text)
    return out


def find_doc_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("doc_id", "document_id", "id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        for item in value.values():
            found = find_doc_id(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_doc_id(item)
            if found:
                return found
    return None


class PageIndexMcpAdapter:
    def __init__(self, config: PageIndexAdapterConfig):
        self.config = config
        self._session: JsonRpcStdioSession | None = None
        self._lock = threading.RLock()

    def _get_session(self) -> JsonRpcStdioSession:
        with self._lock:
            if self._session is None:
                self._session = JsonRpcStdioSession(self.config)
                self._session.start()
            return self._session

    def close(self) -> None:
        with self._lock:
            if self._session is not None:
                self._session.close()
                self._session = None

    def probe(self) -> dict[str, Any]:
        session = self._get_session()
        tools = session.list_tools()
        missing = sorted(REQUIRED_TOOLS - set(tools))
        if missing:
            raise GatewayDenied("PAGEINDEX_REQUIRED_TOOLS_MISSING", "Missing required PageIndex tools: " + ",".join(missing))
        for name, required_fields in EXPECTED_REQUIRED_FIELDS.items():
            schema = tools[name].get("inputSchema", {})
            actual_required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
            if not required_fields.issubset(actual_required):
                raise GatewayDenied(
                    "PAGEINDEX_REMOTE_CONTRACT_DRIFT",
                    f"PageIndex tool schema drift for {name}: required={sorted(actual_required)}",
                )
        return {
            "provider_id": PROVIDER_ID,
            "server_info": session.server_info,
            "tools": sorted(tools),
            "required_tools": sorted(REQUIRED_TOOLS),
            "contract_required_fields": {name: sorted(fields) for name, fields in EXPECTED_REQUIRED_FIELDS.items()},
        }

    def _validate_source(self, source: Any) -> str:
        if not isinstance(source, str) or not source.strip():
            raise GatewayDenied("PAGEINDEX_SOURCE_INVALID", "source is required")
        source = source.strip()
        parsed = urlparse(source)
        if parsed.scheme:
            if parsed.scheme != "https":
                raise GatewayDenied("PAGEINDEX_REMOTE_SOURCE_DENIED", "Remote source must use HTTPS")
            host = (parsed.hostname or "").lower()
            allowed = any(host == h or host.endswith("." + h) for h in self.config.allowed_remote_hosts)
            if not allowed:
                raise GatewayDenied("PAGEINDEX_REMOTE_SOURCE_DENIED", "Remote source host is not allowlisted")
            return source
        path = Path(source).expanduser().resolve()
        if not self.config.allowed_roots:
            raise GatewayDenied("PAGEINDEX_LOCAL_SCOPE_DENIED", "No local PDF roots are admitted")
        if not any(path == root.resolve() or root.resolve() in path.parents for root in self.config.allowed_roots):
            raise GatewayDenied("PAGEINDEX_LOCAL_SCOPE_DENIED", "Local PDF path is outside admitted roots")
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_INVALID", "Local source must be an existing PDF file")
        if path.stat().st_size > 100 * 1024 * 1024:
            raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_TOO_LARGE", "PDF exceeds 100 MiB")
        with path.open("rb") as fh:
            if fh.read(4) != b"%PDF":
                raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_INVALID", "Local source does not have PDF magic bytes")
        return str(path)

    def _call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool not in REQUIRED_TOOLS:
            raise GatewayDenied("PAGEINDEX_TOOL_NOT_ALLOWLISTED", "Upstream tool is not allowlisted")
        self.probe()
        session = self._get_session()
        result = session.call_tool(tool, arguments)
        if result.get("isError") is True:
            raise GatewayDenied("PAGEINDEX_TOOL_ERROR", f"PageIndex tool returned isError: {tool}")
        if contains_secret_key(result):
            raise GatewayDenied("PAGEINDEX_RESULT_SECRET_MATERIAL", "Provider result contains credential-like keys")
        return result

    def index(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = self._validate_source(arguments.get("source"))
        parsed = urlparse(source)
        if not parsed.scheme:
            digest = hashlib.sha256()
            with Path(source).open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    digest.update(chunk)
            decision = arguments.get("_fa3_asset_egress_decision")
            try:
                validate_decision(decision, source_sha256=digest.hexdigest(), provider_id=PROVIDER_ID)
            except Exception as exc:
                raise GatewayDenied("PAGEINDEX_ASSET_EGRESS_DENIED", "Gateway-authorized CAP-140 asset egress decision required") from exc
        upstream_args: dict[str, Any] = {"url": source}
        if "folder_id" in arguments:
            folder_id = arguments["folder_id"]
            if folder_id is not None and not isinstance(folder_id, str):
                raise GatewayDenied("PAGEINDEX_SCHEMA", "folder_id must be string or null")
            upstream_args["folder_id"] = folder_id
        result = self._call("process_document", upstream_args)
        decoded = extract_json_text(result)
        parsed = urlparse(source)
        if parsed.scheme:
            document_name = arguments.get("document_name")
            if not isinstance(document_name, str) or not document_name.strip():
                raise GatewayDenied(
                    "PAGEINDEX_DOCUMENT_NAME_REQUIRED",
                    "document_name is required for remote URL indexing because the final uploaded filename may differ from the URL path",
                )
            document_name = document_name.strip()
        else:
            supplied_name = arguments.get("document_name")
            document_name = supplied_name.strip() if isinstance(supplied_name, str) and supplied_name.strip() else Path(source).name
        return {
            "provider": PROVIDER_ID,
            "operation": "index_pdf",
            "doc_id": find_doc_id(decoded),
            "document_name": document_name,
            "folder_id": arguments.get("folder_id"),
            "upstream_result": result,
        }

    def retrieve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation = arguments.get("operation")
        document_name = arguments.get("document_name")
        if operation not in RETRIEVE_TOOL_MAP:
            raise GatewayDenied("PAGEINDEX_SCHEMA", "operation must be metadata, structure or pages")
        if not isinstance(document_name, str) or not document_name.strip():
            raise GatewayDenied("PAGEINDEX_SCHEMA", "document_name is required")
        tool = RETRIEVE_TOOL_MAP[operation]
        upstream_args: dict[str, Any] = {"doc_name": document_name.strip()}
        folder_id = arguments.get("folder_id")
        if folder_id is not None:
            if not isinstance(folder_id, str) or not folder_id.strip():
                raise GatewayDenied("PAGEINDEX_SCHEMA", "folder_id must be a non-empty string or omitted")
            upstream_args["folder_id"] = folder_id.strip()
        if "wait_for_completion" in arguments:
            if not isinstance(arguments["wait_for_completion"], bool):
                raise GatewayDenied("PAGEINDEX_SCHEMA", "wait_for_completion must be boolean")
            upstream_args["wait_for_completion"] = arguments["wait_for_completion"]
        if operation == "pages":
            pages = arguments.get("pages")
            if not isinstance(pages, str) or not pages.strip():
                raise GatewayDenied("PAGEINDEX_SCHEMA", "pages is required for pages operation")
            upstream_args["pages"] = pages.strip()
        result = self._call(tool, upstream_args)
        return {
            "provider": PROVIDER_ID,
            "operation": operation,
            "upstream_tool": tool,
            "document_name": document_name.strip(),
            "upstream_result": result,
        }


def build_adapters(config: PageIndexAdapterConfig) -> tuple[Adapter, Adapter]:
    impl = PageIndexMcpAdapter(config)
    return (
        Adapter(adapter_id=INDEX_ADAPTER_ID, provider_id=PROVIDER_ID, handler=impl.index),
        Adapter(adapter_id=RETRIEVE_ADAPTER_ID, provider_id=PROVIDER_ID, handler=impl.retrieve),
    )


def factory_from_env() -> tuple[Adapter, Adapter]:
    raw_command = os.environ.get("FA3_PAGEINDEX_MCP_COMMAND", "")
    if not raw_command:
        raise GatewayDenied("PAGEINDEX_COMMAND_MISSING", "FA3_PAGEINDEX_MCP_COMMAND is required")
    try:
        parsed = json.loads(raw_command)
        command = tuple(str(v) for v in parsed) if isinstance(parsed, list) else tuple(shlex.split(raw_command))
    except json.JSONDecodeError:
        command = tuple(shlex.split(raw_command))
    home = os.environ.get("FA3_PAGEINDEX_MCP_OAUTH_HOME", "")
    roots = tuple(Path(v).expanduser().resolve() for v in os.environ.get("FA3_PAGEINDEX_MCP_ALLOWED_ROOTS", "").split(":") if v)
    hosts = tuple(v.strip().lower() for v in os.environ.get("FA3_PAGEINDEX_MCP_ALLOWED_REMOTE_HOSTS", "").split(",") if v.strip())
    source_root_raw = os.environ.get("FA3_PAGEINDEX_MCP_SOURCE_ROOT", "")
    config = PageIndexAdapterConfig(
        command=command,
        oauth_home=Path(home).expanduser(),
        source_root=Path(source_root_raw).expanduser().resolve() if source_root_raw else None,
        allowed_roots=roots,
        allowed_remote_hosts=hosts,
        timeout_seconds=float(os.environ.get("FA3_PAGEINDEX_MCP_TIMEOUT", "30")),
        strict_supply_chain=True,
        source_commit=os.environ.get("FA3_PAGEINDEX_MCP_SOURCE_COMMIT", ""),
        release_sha256=os.environ.get("FA3_PAGEINDEX_MCP_RELEASE_SHA256", ""),
    )
    return build_adapters(config)
