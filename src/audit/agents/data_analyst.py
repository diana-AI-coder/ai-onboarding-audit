"""[A2] Данные-аналитик: сроки, доведённость, удовлетворённость.

Интерпретирует цифры ядра метрик. Каждая находка — с конкретными
числами: дельта, доля пересрока, доля отсева.
"""
from src.audit.model import Finding

AGENT = "data_analyst"


def analyze(data, metrics: dict) -> list[Finding]:
    findings: list[Finding] = []
    timeline = metrics.get("timeline", {})

    for stage, st in timeline.items():
        if st.get("mean_fact_days") is None:
            continue
        norm = st["norm_days"]
        share_late = st.get("share_late", 0.0)
        delta = st.get("mean_delta_days", 0.0)

        if share_late >= 0.5:
            findings.append(
                Finding(
                    agent=AGENT,
                    stage=stage,
                    severity="warning",
                    title="Систематический пересрок этапа",
                    detail=f"Норматив {norm:g} дн., средний факт "
                    f"{st['mean_fact_days']:g} дн. (дельта {delta:+.1f} дн.). "
                    f"Пересрок у {share_late:.0%} новичков — это систематика, "
                    f"а не случайность.",
                )
            )
        elif share_late >= 0.15:
            findings.append(
                Finding(
                    agent=AGENT,
                    stage=stage,
                    severity="ok",
                    title="Локальные отклонения сроков",
                    detail=f"Пересрок у {share_late:.0%} новичков "
                    f"(дельта {delta:+.1f} дн.) — эпизодически, не систематика.",
                )
            )

        reached = st.get("reached_share", 1.0)
        if reached < 1.0:
            ratio = round((1 - reached) * metrics["overall_"]["n_novices"])
            findings.append(
                Finding(
                    agent=AGENT,
                    stage=stage,
                    severity="critical" if ratio >= 2 else "warning",
                    title="Отсев новичков на этапе",
                    detail=f"Доведённость этапа {reached:.0%} — {int(ratio)} из "
                    f"{metrics['overall_']['n_novices']} новичков не прошли "
                    f"этап (нет даты завершения).",
                )
            )

    # удовлетворённость: вопросы ниже среднего
    sat = metrics.get("satisfaction", {})
    q_low = [
        (q, v) for q, v in sat.get("by_question", {}).items() if v < 3.0
    ]
    if q_low:
        worst = min(q_low, key=lambda x: x[1])
        findings.append(
            Finding(
                agent=AGENT,
                stage=None,
                severity="warning",
                title="Низкая удовлетворённость процесса",
                detail=f"Средний балл анкет {sat.get('mean', 0):g}. Вопросы ниже 3.0: "
                f"{', '.join(f'«{q}» — {v:g}' for q, v in sorted(q_low, key=lambda x: x[1]))}. "
                f"Минимальный балл у «{worst[0]}» ({worst[1]:g}).",
            )
        )

    return findings