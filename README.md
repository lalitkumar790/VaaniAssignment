# The Relay — Vaani ML Engineering Intern assignment

**Public demo:** https://vaani-relay.vercel.app · **Two-page submission:** [REPORT.pdf](REPORT.pdf) · **Raw request evidence:** [results.csv](results.csv) · **Reproducibility:** [OPERATIONS.md](OPERATIONS.md)

A Python **five-stage evidence-first research assistant** (classify → retrieve the exact PDF versions → admit/plan → stream with Groq or stand-in → verify citation or refuse). It includes quota/queue admission, retries before streaming, paper-version-aware retrieval, a simulated model with 429/503/slowdown/streaming, and three tested chunking settings.

**Evidence state as of 11 November 2026:** 519 distinct per-request rows merged from baseline and independently recorded V4/V5 experiments; all real Groq calls are explicitly marked `source=real`, simulations `source=stand-in`. The final GitHub Actions [merge/build run](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42971254577) passed the 519-unique-rows and two-PDF-pages assertions.

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
