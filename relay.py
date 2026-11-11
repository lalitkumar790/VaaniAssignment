"""The Relay: version-locked, cited, load-aware three-paper research assistant.

`--demo` explicitly uses a small set of paraphrased, page-checked teaching notes;
without it, the pipeline requires the EXACT three PDF versions from `fetch`.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import time
import urllib.request
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAPERS = {
    "1706.03762v7": "Attention Is All You Need",
    "2410.00037v1": "Moshi: a speech-text foundation model for real-time dialogue",
    "2507.07955v2": "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling",
}
FIELDS = ["request_id", "scenario", "source", "start_time", "first_token_ms", "total_ms", "status", "retries", "tokens_in", "tokens_out", "retrieval_setting", "answer_grade", "queue_peak_observed", "cost_usd"]
SETTINGS = {
    "small": (220, 1, False),
    "balanced": (500, 3, True),
    "wide": (1000, 6, True),
}
UNSUPPORTED = "I can't verify that from the three specified papers, so I won't guess."
STOP = set("what how why when which where who is are was were does do did the a an in on for to of from and or by with as paper model authors they it this that about many much their explain according".split())


def words(text):
    return [w for w in re.findall(r"[a-z0-9]+(?:\.[0-9]+)*", text.lower()) if w not in STOP]


def count_tokens(text):
    """Proxy, NOT Groq billed token count; actual calls use provider usage if supplied."""
    return max(1, math.ceil(len(text) / 4))


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def percentile(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    pos = (len(xs)-1) * p / 100
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(xs[lo] + (xs[hi]-xs[lo])*(pos-lo), 1)


@dataclass
class Passage:
    paper: str
    page: int
    text: str
    note: str = "PDF"

    @property
    def citation(self):
        return f"[{self.paper} p.{self.page}]"


class Corpus:
    def __init__(self, passages):
        self.passages = passages

    @classmethod
    def load(cls, demo=False):
        if demo:
            data = json.loads((ROOT / "data" / "verified_notes.json").read_text(encoding="utf-8"))
            return cls([Passage(**p) for p in data])
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("Install requirements.txt for PyMuPDF; or use --demo") from exc
        passages = []
        for paper in PAPERS:
            path = ROOT / "data" / "papers" / f"{paper}.pdf"
            if not path.exists():
                raise FileNotFoundError(f"Missing {path}. Run `python relay.py fetch` (requires network). Or explicitly use --demo.")
            with fitz.open(path) as doc:
                for idx, page in enumerate(doc):
                    text = page.get_text("text", sort=True)
                    from retrieval_optimized import normalize
                    text = normalize(text)
                    if text:
                        passages.append(Passage(paper, idx + 1, text))
        return cls(passages)

    def retrieve(self, question, setting="balanced"):
        """Cached version-aware retrieval, comparing a distinct optimized revision."""
        from retrieval_optimized import IndexedRetriever
        if not hasattr(self, "_retriever"):
            self._retriever = IndexedRetriever(self.passages, Passage)
        return self._retriever.retrieve(question, setting, SETTINGS[setting])


def fetch_papers():
    """Runtime downloads only the pinned arXiv versions, validates bytes, writes SHA256 provenance."""
    target = ROOT / "data" / "papers"
    target.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for paper, title in PAPERS.items():
        url = f"https://arxiv.org/pdf/{paper}"
        req = urllib.request.Request(url, headers={"User-Agent": "RelayAcademicEvaluation/1.0 contact: local-demo"})
        with urllib.request.urlopen(req, timeout=45) as response:
            blob = response.read(20_000_000)
        if not blob.startswith(b"%PDF-") or len(blob) < 20000:
            raise RuntimeError(f"Invalid PDF for {paper}; not writing")
        path = target / f"{paper}.pdf"
        path.write_bytes(blob)
        manifest[paper] = {"title": title, "url": url, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


class Limited(Exception):
    def __init__(self, reason, retry_after=0):
        super().__init__(reason)
        self.reason = reason
        self.retry_after = retry_after


class TimedOut(Exception):
    pass


class Budget:
    def __init__(self, rpm=20, tpm=16000, rpd=200, max_parallel=3, queue_timeout=0.24):
        self.rpm, self.tpm, self.rpd = rpm, tpm, rpd
        self.minute = deque()
        self.day_calls = 0
        self.tokens = 0
        self.max_parallel = max_parallel
        self.sema = asyncio.Semaphore(max_parallel)
        self.lock = asyncio.Lock()
        self.queue_timeout = queue_timeout
        self.waiters = 0
        self.peak_queue = 0

    async def admit(self, estimated_tokens):
        """Refund a quota reservation if a request never passes the local queue."""
        async with self.lock:
            now = time.monotonic()
            while self.minute and now-self.minute[0][0]>=60:
                _, prior = self.minute.popleft()
                self.tokens -= prior
            if self.day_calls>=self.rpd:
                raise Limited("daily",86400)
            if len(self.minute)>=self.rpm or self.tokens+estimated_tokens>self.tpm:
                raise Limited("minute",max(0,60-(now-self.minute[0][0])) if self.minute else 60)
            reservation=(now,estimated_tokens)
            self.minute.append(reservation)
            self.day_calls+=1
            self.tokens+=estimated_tokens
        self.waiters+=1
        self.peak_queue=max(self.peak_queue,max(0,self.waiters-self.max_parallel))
        try:
            await asyncio.wait_for(self.sema.acquire(),timeout=self.queue_timeout)
        except (asyncio.TimeoutError,asyncio.CancelledError) as exc:
            async with self.lock:
                try:
                    self.minute.remove(reservation)
                except ValueError:
                    pass
                else:
                    self.tokens=max(0,self.tokens-estimated_tokens)
                self.day_calls=max(0,self.day_calls-1)
            if isinstance(exc,asyncio.CancelledError):
                raise
            raise TimedOut("simulator queue deadline") from exc
        finally:
            self.waiters-=1

    def release(self):
        self.sema.release()


class StandIn:
    """Uncalibrated baseline, never represented as measured Groq behavior."""
    source = "stand-in"

    def __init__(self, budget=None, seed=11, base_ms=70, chunk_ms=6, slow_probability=0.08, failure_probability=0.02, fail_first=False):
        self.budget = budget or Budget()
        self.rand = random.Random(seed)
        self.base_ms = base_ms
        self.chunk_ms = chunk_ms
        self.slow_probability = slow_probability
        self.failure_probability = failure_probability
        self.fail_first = fail_first
        self._calls = 0

    async def stream(self, question, evidence, callback, observe=None):
        observe = observe or (lambda event: None)
        prompt = " ".join(p.text for p in evidence)
        predicted = count_tokens(question) + count_tokens(prompt) + 100
        observe("queue_enter")
        await self.budget.admit(predicted)
        observe("queue_leave")
        try:
            jitter = self.rand.lognormvariate(0, 0.32)
            penalty = (1 + .5*max(0, self.budget.max_parallel - self.budget.sema._value - 1))
            if self.rand.random() < self.slow_probability:
                jitter *= 5
            await asyncio.sleep(self.base_ms*jitter*penalty/1000)
            self._calls += 1
            if (self.fail_first and self._calls == 1) or self.rand.random() < self.failure_probability:
                raise RuntimeError("simulated upstream 503")
            observe("prefill_done")
            response = extractive_answer(question, evidence)
            for part in re.findall(r"\S+\s*", response):
                await asyncio.sleep(self.chunk_ms/1000)
                await callback(part)
            return count_tokens(prompt) + count_tokens(question), count_tokens(response)
        finally:
            self.budget.release()


class Groq:
    """Real hosted Groq streaming API; never stores or prints the key."""
    source = "real"

    def __init__(self, model=None):
        self.key = os.getenv("GROQ_API_KEY")
        if not self.key:
            raise RuntimeError("GROQ_API_KEY is not set. Real requests cannot be measured.")
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.header_observations = []

    async def stream(self, question, evidence, callback, observe=None):
        observe = observe or (lambda event: None)
        observe("queue_enter")
        import httpx
        evidence_text = "\n".join(f"{p.citation} {p.text}" for p in evidence)
        instructions = (
            "You answer only from quoted passages of three exact-version research papers. "
            "Identify the precise attribute requested (model variant, dataset, date, theoretical versus practical). "
            "Prefer explicit numerical facts over incidental table captions and dialogue transcripts. "
            "Keep mathematical inverses, divisions and denominators precise: 1/sqrt(d) is not sqrt(d). "
            "Distinguish approximations from exact quantities. Never rely on outside knowledge. "
            "Write one concise supported sentence ending with exactly one source citation copied verbatim, "
            "for example [1706.03762v7 p.4]. No Markdown, speculation or uncited claims. "
            "If the evidence cannot directly resolve the request, respond exactly: "
            + UNSUPPORTED + "\n\n" + evidence_text
        )
        payload = {"model": self.model, "stream": True, "temperature": 0, "max_completion_tokens": 400,
                   "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": question}],
                   "stream_options": {"include_usage": True}}
        if self.model.startswith("openai/gpt-oss-"):
            payload.update(reasoning_effort="low", include_reasoning=False)
        tokens_in, tokens_out = 0, 0
        async with httpx.AsyncClient(timeout=httpx.Timeout(25, connect=6)) as client:
            async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", json=payload,
                                     headers={"Authorization": "Bearer " + self.key}) as response:
                names = ("retry-after", "x-ratelimit-limit-requests", "x-ratelimit-remaining-requests",
                         "x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens",
                         "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens")
                self.header_observations.append({"at": utc(), "http_status": response.status_code,
                                                 "headers": {n: response.headers[n] for n in names if n in response.headers}})
                if response.status_code == 429:
                    raise Limited("groq_429", float(response.headers.get("retry-after", "0") or 0))
                response.raise_for_status()
                observe("queue_leave")  # HTTP accepted; remote queuing cannot be isolated
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    event = json.loads(line[6:])
                    if event.get("usage"):
                        tokens_in = event["usage"].get("prompt_tokens", 0)
                        tokens_out = event["usage"].get("completion_tokens", 0)
                    choices = event.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta") or {}
                        chunk = delta.get("content") or ""
                        if chunk:
                            await callback(chunk)
        return tokens_in, tokens_out


def extractive_answer(question, evidence):
    """Query-aware local evidence extraction; not an LLM or answer key."""
    from retrieval_optimized import semantic_answer
    return semantic_answer(question, evidence, UNSUPPORTED)


def citation_guard(text, evidence):
    """Check citation syntax and numerical support; not full semantic entailment."""
    if text == UNSUPPORTED:
        return text
    pattern = r"\[\d{4}\.\d{5}v\d+ p\.\d+\]"
    found = re.findall(pattern, text)
    allowed = {p.citation for p in evidence}
    if not found or any(c not in allowed for c in found):
        return UNSUPPORTED
    if text.count("[") != len(found) or text.count("]") != len(found):
        return UNSUPPORTED
    claim = re.sub(pattern, "", text).strip()
    if not claim or len(claim)<4:
        return UNSUPPORTED
    def numbers(s):
        s = s.lower().replace("×","x").replace("−","-")
        return set(re.findall(r"(?<!\w)\d+(?:\.\d+)?",s))
    cited_text = " ".join(p.text for p in evidence if p.citation in found)
    if not numbers(claim).issubset(numbers(cited_text)):
        return UNSUPPORTED
    return text


async def ask(question, corpus, model, setting="balanced", scenario="single", request_id="one", retries=0, trace=None):
    """Steps: classify -> retrieve(tool) -> plan -> stream draft -> verify -> optional refuse."""
    started = time.perf_counter()
    wall_start = utc()
    first = None
    timeline = []

    def mark(stage):
        timeline.append({"stage": stage, "elapsed_ms": round(1000*(time.perf_counter()-started), 2)})

    mark("arrival")
    # Step 1: cheap local classification; avoid costly model calls for out-of-scope.
    classified = "research" if len(words(question)) else "unsupported"
    mark("classify")
    # Step 2: actual retrieval tool from the version-locked corpus.
    evidence = corpus.retrieve(question, setting) if classified == "research" else []
    mark("retrieve")
    # Step 3: local plan + relevance / admission gate.
    from retrieval_optimized import best_evidence_span
    supported = bool(evidence) and best_evidence_span(question,evidence) is not None
    mark("plan")
    output_parts = []
    tokens_in, tokens_out = 0, 0
    status, tries = "ok", 0

    async def callback(piece):
        nonlocal first
        if first is None:
            first = round(1000*(time.perf_counter()-started), 2)
            mark("first_token")
        output_parts.append(piece)

    # Local refusals do not produce a model token or spend hosted quota.
    provider_http_before = len(getattr(model, "header_observations", []))
    if not supported:
        output_parts.append(UNSUPPORTED)
        mark("local_refusal")
        tokens_out = count_tokens(UNSUPPORTED)
    else:
        for attempt in range(retries+1):
            try:
                tokens_in, tokens_out = await model.stream(question, evidence, callback, mark)
                if model.source == "real" and not output_parts:
                    mark("no_visible_model_content")
                    status = "error"
                else:
                    status = "ok"
                break
            except Limited as exc:
                mark("limit_" + exc.reason)
                status = "rate_limited"
                # A 60s or 24h retry cannot meet this request's 1s-ish deadline.
                if attempt >= retries or exc.retry_after > 0.15:
                    break
                tries += 1
                await asyncio.sleep(min(.15, exc.retry_after))
            except (TimedOut, asyncio.TimeoutError):
                mark("queue_timeout")
                status = "timeout"
                break
            except Exception:
                mark("upstream_error")
                status = "error"
                if attempt >= retries or first is not None:
                    break  # never replay a partially streamed response
                tries += 1
                await asyncio.sleep(.05*(2**attempt))
    mark("draft_end")
    draft = "".join(output_parts).strip()
    # Step 5: local evidence citation guard and refusal branch.
    answer = citation_guard(draft, evidence) if status == "ok" else (
        "The service is at its usage limit. I can't give a verified answer now." if status == "rate_limited"
        else "I couldn't verify a reply within the response deadline. Please try later.")
    if status == "ok" and answer == UNSUPPORTED and draft != UNSUPPORTED:
        mark("citation_rejected")
    mark("verify")
    total = round(1000*(time.perf_counter()-started), 2)
    http_calls = len(getattr(model, "header_observations", [])) - provider_http_before
    if trace is not None:
        trace.append({"request_id": request_id, "scenario": scenario, "timeline": timeline,
                      "answer": answer, "retrieved": [p.citation for p in evidence],
                      "provider_http_responses": http_calls,
                      "source_note": "demo paraphrased notes" if any(p.note != "PDF" for p in evidence) else "versioned PDFs"})
    record = dict(request_id=request_id, scenario=scenario, source=model.source,
                  start_time=wall_start, first_token_ms=first if first is not None else "",
                  total_ms=total, status=status, retries=tries, tokens_in=tokens_in,
                  tokens_out=tokens_out, retrieval_setting=setting, answer_grade="",
                  queue_peak_observed=0, cost_usd=0.0 if model.source == "stand-in" else "")
    return record, answer


def grade(question_spec, record, answer):
    """Small explicitly authored answer-key check; NOT blinded human review."""
    if question_spec["scope"] == "outside":
        return "refused_correctly" if answer == UNSUPPORTED else "wrong"
    if answer == UNSUPPORTED:
        return "refused_wrongly"
    match = any(term.lower() in answer.lower() for term in question_spec["accept"])
    cited_paper = f"[{question_spec['paper']} p."
    return "correct" if match and cited_paper in answer else "wrong"


async def run_quality(demo, output):
    corpus = Corpus.load(demo=demo)
    questions = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
    all_rows, traces = [], []
    for setting in SETTINGS:
        model = StandIn(budget=Budget(rpm=500, tpm=1000000, rpd=500), seed=31, failure_probability=0, slow_probability=0)
        for idx, item in enumerate(questions):
            record, answer = await ask(item["question"], corpus, model, setting, scenario="retrieval_"+setting,
                                       request_id=f"q-{setting}-{idx:02}", trace=traces)
            record["answer_grade"] = grade(item, record, answer)
            all_rows.append(record)
    write_csv(output, all_rows)
    (output.parent / "quality_answers.json").write_text(json.dumps([{"id": r["request_id"], "grade": r["answer_grade"], "answer": t["answer"]}
                                                              for r, t in zip(all_rows, traces)], indent=2), encoding="utf-8")
    print("Quality grades (automated, fixture-scoped):", dict(Counter(r["answer_grade"] for r in all_rows)))
    return all_rows


async def run_retry_case(demo, output):
    """Controlled failure-injection A/B: drop fast versus retry after upstream 503."""
    corpus = Corpus.load(demo=demo)
    question = "What is the theoretical latency of Moshi?"
    traces, rows = [], []
    for attempts in (0, 1):
        model = StandIn(budget=Budget(rpm=12, rpd=100), seed=91, base_ms=145,
                        chunk_ms=10, slow_probability=0, failure_probability=0, fail_first=True)
        rec, answer = await ask(question, corpus, model, scenario="retry_once" if attempts else "fail_fast",
                                request_id=f"retry-{attempts}", retries=attempts, trace=traces)
        rec["answer_grade"] = "correct" if "160ms" in answer else "refused_wrongly"
        rows.append(rec)
    write_csv(output, rows)
    (output.parent / "retry_traces.json").write_text(json.dumps(traces, indent=2), encoding="utf-8")
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


async def run_load(demo, output):
    corpus = Corpus.load(demo=demo)
    questions = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
    scenarios = [
        ("steady", 12, .22, 60, 100),
        ("burst", 22, 0, 12, 100),
        ("sustained_overload", 28, .035, 10, 100),
        ("rpm_halved", 16, .07, 6, 100),
        ("daily_exhausted", 10, .06, 20, 0),
    ]
    rows, traces = [], []
    for name, count, interval, rpm, rpd in scenarios:
        budget = Budget(rpm=rpm, rpd=rpd, tpm=12000, max_parallel=2, queue_timeout=.24)
        model = StandIn(budget=budget, seed=19, base_ms=82, chunk_ms=7,
                        slow_probability=.12, failure_probability=.035)
        async def send(i):
            await asyncio.sleep(interval*i)
            spec = questions[i%len(questions)]
            rec, ans = await ask(spec["question"], corpus, model,
                                 scenario=name, request_id=f"{name}-{i:03}", retries=1, trace=traces)
            rec["answer_grade"] = grade(spec, rec, ans) if rec["status"] == "ok" else "refused_wrongly"
            return rec, ans
        outcomes = await asyncio.gather(*(send(i) for i in range(count)))
        for rec, _ in outcomes:
            rec["queue_peak_observed"] = budget.peak_queue
            rows.append(rec)
        print(name, dict(Counter(rec["status"] for rec, _ in outcomes)), "peak_queue", budget.peak_queue)
    write_csv(output, rows)
    (output.parent / "traces.json").write_text(json.dumps(traces, indent=2), encoding="utf-8")
    return rows


def stats(rows):
    groups = {}
    for scenario in dict.fromkeys(r["scenario"] for r in rows):
        rr = [r for r in rows if r["scenario"] == scenario]
        durations = [float(r["total_ms"]) for r in rr]
        ft = [float(r["first_token_ms"]) for r in rr if r["first_token_ms"] != ""]
        rates = Counter(r["status"] for r in rr)
        grp = {"n": len(rr), "ttft_p50_p95_p99_ms": [percentile(ft,p) for p in (50,95,99)],
               "total_p50_p95_p99_ms": [percentile(durations,p) for p in (50,95,99)],
               "ok_pct": round(100*rates["ok"]/len(rr), 1),
               "rate_limited_pct": round(100*rates["rate_limited"]/len(rr),1),
               "timeout_or_error_pct": round(100*(rates["timeout"]+rates["error"])/len(rr),1),
               "retries_per_request": round(sum(int(r["retries"]) for r in rr)/len(rr),2),
               "tokens_per_answer": round(sum(int(r["tokens_in"])+int(r["tokens_out"]) for r in rr)/len(rr),1)}
        groups[scenario] = grp
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="Download exact original arXiv PDFs; requires internet")
    for cmd in ("ask", "load", "quality", "retry-case", "real-probe"):
        p = sub.add_parser(cmd)
        p.add_argument("--demo", action="store_true", help="Use limited, paraphrased evidence notes, not full PDFs")
        p.add_argument("--setting", choices=SETTINGS, default="balanced")
        if cmd == "ask":
            p.add_argument("question")
            p.add_argument("--real", action="store_true")
        if cmd == "real-probe":
            p.add_argument("--count", type=int, default=8)
            p.add_argument("--gap", type=float, default=1.0, help="Minimum pause between real calls, to avoid TPM spikes")
    args = parser.parse_args()
    if args.command == "fetch":
        fetch_papers()
        return
    corpus = Corpus.load(demo=args.demo)
    if args.command == "ask":
        model = Groq() if args.real else StandIn(failure_probability=0)
        record, answer = asyncio.run(ask(args.question, corpus, model, args.setting))
        print(answer)
        print(json.dumps(record, indent=2))
    elif args.command == "load":
        path = ROOT / "artifacts" / "load_results.csv"
        rows = asyncio.run(run_load(args.demo, path))
        print(json.dumps(stats(rows), indent=2))
    elif args.command == "quality":
        path = ROOT / "artifacts" / "quality_results.csv"
        rows = asyncio.run(run_quality(args.demo, path))
        print(json.dumps(stats(rows), indent=2))
    elif args.command == "retry-case":
        rows = asyncio.run(run_retry_case(args.demo, ROOT / "artifacts" / "retry_results.csv"))
        print(json.dumps(stats(rows), indent=2))
    elif args.command == "real-probe":
        model = Groq()
        questions = json.loads((ROOT / "data" / "questions.json").read_text(encoding="utf-8"))
        async def probe():
            rows, trace = [], []
            # serial, modest calls; no brute forcing rate limits
            for i in range(args.count):
                record, answer = await ask(questions[i%len(questions)]["question"], corpus, model,
                                           args.setting, "real_modest", f"real-{i:03}", trace=trace)
                record["answer_grade"] = grade(questions[i%len(questions)], record, answer) if record["status"] == "ok" else "refused_wrongly"
                rows.append(record)
                if record["status"] == "rate_limited":
                    break
                await asyncio.sleep(args.gap)
            write_csv(ROOT / "artifacts" / "real_results.csv", rows)
            (ROOT/"artifacts"/"real_traces.json").write_text(json.dumps(trace, indent=2), encoding="utf-8")
            (ROOT/"artifacts"/"real_headers.json").write_text(json.dumps(model.header_observations, indent=2), encoding="utf-8")
            print(json.dumps(stats(rows), indent=2))
        asyncio.run(probe())


if __name__ == "__main__":
    main()
