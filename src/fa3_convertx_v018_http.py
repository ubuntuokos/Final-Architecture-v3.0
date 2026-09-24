#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import http.cookiejar
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit, unquote
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    OpenerDirector,
    Request,
    build_opener,
)


CONTRACT_ID = "FA3-CONVERTX-ADAPTER-CONTRACTS-001"
REFERENCE_RELEASE = "v0.18.0"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_DOWNLOAD_HREF = re.compile(r'href=["\']([^"\']*/download/[^"\']+)["\']', re.IGNORECASE)
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9._+-]+$")


class ConvertXCandidateError(RuntimeError):
    pass


@dataclass(frozen=True)
class CandidateConfig:
    base_url: str
    request_timeout_seconds: float = 15.0
    conversion_timeout_seconds: float = 120.0
    poll_interval_seconds: float = 1.0
    max_input_bytes: int = 268_435_456
    max_output_bytes: int = 268_435_456


@dataclass(frozen=True)
class CandidateResult:
    job_id: str
    download_path: str
    output_path: str
    output_sha256: str
    output_bytes: int
    provider_converter: str
    provider_target: str
    contract_id: str = CONTRACT_ID
    reference_release: str = REFERENCE_RELEASE
    production_routing_enabled: bool = False


class _SameOriginRedirectHandler(HTTPRedirectHandler):
    def __init__(self, origin: tuple[str, str, int | None]):
        super().__init__()
        self.origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        absolute = urljoin(req.full_url, newurl)
        if _origin(absolute) != self.origin:
            raise ConvertXCandidateError("redirect outside pinned loopback origin denied")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ConvertXCandidateError("invalid endpoint port") from exc
    if port is None:
        port = 443 if scheme == "https" else 80 if scheme == "http" else None
    return scheme, host, port


def validate_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ConvertXCandidateError("only http/https loopback endpoints are permitted")
    if (parsed.hostname or "").lower() not in _LOOPBACK_HOSTS:
        raise ConvertXCandidateError("non-loopback ConvertX endpoint denied")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConvertXCandidateError("credentials, query, and fragment are forbidden in base URL")
    if parsed.path not in {"", "/"}:
        raise ConvertXCandidateError("candidate executor requires ConvertX at origin root")
    _origin(base_url)
    return base_url.rstrip("/") + "/"


def _safe_input(path: Path, max_bytes: int) -> tuple[Path, str]:
    candidate = path.expanduser().absolute()
    if candidate.is_symlink() or not candidate.is_file():
        raise ConvertXCandidateError("input must be a regular non-symlink file")
    parent = candidate.parent
    if parent.resolve(strict=True) != parent:
        raise ConvertXCandidateError("symlinked input parent path denied")
    size = candidate.stat().st_size
    if size <= 0 or size > max_bytes:
        raise ConvertXCandidateError("input size outside candidate limits")
    suffix = candidate.suffix.lower().lstrip(".")
    if not suffix or not re.fullmatch(r"[a-z0-9]{1,12}", suffix):
        raise ConvertXCandidateError("input extension cannot be safely staged")
    return candidate, f"fa3-input.{suffix}"


def _safe_output(path: Path) -> Path:
    output = path.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ConvertXCandidateError("output overwrite/symlink denied")
    parent = output.parent
    if not parent.is_dir() or parent.resolve(strict=True) != parent:
        raise ConvertXCandidateError("output parent must be an existing non-symlink directory")
    return output


def _multipart_file(field: str, filename: str, data: bytes) -> tuple[bytes, str]:
    boundary = "fa3-" + uuid.uuid4().hex
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("ascii")
    body = head + data + f"\r\n--{boundary}--\r\n".encode("ascii")
    return body, f"multipart/form-data; boundary={boundary}"


def _cookie_value(jar: http.cookiejar.CookieJar, name: str) -> str | None:
    values = [str(cookie.value) for cookie in jar if cookie.name == name]
    if len(values) != 1:
        return None
    return values[0]


def _small_read(response: BinaryIO, limit: int = 4 * 1024 * 1024) -> bytes:
    data = response.read(limit + 1)
    if len(data) > limit:
        raise ConvertXCandidateError("unexpectedly large ConvertX control response")
    return data


def _request(
    opener: OpenerDirector,
    request: Request,
    timeout: float,
    *,
    control_limit: int = 4 * 1024 * 1024,
) -> tuple[int, bytes, str]:
    try:
        with opener.open(request, timeout=timeout) as response:
            status = int(getattr(response, "status", response.getcode()))
            body = _small_read(response, control_limit)
            return status, body, response.geturl()
    except ConvertXCandidateError:
        raise
    except HTTPError as exc:
        raise ConvertXCandidateError(f"ConvertX HTTP error: {exc.code}") from exc
    except URLError as exc:
        raise ConvertXCandidateError(f"ConvertX transport error: {exc.reason}") from exc


def _validate_mapping(provider_converter: str, provider_target: str) -> None:
    if not _SAFE_TOKEN.fullmatch(provider_converter) or not _SAFE_TOKEN.fullmatch(provider_target):
        raise ConvertXCandidateError("invalid provider mapping token")
    if provider_converter.lower() in {"xelatex", "latex", "pdflatex", "lualatex"}:
        raise ConvertXCandidateError("LaTeX-family converter denied")
    if any(part in provider_target for part in ("/", "\\", "..")):
        raise ConvertXCandidateError("unsafe provider target denied")


def _extract_download_url(base_url: str, job_id: str, body: bytes) -> str | None:
    text = body.decode("utf-8", errors="strict")
    links = {html.unescape(match) for match in _DOWNLOAD_HREF.findall(text)}
    if not links:
        return None
    if len(links) != 1:
        raise ConvertXCandidateError("multiple distinct ConvertX result links denied")
    absolute = urljoin(base_url, next(iter(links)))
    if _origin(absolute) != _origin(base_url):
        raise ConvertXCandidateError("result download origin mismatch")
    parsed = urlsplit(absolute)
    decoded = unquote(parsed.path)
    if "\\" in decoded or "\x00" in decoded:
        raise ConvertXCandidateError("unsafe result download path")
    parts = decoded.split("/")
    if len(parts) != 5 or parts[1] != "download":
        raise ConvertXCandidateError("unexpected result download route")
    _user_id, route_job_id, file_name = parts[2], parts[3], parts[4]
    if route_job_id != job_id:
        raise ConvertXCandidateError("result job identity mismatch")
    if not _user_id or not file_name or file_name in {".", ".."} or "/" in file_name:
        raise ConvertXCandidateError("unsafe result identity")
    if parsed.query or parsed.fragment:
        raise ConvertXCandidateError("result URL query/fragment denied")
    return absolute


def _download_atomic(
    opener: OpenerDirector,
    url: str,
    output: Path,
    timeout: float,
    max_bytes: int,
) -> tuple[str, int]:
    tmp = output.parent / f".{output.name}.fa3-{uuid.uuid4().hex}.part"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(tmp, flags, 0o600)
    digest = hashlib.sha256()
    total = 0
    try:
        try:
            response = opener.open(Request(url, method="GET"), timeout=timeout)
        except HTTPError as exc:
            raise ConvertXCandidateError(f"result download HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ConvertXCandidateError(f"result download transport error: {exc.reason}") from exc
        with response, os.fdopen(fd, "wb", closefd=True) as target:
            fd = -1
            status = int(getattr(response, "status", response.getcode()))
            if status != 200:
                raise ConvertXCandidateError(f"result download returned HTTP {status}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ConvertXCandidateError("result exceeds output size limit")
                digest.update(chunk)
                target.write(chunk)
            if total <= 0:
                raise ConvertXCandidateError("empty result denied")
            target.flush()
            os.fsync(target.fileno())
        try:
            os.link(tmp, output, follow_symlinks=False)
        except FileExistsError as exc:
            raise ConvertXCandidateError("output appeared during candidate execution") from exc
        os.unlink(tmp)
        return digest.hexdigest(), total
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def build_opener_for(base_url: str) -> tuple[OpenerDirector, http.cookiejar.CookieJar]:
    normalized = validate_base_url(base_url)
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar), _SameOriginRedirectHandler(_origin(normalized)))
    return opener, jar


def execute_candidate(
    *,
    config: CandidateConfig,
    input_path: Path,
    output_path: Path,
    provider_converter: str,
    provider_target: str,
    opener: OpenerDirector | None = None,
    cookie_jar: http.cookiejar.CookieJar | None = None,
) -> CandidateResult:
    """Execute one v0.18.0 candidate conversion against a loopback-only ConvertX worker.

    This function does not perform or replace FA3 resource admission and does not enable
    production routing. The caller must complete authoritative resource admission before
    invoking it and must independently prove container egress denial for current-host PASS.
    """
    base_url = validate_base_url(config.base_url)
    _validate_mapping(provider_converter, provider_target)
    source, staged_name = _safe_input(Path(input_path), config.max_input_bytes)
    output = _safe_output(Path(output_path))

    if opener is None or cookie_jar is None:
        opener, cookie_jar = build_opener_for(base_url)

    status, _body, final_url = _request(
        opener,
        Request(base_url, method="GET"),
        config.request_timeout_seconds,
    )
    if status != 200 or _origin(final_url) != _origin(base_url):
        raise ConvertXCandidateError("ConvertX bootstrap failed")
    job_id = _cookie_value(cookie_jar, "jobId")
    if job_id is None or not re.fullmatch(r"[0-9]+", job_id):
        raise ConvertXCandidateError("missing or invalid ConvertX jobId cookie")

    payload = source.read_bytes()
    upload_body, content_type = _multipart_file("file", staged_name, payload)
    upload = Request(
        urljoin(base_url, "upload"),
        data=upload_body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    upload_status, upload_response, _ = _request(opener, upload, config.request_timeout_seconds)
    if upload_status != 200:
        raise ConvertXCandidateError("ConvertX upload failed")
    try:
        upload_json = json.loads(upload_response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConvertXCandidateError("unexpected ConvertX upload response") from exc
    if upload_json.get("message") != "Files uploaded successfully.":
        raise ConvertXCandidateError("ConvertX did not confirm upload")

    form = urlencode(
        {
            "convert_to": f"{provider_target},{provider_converter}",
            "file_names": json.dumps([staged_name], separators=(",", ":")),
        }
    ).encode("ascii")
    convert = Request(
        urljoin(base_url, "convert"),
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    convert_status, _convert_body, convert_final_url = _request(
        opener,
        convert,
        config.request_timeout_seconds,
    )
    if convert_status != 200 or _origin(convert_final_url) != _origin(base_url):
        raise ConvertXCandidateError("ConvertX conversion start failed")

    deadline = time.monotonic() + config.conversion_timeout_seconds
    download_url: str | None = None
    progress_url = urljoin(base_url, f"progress/{quote(job_id, safe='')}")
    while time.monotonic() < deadline:
        progress = Request(
            progress_url,
            data=b"",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        progress_status, progress_body, _ = _request(
            opener,
            progress,
            config.request_timeout_seconds,
        )
        if progress_status != 200:
            raise ConvertXCandidateError("ConvertX progress polling failed")
        download_url = _extract_download_url(base_url, job_id, progress_body)
        if download_url is not None:
            break
        time.sleep(config.poll_interval_seconds)
    if download_url is None:
        raise ConvertXCandidateError("ConvertX candidate conversion timed out")

    digest, total = _download_atomic(
        opener,
        download_url,
        output,
        config.request_timeout_seconds,
        config.max_output_bytes,
    )
    return CandidateResult(
        job_id=job_id,
        download_path=urlsplit(download_url).path,
        output_path=str(output),
        output_sha256=digest,
        output_bytes=total,
        provider_converter=provider_converter,
        provider_target=provider_target,
    )
