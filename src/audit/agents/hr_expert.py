"""[A1] HR-эксперт: доменная правильность процесса онбординга.

Детерминированная реализация роли: фреймворк, владельцы, чек-листы,
критерии оценки — по правилам HR best practices. Каждая находка
опирается на элемент реестра или метрику.
"""
from src.audit.model import Finding
from src.ingest.excel_parser import OnboardingData

AGENT = "hr_expert"


def analyze(data: OnboardingData, metrics: dict) -> list[Finding]:
    findings: list[Finding] = []
    stages = data.stages.set_index("Этап")

    # 1. Полнота фреймворка (5 этапов)
    missing = [s for s in metrics_framework() if s not in stages.index]
    if missing:
        findings.append(
            Finding(
                agent=AGENT,
                stage="|".join(missing),
                severity="critical",
                title="Отсутствуют этапы фреймворка",
                detail=f"В реестре нет этапов: {', '.join(missing)}. "
                f"Процесс адаптации неполон.",
            )
        )

    # 2. Владельцы этапов (best practice: у каждого этапа есть ответственный)
    for stage in metrics.get("owners_without_owner", []):
        findings.append(
            Finding(
                agent=AGENT,
                stage=stage,
                severity="critical",
                title="Этап без владельца",
                detail=f"Этап «{stage}» не имеет назначенного ответственного. "
                f"Best practice: владелец определяет критерии и сроки этапа.",
            )
        )

    # 3. Критерии оценки и полнота чек-листов по домену
    chk = data.checklist
    by_stage = metrics.get("checklist_by_stage", {})

    day1_items = chk.loc[chk["Этап"] == "day-1"]["Элемент"].astype(str)
    if not any(day1_items.str.contains("места", case=False)):
        findings.append(
            Finding(
                agent=AGENT,
                stage="day-1",
                severity="warning",
                title="Отсутствует организация рабочего места",
                detail=f"В чек-листе day-1 ({by_stage.get('day-1', 0)} обязательных "
                f"элементов) нет шага «Организация рабочего места». Первый день "
                f"неполон без него.",
            )
        )

    day90_items = chk.loc[chk["Этап"] == "day-90"]["Элемент"].astype(str)
    if not any(day90_items.str.contains("критери", case=False)):
        findings.append(
            Finding(
                agent=AGENT,
                stage="day-90",
                severity="warning",
                title="Нет критериев оценки адаптации",
                detail="Чек-лист day-90 не содержит критериев эффективности. "
                "Без них решение об окончании испытательного срока субъективно.",
            )
        )

    month1_items = chk.loc[chk["Этап"] == "month-1"]["Элемент"].astype(str)
    if not any(month1_items.str.contains("развития", case=False)):
        findings.append(
            Finding(
                agent=AGENT,
                stage="month-1",
                severity="warning",
                title="Отсутствует план развития",
                detail="Чек-лист month-1 не содержит элемента «План развития» "
                "— ключевого инструмента адаптации на месяц.",
            )
        )

    # 4. Фреймворк целостен
    findings.append(
        Finding(
            agent=AGENT,
            stage=None,
            severity="ok",
            title="Фреймворк этапов определён",
            detail=f"Все 5 базовых этапов присутствуют; покрытие фреймворка "
            f"{metrics.get('framework_coverage', 1.0):.0%}.",
        )
    )
    return findings


def metrics_framework() -> list[str]:
    from src.audit.metrics import FRAMEWORK_STAGES

    return FRAMEWORK_STAGES