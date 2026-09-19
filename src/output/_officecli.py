"""Общий слой запуска officecli через node (прямой вызов, без обёрток)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

CANDIDATES = [
    Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules" / "@officecli" / "officecli" / "officecli.js",
    Path.home() / ".local" / "share" / "npm" / "node_modules" / "@officecli" / "officecli" / "officecli.js",
    Path("/usr/local/lib/node_modules/@officecli/officecli/officecli.js"),
]


def js_path() -> Path:
    import shutil

    # 1) центральная установка npm (обычный путь)
    for c in CANDIDATES:
        if c.exists():
            return c
    # 2) поиск по node_modules от cwd вверх (если проект в node-окружении)
    here = Path.cwd()
    for parent in [here, *here.parents]:
        hit = parent / "node_modules" / "@officecli" / "officecli" / "officecli.js"
        if hit.exists():
            return hit
    # 3) node установлен глобально, но путь не найден — пробуем shim в PATH
    shim = shutil.which("officecli.cmd")
    if shim:
        raise RuntimeError(
            f"Не нашёл officecli.js (узлы npm другие). Шим есть: {shim}. "
            "Установи officecli через npm, либо задайте NODE path в окружении."
        )
    raise RuntimeError("officecli.js не найден. Установите: npm i -g @officecli/officecli")


def run(args: list[str], timeout: int = 120) -> str:
    """Выполняет officecli с аргументами, возвращает stdout (UTF-8)."""
    cmd = [_node(), str(js_path()), *args]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"officecli {args[0] if args else ''} завершился {proc.returncode}: "
            f"{err.strip() or out.strip()}"
        )
    return out


def _node() -> str:
    return os.environ.get("OFFICECLI_NODE", "node")