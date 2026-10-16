"""Functional checks against a running Letta. Set LETTA_E2E=1, LETTA_SERVER_URL, and LETTA_SERVER_PASSWORD."""

import json
import os
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("LETTA_E2E") != "1", reason="Set LETTA_E2E=1 to hit a live Letta")


def _request(method, path, body=None, auth=True):
    base = os.environ["LETTA_SERVER_URL"].rstrip("/")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if auth:
        req.add_header("Authorization", "Bearer " + os.environ["LETTA_SERVER_PASSWORD"])
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw.decode(errors="replace")
        return exc.code, parsed


def test_health():
    status, body = _request("GET", "/v1/health/", auth=False)
    assert status == 200
    assert body["status"] == "ok"


def test_slash_label_is_rejected_and_plain_label_round_trips():
    status, body = _request("POST", "/v1/blocks/", {"label": "songs/fourth_of_july", "value": "x"})
    assert status == 422
    blob = json.dumps(body).lower()
    assert "slash" in blob

    status, created = _request("POST", "/v1/blocks/", {"label": "qc_gate_label", "value": "gate"})
    assert status == 200
    block_id = created["id"]
    try:
        status, fetched = _request("GET", f"/v1/blocks/{block_id}")
        assert status == 200
        assert fetched["label"] == "qc_gate_label"
    finally:
        status, _deleted = _request("DELETE", f"/v1/blocks/{block_id}")
        assert status == 200


def test_sync_alias_returns_resync_summary():
    status, body = _request("POST", "/v1/tools/mcp/servers/qc-page-flag/sync")
    assert status == 200, body
    assert body.get("added") == []
    skipped = body.get("skipped") or []
    assert any(item.get("name") == "qc_unhealable" for item in skipped), skipped


def test_imported_playground_core_memory_is_readable():
    status, agents = _request("GET", "/v1/agents/?limit=100")
    assert status == 200
    playground = next(agent for agent in agents if agent.get("name") == "ADE Playground")
    agent_id = playground["id"]
    status, blocks = _request("GET", f"/v1/agents/{agent_id}/core-memory/blocks?limit=20")
    assert status == 200
    assert blocks
    label = blocks[0]["label"]
    status, one = _request("GET", f"/v1/agents/{agent_id}/core-memory/blocks/{label}")
    assert status == 200
    assert one["label"] == label
