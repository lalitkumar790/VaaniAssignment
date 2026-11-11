"""Assemble immutable V1-V5 raw evidence into the required results.csv.

Reads two downloaded, pinned GitHub Actions run artifacts. It never synthesizes a
measurement or discards a historical error record. Idempotent on repeated calls.
"""
from pathlib import Path
import csv
import shutil
import json
from collections import Counter
from datetime import date

ROOT=Path(__file__).resolve().parent
FIELDS=["request_id","scenario","source","start_time","first_token_ms","total_ms","status","retries","tokens_in","tokens_out","retrieval_setting","answer_grade","queue_peak_observed","cost_usd"]

def load(path):
    with Path(path).open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=FIELDS:
            raise ValueError(f"Schema changed in {path}: {reader.fieldnames}")
        return list(reader)

base=load(ROOT/"results.csv")
sources=[
    ("v4",ROOT/"_downloaded"/"v4"/"artifacts"/"v4_fullpdf_quality_results.csv"),
    ("v5",ROOT/"_downloaded"/"v5"/"artifacts"/"v5_real_results.csv")
]
seen={r["request_id"] for r in base}
for prefix,path in sources:
    assert path.is_file(),f"Missing run artifact {path}"
    incoming=load(path)
    assert len(incoming)==(54 if prefix=="v4" else 18)
    for record in incoming:
        row=dict(record)
        row["request_id"]=prefix+"-"+row["request_id"]
        row["scenario"]=prefix+"_"+row["scenario"]
        if row["request_id"] in seen:
            continue
        seen.add(row["request_id"])
        base.append(row)
assert len(base)==519,(len(base),Counter(r["scenario"] for r in base))
assert len(seen)==519,"Duplicate request ids in merged raw results"
assert sum(r["scenario"]=="v5_real_modest" for r in base)==18
assert sum(r["scenario"].startswith("v4_retrieval_") for r in base)==54

with (ROOT/"results.csv").open("w",newline="",encoding="utf-8") as f:
    writer=csv.DictWriter(f,fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(base)
for prefix,_ in sources:
    source=ROOT/"_downloaded"/prefix/"artifacts"
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item,ROOT/"artifacts"/item.name)
# Paper manifest shared across all pinned version runs.
latest_manifest=ROOT/"_downloaded"/"v5"/"data"/"papers"/"manifest.json"
if latest_manifest.exists():
    shutil.copy2(latest_manifest,ROOT/"data"/"papers"/"manifest.json")

v5=[x for x in base if x["scenario"]=="v5_real_modest"]
v4=[x for x in base if x["scenario"].startswith("v4_retrieval_")]
v5grade=Counter(x["answer_grade"] for x in v5)
v4grade=Counter(x["answer_grade"] for x in v4)
assert len(v5)==18 and len(v4)==54

summary={
    "date":"2026-11-11",
    "rows":len(base),
    "v5_run_id":42970031360,
    "v4_full_pdf_run_id":42969980873,
    "v5_status":dict(Counter(x["status"] for x in v5)),
    "v5_strict_grades":dict(v5grade),
    "v4_strict_grades":dict(v4grade),
}
(ROOT/"artifacts"/"final_merge_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
print("MERGE_SUMMARY="+json.dumps(summary,sort_keys=True))
