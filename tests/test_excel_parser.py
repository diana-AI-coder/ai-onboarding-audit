"""Юнит-тесты слоя ингестии (excel_parser)."""
from pathlib import Path

import pandas as pd

from src.ingest import excel_parser as ep

DATA = Path(__file__).resolve().parent.parent / "data"


def test_load_reads_all_frames():
    d = ep.load(DATA)
    assert set(d.stage_names) == {
        "preboarding",
        "day-1",
        "week-1",
        "month-1",
        "day-90",
    }
    assert len(d.profiles) == 10
    assert set(d.schedule.columns) >= {"ID", "Этап", "Дата_завершения"}
    assert not d.schedule["Дата_завершения"].isna().any()
    assert len(d.ankets) == 40  # 10 новичков * 4 вопроса


def test_registry_normalization():
    d = ep.load(DATA)
    stage = d.stages.loc[d.stages["Этап"] == "preboarding"].iloc[0]
    assert stage["norm_days"] == 5
    assert bool(stage["mandatory"]) is True
    assert stage["owner"] == "HR-отдел"


def test_integrity_finds_missing_owner():
    d = ep.load(DATA)
    owners = {i["stage"] for i in d.issues if i["subject"] == "Владелец этапа"}
    assert "month-1" in owners


def test_integrity_no_false_positive_on_valid_owner():
    d = ep.load(DATA)
    owner_issues = [i for i in d.issues if i["subject"] == "Владелец этапа"]
    assert all(i["stage"] != "day-90" for i in owner_issues)


def test_missing_file_raises():
    try:
        ep.load(Path("nonexistent"))
    except FileNotFoundError:
        return
    raise AssertionError("Ожидалась FileNotFoundError")


def test_schedule_dates_are_datetime():
    d = ep.load(DATA)
    assert isinstance(d.schedule["Дата_завершения"].iloc[0], pd.Timestamp)


def test_checklist_mandatory_flag():
    d = ep.load(DATA)
    day1 = d.checklist.loc[d.checklist["Этап"] == "day-1"]
    assert day1["mandatory"].all()
    assert not any(
        day1["Элемент"].astype(str).str.contains("рабочего места")
    )  # заложенный дефект: элемент отсутствует