"""Regression tests for corpus-aware retrieval and quota accounting."""
import asyncio
import json
from pathlib import Path

from relay import Budget, Corpus, Passage, StandIn, UNSUPPORTED, ask, citation_guard, grade
from retrieval_optimized import text_windows, normalize, paper_scope

ROOT = Path(__file__).resolve().parents[1]

def test_fixture_accuracy_is_not_regressed():
    questions=json.loads((ROOT/"data"/"questions.json").read_text())
    corpus=Corpus.load(demo=True)
    for setting in ("small","balanced","wide"):
        model=StandIn(seed=8,failure_probability=0,slow_probability=0,chunk_ms=0)
        grades=[]
        for item in questions:
            row,answer=asyncio.run(ask(item["question"],corpus,model,setting))
            grades.append(grade(item,row,answer))
        assert grades.count("correct")>=15
        assert grades.count("refused_correctly")==3
        assert "wrong" not in grades

def test_anchored_paper_scope():
    assert paper_scope("How does Moshi model user speech?")=={"2410.00037v1"}
    assert paper_scope("Does H-Net learn chunk boundaries?")=={"2507.07955v2"}
    assert paper_scope("What is the Transformer BLEU score?")=={"1706.03762v7"}

def test_cached_retrieval_index():
    corpus=Corpus.load(demo=True)
    assert corpus.retrieve("What is Moshi latency?","balanced")
    cached=corpus._retriever.cache["balanced"]
    assert corpus.retrieve("How does Moshi generate speech?","balanced")
    assert corpus._retriever.cache["balanced"] is cached

def test_windows_do_not_truncate_paper_claims():
    text="The system does the first thing. "+("token "*60)+"Then it does the second thing."
    pieces=text_windows(text,100)
    assert len(pieces)>2
    assert any("second thing" in p for p in pieces)
    assert normalize("audio to-\nkens")=="audio tokens"

def test_numeric_claim_must_match_cited_evidence():
    passages=[Passage("2410.00037v1",1,"The paper reports theoretical latency of 160ms.")]
    assert citation_guard("Latency is 640ms. [2410.00037v1 p.1]",passages)==UNSUPPORTED
    assert citation_guard("Latency is 160ms. [2410.00037v1 p.1]",passages)!=UNSUPPORTED

def test_unissued_queue_request_refunds_limits():
    async def run():
        b=Budget(rpm=5,tpm=1000,rpd=3,max_parallel=1,queue_timeout=.005)
        await b.sema.acquire()
        try:
            try: await b.admit(500)
            except Exception as e:
                assert e.__class__.__name__=="TimedOut"
            else: raise AssertionError("should time out in queue")
            assert b.day_calls==0 and b.tokens==0 and len(b.minute)==0
        finally: b.sema.release()
    asyncio.run(run())
