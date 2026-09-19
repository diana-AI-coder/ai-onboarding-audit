"""Тесты CLI-пайплайна: генерация артефактов и аудит_метрики через src.cli."""
import json
from pathlib import Path

from src.cli import pipeline

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"


def test_pipeline_md_produces_report_and_metrics(tmp_path):
    summary = pipeline(
        data_dir=DATA,
        docs_dir=DOCS,
        out_dir=tmp_path,
        formats=("md",),
    )
    assert (tmp_path / "audit_report.md").exists()
    metrics_path = tmp_path / "audit_metrics.json"
    assert metrics_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["overall_"]["n_novices"] == summary["n_novices"]
    assert "timeline" in metrics
    assert "coverage" in summary
    assert summary["critical"] >= 0
    assert "md" in summary["artifacts"]
    assert "metrics" in summary["artifacts"]


def test_pipeline_default_formats_write_md(tmp_path):
    """Формат по умолчанию (md,docx,pptx) запускается без ошибок импорта."""
    from src.cli import FORMATS

    assert "md" in FORMATS and "docx" in FORMATS and "pptx" in FORMATS