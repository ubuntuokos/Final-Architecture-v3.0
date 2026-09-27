import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fa3_agent_deliberation_runtime import make_server


def _agent(pid):
    return {
        "participant_id": pid,
        "role": "AGENT",
        "identity_receipt_ref": f"identity:{pid}",
        "authorized": True,
        "authority_grants": [],
        "capability_grants": [],
        "model_binding": {
            "router_authority": "FA3-AUTH-MODEL-ROUTER-001",
            "route_id": f"route:{pid}",
            "provider_id": f"provider:{pid}",
            "model_id": f"model:{pid}",
            "receipt_ref": f"receipt:{pid}",
            "binding_source": "MODEL_ROUTER_RECEIPT",
        },
    }


def _call(base, method, path, body=None):
    raw = None if body is None else json.dumps(body).encode()
    req = Request(base + path, data=raw, method=method)
    if raw is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_reference_runtime_uses_loopback_dynamic_port_and_fail_closed_message_validation():
    server = make_server(port=0)
    assert server.server_address[0] == "127.0.0.1"
    assert server.server_address[1] > 0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        status, _ = _call(base, "POST", "/v1/sessions", {
            "session_id": "t",
            "objective": "test",
            "participants": [_agent("a"), _agent("b")],
        })
        assert status == 201
        msg = {
            "message": {
                "message_id": "m1",
                "session_id": "t",
                "sender_id": "a",
                "communication_mode": "HUMAN_LANGUAGE",
                "language_tag": "en",
                "human_readable_text": "hello",
                "human_readable_authoritative": True,
                "secret_values_present": False,
                "client_asserted_host_verified": True,
            }
        }
        status, body = _call(base, "POST", "/v1/sessions/t/messages", msg)
        assert status == 400
        assert "host verification" in body["error"].lower()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
