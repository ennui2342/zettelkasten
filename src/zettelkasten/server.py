"""Local HTTP ingest server for the browser bookmarklet.

Accepts POST /ingest with JSON {html: str, url: str}.
Extracts text from the rendered HTML using trafilatura, then runs the
full Form → Gather → Integrate pipeline.

Uses only stdlib http.server — no extra dependencies.
"""
from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import trafilatura

log = logging.getLogger("zettelkasten")

_MAX_BODY = 20 * 1024 * 1024  # 20 MB — enough for any rendered page


# ---------------------------------------------------------------------------
# Handler factory
# ---------------------------------------------------------------------------


def make_handler(store, llm, embed, fast_llm=None, inbox_dir=None, save_only=False):
    """Return a request handler class bound to *store*, *llm*, *embed*.

    When *save_only* is True the handler saves incoming documents to
    *inbox_dir* but skips the Form → Gather → Integrate pipeline.
    """
    _fast_llm = fast_llm or llm
    _inbox_dir = inbox_dir
    _save_only = save_only

    class _Handler(BaseHTTPRequestHandler):

        # ---- routing ----

        def do_OPTIONS(self):
            self.send_response(200)
            self._cors()
            self.end_headers()

        def do_GET(self):
            if self.path == "/health":
                self._json(200, {"status": "ok"})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/ingest":
                self._handle_ingest()
            else:
                self._json(404, {"error": "not found"})

        # ---- ingest ----

        def _handle_ingest(self):
            length = int(self.headers.get("Content-Length", 0))
            if length > _MAX_BODY:
                self._json(413, {"error": "payload too large"})
                return

            try:
                body = self.rfile.read(length)
                data = json.loads(body)
            except (json.JSONDecodeError, OSError) as exc:
                self._json(400, {"error": f"bad request: {exc}"})
                return

            html = data.get("html", "")
            url = data.get("url", "")

            text = trafilatura.extract(
                html,
                url=url or None,
                include_comments=False,
                include_tables=False,
            )
            if not text:
                log.warning("server.no_content url=%r", url)
                self._json(400, {"error": "no content could be extracted from the page"})
                return

            if _inbox_dir is not None:
                from .inbox import save_to_inbox
                saved = save_to_inbox(_inbox_dir, text, source=url or None)
                log.info("server.saved path=%s", saved)

            if _save_only:
                msg = "saved to inbox"
                log.info("server.save_only url=%r path=%s", url, saved if _inbox_dir else "(no inbox_dir)")
                self._json(200, {"ok": True, "results": [], "summary": msg})
                return

            log.info("server.ingest url=%r text_len=%d", url, len(text))
            try:
                results = store.ingest_text(text, llm, embed, source=url or None, fast_llm=_fast_llm)
            except Exception as exc:
                log.exception("server.ingest_error")
                self._json(500, {"error": str(exc)})
                return

            summary = [
                {
                    "operation": r.operation,
                    "note_id":   getattr(r, "note_id", "") or "",
                    "title":     r.note_title,
                    "confidence": r.confidence,
                }
                for r in results
            ]
            msg = f"{len(results)} draft(s) processed"
            log.info("server.ingest_complete url=%r %s", url, msg)
            self._json(200, {"ok": True, "results": summary, "summary": msg})

        # ---- helpers ----

        def _json(self, status: int, data: dict) -> None:
            body = json.dumps(data).encode()
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, fmt, *args):  # silence default stderr logging
            log.debug("server.http " + fmt, *args)

    return _Handler


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def make_server(store, llm, embed, host: str = "127.0.0.1", port: int = 7842, fast_llm=None, inbox_dir=None, save_only=False):
    """Create and return a :class:`ThreadingHTTPServer` (not yet started)."""
    handler = make_handler(store, llm, embed, fast_llm=fast_llm, inbox_dir=inbox_dir, save_only=save_only)
    return ThreadingHTTPServer((host, port), handler)


# ---------------------------------------------------------------------------
# Bookmarklet generator
# ---------------------------------------------------------------------------


def bookmarklet_js(port: int = 7842) -> str:
    """Return a ``javascript:`` bookmarklet URL that POSTs the current page."""
    js = (
        "(function(){"
        "var h=document.documentElement.outerHTML,"
        "u=document.URL;"
        f"fetch('http://127.0.0.1:{port}/ingest',"
        "{method:'POST',"
        "headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({html:h,url:u})})"
        ".then(function(r){return r.json()})"
        ".then(function(d){alert('\\u2705 '+d.summary)})"
        ".catch(function(e){alert('\\u274c Ingest failed: '+e)});"
        "})()"
    )
    return "javascript:" + js
