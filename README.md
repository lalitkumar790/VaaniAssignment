# The Relay — Vaani ML Engineering Intern assignment

A research-paper QA pipeline with an explicit **citation-or-refuse** policy, configurable retrieval, a Groq streaming adapter, a failure-injecting stand-in, and per-request latency/load instrumentation.

> **Submission state (2026-11-10):** Local stand-in tests are reproducible. **Real Groq requests have not been run** because there is no user Groq key in this execution environment. The stand-in has **not** been calibrated to real Groq measurements. The local fixture is **19 paraphrased, page-checked notes** from the exact versions, not a substitute for downloading and indexing the full papers. This is a working prototype and an honest partial empirical submission, **not** a claim to have completed all brief requirements.

## Exact library (versions cannot float)

- [Attention Is All You Need, 1706.03762v7](https://arxiv.org/pdf/1706.03762v7)
- [Moshi, 2410.00037v1](https://arxiv.org/pdf/2410.00037v1)
- [Dynamic Chunking, 2507.07955v2](https://arxiv.org/pdf/2507.07955v2)

The real (non-demo) mode refuses to start unless **all three** pinned PDFs are present. `fetch` validates PDF bytes and records URL, size, SHA-256 in `data/papers/manifest.json`. PDFs are excluded from Git to keep the repository light.

## Quick start

Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q

# Fully offline, transparent local demo (limited evidence notes)
python relay.py ask --demo "What is the theoretical latency of Moshi?"
python relay.py quality --demo
python relay.py load --demo
python relay.py retry-case --demo
python build_report.py

# Full version-locked PDFs (requires internet)
python relay.py fetch
python relay.py ask "How does Moshi support full-duplex speech?"

# Real Groq hosted inference (requires YOUR free key and network access)
# PowerShell: $env:GROQ_API_KEY="your-key"
# bash: export GROQ_API_KEY="your-key"
python relay.py ask --real "How does Moshi support full-duplex speech?"
python relay.py real-probe --count 8
```

**Never commit API keys.** The script reads `GROQ_API_KEY` from the environment. The brief asks you to use your own account, observe your exact RPM/TPM/RPD limits, watch `429` headers, measure a modest amount of real service traffic, then fit stand-in delay distributions to those observations. Until that is done, keep the report explicitly marked **not measured**.

## Five stages and safety

`classify → retrieve(page citation tool) → evidence/scope plan → streaming draft → citation validation (or refusal)`.

The retrieval code uses deterministic lexical BM25 and an optional transparent lexical re-rank. It preserves paper version and page number. The stand-in streams *internally* one word at a time; the full answer is **held until citation verification** rather than exposing potentially uncited partial facts to a user. Therefore `first_token_ms` is **the first internal generated token**, not first user-visible verified answer. This is an explicit quality-versus-latency tradeoff.

429/day and 429/minute are not retried if the reset exceeds the deadline; transient 503 is retried once only **before** any token has been emitted. A successful retry is recorded as `ok` after verification.

## Reproduce the evidence

- `results.csv`: **144 local stand-in request records**; one row per request, including exactly the brief's required fields plus `queue_peak_observed`, `cost_usd` to reproduce all results-table fields.
- `REPORT.pdf`: **exactly two pages** with the required section order and all three tables.
- `REPORT.md`: corresponding readable narrative and tables.
- `artifacts/load_results.csv`: five scenario records, including steady, burst, sustained overload, half the RPM, exhausted day.
- `artifacts/quality_results.csv` and `artifacts/quality_answers.json`: 18 manually authored questions × 3 retrieval settings, with a transparent substring-plus-citation *automated* scoring oracle. Do not mistake for blinded human grading.
- `artifacts/retry_results.csv`, `artifacts/retry_traces.json`: intentionally failing first attempt versus one retry.
- `artifacts/traces.json`: chronological timestamps for phase-level latency diagnosis.
- `artifacts/experiment_manifest.json`: scenario parameters, summary, and important caveats.
- `conversation_history.md`: accessible user instruction and unedited local work steps; this is **not** a complete platform chat export.

The stand-in simulates queueing, streaming chunks, lognormal startup delays, load-sensitive slowness, injected 503, RPM / TPM / daily budget admission, and queue deadline. Its latency and usage parameters are *chosen*, not fit to real Groq. The model uses a deterministic extractive response proxy—not learned inference—and its tokens are a four-characters-per-token estimate. A local stand-in has zero external API charges; that excludes compute and electricity.

## Known limitations and completion checklist

1. **Must complete:** download real full PDFs with `fetch` (run in an Internet-connected terminal); inspect SHA-256 manifest.
2. **Must complete:** obtain a free Groq key privately and run modest real probes. Save headers/limit recovery evidence and actual prompt/completion token counts.
3. **Must complete:** calibrate stand-in service and load penalties with those real observations, then rerun all 5 scenarios and 3 retrieval settings using real full-paper passages.
4. **Must complete:** manually assess at least 15 QA responses, including plausible but unsupported questions, and update report tables from the final CSV.
5. **Must complete:** export your actual conversation history and *personally* review choices/overrides. The assignment asks for your honest choices, not AI-fabricated attribution.

Do not report the prototype's benchmark figures as validated real Groq performance.
