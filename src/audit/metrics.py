"""Ядро метрик аудита онбординга.

Все расчёты — детерминированные pandas-выражения над данными,
загруженными excel_parser. Никаких «ощущений»: каждая метрика имеет
формулу и смысл. Результат сериализуется в JSON (audit_metrics.json)
и переиспользуется агентами и отчётчиками.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from src.ingest.excel_parser import OnboardingData

FRAMEWORK_STAGES = ["preboarding", "day-1", "week-1", "month-1", "day-90"]


def measure(data: OnboardingData, docs_dir: Path | None = None) -> dict:
    """Возвращает полный словарь метрик по данным онбординга."""
    stages = data.stages.set_index("Этап")
    total_novices = len(data.profiles)
    start_by_id = dict(zip(data.profiles["ID"], data.profiles["Дата_старта"]))

    # 1-2. покрытие этапов и владельцев
    present = [s for s in FRAMEWORK_STAGES if s in stages.index]
    framework_coverage = len(present) / len(FRAMEWORK_STAGES)
    owner_coverage = (
        stages["owner"].str.len() > 0
    ).sum() / len(stages)

    # 3. полнота обязательного чек-листа (ссылки на документы существуют)
    checklist = data.checklist
    mandatory = checklist.loc[checklist["mandatory"]]
    if docs_dir is not None:
        exist_refs = mandatory["doc_ref"].map(
            lambda r: (docs_dir / Path(r).name).exists() if r else False
        )
        checklist_completeness = float(exist_refs.mean()) if len(mandatory) else 1.0
    else:
        checklist_completeness = (
            float((mandatory["doc_ref"] != "").mean()) if len(mandatory) else 1.0
        )

    # 4. сроки: дельта, доля пересрока, доведённость по этапам
    by_stage: dict[str, dict] = {}
    for stage in FRAMEWORK_STAGES:
        if stage not in stages.index:
            by_stage[stage] = {"reached_share": 0.0}
            continue
        norm = float(stages.at[stage, "norm_days"])
        rows = data.schedule.loc[data.schedule["Этап"] == stage]
        if rows.empty:
            by_stage[stage] = {
                "norm_days": norm,
                "reached_share": 0.0,
                "mean_fact_days": None,
                "mean_delta_days": None,
                "share_late": 0.0,
            }
            continue
        fact_days = (rows.set_index(rows.index)["Дата_завершения"] - pd.Series(
            [start_by_id[i] for i in rows["ID"]], index=rows.index
        )).dt.days
        late = (fact_days > norm).mean()
        by_stage[stage] = {
            "norm_days": norm,
            "reached_share": float(len(rows) / total_novices),
            "mean_fact_days": float(fact_days.mean()),
            "mean_delta_days": float(fact_days.mean() - norm),
            "share_late": float(late),
        }

    late_rows = [v for v in by_stage.values() if v.get("mean_fact_days") is not None]
    overall_delay = (
        sum(v["mean_delta_days"] for v in late_rows) / len(late_rows) if late_rows else 0.0
    )

    # 5. удовлетворённость (анкеты обратной связи)
    satisfaction = float(data.ankets["Балл"].mean())
    satisfaction_by_question = (
        data.ankets.groupby("Вопрос")["Балл"].mean().round(2).to_dict()
    )

    # 6. граф документов (плотность + «невисячие» узлы)
    doc_stats = _measure_docs(docs_dir, checklist)

    metrics = {
        "framework_coverage": round(framework_coverage, 3),
        "owner_coverage": round(owner_coverage, 3),
        "owners_without_owner": [
            s for s in FRAMEWORK_STAGES if s in stages.index and stages.at[s, "owner"] == ""
        ],
        "checklist_completeness": round(checklist_completeness, 3),
        "checklist_by_stage": {
            s: int(((checklist["Этап"] == s) & checklist["mandatory"]).sum())
            for s in FRAMEWORK_STAGES
        },
        "timeline": by_stage,
        "overall_": {
            "mean_delta_days": round(overall_delay, 2),
            "n_stages": int(len(stages)),
            "n_novices": int(total_novices),
        },
        "satisfaction": {
            "mean": round(satisfaction, 2),
            "by_question": satisfaction_by_question,
        },
        "doc_graph": doc_stats,
    }
    return metrics


def _measure_docs(docs_dir: Path | None, checklist: pd.DataFrame) -> dict:
    """Плотность графа документов и список «невисячих» узлов.

    «Невисячий узел» — документ в docs/, на который не ссылается
    ни один элемент чек-листа (нет связи с процессом).
    """
    if docs_dir is None or not docs_dir.exists():
        return {"n_docs": 0, "mean_wikilinks": 0.0, "orphan_docs": []}

    referenced = set()
    for r in checklist["doc_ref"]:
        if r:
            referenced.add(Path(r).name)

    wikilinks = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
    orphans, links_per_doc = [], []
    for doc in sorted(docs_dir.glob("*.md")):
        text = doc.read_text(encoding="utf-8", errors="ignore")
        links_per_doc.append(len(wikilinks.findall(text)))
        if doc.name not in referenced:
            orphans.append(doc.name)

    return {
        "n_docs": len(links_per_doc),
        "mean_wikilinks": round(
            sum(links_per_doc) / len(links_per_doc), 2
        ) if links_per_doc else 0.0,
        "orphan_docs": orphans,
    }


def save_metrics(
    data: OnboardingData,
    docs_dir: Path,
    out_path: Path,
) -> Path:
    """Считает и записывает метрики в JSON, возвращает путь."""
    metrics = measure(data, docs_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path