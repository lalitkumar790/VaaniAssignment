# The Relay — Vaani ML Engineering Intern assignment: versioned results
**Source of truth:** [V1 Groq run](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42866165930) · [V3 corrected Groq run](https://github.com/lalitkumar790/VaaniAssignment/actions/runs/42870960714). All statistics below recomputed from [results.csv](results.csv) (447 individual request records). [Hosted dashboard](https://vaani-relay.vercel.app) is publicly accessible without Vercel sign-in.

## 1 What I built and why
Python five-stage classify → real version-pinned PDF search → plan/admit → streamed response → verify citation or refuse. Architectural choice: do not send a guessed answer to improve latency. Includes tools, branching, retries, simulated 429/503/slowdown and token-streaming.

## 2 The real service and my stand-in
**V1:** 17 actual Groq requests, 16 successes and one HTTP429 at the token-per-minute limit (Retry-After 5 s). **V2:** 18 HTTP401 authentication failures caused by a literal escape character in the GitHub Actions secret expression; these are invalid as a hosted-model latency baseline. **V3:** 18 real paced Groq requests, all HTTP200, `openai/gpt-oss-20b`; low reasoning effort made content visible within the response budget. Calibrated stand-in uses V1 content-TTFT median and observed TPM/RPD, but queuing and in-flight concurrency remain unmeasured assumptions.

### Table 1 — Limits
| Limit | Value found | How found | Confidence |
|---|---|---|---|
| Requests/min | 30 (documentation, **not directly measured**) | Published free-model guide | medium |
| Tokens/min | 8,000 | Groq `x-ratelimit-limit-tokens` on V1 HTTP200/429 | high |
| Requests/day | 1,000 | Groq `x-ratelimit-limit-requests` on V1; this is **RPD not RPM** | high |
| Tokens/day | 200,000 (documentation; not measured) | Groq published limits | medium |
| Requests simultaneously in flight | not measured | All real calls serial | low |
| Response on limit | HTTP429 and `retry-after: 5` | V1 last request | high |
| Recovery time | not measured | Retry-After observed, actual recovery not tested | low |

## 3 Results
**Time to first token (TTFT)** is first observed model-content delta, not necessarily time to a fully verified user-facing citation. If no token was emitted, TTFT is not measured; this means conditional TTFT p50 may exceed all-outcome total p50. Asterisks on price indicate counterfactual list pricing, **not** a free-tier charge.

### Table 2a — Latency
| Scenario | Real or stand-in | Requests | Duration (s) | Offered/min | First token p50/p95/p99 (ms) | Total p50/p95/p99 (ms) |
|---|---|---:|---:|---:|---|---|
| Real Groq V3 | real | 18 | 91.50 | 11.8 | 322.9/454.7/496.4 | 348.5/475.5/528.3 |
| Steady | stand-in | 12 | 3.85 | 186.8 | 1079.9/1270.5/1347.5 | 953.5/1304.4/1394.4 |
| Burst | stand-in | 22 | 0.73 | 1797.5 | 270.2/677.5/694.9 | 250.9/649.7/716.5 |
| Sustained overload | stand-in | 28 | 1.94 | 867.5 | 614.1/1287.7/1351.7 | 251.1/1149.1/1362.8 |
| RPM halved | stand-in | 16 | 2.02 | 475.2 | 698.9/1303.9/1322.6 | 251.5/1321.2/1373.7 |
| Daily exhausted | stand-in | 10 | 0.54 | 1106.2 | not measured/not measured/not measured | 0.4/0.5/0.5 |

### Table 2b — Outcomes
| Scenario | Succeeded | Rate-limited | Timed out or error | Retries/request | Peak queue | Tokens/answer | USD/1,000* |
|---|---:|---:|---:|---:|---:|---:|---:|
| Real Groq V3 | 100.0% | 0.0% | 0.0% | 0.00 | 0 | 530.1 | 0.052* |
| Steady | 83.3% | 0.0% | 16.7% | 0.00 | 0 | 96.9 | 0.000* |
| Burst | 27.3% | 0.0% | 72.7% | 0.00 | 13 | 18.9 | 0.000* |
| Sustained overload | 32.1% | 0.0% | 67.9% | 0.00 | 4 | 29.5 | 0.000* |
| RPM halved | 43.8% | 0.0% | 56.3% | 0.00 | 1 | 45.9 | 0.000* |
| Daily exhausted | 0.0% | 100.0% | 0.0% | 0.00 | 0 | 0.0 | 0.000* |

### Table 3 — Full-PDF retrieval settings (stand-in, 18 authored questions per setting)
| Setting | Questions | Correct + cited | Wrong | Correctly refused | Token proxy/answer | TTFT p50/p95 ms | Total p50/p95 ms |
|---|---:|---:|---:|---:|---:|---|---|
| 220 chars / top-1 / no rerank | 18 | 33.3% | 55.6% | 0.0% | 104.6 | 106.8/163.4 | 266.4/359.6 |
| 500 chars / top-3 / lexical rerank | 18 | 33.3% | 61.1% | 0.0% | 379.1 | 113.9/159.9 | 307.5/396.9 |
| 1000 chars / top-6 / lexical rerank | 18 | 33.3% | 61.1% | 0.0% | 1394.9 | 109.8/153.4 | 288.5/415.8 |

**Quality boundary:** The full-PDF deterministic stand-in strict grades were 18/54 correct, 32/54 wrong and 4/54 wrongly refused. V3 hosted Groq strict oracle graded 6/18 correct, 7 wrong, 2 wrongly refused and 3 correctly refused. A provisional **AI-assisted semantic review**, accounting for valid paraphrases and math notation, found 12/18 correctly answered/cited, 3/18 correct refusals, 2/18 wrongful refusals and 1/18 wrong. That audit is **not independently verified**: manual comparison with exact PDFs is required prior to submission.

## 4 Where the time goes
V3 slow request `real-002` measured total 541.5 ms, first content at 506.9 ms. Local classify/retrieve/plan ~8.1 ms, dispatch through server acceptance ~446.6 ms, acceptance to content ~52.1 ms, after-content streaming and verification ~34.6 ms, retries 0. The HTTP acceptance interval includes network, server processing and possibly provider queuing; not a measured provider-queue-only delay.

## 5 When a limit is hit
At TPM, downsize retrieval, bound queueing, and honor Retry-After only if the request deadline allows. At RPD exhaustion stop Groq calls and explicitly state capacity failure. Do not turn off citation safeguards or silently generate a weaker answer to improve completion rate.

## Retrieval: quality versus cost
Tested 220-character top-1 without rerank, 500-character top-3 lexical rerank, 1,000-character top-6 lexical rerank. All scored 6/18 on the strict full-PDF stand-in test; cost rose substantially with context. Choose **balanced** by evidence budget, but quality remains too low for an unattended trusted agent. Under near-quota conditions use smaller K or refuse rather than pretending evidence exists.

## How this library will mislead a naive retriever
Transformer vs Moshi/H-Net share “attention heads”; Moshi's 640 ms delay-related material can be confused with the paper's 160 ms theoretical latency; extracted PDF equations can break math notation (e.g. 1/√dₖ). Page-level citations and paper-aware lexical routing are necessary but insufficient.

## 6 Retries
Retry only a transient pre-stream failure and only within a deadline. A controlled 503 retry recovered an answer but increased latency. The V1 429 returned 5 seconds Retry-After, so immediate retry would worsen user wait without solving capacity.

## 7 What the person sees
At 3pm when RPD is gone: “I can’t provide a verified answer right now because today’s hosted-model quota has been exhausted. Please try after it resets.” No uncited fallback.

## 8 What I'm unsure about, what I left out, what I learned
Least-certain assumption: stand-in concurrency slowdown, because Groq was tested serially. If wrong, p95 overload estimates will fail. Deliberately omitted production authentication/multi-tenant backend and embedding-based reranker. Key lesson: day quota can remain high even while minute tokens reject a request, and HTTP200 does not imply a correct cited answer.

## Your feedback on Vaani
The distinction between call dispatch and completion in Vaani's developer flow stood out. Latency definitions (interrupt vs full response) were hard to compare. A consistent glossary with p50/p95 and test conditions would improve clarity. This drafted feedback should be reviewed as the applicant's own opinion.

## How I worked with the assistant
The implementation, experiments, dashboard and report were AI-assisted. The applicant supplied the assignment and initiated the Groq run. The assistant's early fixture-based quality claim was disproven by full-PDF testing; a later V2 workflow bug escaped a literal backslash into the API-key expression (all 401s), caught by inspecting response headers and fixed before V3. The applicant must supply the **unmodified complete conversation history** and review or correct the AI-authored reflection to distinguish their own engineering decisions; the existing repository excerpt is not a full transcript.

Further evidence: `artifacts/v3_real_results.csv`, `artifacts/v3_real_traces.json`, `artifacts/v3_fullpdf_quality_results.csv`, version-pinned `data/papers/manifest.json`. No secret values are stored in the repository.
