"""Генератор диаграммы архитектуры onboarding-audit.

Пишет `docs/architecture.svg` (векторная, без внешних зависимостей)
и `docs/architecture.mmd` (Mermaid-источник, рендерится на GitHub).
Запуск:  python scripts/gen_architecture_diagram.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

BAND_FILL = "#f2f6fb"
BOX_FILL = "#ffffff"
HEAD_FILL = "#dce8f7"
AGENT_FILL = "#eef4ea"
OUT_FILL = "#fdf3e3"
FONT = "Segoe UI, Arial, sans-serif"
MONO = "Cascadia Mono, Consolas, Courier New, monospace"
W, H = 940, 806


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(x: int, y: int, w: int, h: int, head: str, lines: list[str],
        head_fill: str = HEAD_FILL, body_fill: str = BOX_FILL, mono: bool = False) -> list[str]:
    fam = MONO if mono else FONT
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{body_fill}" '
        f'stroke="#91a7c2" stroke-width="1.4"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="8" fill="{head_fill}" stroke="none"/>',
        f'<rect x="{x}" y="{y+12}" width="{w}" height="14" fill="{head_fill}" stroke="none"/>',
        f'<text x="{x+w//2}" y="{y+18}" text-anchor="middle" '
        f'font-family="{FONT}" font-size="13" font-weight="700" fill="#1d3557">{_esc(head)}</text>',
    ]
    yy = y + 46
    for ln in lines:
        out.append(
            f'<text x="{x+w//2}" y="{yy}" text-anchor="middle" '
            f'font-family="{fam}" font-size="12" fill="#33415c">{_esc(ln)}</text>'
        )
        yy += 18
    return out


def band(x: int, y: int, w: int, h: int, label: str) -> list[str]:
    return [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{BAND_FILL}" stroke="#c5d3e6" stroke-width="1"/>',
        f'<text x="{x+14}" y="{y+24}" font-family="{FONT}" font-size="13" '
        f'font-weight="600" fill="#5a7393">{_esc(label)}</text>',
    ]


def arrow(x1: int, y1: int, x2: int, y2: int, dash: str = "") -> str:
    a = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#5a7393" '
        f'stroke-width="1.5" marker-end="url(#ah)"{a}/>'
    )


def poly(points: str, dash: str = "") -> str:
    a = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{points}" fill="none" stroke="#5a7393" stroke-width="1.5" marker-end="url(#ah)"{a}/>'


def build() -> str:
    r: list[str] = []
    r.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="100%" height="auto" font-family="{FONT}">'
    )
    r.append(
        '<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" '
        'orient="auto"><path d="M0,0L8,3L0,6Z" fill="#5a7393"/></marker></defs>'
    )
    r.append(
        f'<text x="470" y="34" text-anchor="middle" font-family="{FONT}" '
        'font-size="20" font-weight="700" fill="#1d3557">onboarding-audit — архитектура</text>'
    )
    r.append(
        f'<text x="470" y="56" text-anchor="middle" font-family="{MONO}" '
        'font-size="12" fill="#5a7393">источники — метрики — три агента — план действий — отчёты</text>'
    )

    # ---- Запуск (40..154)
    r += band(40, 82, 860, 72, "Запуск")
    r += box(60, 108, 260, 42, "CLI", ["run / verify / serve :8017"], mono=True)
    r += box(360, 108, 300, 42, "n8n webhook", ["POST /audit → pipeline()"], mono=True)
    r += box(700, 108, 180, 42, "HTTP", ["412 / 400 / 500"], mono=True)

    # ---- Источники (182..294)
    r += band(40, 182, 860, 112, "Источники")
    r += box(60, 214, 240, 60, "data/", ["onboarding_registry.xlsx", "novices.xlsx"], mono=True)
    r += box(330, 214, 300, 60, "docs/", ["чек-листы 5 этапов · md", "dogovor-trudovoy.md",
                                          "(RAG-контекст агентам)"], mono=True)
    r += box(670, 214, 210, 60, "model", ["Finding · Metrics", "AuditData · AuditResult"], mono=True)

    # ---- Приём и метрики (322..414)
    r += band(40, 322, 860, 92, "Приём и метрики")
    r += box(60, 354, 240, 54, "excel_parser.load()", ["реестр + новички → AuditData"], mono=True)
    r += box(340, 354, 260, 54, "metrics.measure()", ["сроки · переносы · отсев", "покрытие этапов"], mono=True)
    r += box(660, 354, 220, 54, "prompts/", ["промпты 5 ролей", ".md-инструкции"], mono=True)

    # ---- Агенты (442..554)
    r += band(40, 442, 860, 112, "Агенты анализа (мультиагент, промпты в src/audit/prompts)")
    r += box(60, 474, 250, 72, "hr_expert", ["процесс и план развития", "обязательные элементы"], head_fill="#cfe3cf")
    r += box(345, 474, 250, 72, "data_analyst", ["день 1 · месяц 1 · 90 дней", "пересроки, отсев, скорость"])
    r += box(630, 474, 250, 72, "compliance", ["ГОСТ Р ИСО 9001", "владелец процесса"], head_fill="#e9d8f4")

    # ---- Синтез (578..666)
    r += band(40, 578, 860, 88, "Синтез")
    r += box(60, 610, 240, 52, "Findings", ["находки агентов", "severity + stage"], mono=True)
    r += box(340, 610, 280, 52, "recommender.recommend()", ["кластеризация по смыслу", "план: действие/владелец/срок"], mono=True)
    r += box(660, 610, 220, 52, "AuditResult", ["summary · critical/warnings", "покрытие"], mono=True)

    # ---- Выходы (682..778)
    r += band(40, 682, 860, 96, "Выходы (out_dir / reports)")
    r += box(60, 724, 190, 48, "report_md", ["audit_report.md"], mono=True, body_fill=OUT_FILL)
    r += box(270, 724, 190, 48, "report_docx", ["audit_report.docx", "via officecli"], mono=True, body_fill=OUT_FILL)
    r += box(480, 724, 190, 48, "deck_pptx", ["audit_presentation.pptx"], mono=True, body_fill=OUT_FILL)
    r += box(690, 724, 190, 48, "save_metrics", ["audit_metrics.json"], mono=True, body_fill=OUT_FILL)

    # ---- Стрелки: запуск → источники ----
    r.append(arrow(190, 150, 190, 214))      # CLI → data
    r.append(arrow(460, 150, 210, 214))      # n8n → data
    r.append(arrow(560, 150, 470, 214))      # n8n → docs
    r.append(arrow(660, 129, 700, 129, dash="5,4"))  # n8n → HTTP

    # ---- источники → приём ----
    r.append(arrow(190, 274, 190, 354))      # data → excel_parser
    r.append(arrow(470, 274, 470, 354))      # docs → metrics

    # ---- приём → агенты ----
    r.append(arrow(190, 408, 195, 474))        # excel_parser → hr_expert
    r.append(arrow(470, 408, 470, 474))        # metrics → data_analyst
    r.append(arrow(598, 408, 628, 474))        # metrics → compliance
    r.append(arrow(660, 408, 660, 474))        # prompts → compliance (метка строки ниже)
    r.append(poly("330,230 330,470 310,470", dash="5,4"))        # docs(RAG) → hr_expert
    r.append(poly("630,260 640,408 630,408 630,474", dash="5,4"))  # docs(RAG) → compliance

    # ---- агенты → синтез ----
    r.append(arrow(185, 546, 185, 610))      # hr_expert → findings
    r.append(arrow(470, 546, 300, 610))      # data_analyst → findings
    r.append(arrow(755, 546, 620, 610))      # compliance → recommender
    r.append(arrow(300, 636, 340, 636))      # findings → recommender
    r.append(arrow(620, 636, 660, 636))      # recommender → auditresult

    # ---- синтез → выходы ----
    r.append(arrow(400, 662, 155, 724))      # plan → report_md
    r.append(arrow(480, 662, 365, 724))      # plan → report_docx
    r.append(arrow(560, 662, 575, 724))      # plan → deck_pptx
    r.append(arrow(605, 662, 770, 724))      # plan → save_metrics

    r.append("</svg>")
    return "\n".join(r)


def build_mmd() -> str:
    return """flowchart TB
    CLI["CLI<br/>run / verify / serve :8017"]
    N8N["n8n webhook<br/>POST /audit"]
    DATA[("data/<br/>onboarding_registry.xlsx<br/>novices.xlsx")]
    DOCS[("docs/<br/>чек-листы · dogovor-trudovoy.md")]
    PARSER["excel_parser.load()"]
    METRICS["metrics.measure()"]
    MOD["save_metrics()"]
    HR["hr_expert"]
    DA["data_analyst"]
    CM["compliance"]
    FIND["Findings"]
    REC["recommender.recommend()<br/>план: действие / владелец / срок"]
    RES["AuditResult"]
    MD["report_md<br/>audit_report.md"]
    DOCX["report_docx<br/>audit_report.docx"]
    PPTX["deck_pptx<br/>audit_presentation.pptx"]
    MT["audit_metrics.json"]

    CLI --> DATA
    N8N --> DATA
    N8N --> DOCS
    DATA --> PARSER
    DOCS -.RAG.-> HR
    DOCS -.RAG.-> DA
    DOCS -.RAG.-> CM
    DOCS --> METRICS
    MOD --> METRICS
    PARSER --> METRICS
    METRICS --> HR
    METRICS --> DA
    METRICS --> CM
    HR --> FIND
    DA --> FIND
    CM --> FIND
    FIND --> REC
    REC --> RES
    RES --> MD
    RES --> DOCX
    RES --> PPTX
    RES --> MT
"""


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "architecture.svg").write_text(build(), encoding="utf-8")
    (DOCS / "architecture.mmd").write_text(build_mmd(), encoding="utf-8")
    print("written docs/architecture.svg + docs/architecture.mmd")


if __name__ == "__main__":
    main()