import hashlib
import http.cookiejar
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

import fa3_convertx_v018_http as x


class _State:
    upload_body = b""
    convert_form = {}
    progress_mode = "normal"
    download_body = b"candidate-jpeg-result"
    set_job_cookie = True
    redirect_external = False


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def log_message(self, *_args):
        pass

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length)

    def _send(self, status, body=b"", content_type="text/html", headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in headers or []:
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            headers = [("Set-Cookie", "auth=fake; Path=/; HttpOnly")]
            if _State.set_job_cookie:
                headers.append(("Set-Cookie", "jobId=42; Path=/; HttpOnly"))
            self._send(200, b"bootstrap", headers=headers)
            return
        if self.path == "/results/42":
            self._send(200, b"results")
            return
        if self.path == "/download/123/42/fa3-input.jpeg":
            self._send(200, _State.download_body, content_type="image/jpeg")
            return
        self._send(404, b"not found")

    def do_POST(self):
        if self.path == "/upload":
            _State.upload_body = self._body()
            response = json.dumps({"message": "Files uploaded successfully."}).encode()
            self._send(200, response, content_type="application/json")
            return
        if self.path == "/convert":
            raw = self._body().decode("ascii")
            _State.convert_form = parse_qs(raw)
            location = "http://example.com/escape" if _State.redirect_external else "/results/42"
            self._send(302, headers=[("Location", location)])
            return
        if self.path == "/progress/42":
            self._body()
            if _State.progress_mode == "normal":
                body = (
                    '<a href="/download/123/42/fa3-input.jpeg">view</a>'
                    '<a href="/download/123/42/fa3-input.jpeg">download</a>'
                ).encode()
            elif _State.progress_mode == "multiple":
                body = (
                    '<a href="/download/123/42/one.jpeg">one</a>'
                    '<a href="/download/123/42/two.jpeg">two</a>'
                ).encode()
            elif _State.progress_mode == "wrong_job":
                body = '<a href="/download/123/99/fa3-input.jpeg">bad</a>'.encode()
            else:
                body = b"<div>pending</div>"
            self._send(200, body)
            return
        self._send(404, b"not found")


class ConvertXV018ExecutorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self):
        _State.upload_body = b""
        _State.convert_form = {}
        _State.progress_mode = "normal"
        _State.download_body = b"candidate-jpeg-result"
        _State.set_job_cookie = True
        _State.redirect_external = False

    def _execute(self, td, **config_overrides):
        root = Path(td)
        source = root / "sample.png"
        source.write_bytes(b"\x89PNG\r\nFA3")
        output = root / "result.jpeg"
        config = x.CandidateConfig(
            base_url=self.base_url,
            poll_interval_seconds=0.01,
            conversion_timeout_seconds=1.0,
            **config_overrides,
        )
        result = x.execute_candidate(
            config=config,
            input_path=source,
            output_path=output,
            provider_converter="vips",
            provider_target="jpeg",
        )
        return result, output

    def test_realistic_cookie_upload_convert_progress_download_flow(self):
        with tempfile.TemporaryDirectory() as td:
            result, output = self._execute(td)
            self.assertEqual("42", result.job_id)
            self.assertEqual("vips", result.provider_converter)
            self.assertEqual("jpeg", result.provider_target)
            self.assertFalse(result.production_routing_enabled)
            self.assertEqual(_State.download_body, output.read_bytes())
            self.assertEqual(hashlib.sha256(_State.download_body).hexdigest(), result.output_sha256)
            self.assertIn(b'name="file"; filename="fa3-input.png"', _State.upload_body)
            self.assertEqual(["jpeg,vips"], _State.convert_form["convert_to"])
            self.assertEqual(['["fa3-input.png"]'], _State.convert_form["file_names"])

    def test_non_loopback_endpoint_is_denied(self):
        with self.assertRaises(x.ConvertXCandidateError):
            x.validate_base_url("https://example.com/")

    def test_base_url_with_path_is_denied(self):
        with self.assertRaises(x.ConvertXCandidateError):
            x.validate_base_url(self.base_url + "hidden")

    def test_missing_job_cookie_is_denied(self):
        _State.set_job_cookie = False
        with tempfile.TemporaryDirectory() as td, self.assertRaises(x.ConvertXCandidateError):
            self._execute(td)

    def test_external_redirect_is_denied(self):
        _State.redirect_external = True
        with tempfile.TemporaryDirectory() as td, self.assertRaises(x.ConvertXCandidateError):
            self._execute(td)

    def test_multiple_distinct_results_are_denied(self):
        _State.progress_mode = "multiple"
        with tempfile.TemporaryDirectory() as td, self.assertRaises(x.ConvertXCandidateError):
            self._execute(td)

    def test_result_from_wrong_job_is_denied(self):
        _State.progress_mode = "wrong_job"
        with tempfile.TemporaryDirectory() as td, self.assertRaises(x.ConvertXCandidateError):
            self._execute(td)

    def test_latex_family_converter_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample.png"
            source.write_bytes(b"data")
            with self.assertRaises(x.ConvertXCandidateError):
                x.execute_candidate(
                    config=x.CandidateConfig(base_url=self.base_url),
                    input_path=source,
                    output_path=root / "out.pdf",
                    provider_converter="xelatex",
                    provider_target="pdf",
                )

    def test_output_overwrite_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample.png"
            source.write_bytes(b"data")
            output = root / "result.jpeg"
            output.write_bytes(b"existing")
            with self.assertRaises(x.ConvertXCandidateError):
                x.execute_candidate(
                    config=x.CandidateConfig(base_url=self.base_url),
                    input_path=source,
                    output_path=output,
                    provider_converter="vips",
                    provider_target="jpeg",
                )
            self.assertEqual(b"existing", output.read_bytes())

    def test_output_size_limit_is_fail_closed_and_leaves_no_output(self):
        _State.download_body = b"0123456789"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "sample.png"
            source.write_bytes(b"data")
            output = root / "result.jpeg"
            config = x.CandidateConfig(
                base_url=self.base_url,
                poll_interval_seconds=0.01,
                conversion_timeout_seconds=1.0,
                max_output_bytes=4,
            )
            with self.assertRaises(x.ConvertXCandidateError):
                x.execute_candidate(
                    config=config,
                    input_path=source,
                    output_path=output,
                    provider_converter="vips",
                    provider_target="jpeg",
                )
            self.assertFalse(output.exists())
            self.assertEqual([], list(root.glob(".*.part")))

    def test_candidate_executor_does_not_need_or_parse_upstream_jwt(self):
        opener, jar = x.build_opener_for(self.base_url)
        self.assertIsInstance(jar, http.cookiejar.CookieJar)
        self.assertIsNotNone(opener)
        self.assertFalse(hasattr(x, "decode_jwt"))


if __name__ == "__main__":
    unittest.main()
