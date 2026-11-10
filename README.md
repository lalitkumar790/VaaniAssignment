# The Relay — Vaani ML Engineering Intern

This repository is for a version-locked, citation-first research-paper QA and load-shedding assignment. The implementation is in Python with a Groq streaming adapter, a deterministic streaming stand-in, and instrumented benchmark scenarios.

**Evidence status:** Local stand-in evaluation only. The user's Groq API key was not available to this execution environment, so real Groq limits, latency, quota headers, and calibration were **not measured**. No fabricated real measurements should be reported. The offline fixture consists of 19 paraphrased notes checked against the specified pages, not full-paper retrieval. The full-paper workflow is built to download and index these exact PDFs:

- https://arxiv.org/pdf/1706.03762v7
- https://arxiv.org/pdf/2410.00037v1
- https://arxiv.org/pdf/2507.07955v2

**Local verification:** 6 unit tests passed; 144 stand-in request records produced across 5 load shapes, 3 retrieval settings, and a controlled retry comparison. Each retrieval setting correctly answered and cited 15 of 18 prewritten questions and correctly refused the other 3, in the limited fixture.

**Important:** This is a tested local prototype, not a fully compliant final submission until real hosted-model probes and full-PDF evaluation are completed with the applicant's own account. The accompanying downloadable submission archive in the chat contains the working source, raw results, and an exactly two-page PDF report. Keep keys outside Git.
