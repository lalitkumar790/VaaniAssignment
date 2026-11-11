"""Build precisely two visually structured A3 landscape pages from versioned CSV evidence.
Do not reclassify HTTP 401 as a valid hosted measurement or stand-in as real.
"""
from pathlib import Path
import csv, json, math, statistics
from collections import Counter
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A3
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
import fitz

ROOT=Path(__file__).resolve().parent
ROWS=list(csv.DictReader((ROOT/"results.csv").open(encoding="utf-8")))
TR=json.loads((ROOT/"artifacts/v5_real_traces.json").read_text())
def GROUP(name):
    rows=[x for x in ROWS if x["scenario"]==name]
    # V5: 18 pipeline records, but only 16 actual hosted Groq responses.
    if name=="v5_real_modest":
        rows=[r for r in rows if int(r["tokens_in"])>0]
    return rows
def quant(vals,p):
    z=sorted(float(x) for x in vals if x not in ("",None))
    if not z:return "NM"
    j=(len(z)-1)*p/100;k=math.floor(j)
    return f"{z[k]+(z[math.ceil(j)]-z[k])*(j-k):.1f}"
def q3(xs,k):return "/".join(quant([r[k] for r in xs],p) for p in (50,95,99))
def q2(xs,k):return "/".join(quant([r[k] for r in xs],p) for p in (50,95))
def pct(k,n):return f"{100*k/n:.1f}%" if n else "NM"
def dur(rs):
    st=min(datetime.fromisoformat(x["start_time"]) for x in rs)
    en=max(datetime.fromisoformat(x["start_time"])+timedelta(milliseconds=float(x["total_ms"])) for x in rs)
    return (en-st).total_seconds()
def proxy(rs):return sum(int(x["tokens_in"])+int(x["tokens_out"]) for x in rs)/len(rs)
S=[("v5_real_modest","Real Groq V5","Groq"),
   ("cal_steady","Steady","stand-in"),
   ("cal_burst","Burst","stand-in"),
   ("cal_sustained_overload","Sustained","stand-in"),
   ("cal_rpm_halved","RPM halved","stand-in"),
   ("cal_daily_exhausted","RPD exhausted","stand-in")]
T2a=[];T2b=[]
for key,name,src in S:
    r=GROUP(key);n=len(r);d=dur(r);c=Counter(x["status"] for x in r)
    T2a.append([name,src,str(n),f"{d:.2f}",f"{n*60/d:.1f}",q3([x for x in r if int(x["tokens_in"])>0],"first_token_ms"),q3(r,"total_ms")])
    usd=(sum((int(x["tokens_in"])*.075+int(x["tokens_out"])*.30)/1e6 for x in r)/n*1000 if src=="Groq" else 0)
    T2b.append([name,pct(c["ok"],n),pct(c["rate_limited"],n),pct(c["timeout"]+c["error"],n),
               f"{sum(int(x['retries']) for x in r)/n:.2f}",str(max(int(x["queue_peak_observed"]) for x in r)),
               f"{proxy(r):.1f}",f"{usd:.3f}"])
T3=[]
for setting,label in [("small","220 chars / top1 / no"),("balanced","500 chars / top3 / yes"),("wide","1000 chars / top6 / yes")]:
    r=GROUP("v4_retrieval_"+setting);n=len(r);c=Counter(x["answer_grade"] for x in r)
    T3.append([label,str(n),pct(c["correct"],n),pct(c["wrong"]+c["refused_wrongly"],n),pct(c["refused_correctly"],n),
               f"{proxy(r):.1f}",q2(r,"first_token_ms"),q2(r,"total_ms")])
slow=max((x for x in GROUP("v5_real_modest") if x["status"]=="ok"),key=lambda x:float(x["total_ms"]))
trace=next(t for t in TR if t["request_id"]==slow["request_id"].removeprefix("v5-"))
m={x["stage"]:x["elapsed_ms"] for x in trace["timeline"]}
navy=colors.HexColor("#101E2D");ink=colors.HexColor("#10263B");teal=colors.HexColor("#0C897A")
pale=colors.HexColor("#EEF5F8");line=colors.HexColor("#CADAE2");muted=colors.HexColor("#60738A")
PW,PH=landscape(A3);W,H=PW/1.2,PH/1.2;mar=29;fw=W-2*mar
pdf=canvas.Canvas(str(ROOT/"REPORT.pdf"),pagesize=(PW,PH),pageCompression=1)
pdf.setTitle("The Relay - Vaani - Full-PDF and real Groq V5 engineering report")
pdf.scale(1.2,1.2)
def textwrap(s,x,y,w=0,font=7.9,leading=10):
    pdf.setFont("Helvetica",font);pdf.setFillColor(ink)
    for seg in simpleSplit(s,"Helvetica",font,w or fw):
        pdf.drawString(x,y,seg);y-=leading
    return y
def head(n):
    pdf.setFillColor(navy);pdf.rect(0,H-53,W,53,fill=1,stroke=0)
    pdf.setFont("Helvetica-Bold",17);pdf.setFillColor(colors.white);pdf.drawString(mar,H-29,"THE RELAY")
    pdf.setFont("Helvetica",9);pdf.setFillColor(colors.HexColor("#B7CADC"))
    pdf.drawString(mar+124,H-27,"Vaani · ML Engineering Intern · observed / simulated evidence")
    pdf.setFont("Helvetica-Bold",7);pdf.drawRightString(W-mar,H-29,f"{n} / 2")
    pdf.setFillColor(muted);pdf.setFont("Helvetica",6.8)
    pdf.drawString(mar,13,"Evidence: results.csv · V1 GitHub run 42866165930 · V5 GitHub run 42970031360 · 11 November 2026")
    pdf.drawRightString(W-mar,13,"* Counterfactual retail pricing; no free-tier bill")
def sec(num,name,y):
    pdf.setFillColor(teal);pdf.setFont("Helvetica-Bold",10);pdf.drawString(mar,y,num)
    pdf.setFillColor(ink);pdf.drawString(mar+25,y,name);return y-15
def title(t,y):
    pdf.setFillColor(ink);pdf.setFont("Helvetica-Bold",9.2);pdf.drawString(mar,y,t);return y-14
def table(hd,data,widths,y,rh=17,hh=19):
    x=mar;size=sum(widths);pdf.setFillColor(navy);pdf.roundRect(x,y-hh,size,hh,3,stroke=0,fill=1)
    pdf.setFillColor(colors.white);pdf.setFont("Helvetica-Bold",7)
    for label,w in zip(hd,widths):
        pdf.drawString(x+5,y-hh+6,str(label)[:34]);x+=w
    y-=hh
    for i,row in enumerate(data):
        if i%2==0:
            pdf.setFillColor(pale);pdf.rect(mar,y-rh,size,rh,stroke=0,fill=1)
        x=mar;pdf.setFont("Helvetica",7.1);pdf.setFillColor(ink)
        for val,w in zip(row,widths):
            pdf.drawString(x+5,y-rh+5,str(val)[:42]);x+=w
        y-=rh
    pdf.setStrokeColor(line);pdf.line(mar,y,mar+size,y)
    return y-11
def mini(t,b,x,y,cw):
    pdf.setFont("Helvetica-Bold",9);pdf.setFillColor(teal);pdf.drawString(x,y,t)
    return textwrap(b,x,y-13,cw,7.9,10)-9

head(1);y=H-68
y=sec("01","What I built and why",y)
y=textwrap("Five Python stages: classify -> page-cited retrieval from three locked PDFs -> admit/plan -> stream via Groq or stand-in -> verify/refuse. Deliberate trade-off: refuse unsupported claims instead of generating fast uncited answers.",mar,y)-8
y=sec("02","The real service and my stand-in",y)
y=textwrap("Groq V5: 18 pipeline questions, 16 HTTP200 and 2 local refusals. Actual provider TTFT p50 390.7 ms; p95 768.8 ms; V1: 16 successes then one HTTP429 at the token/min boundary (retry-after 5s). Headers showed 8,000 TPM and 1,000 RPD. V2's 18 HTTP401 failures came from an escaped secret, and are NOT successful real probes. Stand-in fits V1 median TTFT, not unmeasured parallel slowdowns.",mar,y,font=7.7,leading=9.3)-5
y=title("TABLE 1  /  Provider limits — measurement versus published documentation",y)
limitrows=[["Requests/min","30 (docs)","Public free plan; not challenged","medium"],
           ["Tokens/min","8,000","x-ratelimit-limit-tokens, HTTP200/429","high"],
           ["Requests/day","1,000","x-ratelimit-limit-requests is RPD","high"],
           ["Tokens/day","200,000 (docs)","No account TPD header measured","medium"],
           ["In flight at once","not measured","Only sequential hosted calls","low"],
           ["Limit response","HTTP 429; 5 sec","V1 17th request retry-after=5","high"],
           ["Real recovery","not measured","5sec suggested, not tested","low"]]
y=table(["Limit","Value found","How discovered","Confidence"],limitrows,[120,111,421,132],y,rh=16)
y=sec("03","Results",y)
y=textwrap("Milliseconds p50/p95/p99. TTFT excludes zero-input local refusals and unserved requests; completion latency includes all offered scenario requests. NM = not measured. Calibrated stand-in load shapes remain modelled, not observed Groq concurrency.",mar,y,font=7.6)-3
y=title("TABLE 2a  /  First token and completion time by traffic shape",y)
y=table(["Scenario","Source","N","Duration s","Offer/min","TTFT p50/p95/p99 ms","Total p50/p95/p99 ms"],T2a,[115,72,35,75,78,201,208],y,rh=16)
y=title("TABLE 2b  /  Delivery outcomes and costs from the same per-request file",y)
y=table(["Scenario","Success","Rate-limited","Timeout/error","Retries/req","Peak queue","Tokens/answer","USD/1k*"],T2b,[115,83,96,107,100,70,105,108],y,rh=16)
if y<39:raise RuntimeError(f"Page1 overflow {y}")
pdf.showPage();pdf.scale(1.2,1.2)
head(2);y=H-68
y=title("TABLE 3  /  Three full-PDF retrieval settings, 18 questions each; strict string/citation oracle",y)
y=table(["Chunk / K / rerank","N","Correct+cited","Wrong","Correct refuse","Token proxy/answer","TTFT p50/p95 ms","Total p50/p95 ms"],T3,[176,35,91,65,106,119,95,97],y,rh=17)
y=textwrap("V4 full-PDF proxy: 17/54 literal-key correct, 29 wrong, 1 wrongful and 7 justified refusals. V5 pipeline: 6/18 literal-key correct; 16 HTTP200 and 2 local refusals. Unicode, phrasing and units distort this grade; human review required.",mar,y,font=7.8)-9
cw=(fw-18)/2;left=mar;right=mar+cw+18;yl=y;yr=y
yl=mini("04  Where the time goes",f"Slow Groq V5 request {trace['request_id']}: total {m['verify']:.1f}ms; first content {m['first_token']:.1f}ms. Local retrieval/plan {m['queue_enter']:.1f}ms, HTTP acceptance/server interval {m['queue_leave']-m['queue_enter']:.1f}ms, accepted-to-content {m['first_token']-m['queue_leave']:.1f}ms, post-content stream+verify {m['verify']-m['first_token']:.1f}ms, 0 retries. Groq's internal queuing is not separately measurable.",left,yl,cw)
yl=mini("05  When a limit is hit","At TPM, shrink evidence and check whether Retry-After fits the waiting person's deadline; otherwise reject explicitly. At RPD exhaustion, stop hosted calls and never silently downgrade into an uncited guess. V1 measured a five-second retry-after, but not actual recovery.",left,yl,cw)
yl=mini("Retrieval: quality versus cost","Three tested settings: 220 chars/top-1, 500 chars/top-3, 1,000 chars/top-6. Strict scores were 4/18 small, 6/18 balanced, 7/18 wide; larger context used more proxy tokens. Prefer the balanced K=3 for budget, but this correctness is not adequate for unattended deployment. Near budget: smaller K or refusal.",left,yl,cw)
yl=mini("How this library misleads a naive retriever","Attention heads appear in multiple papers; latency passages mix Moshi's 160ms theoretical value with other delay values; PDF extraction can break mathematical formula text such as sqrt(dk). Paper routing and version/page citations mitigate, but do not solve, these errors.",left,yl,cw)
yl=mini("06  Retries","One pre-first-token transient 503 retry recovered an answer but took longer. Never restart a partially streamed reply. Retrying a measured 429 immediately would worsen latency, since the returned retry-after was 5 seconds.",left,yl,cw)
yr=mini("07  What the person sees",'At 3pm when the day quota is exhausted: "I cannot provide a verified answer now because the daily hosted-model quota is exhausted. Please try after reset." Do not fabricate a paper citation.',right,yr,cw)
yr=mini("08  What I am unsure about, left out, learned","Least certain: the stand-in's concurrency slowdown; all Groq calls were serial. Wrong assumption breaks p95 overload. Deliberately omitted public multi-tenant auth and an embedding reranker. Lesson: a 200 status need not mean a correct answer; minute tokens can run out long before daily requests.",right,yr,cw)
yr=mini("Your feedback on Vaani","The Vaani developer guide's distinction between dispatch and completion stands out. Latency definitions (interrupt vs full response) are difficult to compare; a common glossary showing p50/p95, load, sample size and measurement boundaries would help. Applicant should personally review this opinion.",right,yr,cw)
yr=mini("How I worked with the assistant","The original user supplied the brief and GitHub repository, then configured a Groq Secret and sent the run link. The assistant wrote code, results and this report. The first optimistic fixture metric failed on real PDFs; an assistant-introduced V2 secret bug caused HTTP401 until detected and fixed. Applicant must include unedited conversation history and verify personal decisions before submission.",right,yr,cw)
yr=mini("Evidence and limitations","519 per-request rows retain V1 (real 429), V2 (HTTP401), V3/V4/V5 pipeline runs and stand-ins; V5 has 16 actual Groq calls plus two local refusals. Cost is hypothetical list price, not charge. Groq recovery, true in-flight limit and external human semantic grading remain unmeasured.",right,yr,cw)
if min(yl,yr)<40:raise RuntimeError(f"Page2 overflow: {yl}, {yr}")
pdf.showPage();pdf.save()
doc=fitz.open(ROOT/"REPORT.pdf")
assert len(doc)==2
assert "Real Groq V5" in doc[0].get_text()
print("Generated 2-page PDF with",len(ROWS),"source rows")
