"""Общая модель данных аудита: находка и итоговый отчёт."""
from dataclasses import dataclass, field

SEVERITY_ORDER = {"critical": 0, "warning": 1, "ok": 2}

VERDICT_MAP = {"critical": "❌", "warning": "⚠️", "ok": "✅"}


@dataclass
class Finding:
    agent: str
    stage: str | None
    severity: str  # critical | warning | ok
    title: str
    detail: str
    priority: int = 1  # 1 — высший

    def key(self) -> str:
        return f"{self.stage}|{self.title}".lower()


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)

    @property
    def critical(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "critical"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def ok(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ok"]

    def stage_verdicts(self, stages: list[str]) -> dict[str, str]:
        """Вердикт этапа по худшей серьёзности его находок."""
        verdicts: dict[str, str] = {}
        for stage in stages:
            worst = "ok"
            for f in self.findings:
                if f.stage != stage:
                    continue
                if SEVERITY_ORDER[f.severity] < SEVERITY_ORDER[worst]:
                    worst = f.severity
            verdicts[stage] = VERDICT_MAP.get(worst, "✅")
        return verdicts

    def top_issues(self, n: int = 3) -> list[Finding]:
        ordered = sorted(self.findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.priority))
        return [f for f in ordered if f.severity != "ok"][:n]