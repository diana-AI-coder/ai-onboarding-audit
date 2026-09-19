"""[отчёт PPTX] Презентация отчёта аудита для руководства (officecli).

10 слайдов: титул, методология, общая оценка, карта этапов, узкие места,
риски, рекомендации, план действий, источники, следующие шаги.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.audit.orchestrator import OrchestrationResult
from src.ingest.excel_parser import OnboardingData
from src.output._officecli import run

STAGE_LABEL = {
    "preboarding": "Preboarding",
    "day-1": "День 1",
    "week-1": "Неделя 1",
    "month-1": "Месяц 1",
    "day-90": "90 дней",
}


def _add_slide(pptx: Path, title: str, text: str | None = None) -> None:
    args = ["add", str(pptx), "/", "--type", "slide", "--prop", f"title={title}"]
    if text:
        args += ["--prop", f"text={text}"]
    run(args)


def build(data: OnboardingData, metrics: dict, res: OrchestrationResult, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    run(["create", str(out_path)])

    today = datetime.now().strftime("%d.%m.%Y")

    # 1. Титул
    _add_slide(
        out_path,
        "ИИ-аудит процесса онбординга",
        f"Заключение для руководства\n{metrics['overall_']['n_novices']} новичков в выборке · {today}\nСистема: мультиагентный аудит (4 роли) + RAG по документам",
    )

    # 2. Методология
    _add_slide(
        out_path,
        "Как проводился аудит",
        "· Эталон процесса: реестр этапов и чек-листов (Excel)\n"
        "· Факты: сроки, оценки наставников, анкеты новичков\n"
        "· Стандарты: ГОСТ Р ИСО 9001 + HR best practices\n"
        "· Команда агентов: HR-эксперт, данные-аналитик, комплаенс, рекомендатор",
    )

    # 3. Общая оценка
    m = metrics
    _add_slide(
        out_path,
        "Общая оценка процесса",
        f"· Критических находок: {len(res.report.critical)} · Предупреждений: {len(res.report.warnings)}\n"
        f"· Покрытие фреймворка этапов: {m['framework_coverage']:.0%}\n"
        f"· Этапы с владельцем: {m['owner_coverage']:.0%}\n"
        f"· Средняя дельта сроков: {m['overall_']['mean_delta_days']:+.1f} дн.\n"
        f"· Удовлетворённость новичков: {m['satisfaction']['mean']:g} из 5",
    )

    # 4. Карта этапов
    rows = []
    tl = metrics["timeline"]
    for stage in tl:
        st = tl[stage]
        owner = data.stages.set_index("Этап").at[stage, "owner"] or "—"
        late = f"{st.get('share_late', 0.0):.0%}"
        rows.append(f"{STAGE_LABEL[stage]} | владелец: {owner} | пересрок: {late} | {res.verdicts[stage]}")
    _add_slide(out_path, "Карта этапов онбординга", "\n".join(rows))

    # 5. Узкие места
    issues = [f"· {f.stage or 'процесс'}: {f.title} — {f.detail}" for f in res.report.top_issues(4)]
    _add_slide(out_path, "Узкие места", "\n".join(issues))

    # 6. Риски
    risks = []
    for f in res.report.critical:
        if "Владелец" in f.title or "ответственн" in f.title:
            risks.append(f"· {f.stage or 'процесс'} — этап без назначенной ответственности")
        elif "Отсев" in f.title:
            risks.append(f"· {f.stage or 'процесс'} — риск отсева новичков и повторного найма")
        else:
            risks.append(f"· {f.stage or 'процесс'} — {f.title.lower()}")
    _add_slide(out_path, "Риски", "\n".join(dict.fromkeys(risks)) or "Критических рисков не выявлено")

    # 7. Рекомендации
    recs = [f"· [{r['severity']}] {r['problem']} — {r['action']}" for r in res.recommendations]
    _add_slide(out_path, "Рекомендации", "\n".join(recs))

    # 8. План действий
    plan = [f"· {r['owner']} · {r['deadline']}: {r['action']}" for r in res.recommendations]
    _add_slide(out_path, "План действий", "\n".join(plan))

    # 9. Источники
    _add_slide(
        out_path,
        "Источники и данные",
        f"· Синтетическая выборка {metrics['overall_']['n_novices']} новичков\n"
        "· Документы: docs/ (чек-листы онбординга)\n"
        "· Структурные проблемы данных: см. отчёт (раздел 7.2)",
    )

    # 10. Следующие шаги
    _add_slide(
        out_path,
        "Следующие шаги",
        "· Назначить владельца этапа «Месяц 1» (1 неделя)\n"
        "· Ввести контроль прохождения этапов и уведомления (2 недели)\n"
        "· Разработать критерии оценки «90 дней» (1 месяц)\n"
        "· Разобрать низкие баллы анкет и запустить повторный аудит",
    )

    run(["save", str(out_path)])
    return out_path