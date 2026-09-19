"""Генератор синтетических данных для демо-аудита онбординга.

Создаёт:
  - data/onboarding_registry.xlsx  — эталон процесса (этапы + чек-листы)
  - data/novices.xlsx              — факты по новичкам (4 листа)

Заложенные дефекты (задача аудита — их найти):
  1. Этап «month-1» не имеет владельца (колонка Владелец пустая).
  2. Этап «day-90» — в чек-листе отсутствует обязательный элемент
     «Критерии эффективности» и нет критериев оценки.
  3. Этап «day-1» — пропущен обязательный элемент «Организация рабочего места».
  4. Файл docs/dogovor-trudovoy.md существует, но ни один элемент чек-листа
     на него не ссылается (невисячий узел).
  5. Данные: норматив этапа «month-1» = 30 дней, фактически у 7 из 10 новичков
     завершение на 39-42 день (систематический пересрок).
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

STAGES = ("preboarding", "day-1", "week-1", "month-1", "day-90")

# ---------------------------------------------------------------- registry
STAGES_DF = pd.DataFrame(
    {
        "№": [1, 2, 3, 4, 5],
        "Этап": list(STAGES),
        "Название": [
            "Подготовка до выхода на работу",
            "Первый рабочий день",
            "Первая неделя",
            "Первый месяц (адаптация)",
            "Девяносто дней (итоговая оценка)",
        ],
        "Владелец": ["HR-отдел", "IT-отдел", "Наставник", "", "Руководитель"],
        "Норматив_дней": [5, 1, 7, 30, 60],
        "Обязателен": ["Да", "Да", "Да", "Да", "Да"],
    }
)

CHECKLIST_DF = pd.DataFrame(
    {
        "№": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "Этап": [
            "preboarding",
            "preboarding",
            "preboarding",
            "day-1",
            "day-1",
            "week-1",
            "week-1",
            "week-1",
            "month-1",
            "month-1",
            "day-90",
            "day-90",
        ],
        "Элемент": [
            "Выдача техники и доступов",
            "Заведение учётной записи",
            "Оформление пропуска",
            "Вводный инструктаж",
            "Знакомство с командой",
            "Назначение наставника",
            "Первая 1:1 встреча",
            "Демонстрация рабочих систем",
            "План развития",
            "Промежуточный 1:1",
            "Итоговая оценка",
            "Анкета обратной связи",
        ],
        "Обязателен": ["Да", "Да", "Нет", "Да", "Да", "Да", "Да", "Да", "Да", "Да", "Да", "Да"],
        "Ссылка_на_документ": [
            "docs/cheklist-preboarding.md",
            "docs/cheklist-preboarding.md",
            "docs/cheklist-preboarding.md",
            "docs/cheklist-day-1.md",
            "docs/cheklist-day-1.md",
            "docs/cheklist-week-1.md",
            "docs/cheklist-week-1.md",
            "docs/cheklist-week-1.md",
            "docs/cheklist-month-1.md",
            "docs/cheklist-month-1.md",
            "docs/cheklist-day-90.md",
            "docs/cheklist-day-90.md",
        ],
    }
)

# ------------------------------------------------------------- novices
NOVICE_NAMES = [
    ("Иванов А.", "Менеджер"),
    ("Петрова Е.", "Бухгалтер"),
    ("Сидоров К.", "Юрист"),
    ("Кузнецова М.", "Специалист закупок"),
    ("Смирнов Д.", "Аналитик"),
    ("Орлова Н.", "HR-специалист"),
    ("Волков П.", "Тендерный специалист"),
    ("Фёдорова Л.", "Финансист"),
    ("Морозов И.", "Экономист"),
    ("Никитина С.", "Секретарь"),
]

START = pd.Timestamp("2025-09-01")

# фактические сдвиги (в днях от старта) по каждому этапу:
# preboarding завершается ДО старта (минус), day-1 в день старта,
# week-1 ~ +6..8, month-1: 7 человек +39..42 (дефект), трое +26..29,
# day-90: 7 человек +92..95, трое +87..90
SHIFTS = {
    "preboarding": lambda i: -(i % 3) - 2,
    "day-1": lambda i: 0 if i % 2 == 0 else 1,
    "week-1": lambda i: 6 + (i % 3),
    "month-1": lambda i: (39 + i % 4) if i < 7 else (26 + i % 4),
    "day-90": lambda i: (92 + i % 4) if i < 7 else (87 + i % 4),
}

profiles, schedule, scores = [], [], []
for i, (name, role) in enumerate(NOVICE_NAMES):
    nid = f"N-{i + 1:02d}"
    dept = {
        "Менеджер": "Коммерческий",
        "Бухгалтер": "Финансы",
        "Юрист": "Юридический",
        "Специалист закупок": "Закупки",
        "Аналитик": "Аналитика",
        "HR-специалист": "HR",
        "Тендерный специалист": "Тендеры",
        "Финансист": "Финансы",
        "Экономист": "Планирование",
        "Секретарь": "АУП",
    }[role]
    profiles.append((nid, name, role, dept, START))
    for stage in STAGES:
        if stage == "day-90" and i >= 8:
            continue  # дефект отсева: N-09 и N-10 не доведены до итогового этапа
        day = SHIFTS[stage](i)
        date = (START + pd.Timedelta(days=day)).strftime("%Y-%m-%d")
        schedule.append((nid, stage, date))

    # bal-л наставника 1..5: у пересроченных месяц-1 ниже по вопросу «План развития»
    base = 5 if i >= 7 else (3 + i % 3)  # у первых 7 (дефектных) ниже
    scores.append((nid, "month-1", min(base, 5), "дельта по срокам" if i < 7 else ""))
    scores.append((nid, "day-90", 4 if i < 3 else 4 + i % 2, "итог"))


def as_dates(rows):
    return [(a, b, c, d, pd.Timestamp(e)) for a, b, c, d, e in rows]


PROFILES_DF = pd.DataFrame(
    as_dates(profiles),
    columns=["ID", "ФИО", "Роль", "Департамент", "Дата_старта"],
)

SCHEDULE_DF = pd.DataFrame(schedule, columns=["ID", "Этап", "Дата_завершения"])
SCHEDULE_DF["Дата_завершения"] = pd.to_datetime(SCHEDULE_DF["Дата_завершения"])

SCORES_DF = pd.DataFrame(scores, columns=["ID", "Этап", "Балл", "Комментарий"])

# анкеты: низкие баллы по «План развития» у первых 7 (совпадает с пересроком)
QUESTIONS = [
    "План развития был понятен?",
    "Наставник оказывал поддержку?",
    "Этапы онбординга прошли в срок?",
    "Готовность к работе через 90 дней?",
]
ANKE_DF_rows = []
for i, (name, _) in enumerate(NOVICE_NAMES):
    nid = f"N-{i + 1:02d}"
    q2 = 2 if i < 7 else 4          # план развития — низкий у пересроченных
    q3 = 2 if i < 7 else 4          # сроки — низкий у пересроченных
    q1 = 4 if i < 7 else 5
    q4 = 3 if i < 7 else 4
    text2 = "План развития не предоставлен в первый месяц" if i < 7 else "Всё понятно"
    ANKE_DF_rows.extend(
        [
            (nid, QUESTIONS[0], q1, text2),
            (nid, QUESTIONS[1], q2, ""),
            (nid, QUESTIONS[2], q3, "Этап месяц-1 затянулся" if i < 7 else ""),
            (nid, QUESTIONS[3], q4, ""),
        ]
    )
ANKET_DF = pd.DataFrame(ANKE_DF_rows, columns=["ID", "Вопрос", "Балл", "Текст"])


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    registry_path = DATA / "onboarding_registry.xlsx"
    novices_path = DATA / "novices.xlsx"
    with pd.ExcelWriter(registry_path, engine="openpyxl") as w:
        STAGES_DF.to_excel(w, sheet_name="Этапы", index=False)
        CHECKLIST_DF.to_excel(w, sheet_name="Чек-листы", index=False)
    with pd.ExcelWriter(novices_path, engine="openpyxl") as w:
        PROFILES_DF.to_excel(w, sheet_name="Профили", index=False)
        SCHEDULE_DF.to_excel(w, sheet_name="Сроки", index=False)
        SCORES_DF.to_excel(w, sheet_name="Оценки", index=False)
        ANKET_DF.to_excel(w, sheet_name="Анкеты", index=False)
    print(f"OK: {registry_path}")
    print(f"OK: {novices_path}")


if __name__ == "__main__":
    main()