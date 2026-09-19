"""[отчёт DOCX] Официальное заключение аудита через officecli.

officecli разворачивает markdown-отчёт в native-элементы Word
(add markdown src=...), затем документ сохраняется. Вердикты-эмодзи
заменяются официальными формулировками для формата документа.
"""
from __future__ import annotations

from pathlib import Path

from src.output._officecli import run

VERDICT_REPLACE = {"✅": "Соответствует", "⚠️": "Частично", "❌": "Не соответствует"}


def build(md_path: Path, out_path: Path, markdown: str) -> Path:
    """Собирает .docx из готового markdown-отчёта."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    official = markdown
    for emoji, label in VERDICT_REPLACE.items():
        official = official.replace(emoji, label)

    tmp_md = out_path.with_suffix(".md.src")
    tmp_md.write_text(official, encoding="utf-8-sig")

    run(["create", str(out_path)])
    run(["add", str(out_path), "/", "--type", "markdown", "--prop", f"src={tmp_md}"])
    run(["save", str(out_path)])
    tmp_md.unlink(missing_ok=True)
    return out_path