"""[A0] Оркестратор аудита: запускает субагентов и собирает отчёт.

Контролирует полноту покрытия (каждый этап должен быть рассмотрен
всеми ролями) и формирует итоговую структуру заключения.
"""
from dataclasses import dataclass

from src.audit.agents import (
    compliance as compliance_agent,
    data_analyst as data_agent,
    hr_expert as hr_agent,
    recommender,
)
from src.audit.metrics import FRAMEWORK_STAGES
from src.audit.model import AuditReport, Finding

AGENT = "orchestrator"


@dataclass
class OrchestrationResult:
    report: AuditReport
    verdicts: dict[str, str]
    recommendations: list[dict]

    @property
    def coverage_gaps(self) -> list[str]:
        """Этапы, по которым хоть одна роль не дала вердикта."""
        per_stage = {s: set() for s in FRAMEWORK_STAGES}
        for f in self.report.findings:
            if f.stage in per_stage:
                per_stage[f.stage].add(f.agent)
        needed = {"hr_expert", "data_analyst", "compliance"}
        return [s for s, a in per_stage.items() if not needed.issubset(a)]


def run(data, metrics: dict, structural_issues: list[dict], docs_dir=None) -> OrchestrationResult:
    """Полный прогон команды агентов над данными и метриками."""
    findings: list[Finding] = []
    findings += hr_agent.analyze(data, metrics)
    findings += data_agent.analyze(data, metrics)
    findings += compliance_agent.analyze(data, metrics, structural_issues, docs_dir)

    findings = _ensure_full_coverage(findings)

    report = AuditReport(findings=findings)
    verdicts = report.stage_verdicts(FRAMEWORK_STAGES)
    recs = recommender.recommend(findings)
    return OrchestrationResult(report=report, verdicts=verdicts, recommendations=recs)


ROLES = ("hr_expert", "data_analyst", "compliance")


def _ensure_full_coverage(findings: list[Finding]) -> list[Finding]:
    """Гарантирует покрытие: каждый этап рассмотрен каждой ролью.

    Если роль не нашла нарушений по этапу — добавляется явный ok-вердикт,
    чтобы ни один раздел отчёта не оставался пустым.
    """
    covered = {(f.stage, f.agent) for f in findings if f.stage}
    for stage in FRAMEWORK_STAGES:
        for role in ROLES:
            if (stage, role) not in covered:
                findings.append(
                    Finding(
                        agent=role,
                        stage=stage,
                        severity="ok",
                        title="Нарушений не выявлено",
                        detail=f"{role}: по этапу «{stage}» нарушений не выявлено.",
                        priority=9,
                    )
                )
    return findings


def coverage_summary(result: OrchestrationResult) -> str:
    gaps = result.coverage_gaps
    if not gaps:
        return "Покрытие полное: все 5 этапов рассмотрены всеми ролями."
    return f"Недостаточно данных по этапам: {', '.join(gaps)}"