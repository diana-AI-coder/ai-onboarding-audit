"""Тесты оркестратора: полнота покрытия, вердикты, рекомендации."""
from pathlib import Path

from src.audit import metrics as m
from src.audit import orchestrator as o
from src.ingest import excel_parser as ep

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"


def load_ctx():
    data = ep.load(DATA)
    met = m.measure(data, DOCS)
    return data, met


def test_full_coverage():
    data, met = load_ctx()
    res = o.run(data, met, data.issues, DOCS)
    assert res.coverage_gaps == []
    assert o.coverage_summary(res).startswith("Покрытие полное")


def test_verdicts_expected():
    data, met = load_ctx()
    res = o.run(data, met, data.issues, DOCS)
    assert res.verdicts["month-1"] == "❌"  # нет владельца + пересрок
    assert res.verdicts["day-90"] == "❌"   # отсев + нет критериев
    assert res.verdicts["preboarding"] == "✅"
    assert res.verdicts["day-1"] == "⚠️"   # пропущен обязательный элемент


def test_findings_present_for_all_stages():
    data, met = load_ctx()
    res = o.run(data, met, data.issues, DOCS)
    stages_with_findings = {f.stage for f in res.report.findings if f.stage}
    assert {"preboarding", "day-1", "week-1", "month-1", "day-90"} <= stages_with_findings


def test_no_empty_sections_recommendations():
    data, met = load_ctx()
    res = o.run(data, met, data.issues, DOCS)
    assert res.recommendations, "рекомендации не должны быть пустыми"
    for r in res.recommendations:
        assert r["action"] and r["owner"] and r["deadline"]


def test_deduplication_owner_issue():
    data, met = load_ctx()
    res = o.run(data, met, data.issues, DOCS)
    owner_recs = [r for r in res.recommendations if r["problem"] == "Владелец этапа не назначен"]
    assert len(owner_recs) == 1  # HR + комплаенс + данные нашли одно — рекомендация одна


def test_deduplication_same_cluster_cross_stage():
    """«Пересрок» на двух этапах = ОДНА рекомендация, не две одинаковые."""
    from src.audit.agents import recommender
    from src.audit.model import Finding

    findings = [
        Finding(agent="data_analyst", stage="month-1", severity="warning",
                title="Систематический пересрок этапа", detail="70% пересрок"),
        Finding(agent="data_analyst", stage="day-90", severity="warning",
                title="Систематический пересрок этапа", detail="100% пересрок"),
    ]
    recs = recommender.recommend(findings)
    delays = [r for r in recs if r["problem"] == "Систематический пересрок этапа"]
    assert len(delays) == 1