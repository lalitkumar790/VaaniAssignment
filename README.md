# The Relay — Vaani ML Engineering Intern assignment

> **Web demo:** https://vaani-relay.vercel.app — deployed on Vercel. Currently protected by the owner's Vercel Authentication setting; external access needs explicit owner approval. The site uses local stand-in CSV and paraphrased evidence notes only, **not a live Groq-backed chatbot**. For real free-tier measurements, see [OPERATIONS.md](OPERATIONS.md) and the manual **Groq measurements** GitHub Actions workflow. Do not share an API key in the repository or chat.


A research-paper QA pipeline with an explicit **citation-or-refuse** policy, configurable retrieval, a Groq streaming adapter, a failure-injecting stand-in, and per-request latency/load instrumentation.

> **Verified 10 November 2026:** Exact arXiv PDFs downloaded, 18 real Groq V3 calls succeeded, and the earlier first run measured 16 successful requests followed by one HTTP429. Calibrated stand-in traffic scenarios are available. **Accuracy is still limited:** automated full-PDF stand-in oracle 18/54 correct, and assistant-reviewed live-model quality 12/18 correct plus 3 justified refusals (not independently human-audited). Never equate HTTP200 with a correct answer.

**Interactive research dashboard:** https://vaani-relay.vercel.app (deployment ready; currently requires owner Vercel login). **Detailed tables:** [REPORT.md](REPORT.md); **answer audit:** [QUALITY_AUDIT.md](QUALITY_AUDIT.md); **exact raw measurements:** [results.csv](results.csv) (447 request records). **Real-provider evidence:** [V1](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42866165930), [V3](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42870960714). **V2** contained an escaped secret expression and its 18 HTTP401 errors are preserved but not treated as valid latency results.


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
python relay.py real-probe --count 8 --gap 5
# Saves artifacts/real_results.csv, real_traces.json and real_headers.json
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


## Submission integrity

- Main report must fit **two pages**. The full [REPORT.md](REPORT.md) is evidence backing, not the two-page deliverable. The latest two-page PDF is provided with the submission archive; an earlier `REPORT.pdf` checked into GitHub may be from the preliminary run, so do not submit an old copy without checking its date and numbers.
- An assistant-created question bank is not automatically "questions you wrote yourself". Applicant should review/rewrite the 18 questions, validate the 3 exact PDF citations, and defend the grade criteria.
- The existing `conversation_history.md` is an excerpt, **not a verbatim complete export**. Attach the unedited actual conversation to meet the assignment's disclosure requirement.
- The Vercel demo is a static evidence viewer with curated notes, not a public Groq agent; do not expose your API key in the client.
- The hosted Groq key belongs only in GitHub Actions secret `GROQ_API_KEY`, never source files or chat messages.
