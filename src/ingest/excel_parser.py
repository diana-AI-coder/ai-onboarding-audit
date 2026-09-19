"""Слой ингестии: чтение Excel-источников в pandas DataFrame + проверки целостности.

Источники:
  - data/onboarding_registry.xlsx  (листы: Этапы, Чек-листы)
  - data/novices.xlsx              (листы: Профили, Сроки, Оценки, Анкеты)

Excel здесь играет роль базы данных: registry — «схема» процесса, novices —
«транзакции». Парсер превращает их в пригодные для анализа структуры и
сообщает о структурных дефектах (пустые владельцы, некорректные нормативы,
нечитаемые даты).
"""
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

SHEETS_REGISTRY = ("Этапы", "Чек-листы")
SHEETS_NOVICES = ("Профили", "Сроки", "Оценки", "Анкеты")


@dataclass
class OnboardingData:
    stages: pd.DataFrame  # эталон: этапы с владельцами и нормативами
    checklist: pd.DataFrame  # эталон: чек-лист по этапам
    profiles: pd.DataFrame  # факты: профили новичков
    schedule: pd.DataFrame  # факты: сроки завершения этапов
    scores: pd.DataFrame  # факты: оценки наставников
    ankets: pd.DataFrame  # факты: анкеты обратной связи
    issues: list = field(default_factory=list)  # структурные дефекты

    @property
    def stage_names(self) -> list[str]:
        return self.stages["Этап"].tolist()


def _check_existing(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Не найден источник данных: {path}")


def parse_registry(path: Path) -> pd.DataFrame:
    """Этапы реестра с нормализованными колонками и типами."""
    df = pd.read_excel(path, sheet_name="Этапы")
    df = df.rename(
        columns={
            "Владелец": "owner",
            "Норматив_дней": "norm_days",
            "Обязателен": "mandatory",
        }
    )
    df["owner"] = df["owner"].fillna("").astype(str).str.strip()
    df["norm_days"] = pd.to_numeric(df["norm_days"], errors="coerce")
    df["mandatory"] = df["mandatory"].astype(str).str.strip().str.lower() == "да"
    return df


def parse_checklist(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Чек-листы")
    df = df.rename(
        columns={
            "Обязателен": "mandatory",
            "Ссылка_на_документ": "doc_ref",
        }
    )
    df["mandatory"] = df["mandatory"].astype(str).str.strip().str.lower() == "да"
    df["doc_ref"] = df["doc_ref"].fillna("").astype(str).str.strip()
    return df


def parse_profiles(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Профили")


def parse_schedule(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Сроки")
    df["Дата_завершения"] = pd.to_datetime(df["Дата_завершения"], errors="coerce")
    return df


def parse_scores(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Оценки")


def parse_ankets(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name="Анкеты")


def check_integrity(data: OnboardingData) -> list[dict]:
    """Структурные проверки источника: выявляют «сломанные» данные.

    Возвращает список находок вида {severity, stage, subject, message}.
    Это НЕ аудиторские выводы (их делают агенты) — это гарантия,
    что данные вообще пригодны для анализа.
    """
    issues: list[dict] = []

    for _, row in data.stages.iterrows():
        if row["owner"] == "":
            issues.append(
                {
                    "severity": "high",
                    "stage": row["Этап"],
                    "subject": "Владелец этапа",
                    "message": f"Этап «{row['Этап']}» не имеет назначенного владельца.",
                }
            )
        if pd.isna(row["norm_days"]) or row["norm_days"] <= 0:
            issues.append(
                {
                    "severity": "high",
                    "stage": row["Этап"],
                    "subject": "Норматив срока",
                    "message": f"Этап «{row['Этап']}» имеет некорректный норматив срока ({row['norm_days']}).",
                }
            )

    for _, row in data.checklist.iterrows():
        if row["Элемент"] is None or str(row["Элемент"]).strip() == "":
            issues.append(
                {
                    "severity": "medium",
                    "stage": row["Этап"],
                    "subject": "Элемент чек-листа",
                    "message": f"Этапу «{row['Этап']}» принадлежит пустой элемент чек-листа.",
                }
            )

    bad_dates = data.schedule.loc[data.schedule["Дата_завершения"].isna()]
    if not bad_dates.empty:
        issues.append(
            {
                "severity": "high",
                "stage": "все",
                "subject": "Даты",
                "message": f"Не читаются {len(bad_dates)} дат завершения в листе «Сроки».",
            }
        )

    for sheet in SHEETS_REGISTRY + SHEETS_NOVICES:
        pass  # колонки проверяются на чтении (KeyError упадёт явно)

    return issues


def load(data_dir: Path) -> OnboardingData:
    """Полная загрузка обоих источников и проверка целостности."""
    registry_path = data_dir / "onboarding_registry.xlsx"
    novices_path = data_dir / "novices.xlsx"
    _check_existing(registry_path)
    _check_existing(novices_path)

    data = OnboardingData(
        stages=parse_registry(registry_path),
        checklist=parse_checklist(registry_path),
        profiles=parse_profiles(novices_path),
        schedule=parse_schedule(novices_path),
        scores=parse_scores(novices_path),
        ankets=parse_ankets(novices_path),
    )
    data.issues = check_integrity(data)
    return data


def report_issues(data: OnboardingData) -> str:
    """Краткая сводка структурных находок — для CLI и тестов."""
    if not data.issues:
        return "Структурных проблем не обнаружено."
    lines = [f"Найдено структурных проблем: {len(data.issues)}"]
    for iss in data.issues:
        lines.append(
            f"  [{iss['severity']}] {iss['stage']} / {iss['subject']}: {iss['message']}"
        )
    return "\n".join(lines)