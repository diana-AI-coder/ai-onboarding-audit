"""[A3] Комплаенс-агент: соответствие регламентам и стандартам.

Проверяет обязательность, ответственность и полноту документации
в терминах требований: внутренние регламенты, ГОСТ Р ИСО 9001
(ответственность и полномочия, управление записями, контроль процесса).
"""
from pathlib import Path

from src.audit.model import Finding

AGENT = "compliance"

REQ_OWNER = "ГОСТ Р ИСО 9001: отсутствует назначенная ответственность и полномочия (п. 5.3)"
REQ_CHECKLIST = "Обязательный элемент чек-листа, определённый реестром процесса"


def analyze(data, metrics: dict, structural_issues: list[dict], docs_dir: Path | None = None) -> list[Finding]:
    findings: list[Finding] = []

    # 1. Владелец этапов — требование ответственности и полномочий
    for stage in metrics.get("owners_without_owner", []):
        findings.append(
            Finding(
                agent=AGENT,
                stage=stage,
                severity="critical",
                title="Этап без ответственного (нарушение п. 5.3 ГОСТ Р ИСО 9001)",
                detail=f"Этап «{stage}» не имеет владельца — не выполнено требование "
                f"«ответственность и полномочия»: некому отвечать за сроки, "
                f"критерии и результат этапа.",
            )
        )

    # 2. Обязательные элементы чек-листов по домену
    chk = data.checklist
    day1 = chk.loc[chk["Этап"] == "day-1"]["Элемент"].astype(str)
    if not any(day1.str.contains("места", case=False)):
        findings.append(
            Finding(
                agent=AGENT,
                stage="day-1",
                severity="warning",
                title="Не регламентирован обязательный элемент day-1",
                detail=f"{REQ_CHECKLIST}: «Организация рабочего места» отсутствует "
                f"в чек-листе первого дня — этап формально неполон.",
            )
        )

    day90 = chk.loc[chk["Этап"] == "day-90"]["Элемент"].astype(str)
    if not any(day90.str.contains("критери", case=False)):
        findings.append(
            Finding(
                agent=AGENT,
                stage="day-90",
                severity="warning",
                title="Нет критериев оценки (запись решения не проверяема)",
                detail="ГОСТ Р ИСО 9001 требует записей, подтверждающих результат. "
                "Без критериев эффективности итоговая запись об окончании "
                "испытательного срока не может быть объективно подтверждена.",
            )
        )

    # 3. Ссылочная целостность чек-листов
    completeness = metrics.get("checklist_completeness", 1.0)
    if completeness < 1.0 and docs_dir is not None:
        missing = sorted(
            {
                Path(r).name
                for r in data.checklist["doc_ref"]
                if r and not (docs_dir / Path(r).name).exists()
            }
        )
        findings.append(
            Finding(
                agent=AGENT,
                stage=None,
                severity="warning",
                title="Отсутствуют документы-основания",
                detail=f"Доля существующих ссылок {completeness:.0%}; нет файлов: "
                f"{', '.join(missing[:5]) if missing else '—'}.",
            )
        )

    # 4. Документы, не встроенные в процесс (невисячие узлы)
    orphans = metrics.get("doc_graph", {}).get("orphan_docs", [])
    if orphans:
        findings.append(
            Finding(
                agent=AGENT,
                stage=None,
                severity="warning",
                title="Документы не встроены в процесс",
                detail="ГОСТ Р ИСО 9001: записи должны быть прослеживаемы. "
                f"Документы, на которые не ссылается ни один чек-лист: "
                f"{', '.join(orphans)} — невисячие узлы в графе знаний.",
            )
        )

    # 5. Структурные проблемы данных (из excel_parser)
    sev_map = {"high": "critical", "medium": "warning", "low": "ok"}
    for iss in structural_issues:
        findings.append(
            Finding(
                agent=AGENT,
                stage=iss.get("stage"),
                severity=sev_map.get(iss.get("severity", ""), "warning"),
                title=f"Проблема данных: {iss.get('subject', '')}",
                detail=iss.get("message", ""),
            )
        )

    return findings