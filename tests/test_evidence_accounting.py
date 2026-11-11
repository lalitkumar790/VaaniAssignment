"""Regression checks: true provider-call counts versus locally generated refusals."""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_evidence import build_audit
from relay import Corpus,StandIn,UNSUPPORTED,ask,Passage

def test_v5_http_evidence_accounting():
    report=build_audit()
    assert report["pipeline_requests"]==18
    assert report["hosted_http_requests"]==16
    assert report["http_statuses"]=={200:16}
    assert report["local_no_http_requests"]==2
    assert report["hosted_content_ttft_p50_p95_p99_ms"][0]==390.7

def test_local_refusal_has_no_model_first_token():
    tr=[]
    rec,ans=asyncio.run(ask("What was Vaani's stock-market price yesterday?",
        Corpus.load(demo=True),StandIn(failure_probability=0,slow_probability=0),trace=tr))
    assert ans==UNSUPPORTED
    assert rec["first_token_ms"]==""
    assert tr[0]["provider_http_responses"]==0
    assert any(x["stage"]=="local_refusal" for x in tr[0]["timeline"])

def test_traces_record_model_http_observation():
    class FakeGroq:
        source="real"
        def __init__(self):self.header_observations=[]
        async def stream(self,question,evidence,callback,observe=None):
            self.header_observations.append({"http_status":200})
            await callback("Supported answer "+evidence[0].citation)
            return 20,5
    corpus=Corpus([Passage("2410.00037v1",1,"The theoretical latency of Moshi is 160ms.")])
    trace=[]
    rec,_=asyncio.run(ask("What is the theoretical latency of Moshi?",
                          corpus,FakeGroq(),trace=trace))
    assert trace[0]["provider_http_responses"]==1
    assert rec["first_token_ms"]!=""
