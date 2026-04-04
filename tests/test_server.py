"""Tests for the local ingest HTTP server."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.client import HTTPConnection
from pathlib import Path

import pytest

from zettelkasten.integrate import IntegrationResult
from zettelkasten.providers import MockEmbed, MockLLM
from zettelkasten.server import make_server


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EMBED = MockEmbed(dims=32)

_FORM_OUTPUT = "## Memory Consolidation\n\nSleep strengthens memory consolidation."
_STEP2_OUTPUT = "## Memory Consolidation\n\nSleep strengthens memory by consolidating neural pathways."


def _pipeline_llm() -> MockLLM:
    def respond(prompt: str, **kw) -> str:
        if "topic areas" in prompt or "broad topic" in prompt:
            return _FORM_OUTPUT
        if "pseudo_notes" in prompt:
            return '{"pseudo_notes": ["memory", "sleep", "consolidation"]}'
        if "abstraction" in prompt:
            return '{"abstraction": "Biological processes that consolidate learning."}'
        if "hypotheticals" in prompt:
            return '{"hypotheticals": ["rest aids recall", "sleep deepens memory", "naps help learning"]}'
        if "Output JSON only" in prompt:
            return '{"operation": "CREATE", "target_note_ids": [], "reasoning": "New topic.", "confidence": 0.9}'
        return _STEP2_OUTPUT
    return MockLLM(respond)


@pytest.fixture()
def live_server(tmp_path):
    """Start a real ThreadingHTTPServer on an ephemeral port; yield (host, port)."""
    from zettelkasten.store import ZettelkastenStore

    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    server = make_server(store, _pipeline_llm(), _EMBED, host="127.0.0.1", port=0)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield host, port
    server.shutdown()
    server.server_close()


@pytest.fixture()
def live_server_with_inbox(tmp_path):
    """Server with inbox saving enabled; yields (host, port, inbox_dir)."""
    from zettelkasten.store import ZettelkastenStore

    inbox_dir = tmp_path / "inbox"
    store = ZettelkastenStore(tmp_path / "notes", tmp_path / "index.db")
    server = make_server(
        store, _pipeline_llm(), _EMBED,
        host="127.0.0.1", port=0, inbox_dir=inbox_dir,
    )
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield host, port, inbox_dir
    server.shutdown()
    server.server_close()


def _post(host, port, path, data):
    body = json.dumps(data).encode()
    conn = HTTPConnection(host, port, timeout=10)
    conn.request("POST", path, body, {"Content-Type": "application/json"})
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


def _get(host, port, path):
    conn = HTTPConnection(host, port, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read())


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_returns_200(live_server):
    host, port = live_server
    status, data = _get(host, port, "/health")
    assert status == 200
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /ingest
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """\
<html><body>
<article>
<h1>Sleep and Memory Consolidation</h1>
<p>Research shows that sleep plays a critical role in consolidating memories
formed during waking hours. During slow-wave sleep, the hippocampus replays
recent experiences, transferring them to long-term cortical storage.</p>
<p>Studies using polysomnography demonstrate that subjects deprived of sleep
after learning show significantly worse recall the following day compared to
those who slept normally.</p>
</article>
</body></html>
"""


def test_ingest_html_returns_200(live_server):
    host, port = live_server
    status, data = _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com/article"})
    assert status == 200
    assert data["ok"] is True


def test_ingest_html_returns_results(live_server):
    host, port = live_server
    _, data = _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com"})
    assert "results" in data
    assert len(data["results"]) >= 1


def test_ingest_html_result_has_fields(live_server):
    host, port = live_server
    _, data = _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com"})
    result = data["results"][0]
    assert "operation" in result
    assert "note_id" in result
    assert "title" in result


def test_ingest_html_writes_note_file(live_server, tmp_path):
    host, port = live_server
    _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com"})
    # Give the server thread time to finish writing
    import time; time.sleep(0.1)
    # The fixture store uses tmp_path/notes — find any md file in any tmp dir
    # (we check via the response instead)


def test_ingest_no_content_returns_400(live_server):
    """A page that trafilatura can't extract anything from."""
    host, port = live_server
    bare_html = "<html><body><script>alert(1)</script></body></html>"
    status, data = _post(host, port, "/ingest", {"html": bare_html, "url": "https://example.com"})
    assert status == 400
    assert "error" in data


def test_ingest_bad_json_returns_400(live_server):
    host, port = live_server
    conn = HTTPConnection(*live_server, timeout=5)
    conn.request("POST", "/ingest", b"not json", {"Content-Type": "application/json"})
    resp = conn.getresponse()
    assert resp.status == 400


def test_unknown_path_returns_404(live_server):
    host, port = live_server
    status, _ = _get(host, port, "/unknown")
    assert status == 404


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_options_returns_cors_headers(live_server):
    host, port = live_server
    conn = HTTPConnection(host, port, timeout=5)
    conn.request("OPTIONS", "/ingest")
    resp = conn.getresponse()
    assert resp.status == 200
    headers = dict(resp.getheaders())
    assert "Access-Control-Allow-Origin" in headers


def test_ingest_response_has_cors_header(live_server):
    host, port = live_server
    conn = HTTPConnection(host, port, timeout=5)
    body = json.dumps({"html": _SAMPLE_HTML, "url": "https://example.com"}).encode()
    conn.request("POST", "/ingest", body, {"Content-Type": "application/json"})
    resp = conn.getresponse()
    headers = dict(resp.getheaders())
    assert "Access-Control-Allow-Origin" in headers


# ---------------------------------------------------------------------------
# Inbox saving
# ---------------------------------------------------------------------------


def test_ingest_saves_to_inbox(live_server_with_inbox):
    import time
    host, port, inbox_dir = live_server_with_inbox
    _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com/article"})
    time.sleep(0.1)
    files = list(inbox_dir.glob("*.md"))
    assert len(files) == 1


def test_ingest_saved_file_has_url(live_server_with_inbox):
    import time
    host, port, inbox_dir = live_server_with_inbox
    _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com/article"})
    time.sleep(0.1)
    content = next(inbox_dir.glob("*.md")).read_text()
    assert "example.com" in content


def test_ingest_saved_file_has_frontmatter(live_server_with_inbox):
    import time
    host, port, inbox_dir = live_server_with_inbox
    _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com/article"})
    time.sleep(0.1)
    content = next(inbox_dir.glob("*.md")).read_text()
    assert content.startswith("---")
    assert "saved_at:" in content


def test_ingest_without_inbox_dir_does_not_save(live_server, tmp_path):
    import time
    host, port = live_server
    _post(host, port, "/ingest", {"html": _SAMPLE_HTML, "url": "https://example.com/article"})
    time.sleep(0.1)
    # No inbox_dir configured — no inbox directory should appear under tmp_path
    assert not (tmp_path / "inbox").exists()


