"""Промпт-константы агентов: подключаются к субагентам из prompts/.

При включённом LLM-слое текст промпта отправляется модели.
В детерминированном режиме (MVP) промпты документируют логику агента
человекочитаемо — это и есть «промпт-инжиниринг на бумаге».
"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

PROMPTS = {
    "orchestrator": PROMPTS_DIR / "orchestrator.md",
    "hr_expert": PROMPTS_DIR / "hr_expert.md",
    "data_analyst": PROMPTS_DIR / "data_analyst.md",
    "compliance": PROMPTS_DIR / "compliance.md",
    "recommender": PROMPTS_DIR / "recommender.md",
}


def load(name: str) -> str:
    return PROMPTS[name].read_text(encoding="utf-8")