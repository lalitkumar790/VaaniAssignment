"""Regression checks for the production dashboard's data contract.

These checks intentionally do not claim model quality; they prevent the UI from
silently reporting 0% because of mismatched artifact names or scenario labels.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")
FULLPDF = ROOT / "artifacts" / "v3_fullpdf_quality_results.csv"
RESULTS = ROOT / "results.csv"


def rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_dashboard_uses_versioned_full_pdf_evidence():
    path = "/artifacts/v3_fullpdf_quality_results.csv"
    assert path in PAGE
    assert FULLPDF.is_file()
    assert 'x.scenario==="retrieval_"+name' in PAGE
    assert 'x.scenario==="v3_retrieval_"+name' not in PAGE
    data = rows(FULLPDF)
    assert data
    assert all(record["source"] == "stand-in" for record in data)
    for setting in ("small", "balanced", "wide"):
        group = [r for r in data if r["scenario"] == "retrieval_" + setting]
        assert len(group) == 18
        assert sum(r["answer_grade"] == "correct" for r in group) > 0
        assert all(r["retrieval_setting"] == setting for r in group)


def test_dashboard_latency_denominators_are_comparable():
    assert "emittedTotal" in PAGE
    assert "percentile(x.emittedTotal,50)" in PAGE
    assert "percentile(x.emittedTotal,95)" in PAGE
    data = rows(RESULTS)
    for r in data:
        if not r["first_token_ms"]:
            continue
        assert float(r["first_token_ms"]) <= float(r["total_ms"]) + 0.05


def test_all_five_calibrated_scenarios_present():
    data = rows(RESULTS)
    for label in (
        "cal_steady",
        "cal_burst",
        "cal_sustained_overload",
        "cal_rpm_halved",
        "cal_daily_exhausted",
    ):
        assert any(r["scenario"] == label for r in data)
