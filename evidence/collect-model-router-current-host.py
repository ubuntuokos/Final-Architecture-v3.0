#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = "FA3-AUTH-MODEL-ROUTER-001"
GATE_ID = "FA3-MODEL-ROUTER-CURRENT-HOST-GATESET-001"
REQUIRED_ROUTES = ("fa3-text-primary","fa3-text-secondary","fa3-pageindex-index","fa3-pageindex-reason")


class CollectionDenied(RuntimeError):
    pass


def loadj(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def writej(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def read_token(path_value: str | None) -> str:
    path_value = path_value or os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY_FILE") or os.environ.get("FA3_LITELLM_MASTER_KEY_FILE")
    if path_value:
        path = Path(path_value).expanduser().resolve()
        if not path.is_file():
            raise CollectionDenied("router credential file missing")
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            raise CollectionDenied("router credential file must not be group/world accessible")
        token = path.read_text(encoding="utf-8").strip()
    else:
        token = os.environ.get("FA3_MODEL_ROUTER_MASTER_KEY","").strip() or os.environ.get("FA3_LITELLM_MASTER_KEY","").strip()
    if not token:
        raise CollectionDenied("router credential is required")
    return token


def sanitize_backend_message(value: Any) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"(?i)\\bBearer\\s+[^\\s,;]+", "Bearer <REDACTED>", text)
    text = re.sub(r"(?i)\\bsk-[A-Za-z0-9._-]+", "sk-<REDACTED>", text)
    text = re.sub(r"(?i)(api[_ -]?key|token|secret|password)(\\s*[:=]\\s*)[^\\s,;]+", r"\\1\\2<REDACTED>", text)
    text = re.sub(r"https?://[^\\s\"']+", "<URL>", text)
    text = re.sub(r"(?:/home|/run/user|/tmp|/var/tmp)/[^\\s\"']+", "<PATH>", text)
    return text[:500]


def classify_http_error(status: int, raw: bytes) -> tuple[str, str, str, str, str]:
    fingerprint = hashlib.sha256(raw).hexdigest()
    error_type = ""
    error_code = ""
    message = ""
    try:
        parsed = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(parsed, dict):
            error = parsed.get("error")
            if isinstance(error, dict):
                error_type = sanitize_backend_message(error.get("type"))
                error_code = sanitize_backend_message(error.get("code"))
                message = sanitize_backend_message(error.get("message"))
            elif error is not None:
                message = sanitize_backend_message(error)
            if not message:
                message = sanitize_backend_message(parsed.get("message") or parsed.get("detail"))
    except Exception:
        pass

    low = message.lower()
    if "model" in low and ("not found" in low or "does not exist" in low):
        reason = "ROUTER_BACKEND_MODEL_NOT_FOUND"
    elif "does not support" in low or "unsupported" in low:
        reason = "ROUTER_BACKEND_MODEL_CAPABILITY_FAILED"
    elif "api key" in low or "credential" in low or "authentication" in low or "unauthorized" in low:
        reason = "ROUTER_BACKEND_AUTH_FAILED"
    elif "timeout" in low or "timed out" in low:
        reason = "ROUTER_BACKEND_TIMEOUT"
    elif "connection" in low or "connect" in low or "refused" in low:
        reason = "ROUTER_BACKEND_CONNECTION_FAILED"
    elif "invalid" in low or status in {400, 404, 409, 422}:
        reason = "ROUTER_BACKEND_REQUEST_REJECTED"
    else:
        reason = "ROUTER_BACKEND_HTTP_FAILED"
    return reason, error_type, error_code, message, fingerprint


def request_json(method: str, url: str, token: str, body: dict[str, Any] | None = None, timeout: float = 30.0) -> tuple[dict[str, Any], float]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(8 * 1024 * 1024)
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read(64 * 1024)
        reason, error_type, error_code, message, fingerprint = classify_http_error(int(exc.code), raw)
        detail = (
            f"reason_code={reason} http_status={int(exc.code)} "
            f"error_type={error_type or 'UNKNOWN'} error_code={error_code or 'UNKNOWN'} "
            f"error_fingerprint_sha256={fingerprint}"
        )
        if message:
            detail += f" safe_message={message}"
        raise CollectionDenied(f"router request failed: {detail}") from exc
    except urllib.error.URLError as exc:
        fingerprint = hashlib.sha256(str(exc.reason).encode("utf-8", errors="replace")).hexdigest()
        raise CollectionDenied(
            "router request failed: reason_code=ROUTER_TRANSPORT_FAILED "
            f"error_fingerprint_sha256={fingerprint}"
        ) from exc
    elapsed = (time.monotonic() - start) * 1000
    if status < 200 or status >= 300:
        raise CollectionDenied(f"router returned HTTP {status}")
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise CollectionDenied("router returned non-object JSON")
    return parsed, elapsed


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--endpoint",default=os.environ.get("FA3_MODEL_ROUTER_URL","http://127.0.0.1:4000"))
    ap.add_argument("--credential-file")
    ap.add_argument("--selection-receipt",default=os.environ.get("FA3_MODEL_ROUTER_SELECTION_RECEIPT",""))
    ap.add_argument("--output",default="evidence/receipts/model-router-current-host.json")
    args=ap.parse_args()
    parsed=urlparse(args.endpoint)
    if parsed.scheme not in {"http","https"} or (parsed.hostname or "").lower() not in {"127.0.0.1","::1","localhost"}:
        raise CollectionDenied("current-host router endpoint must be loopback")
    token=read_token(args.credential_file)
    selection_path=Path(args.selection_receipt).expanduser().resolve() if args.selection_receipt else Path(os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"))/"fa3-model-router/selection.json"
    if not selection_path.is_file():
        raise CollectionDenied(f"router runtime selection receipt missing: {selection_path}")
    selection=loadj(selection_path)
    if selection.get("authority")!=AUTHORITY or selection.get("result")!="PASS" or selection.get("provider_neutral") is not True:
        raise CollectionDenied("router runtime selection receipt invalid")
    if selection.get("physical_backend_pinned") is not False or selection.get("physical_model_pinned") is not False or selection.get("runtime_selected") is not True:
        raise CollectionDenied("router runtime selection is not dynamic/non-pinned")
    bindings=selection.get("route_bindings",{})
    if not isinstance(bindings,dict) or not set(REQUIRED_ROUTES).issubset(bindings):
        raise CollectionDenied("router selection receipt lacks required logical routes")
    admission_hashes=selection.get("admission_receipt_sha256",{})
    if not isinstance(admission_hashes,dict):
        raise CollectionDenied("router selection receipt lacks provider admission evidence binding")
    selected_provider_ids={
        str(binding.get("provider_id","")).strip()
        for binding in bindings.values()
        if isinstance(binding,dict) and str(binding.get("provider_id","")).strip()
    }
    provider_evidence={}
    for provider_id in sorted(selected_provider_ids):
        digest=str(admission_hashes.get(provider_id,"")).strip().lower()
        if len(digest)!=64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise CollectionDenied(f"selected provider lacks valid admission evidence digest: {provider_id}")
        provider_evidence[provider_id]=digest
    if not provider_evidence:
        raise CollectionDenied("router selection receipt has no selected-provider admission evidence")
    models, models_latency = request_json("GET",args.endpoint.rstrip("/")+"/v1/models",token,timeout=15)
    model_ids={str(row.get("id")) for row in models.get("data",[]) if isinstance(row,dict) and row.get("id")}
    if not set(REQUIRED_ROUTES).issubset(model_ids):
        raise CollectionDenied("central router does not advertise all required logical routes")
    probes={}
    for route in REQUIRED_ROUTES:
        response, latency=request_json(
            "POST",args.endpoint.rstrip("/")+"/v1/chat/completions",token,
            {
                "model":route,
                "temperature":0,
                "max_tokens":24,
                "messages":[
                    {"role":"system","content":"Return exactly FA3_MODEL_ROUTER_PASS."},
                    {"role":"user","content":"FA3 current-host route probe."}
                ],
            },
            timeout=180,
        )
        choices=response.get("choices")
        content=""
        if isinstance(choices,list) and choices and isinstance(choices[0],dict):
            msg=choices[0].get("message",{})
            if isinstance(msg,dict):
                content=str(msg.get("content","")).strip()
        if not content:
            raise CollectionDenied(f"logical route returned empty content: {route}")
        probes[route]={
            "result":"PASS",
            "latency_ms":round(latency,3),
            "response_sha256":"sha256:"+hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "response_model":str(response.get("model","")),
        }
    active=subprocess.run(["systemctl","--user","is-active","--quiet","fa3-model-router.service"]).returncode==0
    if not active:
        raise CollectionDenied("fa3-model-router.service is not active")
    head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    receipt={
        "schema":"fa3.model-router-current-host-receipt.v1",
        "authority":AUTHORITY,
        "gate_id":GATE_ID,
        "result":"PASS",
        "provider_neutral":True,
        "endpoint":args.endpoint.rstrip("/"),
        "logical_routes":list(REQUIRED_ROUTES),
        "route_bindings":bindings,
        "route_probes":probes,
        "models_endpoint_latency_ms":round(models_latency,3),
        "selection_receipt_sha256":sha256_file(selection_path),
        "selection_receipt_verified":True,
        "provider_admission_evidence_sha256":provider_evidence,
        "physical_backend_pinned":False,
        "physical_model_pinned":False,
        "runtime_selected":True,
        "service_active":True,
        "captured_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z"),
        "repository_head":head,
        "global_promotion_claim":False,
    }
    out=ROOT/args.output
    writej(out,receipt)
    print(json.dumps(receipt,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
