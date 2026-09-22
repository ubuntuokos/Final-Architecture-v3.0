#!/usr/bin/env python3
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from fa3_mcp_gateway import Adapter, GatewayDenied

PROVIDER_ID = "FA3-PROVIDER-PAGEINDEX-LOCAL-001"
INDEX_ADAPTER_ID = "fa3.adapter.pageindex.local.index"
RETRIEVE_ADAPTER_ID = "fa3.adapter.pageindex.local.retrieve"
UPSTREAM_COMMIT = "9a8dd6658278fec90347e8ac3388a205305667a3"
PACKAGE_VERSION = "0.2.10"
ROUTER_SENTINEL = "fa3-local-model-router"


@dataclass(frozen=True)
class PageIndexLocalConfig:
    storage_path: Path
    allowed_roots: tuple[Path, ...]
    model_router_base_url: str
    index_route: str
    reason_route: str

    def validate(self) -> None:
        if not self.storage_path.is_absolute():
            raise GatewayDenied("PAGEINDEX_LOCAL_STORAGE_INVALID", "storage_path must be absolute")
        if not self.allowed_roots or any(not p.is_absolute() for p in self.allowed_roots):
            raise GatewayDenied("PAGEINDEX_LOCAL_SCOPE_INVALID", "allowed_roots must contain absolute paths")
        parsed = urlparse(self.model_router_base_url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            raise GatewayDenied("PAGEINDEX_LOCAL_MODEL_ROUTER_EGRESS", "PageIndex Local may use only a loopback FA3 Model Router")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise GatewayDenied("PAGEINDEX_LOCAL_MODEL_ROUTER_INVALID", "Model Router URL may not contain credentials/query/fragment")
        for name, value in (("index_route", self.index_route), ("reason_route", self.reason_route)):
            if not value.strip() or "://" in value or any(ch.isspace() for ch in value):
                raise GatewayDenied("PAGEINDEX_LOCAL_MODEL_ROUTE_INVALID", f"{name} must be a logical Model Router route alias")


class PageIndexLocalProvider:
    def __init__(self, config: PageIndexLocalConfig, client_factory: Callable[..., Any] | None = None):
        self.config = config
        self.config.validate()
        self.client_factory = client_factory
        self._client: Any | None = None

    def _factory(self):
        if self.client_factory is not None:
            return self.client_factory
        module = importlib.import_module("pageindex")
        return getattr(module, "PageIndexClient")

    def _get_client(self):
        if self._client is None:
            self.config.storage_path.mkdir(parents=True, exist_ok=True)
            index_backend = {"api_base": self.config.model_router_base_url, "api_key": ROUTER_SENTINEL}
            chat_backend = {"base_url": self.config.model_router_base_url, "api_key": ROUTER_SENTINEL}
            self._client = self._factory()(
                index={"mode": "local", "model": f"openai/{self.config.index_route}", "backend": index_backend, "storage_path": str(self.config.storage_path)},
                chat={"mode": "local", "model": f"openai/{self.config.reason_route}", "backend": chat_backend},
            )
        return self._client

    def _local_pdf(self, source: Any) -> Path:
        if not isinstance(source, str) or not source.strip():
            raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_INVALID", "source is required")
        path = Path(source).expanduser().resolve()
        roots = tuple(root.resolve() for root in self.config.allowed_roots)
        if not any(path == root or root in path.parents for root in roots):
            raise GatewayDenied("PAGEINDEX_LOCAL_SCOPE_DENIED", "source is outside admitted local roots")
        if not path.is_file() or path.suffix.lower() != ".pdf":
            raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_INVALID", "PageIndex Local currently admits existing PDF files only")
        with path.open("rb") as fh:
            if fh.read(4) != b"%PDF":
                raise GatewayDenied("PAGEINDEX_LOCAL_SOURCE_INVALID", "PDF magic bytes missing")
        return path

    def index(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = self._local_pdf(arguments.get("source"))
        client = self._get_client()
        result = client.submit_document(str(path), mode="flash")
        doc_id = result.get("doc_id") if isinstance(result, dict) else None
        if not isinstance(doc_id, str) or not doc_id:
            raise GatewayDenied("PAGEINDEX_LOCAL_INDEX_RESULT", "PageIndex Local did not return doc_id")
        tree = client.get_tree(doc_id, include_text=False)
        nodes = tree.get("result", []) if isinstance(tree, dict) else []
        return {
            "provider": PROVIDER_ID,
            "operation": "index",
            "doc_id": doc_id,
            "document_name": path.name,
            "structural_index": {
                "source_id": doc_id,
                "root_node_count": len(nodes) if isinstance(nodes, list) else 0,
                "provider": PROVIDER_ID,
                "derived": True,
            },
            "network_egress": "CENTRAL_MODEL_ROUTER_ONLY",
            "model_route": self.config.index_route,
        }

    def retrieve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation = arguments.get("operation")
        doc_id = arguments.get("doc_id")
        if operation not in {"metadata", "structure", "pages", "reason"}:
            raise GatewayDenied("PAGEINDEX_LOCAL_SCHEMA", "operation must be metadata, structure, pages or reason")
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise GatewayDenied("PAGEINDEX_LOCAL_SCHEMA", "doc_id is required")
        client = self._get_client()
        if operation == "metadata":
            payload = client.get_document(doc_id)
        elif operation == "structure":
            payload = client.get_document_structure(doc_id)
        elif operation == "pages":
            pages = arguments.get("pages")
            if not isinstance(pages, str) or not pages.strip():
                raise GatewayDenied("PAGEINDEX_LOCAL_SCHEMA", "pages is required for pages operation")
            payload = client.get_page_content(doc_id, pages.strip())
        else:
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise GatewayDenied("PAGEINDEX_LOCAL_SCHEMA", "query is required for reason operation")
            payload = client.chat(query.strip(), doc_id=doc_id)
        return {
            "provider": PROVIDER_ID,
            "operation": operation,
            "doc_id": doc_id,
            "result": payload,
            "network_egress": "CENTRAL_MODEL_ROUTER_ONLY",
            "model_route": self.config.reason_route if operation == "reason" else None,
            "global_promotion_claim": False,
        }


def build_adapters(config: PageIndexLocalConfig, client_factory: Callable[..., Any] | None = None) -> tuple[Adapter, Adapter]:
    impl = PageIndexLocalProvider(config, client_factory=client_factory)
    return (
        Adapter(adapter_id=INDEX_ADAPTER_ID, provider_id=PROVIDER_ID, handler=impl.index),
        Adapter(adapter_id=RETRIEVE_ADAPTER_ID, provider_id=PROVIDER_ID, handler=impl.retrieve),
    )
