"""Read-only audit: count actual Groq HTTP responses separately from pipeline rows.

V5 requested 18 answers but two were refused locally before reaching the model.
Preserve the original strict grading and historical CSV.
"""
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ART=ROOT/"artifacts"

def percentile(v,p):
    v=sorted(v)
    if not v:return None
    pos=(len(v)-1)*p/100
    lo=math.floor(pos)
    return round(v[lo]+(v[math.ceil(pos)]-v[lo])*(pos-lo),1)

def normalized(s):
    s=unicodedata.normalize("NFKC",s).casefold()
    s=s.replace("‑","-").replace("–","-").replace("—","-")
    return re.sub(r"(?<=\d)\s+(?=ms\b)","",s)

def build_audit():
    questions=json.loads((ROOT/"data/questions.json").read_text(encoding="utf-8"))
    with (ART/"v5_real_results.csv").open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    traces=json.loads((ART/"v5_real_traces.json").read_text(encoding="utf-8"))
    headers=json.loads((ART/"v5_real_headers.json").read_text(encoding="utf-8"))
    assert len(rows)==len(traces)==len(questions)==18
    assert [r["request_id"] for r in rows]==[t["request_id"] for t in traces]
    provider=[r for r in rows if int(r["tokens_in"])>0]
    local=[r for r in rows if int(r["tokens_in"])==0]
    status=Counter(int(h["http_status"]) for h in headers)
    assert len(headers)==len(provider)==16
    assert len(local)==2 and status=={200:16}
    assert all(r["answer_grade"]=="refused_correctly" for r in local)
    review=[]
    for q,r,t in zip(questions,rows,traces):
        a=t["answer"]
        review.append({
            "request_id":r["request_id"],"question":q["question"],
            "strict_grade":r["answer_grade"],
            "http_call_inferred":"yes" if int(r["tokens_in"])>0 else "no",
            "literal_key_match":str(any(x.casefold() in a.casefold() for x in q["accept"])).lower(),
            "unicode_whitespace_normalized_match":str(any(normalized(x) in normalized(a) for x in q["accept"])).lower(),
            "needs_human_semantic_review":str(q["scope"]=="inside" and r["answer_grade"]!="correct").lower(),
            "answer":a
        })
    summary={
        "source":"GitHub V5 run 42970031360; committed requests, HTTP headers and traces",
        "pipeline_requests":len(rows),
        "hosted_http_requests":len(headers),
        "http_statuses":dict(status),
        "local_no_http_requests":len(local),
        "local_request_ids":[r["request_id"] for r in local],
        "hosted_content_ttft_p50_p95_p99_ms":[percentile([float(r["first_token_ms"]) for r in provider],p) for p in (50,95,99)],
        "hosted_total_p50_p95_p99_ms":[percentile([float(r["total_ms"]) for r in provider],p) for p in (50,95,99)],
        "pipeline_content_ttft_p50_p95_p99_ms":[percentile([float(r["first_token_ms"]) for r in rows],p) for p in (50,95,99)],
        "strict_grades_all_pipeline_questions":dict(Counter(r["answer_grade"] for r in rows)),
        "normalized_string_key_matches_only":sum(r["unicode_whitespace_normalized_match"]=="true" for r in review),
        "interpretation":"Normalized string matches are not verified semantic accuracy. Paper-level human citation review is still required."
    }
    (ART/"v5_provider_audit.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    with (ART/"v5_question_review.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(review[0]))
        writer.writeheader();writer.writerows(review)
    return summary

if __name__=="__main__":
    print(json.dumps(build_audit(),indent=2))
