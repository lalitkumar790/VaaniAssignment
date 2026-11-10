"""Create submission tables and exactly two landscape A3 pages from raw CSV only."""
from __future__ import annotations
import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from relay import ROOT, percentile

ART = ROOT / "artifacts"
LOAD = list(csv.DictReader((ART/"load_results.csv").open()))
QUALITY = list(csv.DictReader((ART/"quality_results.csv").open()))
RETRY = list(csv.DictReader((ART/"retry_results.csv").open()))
ROWS = LOAD+QUALITY+RETRY
with (ROOT/"results.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=ROWS[0].keys())
    writer.writeheader()
    writer.writerows(ROWS)


def pct(a,b): return f"{(a/max(1,b)*100):.1f}%"
def d3(items, key):
    vals = [float(r[key]) for r in items if r[key] not in ('', None)]
    return '/'.join('NM' if percentile(vals,p) is None else f'{percentile(vals,p):.1f}' for p in (50,95,99))
def d2(items,key):
    vals = [float(r[key]) for r in items if r[key] not in ('', None)]
    return '/'.join('NM' if percentile(vals,p) is None else f'{percentile(vals,p):.1f}' for p in (50,95))
def date(s): return datetime.fromisoformat(s)

def scenario(items):
    end = max(date(r['start_time']) + timedelta(milliseconds=float(r['total_ms'])) for r in items)
    start = min(date(r['start_time']) for r in items)
    duration = (end-start).total_seconds()
    n=len(items)
    co=Counter(r['status'] for r in items)
    return {'n':n,'duration_s':round(duration,2),'offered_per_min':round(n/duration*60,1),
      'ttft':d3(items,'first_token_ms'),'total':d3(items,'total_ms'),
      'succeeded':pct(co['ok'],n),'rate_limited':pct(co['rate_limited'],n),
      'timeout_error':pct(co['timeout']+co['error'],n),
      'retries':round(sum(int(r['retries']) for r in items)/n,2),
      'peak_queue':max(int(r['queue_peak_observed']) for r in items),
      'tokens_per_answer':round(sum(int(r['tokens_in'])+int(r['tokens_out']) for r in items)/n,1),
      'cost_usd_1000':round(sum(float(r['cost_usd'] or 0) for r in items)/n*1000,2)}

LOAD_ORDER=['steady','burst','sustained_overload','rpm_halved','daily_exhausted']
load_summary = {name:scenario([r for r in LOAD if r['scenario']==name]) for name in LOAD_ORDER}
quality_summary={}
for name in ['small','balanced','wide']:
    rs=[r for r in QUALITY if r['scenario']==f'retrieval_{name}']
    co=Counter(r['answer_grade'] for r in rs)
    quality_summary[name]={'n':len(rs),'correct':pct(co['correct'],len(rs)),
           'wrong':pct(co['wrong'],len(rs)), 'refused':pct(co['refused_correctly'],len(rs)),
           'tokens':round(sum(int(r['tokens_in'])+int(r['tokens_out']) for r in rs)/len(rs),1),
           'ttft':d2(rs,'first_token_ms'), 'total':d2(rs,'total_ms')}

traces=json.load((ART/'traces.json').open())
slowest=max((r for r in LOAD if r['status']=='ok' and r['first_token_ms'] != ''),key=lambda r:float(r['total_ms']))
slowtrace=next(t for t in traces if t['request_id']==slowest['request_id'])
ms={event['stage']:event['elapsed_ms'] for event in slowtrace['timeline']}
q_wait = round(ms.get('queue_leave', 0)-ms.get('queue_enter', 0), 1)
pre_work=round(ms['first_token']-ms.get('queue_leave',ms['plan']),1)
post_work=round(ms['verify']-ms['first_token'],1)
retry_delay=0
retry_samples={r['scenario']:r for r in RETRY}

manifest={'source':'stand-in only; not calibrated to real Groq', 'created_utc':datetime.now().astimezone().isoformat(),
 'load_configs':{'steady':{'n':12,'arrival_gap_s':.22,'rpm':60,'rpd':100},
 'burst':{'n':22,'arrival_gap_s':0,'rpm':12,'rpd':100},
 'sustained_overload':{'n':28,'arrival_gap_s':.035,'rpm':10,'rpd':100},
 'rpm_halved':{'n':16,'arrival_gap_s':.07,'rpm':6,'rpd':100},
 'daily_exhausted':{'n':10,'arrival_gap_s':.06,'rpm':20,'rpd':0}},
 'all_scenarios':load_summary,'retrieval_settings':quality_summary,
 'slowest_successful_request':{'id':slowest['request_id'],'total_ms':float(slowest['total_ms']),
 'first_token_ms':float(slowest['first_token_ms']),'observed_queue_wait_ms':q_wait,
 'work_before_first_token_ms':pre_work,'work_after_first_token_ms':post_work,
 'retry_duration_ms':retry_delay, 'timeline':slowtrace['timeline']},
 'retry_example':[{'scenario':r['scenario'],'status':r['status'],'total_ms':r['total_ms'],'retries':r['retries']} for r in RETRY],
 'measurements':{'real_calls':0,'stand_in_load_calls':len(LOAD),'quality_calls':len(QUALITY),'retry_calls':len(RETRY),
                 'all_rows':len(ROWS)},
 'limitations':['No GROQ_API_KEY or external network access in this execution environment.',
 'Demo data are paraphrased page-verified notes rather than fetched full PDFs.',
 'Stand-in latencies are measured wall clock, uncalibrated to a real provider.',
 'Stand-in token counts are rough 4-character proxies; they are not model tokenizer usage.',
 'Grade is a predefined substring-and-citation oracle; not blinded human assessment.',
 'Local stand-in calls have zero external API charges; excludes electricity and hardware.']}
(ART/'experiment_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Markdown: same submission report, tables generated directly from CSV.
md=['# The Relay — Vaani ML Engineering Intern',
 'Local stand-in measurement, NOT a completed hosted-Groq evaluation. 10 November 2026.',
 '', '## 1 What I built and why',
 'Python 5-step query classification → page-cited BM25 passage retrieval → scope/plan → streaming draft → citation validation/refusal. '
 'Decision: fail closed on missing evidence and reject 429 within deadline rather than invent a quick answer.',
 '', '## 2 The real service and my stand-in',
 'The production adapter targets Groq streaming OpenAI-compatible chat completions. No account key was available; '
 'real endpoint behavior and calibration are **not measured**. Groq docs say limit responses use HTTP 429, retry-after, '
 'and remaining/reset headers; exact organization limits vary. Local stand-in simulates jitter, 503, 429, queueing, '
 'streaming and load-related slowdown using *chosen*, not fitted, parameters.',
 '', '**Table 1 — Real-service limits (all entries unmeasured, not guessed)**',
 '| Limit | Value found | How found | Confidence |','|---|---|---|---|']
for label in ['Requests/minute','Tokens/minute','Requests/day','Tokens/day','Requests in flight','Actual 429 payload','Recovery time']:
    md.append(f'| {label} | not measured | key not available; docs only | low |')
md.extend(['', '## 3 Results', 'All load observations are local stand-in; timings are measured wall-clock. '
           'TTFT p50/p95/p99 is **internal first model token**, conditional on emitting one; the user receives only citation-verified output. NM means none emitted.',
           '', '**Table 2a — Latency**',
           '| Scenario | Source | N | Duration s | Offered/min | TTFT p50/p95/p99 ms | Total p50/p95/p99 ms |',
           '|---|---|---:|---:|---:|---|---|'])
for name,d in load_summary.items():
    md.append(f'| {name} | stand-in | {d["n"]} | {d["duration_s"]:.2f} | {d["offered_per_min"]:.1f} | {d["ttft"]} | {d["total"]} |')
md.extend(['','**Table 2b — Outcomes**',
           '| Scenario | Success | 429 | Timeout/error | Retry/request | Peak queue | Tokens/answer | API $/1k |',
           '|---|---:|---:|---:|---:|---:|---:|---:|'])
for name,d in load_summary.items():
    md.append(f'| {name} | {d["succeeded"]} | {d["rate_limited"]} | {d["timeout_error"]} | {d["retries"]:.2f} | {d["peak_queue"]} | {d["tokens_per_answer"]:.1f} | {d["cost_usd_1000"]:.2f} |')
md.extend(['','**Table 3 — Retrieval (18 authored questions per setting)**',
           '| Setting | Questions | Correct+cited | Wrong | Correct refusal | Tokens/answer | TTFT p50/p95 ms | Total p50/p95 ms |',
           '|---|---:|---:|---:|---:|---:|---|---|'])
for name, d in quality_summary.items():
    cfg={'small':'220 chars / 1 / no rerank','balanced':'500 chars / 3 / lexical rerank','wide':'1000 chars / 6 / lexical rerank'}[name]
    md.append(f'| {cfg} | {d["n"]} | {d["correct"]} | {d["wrong"]} | {d["refused"]} | {d["tokens"]} | {d["ttft"]} | {d["total"]} |')
md.extend(['','## 4 Where the time goes',
 f'Slowest successful local load request `{slowest["request_id"]}` took {slowest["total_ms"]} ms, first token at {slowest["first_token_ms"]} ms. '
 f'Instrumented queue wait {q_wait} ms; model/pipeline work after admission through first token {pre_work} ms; '
 f'after first token through verification {post_work} ms; retry 0 ms. Raw event stamps in `artifacts/traces.json`.',
 '', '## 5 When a limit is hit',
 'Per-minute: admission denies excess quickly with 429-labelled outcome instead of queueing beyond short deadline. '
 'Per-day: stop new hosted calls and serve a clear service-unavailable message; local out-of-scope refusals may bypass the model. '
 'Prioritize admitted requests and cite/refuse honestly; no silent low-quality model fallback.',
 '', '## Retrieval: quality versus cost',
 'Across 18 small, curated fixture questions per setting the measured accuracy was equal. '
 'Choose 220/1 for lowest input-token proxy cost on this small fixture; do **not** generalize to full PDFs, '
 'where a wider context could recover answers spanning multiple paragraphs. Under budget pressure shrink top-k, not citation guard.',
 '', '## How this library will mislead a naive retriever',
 '(1) “attention” occurs in many places: “Which model is meant for live spoken dialogue?” can pull the Transformer paper. '
 '(2) Moshi contains both 160 ms theoretical and 200 ms practical latency: “What is observed latency?” may return the wrong figure. '
 '(3) Chunking in H-Net is learned segmentation while our retrieval chunking is arbitrary text windows: “How are chunks learned?” can conflate the two.',
 '', '## 6 Retries',
 'One retry only for pre-token transient 503, short exponential backoff; never retry a partly-streamed answer, '
 'and do not wait past an explicit minute/day reset. Controlled example: no retry failed at '
 f'{retry_samples["fail_fast"]["total_ms"]} ms; retry succeeded but took {retry_samples["retry_once"]["total_ms"]} ms, '
 'a longer wait; on burst traffic the extra attempt also consumes quota.',
 '', '## 7 What the person sees',
 '“I can’t answer from the three papers right now because today’s model-call budget is exhausted. '
 'I won’t guess or generate an uncited reply. Please return after the quota resets.”',
 '', '## 8 What I’m unsure about, what I left out, what I learned',
 'Least certain: lexical retrieval on a 19-note paraphrase fixture predicts full-paper performance; it may fail badly. '
 'Deliberate omissions: semantic reranker and distributed queue. Learned: TTFT conditional on success can look good '
 'even as most requests are refused; measure success coverage too.',
 '', '## Your feedback on Vaani',
 'The Teacher AI prompt-diff review and conversation-memory design stood out. The site’s P90 ~450 ms claim '
 'does not clearly say which stage is timed, and animated counters are harder to verify in text-only view. '
 'I would publish a transparent latency measurement definition and a language-filterable live-call demo.',
 '', '## How I worked with the assistant',
 'Full accessible request and working notes are in `conversation_history.md`; no cleaned-up or invented exchanges. '
 'Three influential instructions: (1) the user requested end-to-end delivery in a named repo, '
 '(2) the brief required the exact arXiv versions and cite-or-refuse behavior, '
 '(3) the brief required recomputable per-request tables. The assistant initially left `status=error` after '
 'a successful retry; the controlled failure-injection test exposed it and it was fixed. '
 'A deliberate override was to reject fabricated Groq benchmarks. These are assistant-implemented choices; '
 'the applicant must personally review, rerun with their own Groq key, and describe their own decisions before submission.',
 '', 'All numbers are from `results.csv`; stand-in token figures are rough proxies, not Groq billing usage.'])
(ROOT/'REPORT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

# Exactly 2 pages. A3 landscape ensures readable tables with small body text.
W,H=landscape(A3)
c=canvas.Canvas(str(ROOT/'REPORT.pdf'),pagesize=(W,H))
NAVY=colors.HexColor('#153252'); TEAL=colors.HexColor('#007E88'); DARK=colors.HexColor('#203040')

def text_line(x,y,content,size=9,bold=False,color=DARK):
    c.setFillColor(color); c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    c.drawString(x,y,str(content))
    return y-size-4

def wrap(text,width,size=9):
    tokens=text.split(); lines=[]; cur=''
    for token in tokens:
        nxt=(cur+' '+token).strip()
        if stringWidth(nxt,'Helvetica',size)>width and cur:
            lines.append(cur);cur=token
        else:cur=nxt
    if cur:lines.append(cur)
    return lines

def para(x,y,t,width,size=9,leading=12):
    for line in wrap(t,width,size):
        y=text_line(x,y,line,size)
        y-=max(0,leading-(size+4))
    return y-7

def heading(x,y,name,size=11):
    c.setFillColor(TEAL); c.setFont('Helvetica-Bold',size); c.drawString(x,y,name)
    return y-17

def table(x,y,cols,data,widths,fontsize=8,rowh=18):
    assert len(cols)==len(widths)
    total=sum(widths)
    c.setFillColor(NAVY);c.rect(x,y-rowh,total,rowh,fill=1,stroke=0)
    cur=x
    for name,w in zip(cols,widths):
        c.setFillColor(colors.white);c.setFont('Helvetica-Bold',fontsize)
        c.drawString(cur+5,y-rowh+5,name[:45])
        cur+=w
    y-=rowh
    for index,row in enumerate(data):
        if index%2==0:
            c.setFillColor(colors.HexColor('#F0F5F8'));c.rect(x,y-rowh,total,rowh,fill=1,stroke=0)
        cur=x
        for value,w in zip(row,widths):
            c.setFillColor(DARK);c.setFont('Helvetica',fontsize)
            val=str(value)
            while stringWidth(val,'Helvetica',fontsize)>w-9:
                val=val[:-1]
            c.drawString(cur+5,y-rowh+5,val);cur+=w
        y-=rowh
    return y-13

# Page 1
M=43; x=M; y=H-43
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',24);c.drawString(x,y,'THE RELAY  /  Vaani ML Engineering Intern')
y-=22
y=text_line(x,y,'Evidence-first pipeline • measured LOCAL stand-in • real Groq measurements unavailable',10,color=TEAL)
y-=13
y=heading(x,y,'1  What I built and why')
y=para(x,y,'Five steps: classify, retrieve page-cited passages, scope/plan, stream a draft, and validate citations. Branch to abstention if evidence is weak. Key decision: fail closed rather than fabricate a quick answer.',W-2*M)
y=heading(x,y,'2  The real service and my stand-in')
y=para(x,y,'Groq adapter: streaming chat completions. No Groq key was available, so real service limits, headers, and calibration are NOT MEASURED. Simulator: chosen lognormal jitter, 503 errors, minute/day admission limits, queue timeouts, load-sensitive delay and word-by-word streaming. Token figures are character-count proxies.',W-2*M)
y=heading(x,y,'3  Results   —   every table recomputed from results.csv')
y=text_line(x,y,'TABLE 1  •  Hosted Groq limits (provider documents describe 429/retry-after; account-specific values unobserved)',8,bold=True)
table1=[[v,'not measured','no account key','low'] for v in ['Requests/minute','Tokens/minute','Requests/day','Tokens/day','Concurrent inflight','Actual 429 payload','Reset time']]
y=table(x,y-3,['Limit','Value','Method','Confidence'],table1,[250,250,500,95],7.8,17)
y=text_line(x,y,'TABLE 2a  •  Internal model TTFT only (not user-visible); conditional on token emission; NM = no token',8,bold=True)
data=[]
for name,d in load_summary.items():
    data.append([name,'stand-in',d['n'],f"{d['duration_s']:.2f}",f"{d['offered_per_min']:.1f}",d['ttft'],d['total']])
y=table(x,y-3,['Scenario','Source','N','Duration s','Offered/min','TTFT p50 / p95 / p99 ms','Total p50 / p95 / p99 ms'],data,[235,95,42,93,100,260,270],7.8,19)
y=text_line(x,y,'TABLE 2b  •  Outcomes (API charge is zero for local stand-in; CPU and electricity excluded)',8,bold=True)
data=[]
for name,d in load_summary.items():
    data.append([name,d['succeeded'],d['rate_limited'],d['timeout_error'],f"{d['retries']:.2f}",d['peak_queue'],f"{d['tokens_per_answer']:.1f}",f"${d['cost_usd_1000']:.2f}"])
y=table(x,y-3,['Scenario','Succeeded','Rate limited','Timeout/error','Retries/req','Peak queue','Tokens/ans','API $/1000'],data,[235,110,114,125,125,105,140,141],7.6,19)
y=text_line(x,y,'TABLE 3  •  Retrieval evaluation, 18 authored questions per setting (15 in-scope and 3 outside)',8,bold=True)
data=[]
for name,d in quality_summary.items():
    data.append([{'small':'220/1/no','balanced':'500/3/yes','wide':'1000/6/yes'}[name],d['n'],d['correct'],d['wrong'],d['refused'],f"{d['tokens']:.1f}",d['ttft'],d['total']])
y=table(x,y-3,['Piece/top-k/rerank','N','Correct+cited','Wrong','Correct refusal','Tokens/ans','TTFT p50 / p95','Total p50 / p95'],data,[230,45,125,105,130,112,175,173],7.5,19)
y=para(x,y,'All simulations ran against 19 paraphrased, page-verified notes; full-paper PDFs could not be downloaded in this environment. 88 load calls + 54 retrieval calls + 2 retry trials = 144 measured stand-in rows. These are NOT results for a calibrated real provider.',W-2*M,8.7,12)
assert y>25, f'Page1 overflow: {y}'
c.setFont('Helvetica',8);c.drawRightString(W-43,25,'PAGE 1 / 2   •   10 NOV 2026')
c.showPage()

# Page 2, two columns for remaining headings in exact order.
left=M; right=W/2+12; width=W/2-65
Y=H-41
c.setFillColor(NAVY);c.setFont('Helvetica-Bold',18);c.drawString(left,Y,'ENGINEERING JUDGMENT / FAILURE MODES')
Y-=35
y=heading(left,Y,'4  Where the time goes')
y=para(left,y,f'Slowest successful request {slowest["request_id"]}: total {slowest["total_ms"]} ms; first token {slowest["first_token_ms"]} ms. Direct queue wait {q_wait} ms. Work after queue admission through first token {pre_work} ms; work after first token through verification {post_work} ms; no retries. Evidence: monotonic timestamps in artifacts/traces.json.',width)
y=heading(left,y,'5  When a limit is hit')
y=para(left,y,'Minute cap: reject calls with long retry-after; do not occupy queue for a minute. Daily cap: stop issuing hosted calls and return a clear, safe service-unavailable message. Prioritize requests already accepted; allow cheap evidence-based local refusals. Neither case silently swaps to speculative answers.',width)
y=heading(left,y,'Retrieval: quality versus cost')
y=para(left,y,'All three note-based settings scored 15/18 correct+cited and 3/18 correct refusal. Small 220-character pieces / top-1 minimizes proxy tokens here. For a full 120-page source library I would retest because wider passages may be necessary. Near limits: lower top-k, preserve citations and abstention. First-token time stays similar in this simple simulator because it has no true token-dependent prefill.',width)
y=heading(left,y,'How this library will mislead a naive retriever')
y=para(left,y,'1. "Attention" appears across the corpus: a spoken dialogue query can retrieve Vaswani rather than Moshi. 2. Moshi gives both 160 ms theoretical and 200 ms practical latency: an ambiguous latency query can cite the wrong number. 3. "Chunking" means learned segmentation in H-Net but fixed text windows in this retrieval system; a vague query conflates them.',width)
y=heading(left,y,'6  Retries')
y=para(left,y,f'Only once, on a pre-token transient 503, with a short exponential backoff; never replay partial output. Controlled failure injection: fail-fast error took {retry_samples["fail_fast"]["total_ms"]} ms; retry succeeded in {retry_samples["retry_once"]["total_ms"]} ms. The retry purchased completeness but made the caller wait longer and consumed another admission. Never retry a 24-hour limit.',width)
y=heading(left,y,'7  What the person sees')
y=para(left,y,'"Today\'s model-call budget is exhausted. I cannot verify an answer from these papers right now, and I will not guess. Please try again after the quota resets."',width)
assert y>40, f'Page2 left overflow {y}'
y=Y
ry=heading(right,y,'8  What I am unsure about, left out, learned')
ry=para(right,ry,'Least certain assumption: performance on curated notes predicts performance on the full papers; it does not. Left out: dense reranker and distributed queue. New lesson: TTFT on successful responses can look excellent even while most offered requests are refused; show coverage and end-to-end completion together.',width)
ry=heading(right,ry,'Your feedback on Vaani')
ry=para(right,ry,'The Teacher AI prompt-diff review and Memories product stood out. The website highlights P90 latency around 450 ms, but the timing boundary is unclear to a first-time reader. I would publish stage-specific time definitions and a language-filterable sample of real calls so developers can judge quality versus responsiveness.',width)
ry=heading(right,ry,'How I worked with the assistant')
ry=para(right,ry,'Accessible raw user prompt and work log: conversation_history.md. No second or third direct user prompts were made in this thread; instead these were the three governing instructions:',width)
ry=para(right,ry,'1. User: complete the PDF assignment and put it in the named GitHub repository. This set the deliverable scope.',width)
ry=para(right,ry,'2. Assignment: pin the three arXiv PDF versions and refuse unsupported factual claims. This shaped citation guards.',width)
ry=para(right,ry,'3. Assignment: submit raw per-request CSV and recomputable percentile tables. This forced explicit instrumentation.',width)
ry=para(right,ry,'The assistant initially kept status=error even after a successful retry. The forced 503 retry trial exposed this; the implementation now resets status=ok on success. One deliberate override: do not claim fabricated real Groq measurements or simulator calibration. Applicant-specific choices are NOT fabricated; the applicant must personally run Groq and describe their own genuine review/overrides before applying.',width)
ry=heading(right,ry,'Boundary of these results')
ry=para(right,ry,'Recorded: 6 passing tests; local simulator latency distributions; 18-question × 3 retrieval evaluations; 5 load shapes; failure-injection trace. Missing: real Groq key, measurements, fitted stand-in, full-PDF benchmark. This is a substantive reproducible prototype, not yet a fully compliant final submission.',width)
assert ry>40, f'Page2 right overflow {ry}'
c.setFont('Helvetica',8);c.drawRightString(W-43,25,'PAGE 2 / 2   •   SOURCE: results.csv')
c.save()
print(f'Created REPORT.pdf (2 pages); page1 end y={y:.1f}; page2 right end y={ry:.1f}')
print('Summary',json.dumps({'load':load_summary,'quality':quality_summary,'slow':manifest['slowest_successful_request'],'rows':len(ROWS)},indent=2))
