# The Relay — Vaani ML Engineering Intern assignment

**Public demo:** https://vaani-relay.vercel.app · **Two-page submission:** [REPORT.pdf](REPORT.pdf) · **Raw request evidence:** [results.csv](results.csv) · **Reproducibility:** [OPERATIONS.md](OPERATIONS.md)

A Python **five-stage evidence-first research assistant** (classify → retrieve the exact PDF versions → admit/plan → stream with Groq or stand-in → verify citation or refuse). It includes quota/queue admission, retries before streaming, paper-version-aware retrieval, a simulated model with 429/503/slowdown/streaming, and three tested chunking settings.

**Evidence state as of 11 November 2026:** 519 distinct per-request rows merged from baseline and independently recorded V4/V5 experiments; all real Groq calls are explicitly marked `source=real`, simulations `source=stand-in`. The final GitHub Actions [merge/build run](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42971254577) passed the 519-unique-rows and two-PDF-pages assertions.


## Protected live website Q&A (server-side Groq)

The public dashboard at https://vaani-relay.vercel.app now contains two explicitly distinct question modes:

- **Live Groq · full PDFs:** `POST /api/ask` calls the real Python retrieval → Groq streaming → citation verification pipeline using the 120-page, SHA-256-verified, compressed index generated from the exact three original arXiv PDFs. Only verified output is returned to the browser. The passcode remains in browser memory (never local storage); the Groq API key is never sent to the browser.
- **Curated offline preview:** a 19-note, intentionally limited evidence search without any hosted LLM call. This always works without private API credentials.

**Activation (required, private):** the Vercel project `vaani-relay` is connected to GitHub and has `RELAY_DEMO_PASSCODE` set as an encrypted **Production** environment variable. Add `GROQ_API_KEY` as another encrypted **Production** variable directly in **Vercel → vaani-relay → Settings → Environment Variables**. Use the key already saved in your private GitHub Actions secret, or create another at https://console.groq.com/keys. Do **not** paste any key into chat, source code, README, GitHub Issues, or the public website. **Redeploy** the latest `main` commit after setting the variable (existing deployments do not inherit newly added secrets). Then verify that `GET https://vaani-relay.vercel.app/api/ask` returns `"ready":true`. Reviewers need the separate passcode, which the owner must share out of band.

**Abuse controls:** a Vercel WAF rule limits `POST /api/ask` to **2 requests/IP/minute**, and the server verifies a strong reviewer passcode before any model call. Inputs are capped at 220 characters, output at 180 completion tokens, requests must be same-origin, and errors and quota exhaustion fail closed rather than generating uncited fallback text. This is a restricted evaluation demo, **not** a globally budget-capped, multi-tenant production service. Distributed callers sharing the code may still consume the free quota. Revoke or rotate the code when reviewing ends; remove `GROQ_API_KEY` from Vercel to turn live inference off immediately after a fresh deployment.

**Key deployment audit:** `data/web_corpus.json.gz` is generated through [the pinned corpus build workflow](.github/workflows/web-corpus.yml), not curated answers. The public user interface does not reveal or offer download of that compressed corpus. Its source-version hashes are in `data/web_corpus_manifest.json`. Local smoke tests run with no live secret and assert disabled mode; historical Groq latency results are never attributed to this new public deployment.

## Research corpus (exact versions)

- [Attention Is All You Need — 1706.03762v7](https://arxiv.org/pdf/1706.03762v7)
- [Moshi — 2410.00037v1](https://arxiv.org/pdf/2410.00037v1)
- [Dynamic Chunking — 2507.07955v2](https://arxiv.org/pdf/2507.07955v2)

`python relay.py fetch` downloads and hashes all three. Full-PDF mode refuses to run when any version is absent. The public browser “Ask the papers” demonstration uses **curated paraphrased notes** and is **not a live Groq-backed chatbot**.

## Verified measurements (not performance claims)

| Run | Groq requests | TTFT p50 | Total p50 | Strict answer-key score |
| --- | ---: | ---: | ---: | ---: |
| [V3](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42870960714) | 18/18 HTTP200 | 322.9 ms | 348.5 ms | 6/18 |
| [V4](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42969257016) | 18/18 HTTP200 | 318.8 ms | 350.5 ms | 6/18 |
| [V5](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42970031360) | 16 HTTP200 + 2 local refusals | 390.7 ms | 441.0 ms | 6/18 pipeline questions |

The [V1](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42866165930) test recorded 16 successes followed by a genuine **HTTP429, Retry-After 5 s**, with Groq headers indicating **8,000 tokens/min** and **1,000 requests/day**. V2's 18 HTTP401 authentication errors are retained but **excluded from successful-model latency conclusions**.

**Important V5 correction:** The 18-record V5 pipeline includes two refusals that never contacted Groq. HTTP response headers confirm **16 actual hosted calls**. The old 361.6 ms TTFT median includes those local refusals; actual hosted-only TTFT p50 is **390.7 ms**. The 6/18 strict grade checks literal answer-key strings and is **not a verified semantic accuracy estimate**. Run `python audit_evidence.py` to reproduce the distinction.

**Latest full-PDF stand-in ([V4](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42969980873))**: 54 requests covering 18 questions × 3 settings; 17 strict correct+cited, 29 wrong, 7 correctly refused, 1 wrongly refused. Setting-level strict scores: small **4/18**, balanced **6/18**, wide **7/18**. Wide settings use substantially more token-proxy context. These are automated exact-string/citation grades; some semantically correct paraphrases may be undercounted. Conversely a plausible cited answer can still be wrong. **This is an experimental prototype, not production-ready question answering.**

## Run and verify

Python 3.11+, then:

```powershell
git clone https://github.com/lalitkumar790/VaaniAssignment.git
cd VaaniAssignment
python -m pip install -r requirements.txt
python -m pytest -q

# Clearly labeled limited offline note fixture
python relay.py ask --demo "What is Moshi's theoretical latency?"

# Exact 3-paper corpus; internet required
python relay.py fetch
python relay.py ask "How does Moshi support real-time dialogue?"

# On Windows PowerShell only: save your key privately in your shell/session
$env:GROQ_API_KEY = "YOUR_PRIVATE_GROQ_KEY"
python relay.py ask --real "How does Moshi support real-time dialogue?"
```

Do **not** commit your API key. The Groq Actions workflows use the repository's `GROQ_API_KEY` secret. The original strictly measured rows are retained in `artifacts/`; `assemble_final_evidence.py` identifies pinned action runs and versions the merged requests. See `render_evidence_pdf.py` for how the mandatory tables are recomputed from `results.csv`. Latest regression tests include provider-versus-local accounting assertions..

## Engineering decisions & limitations

- Fast refusals are preferred over fabricated uncited replies; the service holds streamed internal tokens until final citation verification. Internal TTFT is **not** user-visible verified-answer latency.
- The stand-in's parallel slowdown and queue behavior were **not observed on Groq** (real calls were serial). Load shapes simulate admission failures rather than reproducing proven hosted concurrency.
- Retrieval uses normalized PDF text, version routing, cached chunk indexes, lexical scoring and optional diversification. Its citation guard rejects unreturned citations and unsupported numerical claims but **cannot guarantee semantic entailment**.
- Queue timeout refunds locally reserved simulated quota; the provider rate-limit headers and observed 429 are distinct from synthetic rate limits.
- **Applicant action before submission:** personally audit cited answers; replace any drafted personal Vaani feedback with your genuine opinion; attach the full original AI conversation history where available (the repo's `conversation_history.md` is explicitly an extract, not a complete transcript).

**Artifacts:** [Two-page PDF](REPORT.pdf) · [Results CSV, 519 rows](results.csv) · [V4 full-PDF quality CSV](artifacts/v4_fullpdf_quality_results.csv) · [V5 real Groq CSV](artifacts/v5_real_results.csv) · [V5 traces](artifacts/v5_real_traces.json) · [Final merge summary](artifacts/final_merge_summary.json)
