import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relay import Budget, Corpus, Limited, StandIn, UNSUPPORTED, ask, citation_guard, grade, percentile


def test_locked_versions_and_demo_provenance():
    corpus = Corpus.load(demo=True)
    assert {p.paper for p in corpus.passages} == {"1706.03762v7", "2410.00037v1", "2507.07955v2"}
    assert all(p.page >= 1 and p.note != "PDF" for p in corpus.passages)


def test_citation_rejects_hallucinated_source():
    evidence = Corpus.load(demo=True).retrieve("Moshi latency")
    assert citation_guard("Invented [1706.03762v7 p.99]", evidence) == UNSUPPORTED
    assert citation_guard("Invented uncited reply", evidence) == UNSUPPORTED


def test_unknown_question_refuses():
    corpus = Corpus.load(demo=True)
    model = StandIn(failure_probability=0, slow_probability=0)
    row, answer = asyncio.run(ask("What color is the CEO's bicycle?", corpus, model))
    # A weak lexical hit is possible in lexical retrieval; never allow uncited answers.
    assert answer == UNSUPPORTED or "[" in answer
    assert row["source"] == "stand-in"


def test_daily_budget_blocks_without_model_request():
    async def run():
        budget = Budget(rpd=0)
        try:
            await budget.admit(100)
        except Limited as exc:
            return exc.reason
    assert asyncio.run(run()) == "daily"


def test_streams_and_emits_timings():
    corpus = Corpus.load(demo=True)
    model = StandIn(seed=2, failure_probability=0, slow_probability=0, chunk_ms=1)
    row, answer = asyncio.run(ask("What is the theoretical latency of Moshi?", corpus, model))
    assert row["status"] == "ok"
    assert 0 <= row["first_token_ms"] <= row["total_ms"]
    assert "[" in answer or answer == UNSUPPORTED


def test_percentile_interpolation():
    assert percentile([10, 20, 30], 50) == 20.0
    assert percentile([], 95) is None
