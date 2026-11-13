"""Vercel Python function: authenticated, citation-checked Groq queries.

The site remains publicly readable. Real requests require a reviewer access code,
a private Groq key, Vercel WAF rate limiting and the pinned full-PDF corpus.
No Groq secret is ever returned to the browser or logged.
"""
from __future__ import annotations

import asyncio
import gzip
import hmac
import json
import os
import re
import sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relay import Corpus, Groq, PAPERS, Passage, UNSUPPORTED, ask  # noqa: E402

CORPUS_FILE = ROOT / "data" / "web_corpus.json.gz"
MAX_REQUEST_BYTES = 1024
MAX_QUESTION_CHARS = 220


@lru_cache(maxsize=1)
def corpus_from_pinned_pdfs():
    with gzip.open(CORPUS_FILE, "rt", encoding="utf-8") as file:
        obj = json.load(file)
    if obj.get("schema") != 1 or set(obj.get("source_sha256", {})) != set(PAPERS):
        raise RuntimeError("Full-paper corpus manifest missing or invalid")
    pages = obj.get("pages", [])
    if len(pages) < 45:
        raise RuntimeError("Incomplete PDF evidence corpus")
    valid = [Passage(p["paper"], int(p["page"]), p["text"])
             for p in pages if p["paper"] in PAPERS and 1 <= int(p["page"]) <= 300]
    if len(valid) != len(pages):
        raise RuntimeError("Corpus contains unexpected paper versions or page IDs")
    return Corpus(valid)


def live_ready():
    return bool(os.getenv("GROQ_API_KEY") and os.getenv("RELAY_DEMO_PASSCODE")
                and len(os.getenv("RELAY_DEMO_PASSCODE", "")) >= 12
                and CORPUS_FILE.is_file())


def valid_reviewer_code(token):
    expected = os.getenv("RELAY_DEMO_PASSCODE", "")
    return bool(expected and len(expected) >= 12 and isinstance(token, str)
                and hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")))


def make_answer(question):
    """Call the exact five-stage research pipeline; model content is verified before release."""
    corpus = corpus_from_pinned_pdfs()
    model = Groq(max_completion_tokens=180)
    trace = []
    record, answer = asyncio.run(ask(question, corpus, model, setting="balanced",
                                     scenario="hosted_demo", request_id="web", trace=trace))
    if record["status"] == "rate_limited":
        return 429, {"error": "provider_quota", "message": "Groq quota reached; please try later."}
    if record["status"] != "ok":
        return 503, {"error": "model_unavailable", "message": "A verified answer is unavailable right now."}

    source_pages = []
    cited = set(re.findall(r"\[\d{4}\.\d{5}v\d+ p\.\d+\]", answer))
    if cited:
        # The verifier already checked these labels against actual retrieved chunks.
        for p in corpus.retrieve(question, "balanced"):
            if p.citation in cited and p.citation not in {x["citation"] for x in source_pages}:
                source_pages.append({"paper": p.paper, "page": p.page, "citation": p.citation,
                                     "url": f"https://arxiv.org/pdf/{p.paper}#page={p.page}",
                                     "excerpt": p.text[:115]})
    return 200, {
        "answer": answer,
        "refused": answer == UNSUPPORTED,
        "mode": "groq_full_pdf" if int(record.get("tokens_in") or 0) > 0 else "local_refusal",
        "model": model.model if int(record.get("tokens_in") or 0) > 0 else None,
        "sources": source_pages,
        "server_elapsed_ms": record["total_ms"],
        "notice": "Research prototype: citation labels and numbers are checked, not full semantic entailment."
    }


class handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        self.reply(200, {"mode": "reviewer_access", "ready": live_ready(),
                         "corpus": "three_version_pinned_full_papers" if CORPUS_FILE.is_file()
                         else "not_built",
                         "note": "Live Groq requires reviewer code; public evidence preview is always available."})

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        host = self.headers.get("Host", "")
        if origin and origin.rstrip("/") != "https://" + host:
            return self.reply(403, {"error": "origin_rejected"})
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit() or int(raw_length) < 1 or int(raw_length) > MAX_REQUEST_BYTES:
            return self.reply(413, {"error": "invalid_payload_size"})
        if "application/json" not in self.headers.get("Content-Type", "").lower():
            return self.reply(415, {"error": "json_required"})
        if not live_ready():
            return self.reply(503, {"error": "live_not_configured",
                                    "message": "This deployment needs its private Groq key and reviewer code."})
        if not valid_reviewer_code(self.headers.get("X-Relay-Access", "")):
            return self.reply(401, {"error": "reviewer_code_required",
                                    "message": "Enter the private reviewer access code for live questions."})
        try:
            value = json.loads(self.rfile.read(int(raw_length)))
            question = value.get("question", "") if isinstance(value, dict) else ""
        except (ValueError, UnicodeDecodeError):
            return self.reply(400, {"error": "invalid_json"})
        if not isinstance(question, str) or not 8 <= len(question.strip()) <= MAX_QUESTION_CHARS:
            return self.reply(400, {"error": "question_must_be_8_to_220_characters"})
        try:
            status, answer = make_answer(question.strip())
            return self.reply(status, answer)
        except Exception:
            # Do not leak Groq headers, credentials, local file paths or tracebacks.
            return self.reply(503, {"error": "verification_unavailable",
                                    "message": "The research assistant could not verify an answer."})

    def do_OPTIONS(self):
        self.reply(405, {"error": "cross_origin_api_disabled"})
