"""[отчёт MD] Полный аудиторский отчёт онбординга в Markdown.

Markdown — «источник истины» отчёта; DOCX и PPTX строятся из тех же данных.
"""
from __future__ import annotations

from datetime import datetime

from src.audit.model import SEVERITY_ORDER
from src.audit.orchestrator import OrchestrationResult
from src.ingest.excel_parser import OnboardingData

STAGE_LABEL = {
    "preboarding": "Preboarding",
    "day-1": "День 1",
    "week-1": "Неделя 1",
    "month-1": "Месяц 1",
    "day-90": "90 дней",
}


def render(data: OnboardingData, metrics: dict, res: OrchestrationResult) -> str:
    lines: list[str] = []
    a = lines.append

    a("# Отчёт ИИ-аудита процесса онбординга")
    a("")
    a(f"*Сформировано:* {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    a(f"*Источники:* onboarding_registry.xlsx, novices.xlsx, docs/")
    a(f"*Новичков в выборке:* {metrics['overall_']['n_novices']}")
    a("")

    # 1. Резюме
    a("## 1. Резюме аудита")
    a("")
    n_crit = len(res.report.critical)
    n_warn = len(res.report.warnings)
    a(
        f"Обнаружено **{n_crit} критических** и **{n_warn} предупреждений**."
        if n_crit
        else f"Обнаружено **{n_warn} предупреждений**, критических нет."
    )
    a("")
    a("Процесс охватывает 5 базовых этапов адаптации, но систематически "
      "нарушается на этапах «Месяц 1» и «90 дней».")
    a("")

    # 2. Оценка по этапам
    a("## 2. Оценка по этапам")
    a("")
    a("| Этап | Владелец | Норматив | Факт (среднее) | Пересрок | Доведённость | Вердикт |")
    a("|---|---|---|---|---|---|---|")
    tl = metrics["timeline"]
    for stage in tl:
        st = tl[stage]
        owner = data.stages.set_index("Этап").at[stage, "owner"] or "—"
        norm = f"{st['norm_days']:g}" if st.get("norm_days") is not None else "—"
        fact = f"{st['mean_fact_days']:.1f}" if st.get("mean_fact_days") is not None else "—"
        late = f"{st.get('share_late', 0.0):.0%}"
        reached = f"{st.get('reached_share', 0.0):.0%}"
        a(f"| {STAGE_LABEL[stage]} | {owner} | {norm} дн. | {fact} дн. | {late} | {reached} | {res.verdicts[stage]} |")
    a("")

    # 3. Метрики
    seen = []
    a("## 3. Ключевые метрики")
    a("")
    a(f"- Покрытие фреймворка этапов: **{metrics['framework_coverage']:.0%}**")
    a(f"- Этапы с назначенным владельцем: **{metrics['owner_coverage']:.0%}**")
    a(f"- Полнота обязательного чек-листа: **{metrics['checklist_completeness']:.0%}**")
    a(f"- Средняя удовлетворённость (анкеты 1–5): **{metrics['satisfaction']['mean']:g}**")
    a(f"- Средняя дельта сроков по этапам: **{metrics['overall_']['mean_delta_days']:+.1f} дн.**")
    a(f"- Среднее число связей документа: **{metrics['doc_graph']['mean_wikilinks']:g}**")
    a("")

    # 4. Узкие места
    a("## 4. Узкие места (топ-5)")
    a("")
    for f in res.report.top_issues(5):
        a(f"- **{f.stage or 'процесс'}** — {f.title}: {f.detail}")
    a("")

    # 5. Риски
    a("## 5. Риски")
    a("")
    a(_risks(res))
    a("")

    # 6. Рекомендации
    a("## 6. Рекомендации (план действий)")
    a("")
    a("| Приоритет | Проблема | Действие | Владелец | Срок |")
    a("|---|---|---|---|---|")
    for r in res.recommendations:
        sev = "Высокий" if r["severity"] == "critical" else "Средний"
        a(f"| {sev} | {r['problem']} | {r['action']} | {r['owner']} | {r['deadline']} |")
    a("")

    # 7. Приложения
    a("## 7. Приложения")
    a("")
    a("### 7.1. Источники данных")
    a("")
    a("- `data/onboarding_registry.xlsx` — эталон процесса (этапы, чек-листы)")
    a("- `data/novices.xlsx` — фактические данные новичков")
    a("- `docs/` — документы онбординга")
    a("")
    a("### 7.2. Структурные проблемы данных")
    a("")
    if data.issues:
        for i in data.issues:
            a(f"- [{i['severity']}] {i.get('stage', 'все')}: {i['message']}")
    else:
        a("- Не обнаружено.")
    a("")
    a("### 7.3. Все находки команды агентов")
    a("")
    a("| Агент | Этап | Серьёзность | Находка |")
    a("|---|---|---|---|")
    for f in sorted(res.report.findings, key=lambda x: (SEVERITY_ORDER.get(x.severity, 9), x.priority)):
        a(f"| {f.agent} | {f.stage or '—'} | {f.severity} | {f.title} |")
    a("")

    return "\n".join(lines)


def _risks(res: OrchestrationResult) -> str:
    risk_lines = []
    for f in res.report.critical:
        stage = f.stage or "процесс"
        if "Владелец" in f.title or "ответственн" in f.title or "Проблема данных" in f.title:
            text = (
                f"- **{stage}**: без назначенной ответственности этап рискует "
                "выполняться хаотично и без контроля сроков."
            )
        elif "Отсев" in f.title:
            text = (
                f"- **{stage}**: продолжение отсева означает потерю новичков "
                "и рост стоимости найма (ре-найм, повторный онбординг)."
            )
        else:
            text = f"- **{stage}**: {f.title.lower()}."
        if text not in risk_lines:
            risk_lines.append(text)
    if not risk_lines:
        return "Критических рисков не выявлено."
    return "\n".join(risk_lines)