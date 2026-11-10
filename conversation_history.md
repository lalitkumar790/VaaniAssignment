# AI-assistance history and provenance

This is a **faithful extract of the accessible user instruction and execution decisions**, not a cleaned-up claim of a complete ChatGPT conversation export. The platform did not supply a full message export or assistant-side private tool logs suitable for including as a raw transcript. All subsequent bullets below are descriptions of actual work, not invented user prompts.

## Original user prompt (verbatim)

> ML Engineering Intern role at Vaani. Your assignment is attached as a PDF. complete it and give me final results do everything [https://github.com/lalitkumar790/VaaniAssignment.git](https://github.com/lalitkumar790/VaaniAssignment.git) here

**Attachment:** `The_Relay_Assignment_Brief.pdf` (four pages). The original assignment PDF was available and read. Its instructions became the working specification.

## Assistant updates actually given in the chat

> I’ll use the PDF as the specification, inspect your GitHub repository, then build and test the pipeline, load simulator, retrieval evaluation, and submission report. I’ll also separate real Groq measurements from simulated results—those can’t be presented as interchangeable.

> The brief requires five load scenarios, three retrieval settings, a 15+ question quality check, raw per-request data, and a two-page report with a fixed section order. The repository is empty and writable through your GitHub connection. I’ve verified the three exact arXiv versions. There’s no Groq API key available in this session, so I can test the stand-in but must leave actual Groq measurements unverified rather than inventing them.

> The local tests exposed a retry bug: a request could recover successfully but still be recorded as an error. I fixed it and reran the tests. The current artifacts include 144 stand-in request records and a two-page report generated from the CSV. The main remaining gaps are actual Groq measurements and full-PDF evaluation; neither is represented as completed.

## Observable execution log (chronological, selected commands)

1. Read the four-page brief; inspected the tables and the requirement to record every request.
2. Used the GitHub connection to verify that `lalitkumar790/VaaniAssignment` exists, is empty, and allows writing.
3. Examined Groq's current limit documentation and the three version-specific arXiv PDF resources.
4. Verified `GROQ_API_KEY` was not set; tested that direct arXiv/GitHub downloads were DNS-blocked in the local container.
5. Built `relay.py`, `data/verified_notes.json`, `data/questions.json`, and `tests/test_relay.py`.
6. Executed `python -m pytest -q` and obtained 6 passing tests.
7. Executed `python relay.py quality --demo` and `python relay.py load --demo` and inspected CSV and traces.
8. Found a false in-scope answer to an out-of-scope question about an office chair. Tightened evidence overlap filtering and reran all three retrieval settings.
9. Tested a failure-then-retry case. Found that successful retry left the status at `error`; fixed state reset and retested.
10. Ran `python relay.py retry-case --demo`, generated CSV and traces, and rebuilt the report from raw observations.
11. Generated a two-page PDF from the live measurements and verified its page count.

## Three governing instructions and how they changed the implementation

1. **The direct user prompt:** complete the assignment in the supplied repository. It triggered a runnable, reviewable artifact rather than an outline.
2. **The PDF's evidence and versioning instruction:** fetch exactly three arXiv revisions and refuse unsupported facts. It triggered version locks, page-level citations, citation guard, and explicit demo/full corpus distinction.
3. **The PDF's measurement and reporting instruction:** one CSV row per request and three required tables. It triggered raw timing traces, load scenarios, exactly two report pages, and automated table calculation.

## One assistant mistake caught

In the initial retry implementation the `status` variable stayed `error` after an attempted recovery. The forced 503 comparison produced a successfully streamed response still recorded as a failure. On inspection, the success branch did not reset the status. The fix explicitly sets `status = "ok"` after the stream succeeds. The tests and retry trial were rerun.

## One design choice that overruled a tempting shortcut

The assignment expects real Groq latency, observed rate-limit headers, and stand-in calibration. The user did not supply a Groq key, and network egress was blocked. **No fabricated measurement, fake header, or made-up calibration** is included. Real rows and exact organization limits are reported as *not measured*. An applicant should run the real tests themselves before submission.

## Attribution boundary

This implementation and drafted report were generated with the assistant. The user's individual engineering decisions, genuine objections, and independent review have **not** been supplied. They should not be fabricated. Before submitting, the candidate must independently validate the system, document any personal choices, and attach a complete ChatGPT export if available.
