"""Evidence-level numerical qualifier checks are stricter than citation-label checks."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relay import Passage,UNSUPPORTED,citation_guard

PAPER="2410.00037v1"

def test_rejects_mixed_up_moshi_latency_values():
    p=Passage(PAPER,1,"Moshi has a theoretical latency of 160ms, 200ms in practice.")
    assert citation_guard("The theoretical latency is 200ms. "+p.citation,[p],"What is Moshi's theoretical latency?")==UNSUPPORTED
    assert citation_guard("The theoretical latency is 160ms. "+p.citation,[p],"What is Moshi's theoretical latency?")!=UNSUPPORTED
    assert citation_guard("The practical latency is 200ms. "+p.citation,[p],"What is Moshi's practical latency?")!=UNSUPPORTED

def test_supports_metric_before_qualifier():
    p=Passage(PAPER,1,"Moshi reports about 200ms practical latency, versus 160ms theoretically.")
    assert citation_guard("The practical latency is 200ms. "+p.citation,[p],"What is Moshi's practical latency?")!=UNSUPPORTED
    assert citation_guard("The theoretical latency is 160ms. "+p.citation,[p],"What is Moshi's theoretical latency?")!=UNSUPPORTED
    assert citation_guard("The practical latency is 160ms. "+p.citation,[p],"What is Moshi's practical latency?")==UNSUPPORTED

def test_citation_still_refuses_unknown_page():
    p=Passage(PAPER,1,"Moshi reports 160ms theoretical latency.")
    assert citation_guard("Moshi is fast. ["+PAPER+" p.99]",[p],"What is theoretical latency?")==UNSUPPORTED
