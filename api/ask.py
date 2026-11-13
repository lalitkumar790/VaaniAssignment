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



def relevant_source_excerpt(question, answer, page_text, max_chars=340):
    """Find a nearby on-page anchor, not the start of an arbitrary retrieved chunk.

    The excerpt is an inspection aid, not a semantic-entailment guarantee. For
    numeric answers, show no excerpt unless the cited full page contains the
    claimed number, to avoid presenting an unrelated passage as evidence.
    """
    import unicodedata
    from retrieval_optimized import normalize, tokenize

    page_text = normalize(page_text)
    claim = re.sub(r"\[\d{4}\.\d{5}v\d+ p\.\d+\]", "", answer).strip()
    claim = unicodedata.normalize("NFKC", claim)
    q = unicodedata.normalize("NFKC", question)
    numbers = list(dict.fromkeys(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?!\d)", claim)))
    keywords = set(tokenize(q + " " + claim))
    matches = []

    if numbers:
        for number in numbers:
            pattern = r"(?<![\d.])" + re.escape(number) + r"(?![\d])"
            for match in re.finditer(pattern, page_text, re.IGNORECASE):
                matches.append((match.start(), match.end(), 4.0))
    else:
        # For nonnumeric claims, select the best textual overlap across the page.
        for match in re.finditer(r"\b[A-Za-z][A-Za-z-]{3,}\b", page_text):
            if match.group().casefold() in keywords:
                matches.append((match.start(), match.end(), 0.0))
                if len(matches) > 900:
                    break

    if not matches:
        return ""

    requested_qualifier = next((w for w in ("theoretical", "practical", "observed") if w in q.lower()), None)
    best = None
    best_score = float("-inf")
    for start, end, bonus in matches:
        left = max(0, start - 180)
        right = min(len(page_text), end + 180)
        window = page_text[left:right]
        context = page_text[max(0, start - 95):min(len(page_text), end + 95)].lower()
        score = bonus + len(keywords & set(tokenize(window))) * 0.75
        if requested_qualifier and requested_qualifier in context:
            score += 8
        if "latency" in q.lower() and "latency" in context:
            score += 3
        if "ms" in claim.lower() and re.search(r"\bms\b", context):
            score += 2
        if score > best_score:
            best_score, best = score, (start, end)

    if best is None:
        return ""
    start, end = best
    # Prefer a complete sentence that includes the matched value.
    search_left = max(0, start - max_chars)
    sentence_left = page_text.rfind(". ", search_left, start)
    left = sentence_left + 2 if sentence_left >= 0 else max(0, start - 135)
    search_right = min(len(page_text), end + max_chars)
    sentence_right = page_text.find(". ", end, search_right)
    right = sentence_right + 1 if sentence_right >= 0 else min(len(page_text), end + 175)
    if right - left > max_chars:
        left = max(0, start - 135)
        right = min(len(page_text), left + max_chars)
        if right <= end:
            right = min(len(page_text), end + 80)
            left = max(0, right - max_chars)
    excerpt = page_text[left:right].strip(" \n\t")
    if left and not excerpt.startswith(("…", " ")):
        excerpt = "…" + excerpt
    if right < len(page_text):
        excerpt += "…"
    return excerpt


def cited_sources(question, answer, corpus):
    """Resolve only validated citations to anchored excerpts of their actual pages."""
    citation_pattern = r"\[\d{4}\.\d{5}v\d+ p\.\d+\]"
    found = set(re.findall(citation_pattern, answer))
    if not found:
        return []
    # Use the full original PDF page; many independently retrieved chunks share
    # the same page citation, and the first chunk may be entirely unrelated.
    pages = {p.citation: p for p in corpus.passages if p.citation in found}
    result = []
    for label in sorted(found):
        page = pages.get(label)
        if page is None:
            continue
        excerpt = relevant_source_excerpt(question, answer, page.text)
        result.append({
            "paper": page.paper,
            "page": page.page,
            "citation": page.citation,
            "url": f"https://arxiv.org/pdf/{page.paper}#page={page.page}",
            "excerpt": excerpt,
        })
    return result


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

    source_pages = cited_sources(question, answer, corpus)
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
