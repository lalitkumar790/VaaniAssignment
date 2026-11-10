# The Relay — completion and deployment runbook

## Current status

- [x] Version-pinned three-paper retrieval pipeline, one tool call, five stages, refusal branch, streaming Groq adapter, stand-in with failure injection, tests.
- [x] Stand-in experiments: 144 request-level CSV rows, five load scenarios, three retrieval settings, error/retry test.
- [x] Interactive static dashboard on Vercel, fed from the committed raw CSV. The Vercel project currently has Vercel Authentication enabled; this is deliberate, not a broken deployment.
- [ ] Hosted Groq results and quota evidence from the applicant's *own* account.
- [ ] Full version-locked PDF accuracy comparison with actual retrieval and model generation; the workflow now supports running the first portion.
- [ ] Calibration of stand-in parameters to actual Groq observations, then new simulated load runs.
- [ ] Regenerate the final exactly-two-page report from updated raw results; applicant's genuine feedback and complete conversation-history appendix.

## Step A — supply the hosted-model credential securely

1. Create a personal free Groq API key at https://console.groq.com/keys.
2. Open GitHub: **VaaniAssignment → Settings → Secrets and variables → Actions → New repository secret**.
3. Set the name to `GROQ_API_KEY`, paste your key *there* and save. **Never commit it or paste it into a chat/message/issue or web client**. Only the GitHub Actions runner should read it.
4. In **GitHub → Actions → Groq measurements (manual, secret-safe) → Run workflow**, choose `main`, model `openai/gpt-oss-20b` (or a model actually available on the account), and 18 max serial requests.
5. When finished, download the action artifact named `relay-measurements-...`. Share the workflow run URL with your assistant, **not** the API key.

The workflow fetches all three exact arXiv PDF versions with SHA256 provenance, runs 18 authored questions at each of three settings against the **full PDF corpus using the stand-in**, sends a modest number of **actual hosted streaming requests** and records status, latency, usage and observed rate-limit headers. It stops when it sees 429 rather than bypassing quotas. A successful pipeline does not imply that any quota was exhausted; limits without direct measurement must be documented as account/docs values with confidence labels.

Official documentation: https://console.groq.com/docs/rate-limits and https://console.groq.com/docs/models. The account's **Limits** page is authoritative for that account, rather than a generic public table.

## Step B — finish evidence

Obtain at least 18 real responses (unless the provider rate-limits first) and save `artifacts/real_results.csv`, `real_headers.json`, `real_traces.json`. Review which results are supported/cited and which are correctly refused. Calibrate stand-in jitter, service delay and rejection/backoff against real latency and 429 observations. Run steady, burst, sustained overload, RPM-halved, and RPD-exhausted synthetic load *again* with explicitly calibrated parameters; keep source labels distinct. Do not invent a per-day exhaustion experiment if actually consuming the quota is impractical.

Use exact versions:
- https://arxiv.org/pdf/1706.03762v7
- https://arxiv.org/pdf/2410.00037v1
- https://arxiv.org/pdf/2507.07955v2

Note: Python currently records model first token internally and performs citation checks at end. Actual user-visible first *verified* token may be later; disclose this measurement boundary. Provider limits should be read from observed headers and the authenticated Limits page, not inferred from the simulator.

## Step C — public demo versus private secrets

Vercel project: `vaani-relay` in `lalitsikarwar2001-6516s-projects`, Git linked to `lalitkumar790/VaaniAssignment`, production branch `main`. The static dashboard is deliberately **not** an API-key-backed public chatbot. It is a visible reproducibility/observability companion to the local research pipeline.

If external reviewers must access it without Vercel sign-in, the owner must explicitly approve changing the **production** deployment protection: **Vercel → vaani-relay → Settings → Deployment Protection → Vercel Authentication**. Do not remove protection from unrelated projects or place the Groq key in client-side JavaScript. Keep arbitrary user-generated LLM usage behind authentication and a server-side quota guard if a hosted real-model API is added later.

## Step D — applicant integrity and delivery

The brief requires at most 2 pages of main writing, exact table headings, raw results.csv, source code, and unedited AI prompts/conversation history. The candidate must personally verify the provider account's limits, the downloaded PDF citations and evaluation judgments, the website feedback, and which AI suggestions they challenged. Do not manufacture a fake history, successful live calls, cost figures, or subjective personal experience.

The original brief requests submission within four days *after receipt*. Confirm the actual receipt date before scheduling.
