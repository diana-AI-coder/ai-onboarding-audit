"""Тесты markdown-отчёта: структура, вердикты и целостность текста."""
from pathlib import Path

from src.audit import metrics as m
from src.audit import orchestrator as o
from src.ingest import excel_parser as ep
from src.output import report_md

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"


def _render() -> str:
    data = ep.load(DATA)
    met = m.measure(data, DOCS)
    res = o.run(data, met, data.issues, DOCS)
    return report_md.render(data, met, res)


def test_report_contains_all_sections():
    md = _render()
    for section in ("## 1. Резюме аудита", "## 2. Оценка по этапам",
                    "## 3. Ключевые метрики", "## 4. Узкие места",
                    "## 5. Риски", "## 6. Рекомендации", "## 7. Приложения"):
        assert section in md


def test_report_verdicts_reflect_audit():
    md = _render()
    assert "| День 1 |" in md and "| Месяц 1 |" in md
    assert "90 дней" in md


def test_report_risks_sentences_are_complete():
    """Финальные фразы рисков не должны обрываться (регрессия обрезки)."""
    md = _render()
    assert "рискует выполняться хаотично" in md
    assert "потерю новичков и рост стоимости найма" in md


def test_recommendations_are_deduplicated():
    """Один кластер проблемы = одна строка плана действий."""
    md = _render()
    table = md.split("## 6. Рекомендации")[1].split("## 7.")[0]
    assert table.count("Систематический пересрок этапа") == 1
    assert table.count("| Средний |") + table.count("| Высокий |") == 7


def test_metrics_jsonline_in_sources():
    md = _render()
    assert "onboarding_registry.xlsx" in md
    assert "novices.xlsx" in md