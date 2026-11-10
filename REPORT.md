# The Relay — Vaani ML Engineering Intern
Local stand-in measurement, NOT a completed hosted-Groq evaluation. 10 November 2026.

## 1 What I built and why
Python 5-step query classification → page-cited BM25 passage retrieval → scope/plan → streaming draft → citation validation/refusal. Decision: fail closed on missing evidence and reject 429 within deadline rather than invent a quick answer.

## 2 The real service and my stand-in
The production adapter targets Groq streaming OpenAI-compatible chat completions. No account key was available; real endpoint behavior and calibration are **not measured**. Groq docs say limit responses use HTTP 429, retry-after, and remaining/reset headers; exact organization limits vary. Local stand-in simulates jitter, 503, 429, queueing, streaming and load-related slowdown using *chosen*, not fitted, parameters.

**Table 1 — Real-service limits (all entries unmeasured, not guessed)**
| Limit | Value found | How found | Confidence |
|---|---|---|---|
| Requests/minute | not measured | key not available; docs only | low |
| Tokens/minute | not measured | key not available; docs only | low |
| Requests/day | not measured | key not available; docs only | low |
| Tokens/day | not measured | key not available; docs only | low |
| Requests in flight | not measured | key not available; docs only | low |
| Actual 429 payload | not measured | key not available; docs only | low |
| Recovery time | not measured | key not available; docs only | low |

## 3 Results
All load observations are local stand-in; timings are measured wall-clock. TTFT p50/p95/p99 is **internal first model token**, conditional on emitting one; the user receives only citation-verified output. NM means none emitted.

**Table 2a — Latency**
| Scenario | Source | N | Duration s | Offered/min | TTFT p50/p95/p99 ms | Total p50/p95/p99 ms |
|---|---|---:|---:|---:|---|---|
| steady | stand-in | 12 | 3.38 | 212.8 | 189.9/825.7/826.2 | 305.9/961.9/962.1 |
| burst | stand-in | 22 | 0.42 | 3150.4 | 66.6/289.2/329.6 | 234.5/247.6/382.5 |
| sustained_overload | stand-in | 28 | 0.95 | 1776.2 | 137.0/400.0/440.6 | 0.5/420.2/500.9 |
| rpm_halved | stand-in | 16 | 1.05 | 912.9 | 202.8/365.5/404.2 | 0.6/424.5/525.4 |
| daily_exhausted | stand-in | 10 | 0.54 | 1107.8 | NM/NM/NM | 0.5/0.8/0.9 |

**Table 2b — Outcomes**
| Scenario | Success | 429 | Timeout/error | Retry/request | Peak queue | Tokens/answer | API $/1k |
|---|---:|---:|---:|---:|---:|---:|---:|
| steady | 100.0% | 0.0% | 0.0% | 0.00 | 0 | 119.6 | 0.00 |
| burst | 27.3% | 31.8% | 40.9% | 0.00 | 8 | 19.5 | 0.00 |
| sustained_overload | 32.1% | 53.6% | 14.3% | 0.00 | 4 | 27.4 | 0.00 |
| rpm_halved | 43.8% | 56.2% | 0.0% | 0.00 | 0 | 48.6 | 0.00 |
| daily_exhausted | 0.0% | 100.0% | 0.0% | 0.00 | 0 | 0.0 | 0.00 |

**Table 3 — Retrieval (18 authored questions per setting)**
| Setting | Questions | Correct+cited | Wrong | Correct refusal | Tokens/answer | TTFT p50/p95 ms | Total p50/p95 ms |
|---|---:|---:|---:|---:|---:|---|---|
| 220 chars / 1 / no rerank | 18 | 83.3% | 0.0% | 16.7% | 64.1 | 69.8/133.4 | 164.5/231.6 |
| 500 chars / 3 / lexical rerank | 18 | 83.3% | 0.0% | 16.7% | 103.1 | 69.9/133.5 | 165.1/231.7 |
| 1000 chars / 6 / lexical rerank | 18 | 83.3% | 0.0% | 16.7% | 142.1 | 70.0/133.7 | 165.3/232.0 |

## 4 Where the time goes
Slowest successful local load request `steady-011` took 962.16 ms, first token at 826.36 ms. Instrumented queue wait 0.0 ms; model/pipeline work after admission through first token 825.9 ms; after first token through verification 135.8 ms; retry 0 ms. Raw event stamps in `artifacts/traces.json`.

## 5 When a limit is hit
Per-minute: admission denies excess quickly with 429-labelled outcome instead of queueing beyond short deadline. Per-day: stop new hosted calls and serve a clear service-unavailable message; local out-of-scope refusals may bypass the model. Prioritize admitted requests and cite/refuse honestly; no silent low-quality model fallback.

## Retrieval: quality versus cost
Across 18 small, curated fixture questions per setting the measured accuracy was equal. Choose 220/1 for lowest input-token proxy cost on this small fixture; do **not** generalize to full PDFs, where a wider context could recover answers spanning multiple paragraphs. Under budget pressure shrink top-k, not citation guard.

## How this library will mislead a naive retriever
(1) “attention” occurs in many places: “Which model is meant for live spoken dialogue?” can pull the Transformer paper. (2) Moshi contains both 160 ms theoretical and 200 ms practical latency: “What is observed latency?” may return the wrong figure. (3) Chunking in H-Net is learned segmentation while our retrieval chunking is arbitrary text windows: “How are chunks learned?” can conflate the two.

## 6 Retries
One retry only for pre-token transient 503, short exponential backoff; never retry a partly-streamed answer, and do not wait past an explicit minute/day reset. Controlled example: no retry failed at 110.85 ms; retry succeeded but took 595.65 ms, a longer wait; on burst traffic the extra attempt also consumes quota.

## 7 What the person sees
“I can’t answer from the three papers right now because today’s model-call budget is exhausted. I won’t guess or generate an uncited reply. Please return after the quota resets.”

## 8 What I’m unsure about, what I left out, what I learned
Least certain: lexical retrieval on a 19-note paraphrase fixture predicts full-paper performance; it may fail badly. Deliberate omissions: semantic reranker and distributed queue. Learned: TTFT conditional on success can look good even as most requests are refused; measure success coverage too.

## Your feedback on Vaani
The Teacher AI prompt-diff review and conversation-memory design stood out. The site’s P90 ~450 ms claim does not clearly say which stage is timed, and animated counters are harder to verify in text-only view. I would publish a transparent latency measurement definition and a language-filterable live-call demo.

## How I worked with the assistant
Full accessible request and working notes are in `conversation_history.md`; no cleaned-up or invented exchanges. Three influential instructions: (1) the user requested end-to-end delivery in a named repo, (2) the brief required the exact arXiv versions and cite-or-refuse behavior, (3) the brief required recomputable per-request tables. The assistant initially left `status=error` after a successful retry; the controlled failure-injection test exposed it and it was fixed. A deliberate override was to reject fabricated Groq benchmarks. These are assistant-implemented choices; the applicant must personally review, rerun with their own Groq key, and describe their own decisions before submission.

All numbers are from `results.csv`; stand-in token figures are rough proxies, not Groq billing usage.
