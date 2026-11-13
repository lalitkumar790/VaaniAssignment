"""Security and deployment regression tests for the optional live reviewer endpoint."""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("vaani_api_ask",ROOT/"api"/"ask.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_locked_full_pdf_corpus_available():
    corpus=module.corpus_from_pinned_pdfs()
    assert len(corpus.passages)>=45
    assert {p.paper for p in corpus.passages}=={"1706.03762v7","2410.00037v1","2507.07955v2"}
    assert all(p.note=="PDF" for p in corpus.passages)

def test_no_private_credentials_means_disabled(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    monkeypatch.delenv("RELAY_DEMO_PASSCODE",raising=False)
    assert module.live_ready() is False
    assert module.valid_reviewer_code("wrong") is False

def test_passcode_is_not_public_and_is_checked_constant_time(monkeypatch):
    monkeypatch.setenv("RELAY_DEMO_PASSCODE","test-very-long-private-code-123")
    assert module.valid_reviewer_code("test-very-long-private-code-123")
    assert not module.valid_reviewer_code("bad")
    assert not module.valid_reviewer_code(None)
    assert not module.valid_reviewer_code("test-very-long-private-code-123 ")

def test_frontend_never_embeds_groq_key():
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    assert 'fetch("/api/ask"' in html
    assert "X-Relay-Access" in html
    assert 'type="password"' in html
    assert "Bearer " not in html

def test_vercel_route_and_waf_intended_endpoint():
    import json
    config=json.loads((ROOT/"vercel.json").read_text())
    assert any(x.get("src")=="^/api/ask/?$" and x.get("dest")=="/api/ask.py" for x in config["routes"])
    assert any(x["src"]=="api/ask.py" and x["use"]=="@vercel/python" for x in config["builds"])
