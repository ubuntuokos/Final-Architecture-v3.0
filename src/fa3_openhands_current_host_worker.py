#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import json
import os
import socket
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field, PrivateAttr, SecretStr

from openhands.sdk import (
    Action,
    Agent,
    Conversation,
    ImageContent,
    Observation,
    TextContent,
    ToolDefinition,
)
from openhands.sdk.llm import Message, MessageToolCall
from openhands.sdk.llm.llm import LLM
from openhands.sdk.llm.llm_response import LLMResponse
from openhands.sdk.llm.utils.metrics import MetricsSnapshot, TokenUsage
from openhands.sdk.tool import Tool, ToolExecutor, register_tool
from openhands.sdk.tool.tool import ToolAnnotations
from openhands.sdk.testing import TestLLM
from litellm.types.utils import Choices, Message as LiteLLMMessage, ModelResponse

from fa3_openhands_adapter import (
    DEFAULT_MODEL_ALIAS,
    PROVIDER_ID,
    OpenHandsAdmissionError,
    sha256_bytes,
    validate_external_tool_authorization,
    validate_relative_path,
)

WORKSPACE = Path("/workspace")
PERSISTENCE = WORKSPACE / ".fa3-openhands-state"


class DelegatedWriteAction(Action):
    relative_path: str = Field(description="Exact FA3-authorized relative workspace path")
    content: str = Field(description="Exact UTF-8 content authorized by FA3")


class DelegatedWriteObservation(Observation):
    relative_path: str
    content_sha256: str
    authorization_class: str

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        return [
            TextContent(
                text=(
                    "FA3 delegated write completed for "
                    f"{self.relative_path}; sha256={self.content_sha256}"
                )
            )
        ]


class DelegatedWriteExecutor(ToolExecutor[DelegatedWriteAction, DelegatedWriteObservation]):
    def __init__(self) -> None:
        self.allowed_path = validate_relative_path(os.environ["FA3_ALLOWED_RELATIVE_PATH"])
        self.expected_content = os.environ["FA3_EXPECTED_CONTENT"]
        self.expected_sha = os.environ["FA3_EXPECTED_CONTENT_SHA256"]
        self.task_id = os.environ["FA3_TASK_ID"]
        self.mode = os.environ["FA3_OPENHANDS_MODE"]
        self.used = False
        self.execution_count = 0
        self.authorization_class = "UNSET"

    def _authorize(self) -> None:
        if self.used:
            raise OpenHandsAdmissionError("single-use delegated write authorization already consumed")
        if self.mode == "isolated":
            self.authorization_class = "FIXTURE_NON_PRODUCTION"
            return
        path = Path(os.environ.get("FA3_TOOL_AUTH_RECEIPT", ""))
        if not path.is_file():
            raise OpenHandsAdmissionError("production tool authorization receipt missing")
        receipt = json.loads(path.read_text(encoding="utf-8"))
        validate_external_tool_authorization(
            receipt,
            task_id=self.task_id,
            relative_path=self.allowed_path,
            content_sha256=self.expected_sha,
        )
        self.authorization_class = "EXTERNAL_CANONICAL_TOOL_AUTHORIZATION"

    def __call__(
        self,
        action: DelegatedWriteAction,
        conversation=None,  # noqa: ARG002
    ) -> DelegatedWriteObservation:
        self._authorize()
        relative = validate_relative_path(action.relative_path)
        if relative != self.allowed_path:
            raise OpenHandsAdmissionError("delegated write path outside exact authorized scope")
        if action.content != self.expected_content:
            raise OpenHandsAdmissionError("delegated write content differs from exact authorized content")
        if sha256_bytes(action.content.encode("utf-8")) != self.expected_sha:
            raise OpenHandsAdmissionError("delegated write content hash mismatch")

        root = WORKSPACE.resolve()
        target = (root / relative).resolve(strict=False)
        if root not in target.parents:
            raise OpenHandsAdmissionError("delegated write escaped workspace")
        if not target.is_file() or target.is_symlink():
            raise OpenHandsAdmissionError("delegated write v0.1 requires a pre-existing regular file")
        tmp = target.with_name(target.name + ".fa3-openhands.tmp")
        tmp.write_text(action.content, encoding="utf-8")
        os.replace(tmp, target)
        self.used = True
        self.execution_count += 1
        return DelegatedWriteObservation(
            relative_path=relative,
            content_sha256=sha256_bytes(target.read_bytes()),
            authorization_class=self.authorization_class,
        )


class FA3DelegatedWriteTool(ToolDefinition[DelegatedWriteAction, DelegatedWriteObservation]):
    name: ClassVar[str] = "fa3_delegated_write"

    @classmethod
    def create(cls, conv_state, **_params) -> Sequence[ToolDefinition]:
        executor = DelegatedWriteExecutor()
        return [
            cls(
                description=(
                    "FA3 exact delegated write. This tool may modify only the exact "
                    "path/content pair authorized by the external FA3 execution boundary."
                ),
                action_type=DelegatedWriteAction,
                observation_type=DelegatedWriteObservation,
                executor=executor,
                annotations=ToolAnnotations(
                    title="FA3 delegated exact write",
                    readOnlyHint=False,
                    destructiveHint=True,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
        ]


register_tool(FA3DelegatedWriteTool.name, FA3DelegatedWriteTool)


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 180.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def _json_default(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


class UnixRouterLLM(LLM):
    route_model: str = Field(default=DEFAULT_MODEL_ALIAS)
    socket_path: str = Field(default="/run/fa3/model-router.sock")
    key_file: str = Field(default="/run/fa3/model-key")
    _response_hashes: list[str] = PrivateAttr(default_factory=list)
    _call_count: int = PrivateAttr(default=0)

    def uses_responses_api(self) -> bool:
        return False

    def completion(
        self,
        messages: list[Message],
        tools: Sequence[ToolDefinition] | None = None,
        add_security_risk_prediction: bool = False,
        on_token=None,  # noqa: ARG002
        call_context=None,  # noqa: ARG002
        **_kwargs: Any,
    ) -> LLMResponse:
        key = Path(self.key_file).read_text(encoding="utf-8").strip()
        if not key:
            raise OpenHandsAdmissionError("central model-router key file is empty")
        payload = {
            "model": self.route_model,
            "messages": self.format_messages_for_llm(messages),
            "tools": [
                tool.to_openai_tool(
                    add_security_risk_prediction=add_security_risk_prediction
                )
                for tool in (tools or [])
            ] or None,
            "tool_choice": "auto",
            "stream": False,
            "temperature": 0,
        }
        body = json.dumps(payload, default=_json_default, separators=(",", ":")).encode("utf-8")
        conn = UnixHTTPConnection(self.socket_path, timeout=180.0)
        try:
            conn.request(
                "POST",
                "/v1/chat/completions",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + key,
                    "User-Agent": "FA3-OpenHands-CurrentHost/1",
                },
            )
            resp = conn.getresponse()
            raw_body = resp.read(8 * 1024 * 1024)
        finally:
            conn.close()
        if resp.status < 200 or resp.status >= 300:
            raise OpenHandsAdmissionError(
                f"central model-router returned HTTP {resp.status}; body_sha256="
                + sha256_bytes(raw_body)
            )
        data = json.loads(raw_body.decode("utf-8"))
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise OpenHandsAdmissionError("central model-router response has no choice")
        choice = choices[0]
        wire_message = choice.get("message")
        if not isinstance(wire_message, dict):
            raise OpenHandsAdmissionError("central model-router response has no message")
        message = Message.from_llm_chat_message(wire_message)
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        metrics = MetricsSnapshot(
            model_name=self.route_model,
            accumulated_cost=0.0,
            max_budget_per_task=None,
            accumulated_token_usage=TokenUsage(
                model=self.route_model,
                prompt_tokens=max(prompt_tokens, 0),
                completion_tokens=max(completion_tokens, 0),
            ),
        )
        lite_message = LiteLLMMessage(**wire_message)
        model_response = ModelResponse(
            id=str(data.get("id") or f"fa3-openhands-{self._call_count + 1}"),
            choices=[
                Choices(
                    message=lite_message,
                    index=int(choice.get("index") or 0),
                    finish_reason=choice.get("finish_reason") or "stop",
                )
            ],
            created=int(data.get("created") or 0),
            model=str(data.get("model") or self.route_model),
            object=str(data.get("object") or "chat.completion"),
        )
        self._call_count += 1
        self._response_hashes.append(sha256_bytes(raw_body))
        return LLMResponse(message=message, metrics=metrics, raw_response=model_response)

    async def acompletion(self, *args, **kwargs) -> LLMResponse:
        return await asyncio.to_thread(self.completion, *args, **kwargs)


def _fixture_llm(relative_path: str, content: str) -> TestLLM:
    return TestLLM.from_messages(
        [
            Message(
                role="assistant",
                content=[TextContent(text="")],
                tool_calls=[
                    MessageToolCall(
                        id="fa3-call-1",
                        name=FA3DelegatedWriteTool.name,
                        arguments=json.dumps(
                            {"relative_path": relative_path, "content": content},
                            separators=(",", ":"),
                        ),
                        origin="completion",
                    )
                ],
            ),
            Message(
                role="assistant",
                content=[TextContent(text="FA3_ISOLATED_RUNTIME_DONE")],
            ),
        ],
        model="fa3-openhands-test-llm",
        usage_id="fa3-openhands-isolated",
    )


def _fixture_resume_llm() -> TestLLM:
    return TestLLM.from_messages(
        [
            Message(
                role="assistant",
                content=[TextContent(text="RESUME_OK")],
            )
        ],
        model="fa3-openhands-test-llm",
        usage_id="fa3-openhands-isolated-resume",
    )


class Lineage:
    def __init__(self) -> None:
        self.count = 0
        self.types: set[str] = set()
        self.head = "0" * 64

    def callback(self, event: Any) -> None:
        self.count += 1
        event_type = type(event).__name__
        event_id = str(getattr(event, "id", ""))
        self.types.add(event_type)
        payload = f"{self.count}|{event_type}|{event_id}|{self.head}".encode("utf-8")
        self.head = hashlib.sha256(payload).hexdigest()


def _persistence_inventory() -> dict[str, Any]:
    files = []
    if PERSISTENCE.exists():
        for path in sorted(PERSISTENCE.rglob("*")):
            if path.is_file():
                files.append(
                    {
                        "relative_path": path.relative_to(PERSISTENCE).as_posix(),
                        "size": path.stat().st_size,
                        "sha256": sha256_bytes(path.read_bytes()),
                    }
                )
    return {
        "file_count": len(files),
        "total_bytes": sum(x["size"] for x in files),
        "files": files,
    }


def _secret_not_persisted(secret: bytes | None) -> bool:
    if not secret:
        return True
    if not PERSISTENCE.exists():
        return True
    for path in PERSISTENCE.rglob("*"):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if secret in data:
            return False
    return True


def _make_agent(llm: LLM) -> Agent:
    return Agent(
        llm=llm,
        tools=[Tool(name=FA3DelegatedWriteTool.name)],
    )


def run(result_path: Path) -> dict[str, Any]:
    mode = os.environ["FA3_OPENHANDS_MODE"]
    task_id = os.environ["FA3_TASK_ID"]
    relative_path = validate_relative_path(os.environ["FA3_ALLOWED_RELATIVE_PATH"])
    expected_content = os.environ["FA3_EXPECTED_CONTENT"]
    expected_sha = os.environ["FA3_EXPECTED_CONTENT_SHA256"]
    if sha256_bytes(expected_content.encode("utf-8")) != expected_sha:
        raise OpenHandsAdmissionError("expected content hash environment mismatch")
    target = (WORKSPACE / relative_path).resolve(strict=False)
    if WORKSPACE.resolve() not in target.parents or not target.is_file() or target.is_symlink():
        raise OpenHandsAdmissionError("delegated target is not a safe pre-existing file")

    secret_bytes: bytes | None = None
    if mode == "production":
        key_path = Path(os.environ["FA3_ROUTER_KEY_FILE"])
        secret_bytes = key_path.read_bytes().strip()
        if not secret_bytes:
            raise OpenHandsAdmissionError("production model-router key is empty")
        llm: LLM = UnixRouterLLM(
            model="openai/gpt-4o",
            api_key=SecretStr("fa3-non-secret-placeholder"),
            usage_id="fa3-openhands-production",
            route_model=os.environ.get("FA3_MODEL_ALIAS", DEFAULT_MODEL_ALIAS),
            socket_path=os.environ["FA3_ROUTER_SOCKET"],
            key_file=str(key_path),
        )
    else:
        llm = _fixture_llm(relative_path, expected_content)

    lineage_first = Lineage()
    conv_id = uuid.uuid5(uuid.NAMESPACE_URL, "fa3-openhands:" + task_id)
    PERSISTENCE.mkdir(parents=True, exist_ok=True)
    conversation = Conversation(
        agent=_make_agent(llm),
        callbacks=[lineage_first.callback],
        workspace=WORKSPACE,
        persistence_dir=PERSISTENCE,
        conversation_id=conv_id,
        max_iteration_per_run=4,
        stuck_detection=False,
        visualizer=None,
    )
    conversation.send_message(
        "Execute the single FA3 delegated write tool exactly once. "
        f"Use relative_path={relative_path!r} and exact content={expected_content!r}. "
        "Do not attempt any other filesystem path, tool, MCP server, shell, network action, "
        "subagent, plugin, or git operation. After the authorized tool succeeds, finish."
    )
    conversation.run()
    if hasattr(conversation, "close"):
        conversation.close()

    if target.read_text(encoding="utf-8") != expected_content:
        raise OpenHandsAdmissionError("OpenHands production/runtime task did not produce exact content")
    first_inventory = _persistence_inventory()
    if first_inventory["file_count"] <= 0:
        raise OpenHandsAdmissionError("OpenHands persistence did not materialize")

    if mode == "production":
        resume_llm: LLM = UnixRouterLLM(
            model="openai/gpt-4o",
            api_key=SecretStr("fa3-non-secret-placeholder"),
            usage_id="fa3-openhands-production-resume",
            route_model=os.environ.get("FA3_MODEL_ALIAS", DEFAULT_MODEL_ALIAS),
            socket_path=os.environ["FA3_ROUTER_SOCKET"],
            key_file=os.environ["FA3_ROUTER_KEY_FILE"],
        )
    else:
        resume_llm = _fixture_resume_llm()

    lineage_resume = Lineage()
    resumed = Conversation(
        agent=_make_agent(resume_llm),
        callbacks=[lineage_resume.callback],
        workspace=WORKSPACE,
        persistence_dir=PERSISTENCE,
        conversation_id=conv_id,
        max_iteration_per_run=2,
        stuck_detection=False,
        visualizer=None,
    )
    resumed.send_message(
        "This is an FA3 crash/resume verification turn. Do not call any tool. "
        "Reply exactly RESUME_OK and stop."
    )
    resumed.run()
    if hasattr(resumed, "close"):
        resumed.close()

    second_inventory = _persistence_inventory()
    if second_inventory["file_count"] < first_inventory["file_count"]:
        raise OpenHandsAdmissionError("OpenHands persistence shrank across resume")
    if lineage_resume.count <= 0:
        raise OpenHandsAdmissionError("OpenHands resumed conversation emitted no new events")
    if not _secret_not_persisted(secret_bytes):
        raise OpenHandsAdmissionError("central model-router secret was persisted by OpenHands")

    production_hashes: list[str] = []
    production_calls = 0
    if isinstance(llm, UnixRouterLLM):
        production_hashes.extend(llm._response_hashes)
        production_calls += llm._call_count
    if isinstance(resume_llm, UnixRouterLLM):
        production_hashes.extend(resume_llm._response_hashes)
        production_calls += resume_llm._call_count

    result = {
        "schema": "fa3.openhands-sandbox-worker-result.v1",
        "provider_id": PROVIDER_ID,
        "status": "PASS",
        "mode": mode,
        "task_id": task_id,
        "conversation_id": str(conv_id),
        "workspace": "/workspace",
        "delegated_relative_path": relative_path,
        "target_sha256": sha256_bytes(target.read_bytes()),
        "tool_surface": {
            "registered_tools": [FA3DelegatedWriteTool.name],
            "provider_native_execute_tool_used": False,
            "provider_native_mcp_enabled": False,
            "terminal_tool_enabled": False,
            "file_editor_tool_enabled": False,
        },
        "isolation_expectation": {
            "general_network_egress": False,
            "host_home_mounted": False,
            "repo_read_only": True,
            "workspace_rw_only": True,
        },
        "persistence": {
            "first": first_inventory,
            "after_resume": second_inventory,
            "raw_router_secret_persisted": False,
        },
        "event_lineage": {
            "first_run_count": lineage_first.count,
            "first_run_types": sorted(lineage_first.types),
            "first_run_chain_head": lineage_first.head,
            "resume_count": lineage_resume.count,
            "resume_types": sorted(lineage_resume.types),
            "resume_chain_head": lineage_resume.head,
        },
        "resume": {
            "same_conversation_id": True,
            "prior_persistence_observed": first_inventory["file_count"] > 0,
            "new_events_after_reopen": lineage_resume.count > 0,
            "status": "PASS",
        },
        "model_route": {
            "class": "CENTRAL_LITELLM_UNIX_BRIDGE" if mode == "production" else "OPENHANDS_TEST_LLM_FIXTURE",
            "model_alias": os.environ.get("FA3_MODEL_ALIAS", DEFAULT_MODEL_ALIAS),
            "production_response_count": production_calls,
            "production_response_sha256": production_hashes,
            "fixture_only": mode != "production",
        },
        "production_admission_claim": mode == "production",
    }
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--result", required=True)
    args = ap.parse_args()
    try:
        result = run(Path(args.result))
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        fail = {
            "schema": "fa3.openhands-sandbox-worker-result.v1",
            "provider_id": PROVIDER_ID,
            "status": "FAIL",
            "mode": os.environ.get("FA3_OPENHANDS_MODE"),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "production_admission_claim": False,
        }
        try:
            Path(args.result).write_text(json.dumps(fail, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        print(json.dumps(fail, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
