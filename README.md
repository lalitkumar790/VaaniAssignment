# The Relay — Vaani ML Engineering Intern assignment

**[Public demonstration](https://vaani-relay.vercel.app)** · **[Exactly two-page report](REPORT.pdf)** · **[519-row raw results.csv](results.csv)** · **[Assignment brief](https://github.com/lalitkumar790/VaaniAssignment)**

The Relay is a Python implementation of a five-stage, evidence-first research-paper QA pipeline: **classify → retrieve cited passages → plan/admit → stream a model draft → verify or refuse**. It includes a live Groq adapter, a calibrated *but not concurrency-validated* stand-in model, failure/429 injection, retriable pre-stream errors, and three retrieval settings.

## Exact source library

| Research paper | Fixed version |
|---|---|
| Attention Is All You Need | [1706.03762v7](https://arxiv.org/pdf/1706.03762v7) |
| Moshi: a speech-text foundation model for real-time dialogue | [2410.00037v1](https://arxiv.org/pdf/2410.00037v1) |
| Dynamic Chunking for End-to-End Hierarchical Sequence Modeling | [2507.07955v2](https://arxiv.org/pdf/2507.07955v2) |

The full-PDF hosted index contains 120 nonempty pages with source SHA-256 hashes in [data/web_corpus_manifest.json](data/web_corpus_manifest.json). The website's **Live Groq** mode calls the server-side `/api/ask` endpoint and requires a private reviewer code; it has been verified on a real Moshi question, including a correct supporting passage. The optional **Offline fixture** uses 19 notes only, without a hosted model call. Neither method guarantees full semantic entailment.

**Security:** Groq and reviewer secrets are Vercel Production environment variables, never client-side JavaScript or repository files. Vercel WAF rate-limits `POST /api/ask` to 2/IP/minute; this is not a global token/day budget. Reviewers must be given the separate passcode privately, not through a public README.

## Evidence and what it does *not* prove

- **V1:** 16 real Groq successes and a measured HTTP 429 with 5 seconds of Retry-After; headers indicated 8,000 TPM and 1,000 RPD for the tested account/model.
- **V5:** 18 pipeline questions, **16 actual Groq HTTP 200 calls and 2 local refusals**. Provider-only first-token p50 **390.7 ms** and total p50 **441.0 ms**. See [the provider audit](artifacts/v5_provider_audit.json).
- **Full-PDF V4 stand-in:** 18 questions × 3 settings; strict literal-key grade: **17/54 correct and cited, 29 wrong, 7 justified refusals, 1 wrongful refusal**. Strict-key scores should **not** be equated with independently reviewed semantic accuracy. A wider retrieval window costs more tokens, but correctness remains limited.
- **All requests:** [results.csv](results.csv) contains 519 unique rows, including rejected and failed requests. Real-provider requests were serial; stand-in overload behavior has not been independently validated against Groq concurrency.

The [two-page PDF](REPORT.pdf) contains the assignment's required Tables 1, 2a, 2b and 3, a slow trace, admission/timeout/retry decisions, quality/cost tradeoffs, retrieval failure cases, and limitations. Recompute or audit its figures via [render_evidence_pdf.py](render_evidence_pdf.py) and [audit_evidence.py](audit_evidence.py). See [OPERATIONS.md](OPERATIONS.md) for more detail.

## Reproduce

Python 3.11+:

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python relay.py fetch
python relay.py ask "What is the theoretical latency of Moshi?"
```

To run hosted calls locally, set `GROQ_API_KEY` privately and use `python relay.py ask --real "What is the theoretical latency of Moshi?"`. Never commit or publish a key. The public Vercel backend is already configured and remains protected by reviewer access and provider quotas.

## Required submission and ownership

Submit **REPORT.pdf**, **results.csv**, **the repository/source**, and **your authentic unedited assistant conversation history**. The website is optional supporting evidence.

**Applicant review required:** The repository's [conversation_history.md](conversation_history.md) is only a partial extract, not the requested full transcript. The two-page report contains draft feedback and assistant-work reflection that must be confirmed or revised in the applicant's own words: three consequential prompts, one caught assistant error, one override, and what was distinctly the applicant's contribution. Do not submit invented personal claims.

**Current state:** reproducible evaluated prototype, not a production-ready factual QA service.
