# The Relay — final evidence summary (11 November 2026)

**Authoritative submission:** [Exactly two-page report (PDF)](REPORT.pdf) · [519-row results.csv](results.csv) · [Source code](relay.py) · [Public presentation](https://vaani-relay.vercel.app). This Markdown is an accessible **evidence companion**; submit the two-page PDF as the main write-up.

## 1 What I built and why

Five Python stages: classify, retrieve passages from exact-version PDFs, scope/admit, stream through Groq or a controlled stand-in, and verify citations/refuse. The central choice was **evidence over throughput**: an unsupported claim is refused even when that harms completion rate.

## 2 The real service and my stand-in

The hosted model is Groq `openai/gpt-oss-20b`. V1 measured 16 successes and one HTTP429, V2 had 18 invalid HTTP401 authentication responses, and V3 recorded 18 hosted HTTP200 responses. V5 recorded 18 pipeline questions but only **16 hosted HTTP200 responses**; two questions were refused locally without an API call. The V4 study remains a separately measured prior run. Simulations reproduce streaming, 503, quota rejection, burst queues and slow tails; their concurrency effects have **not been validated on Groq**.

| Limit | Value found | How found | Confidence |
|---|---|---|---|
| Requests/minute | 30 (documentation, not directly measured) | Groq free-model documentation | Medium |
| Tokens/minute | 8,000 | Groq provider response headers | High |
| Requests/day | 1,000 | Groq provider response headers | High |
| Tokens/day | 200,000 (documentation, not directly measured) | Groq published limit | Medium |
| Requests in flight | Not measured | Hosted probes were serial | Low |
| Limit response | HTTP429, Retry-After 5 s | V1 last call | High |
| Actual recovery | Not measured | Retry-After is not proof of recovery | Low |

## 3 Results

The final [two-page PDF](REPORT.pdf) contains all three required results tables, computed from the merged [results.csv](results.csv). Times in milliseconds; p50/p95/p99 are computed from actual rows. First-token time is internal first generated text, not time to deliver a validated user-facing answer; rejected requests can lack TTFT entirely.

| Scenario | Source | N | TTFT p50/p95/p99 | Total p50/p95/p99 | Success | Rate-limited | Timeout/error |
|---|---|---:|---|---|---:|---:|---:|
| Real Groq V5 (actual HTTP calls) | Real | 16 | 390.7/768.8/925.5 | 441.0/849.8/973.0 | 100.0% | 0.0% | 0.0% |
| Steady | Stand-in | 12 | 1079.9/1270.5/1347.5 | 953.5/1304.4/1394.4 | 83.3% | 0.0% | 16.7% |
| Burst | Stand-in | 22 | 270.2/677.5/694.9 | 250.9/649.7/716.5 | 27.3% | 0.0% | 72.7% |
| Sustained | Stand-in | 28 | 614.1/1287.7/1351.7 | 251.1/1149.1/1362.8 | 32.1% | 0.0% | 67.9% |
| RPM halved | Stand-in | 16 | 698.9/1303.9/1322.6 | 251.5/1321.2/1373.7 | 43.8% | 0.0% | 56.3% |
| Daily exhausted | Stand-in | 10 | Not measured | 0.4/0.5/0.5 | 0.0% | 100.0% | 0.0% |

**Important denominator:** first-token p50 excludes requests that never emitted a token, while total p50 includes all requests. Thus the steady TTFT p50 (1,079.9 ms) exceeds all-outcome total p50 (953.5 ms) without any individual request having total latency below its own TTFT. The interactive dashboard compares only token-emitting requests for both headline latency medians.

### Table 3 — full-PDF retrieval (stand-in)

| Setting | Questions | Correct + cited | Wrong or wrongful refusal | Correct refusal | Token proxy / answer | TTFT p50/p95 |
|---|---:|---:|---:|---:|---:|---|
| 220 chars / K=1 | 18 | 22.2% | 61.1% | 16.7% | 94.2 | 96.3/168.4 |
| 500 chars / K=3 + rerank | 18 | 33.3% | 55.6% | 11.1% | 335.9 | 106.5/178.1 |
| 1,000 chars / K=6 + rerank | 18 | 38.9% | 50.0% | 11.1% | 1,221.1 | 117.7/189.3 |

V4 automated stand-in totals: **17/54 correct+cited**, 29 wrong, 7 correctly refused, 1 wrongly refused. V5's **18 pipeline questions** had 6 literal answer-key matches, 9 labelled wrong and 3 justified refusals under the strict grader. This is **not independently verified semantic accuracy**: Unicode spacing (e.g. `160 ms` versus `160ms`), grammatical paraphrases and the paper's `3.6×` versus the key's `4x` can be mislabelled. V5 had 16 HTTP200 calls and two local refusals; `audit_evidence.py` verifies header counts and creates a per-question review file. An earlier AI-assisted semantic review of V3 considered some paraphrased answers valid, but **has not been independently human-audited**, so its score is not promoted to a proven accuracy figure.

## 4 Where the time goes

The PDF includes one real V5 slow-request trace split into retrieval/planning, provider HTTP acceptance, accepted-to-first-content and post-content work. The HTTP-acceptance interval combines network/provider computation/possibly queuing; it is **not** a separately measured upstream queue. No retries occurred in V5.

## 5 When a limit is hit

At TPM/RPM boundaries, reduce retrieval context where feasible and refuse/queue only within an explicit deadline. At RPD exhaustion, stop hosted calls and disclose it. Do not silently bypass citations or provider limits to improve success percentages.

## Retrieval: quality versus cost

More context increased token proxy materially: **94.2 → 335.9 → 1,221.1**, for strict correctness **4/18 → 6/18 → 7/18**. For this constrained assignment, balanced K=3 is a defensible latency/cost compromise, **not** evidence that every question is answerable.

## How this library will mislead a naive retriever

(1) “Attention heads” refers to multiple models; paper-aware routing is required. (2) Moshi mentions both **160 ms theoretical** and separate practical timing, alongside 640 ms latency for an incompatible delay setting. (3) H-Net's learned “chunking” differs from arbitrary retrieval chunking, and PDF extraction breaks equations and hyphenated text.

## 6 Retries

Retry once for transient **pre-stream** 503 while a deadline permits; never replay a partially streamed answer. Retrying after a true HTTP429 with five seconds Retry-After would worsen latency for a short-deadline request.

## 7 What the person sees

> Today's hosted model quota is exhausted. I can't provide a verified answer from these papers right now, and I won't guess. Please try after the quota resets.

## 8 What I'm unsure about, what I left out, what I learned

The least certain assumption is stand-in behavior under actual concurrent hosted load; all hosted Groq experiments were serial. Deliberately not built: production multi-tenant authentication/billing and semantic cross-encoder reranking. An unexpected observation was that stricter refusal logic improved unsupported-question safety but did **not** increase full-PDF exact-string accuracy; median first-token time does not measure user-visible verified answer delivery.

## Your feedback on Vaani

The previously drafted product impressions must be checked personally by the applicant against https://www.vaani.dev/ before submission. No AI-generated subjective opinion should be attributed to the applicant without confirmation.

## How I worked with the assistant

The pipeline, tests, public demo and experimental analysis were developed with substantial AI assistance. The applicant supplied the brief and repository, installed the personal Groq secret and triggered the first real-model workflow. The assistant's initial fixture-based confidence was contradicted by the full-PDF evaluations; subsequent V4/V5 comparisons kept the negative findings instead of claiming unmeasured progress. The earlier workflow's literal escaped-secret issue produced V2 HTTP401s and was corrected. The applicant must attach their authentic **complete raw conversation history** (the existing `conversation_history.md` is explicitly only a partial extract), personally confirm their own three consequential prompts, oversight and overruling decisions, and verify citations.

**Provenance:** [Initial real V1](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42866165930), [real V3](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42870960714), [V4 full-PDF](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42969980873), [real V4](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42969257016), [real V5](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42970031360), [519-row merge + two-page report](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42971254577).
