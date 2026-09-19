"""[Фаза 6] CLI-интерфейс аудита онбординга + webhook-сервер для n8n.

Примеры:
  python -m src.cli run                # полный прогон: md + docx + pptx
  python -m src.cli run --formats md   # только markdown
  python -m src.cli verify             # проверка источников и покрытия
  python -m src.cli serve --port 8017  # webhook (POST /audit) для n8n
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from src.audit import metrics as M
from src.audit import orchestrator as O
from src.ingest import excel_parser as EP
from src.output import deck_pptx, report_docx, report_md

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data"
DEFAULT_DOCS = ROOT / "docs"
DEFAULT_OUT = ROOT / "examples" / "sample_report"
FORMATS = ("md", "docx", "pptx")


def _check_formats(formats: tuple[str, ...]) -> tuple[str, ...]:
    unknown = set(formats) - set(FORMATS)
    if unknown:
        raise ValueError(f"Неизвестные форматы: {', '.join(sorted(unknown))} (доступно: {', '.join(FORMATS)})")
    return tuple(formats)


def pipeline(
    data_dir: Path = DEFAULT_DATA,
    docs_dir: Path = DEFAULT_DOCS,
    out_dir: Path = DEFAULT_OUT,
    formats: tuple[str, ...] = FORMATS,
) -> dict:
    """Полный прогон: загрузка → метрики → агенты → отчёты."""
    formats = _check_formats(tuple(formats))
    data = EP.load(data_dir)
    metrics = M.measure(data, docs_dir)
    res = O.run(data, metrics, data.issues, docs_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, Path] = {}
    md_text = None
    if "md" in formats:
        md_text = report_md.render(data, metrics, res)
        artifacts["md"] = _write(out_dir / "audit_report.md", md_text)
    if "docx" in formats:
        md_text = md_text or report_md.render(data, metrics, res)
        artifacts["docx"] = report_docx.build(
            _write(out_dir / "audit_report.md", md_text),
            out_dir / "audit_report.docx",
            md_text,
        )
    if "pptx" in formats:
        artifacts["pptx"] = deck_pptx.build(data, metrics, res, out_dir / "audit_presentation.pptx")
    artifacts["metrics"] = M.save_metrics(data, docs_dir, out_dir / "audit_metrics.json")

    return _summary(data, metrics, res, artifacts)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _summary(data, metrics, res, artifacts: dict) -> dict:
    return {
        "n_novices": metrics["overall_"]["n_novices"],
        "critical": len(res.report.critical),
        "warnings": len(res.report.warnings),
        "coverage": O.coverage_summary(res),
        "artifacts": {k: str(v) for k, v in artifacts.items()},
    }


def cmd_verify(args) -> None:
    data = EP.load(Path(args.data_dir))
    print(EP.report_issues(data))
    metrics = M.measure(data, Path(args.docs_dir))
    res = O.run(data, metrics, data.issues, Path(args.docs_dir))
    print("Метрики:")
    print(f"  покрытие фреймворка: {metrics['framework_coverage']:.0%}")
    print(f"  владельцы этапов:    {metrics['owner_coverage']:.0%}")
    print(f"  критические:         {len(res.report.critical)}")
    print(O.coverage_summary(res))


def cmd_run(args) -> None:
    formats = tuple(f.strip().lower() for f in args.formats.split(","))
    try:
        formats = _check_formats(formats)
    except ValueError as e:
        raise SystemExit(str(e))
    summary = pipeline(
        data_dir=Path(args.data_dir),
        docs_dir=Path(args.docs_dir),
        out_dir=Path(args.out_dir),
        formats=formats,
    )
    print(f"Новичков: {summary['n_novices']} · критических: {summary['critical']} "
          f"· предупреждений: {summary['warnings']}")
    print(summary["coverage"])
    for fmt, path in summary["artifacts"].items():
        print(f"  {fmt:4s} → {path}")


class _Handler(BaseHTTPRequestHandler):
    server: "AuditServer" = None  # type: ignore[assignment]

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (стандарт http.server)
        if self.path.startswith("/health"):
            self._json(200, {"ok": True, "service": "onboarding-audit"})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if not self.path.startswith("/audit"):
            self._json(404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "body must be JSON"})
            return

        data_dir = Path(body.get("dataDir", str(self.server.data_dir)))
        docs_dir = Path(body.get("docsDir", str(self.server.docs_dir)))
        out_dir = Path(body.get("outDir", str(self.server.out_dir)))
        formats = tuple(body.get("formats", FORMATS))
        candidate = body.get("candidate", "n8n-триггер")
        try:
            summary = pipeline(data_dir=data_dir, docs_dir=docs_dir, out_dir=out_dir, formats=formats)
            self._json(200, {"ok": True, "triggered_by": candidate, **summary})
        except ValueError as e:
            self._json(400, {"ok": False, "error": str(e)})
        except FileNotFoundError as e:
            self._json(412, {"ok": False, "error": str(e)})
        except Exception as e:  # noqa: BLE001 — внешний webhook отвечает всегда
            self._json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})


class AuditServer(ThreadingHTTPServer):
    def __init__(self, addr, data_dir, docs_dir, out_dir):
        self.data_dir = data_dir
        self.docs_dir = docs_dir
        self.out_dir = out_dir
        super().__init__(addr, _Handler)


def cmd_serve(args) -> None:
    server = AuditServer(
        (args.host, args.port),
        data_dir=Path(args.data_dir),
        docs_dir=Path(args.docs_dir),
        out_dir=Path(args.out_dir),
    )
    print(f"Webhook-сервер аудита: http://{args.host}:{args.port}/audit")
    print(f"  данные: {args.data_dir} · отчёты: {args.out_dir}")
    print("Health: http://{host}:{port}/health".format(host=args.host, port=args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


def main(argv=None) -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # Windows-консоль + кириллица
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="onboarding-audit", description="ИИ-аудит процесса онбординга")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_paths(p):
        p.add_argument("--data-dir", default=str(DEFAULT_DATA), help="каталог с xlsx-источниками")
        p.add_argument("--docs-dir", default=str(DEFAULT_DOCS), help="каталог документов онбординга")
        return p

    p_run = add_paths(sub.add_parser("run", help="полный прогон аудита + отчёты"))
    p_run.add_argument("--out-dir", default=str(DEFAULT_OUT), help="куда писать отчёты")
    p_run.add_argument("--formats", default="md,docx,pptx", help="форматы через запятую: md,docx,pptx")
    p_run.set_defaults(func=cmd_run)

    p_ver = add_paths(sub.add_parser("verify", help="проверка источников и покрытия"))
    p_ver.set_defaults(func=cmd_verify)

    p_serve = add_paths(sub.add_parser("serve", help="webhook-сервер для n8n"))
    p_serve.add_argument("--out-dir", default=str(DEFAULT_OUT))
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8017)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()