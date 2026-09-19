# Фаза 6 — CLI и webhook-запуск аудита (n8n)

## CLI

Простые команды из корня проекта:

```bash
python -m src.cli verify           # проверка источников + покрытие
python -m src.cli run              # полный аудит: md + docx + pptx
python -m src.cli run --formats md # только markdown
python -m src.cli run --out-dir reports/2026-09
```

Опции: `--data-dir`, `--docs-dir`, `--out-dir`, `--formats md,docx,pptx`.

`run` пишет отчёты и печатает итог: число новичков, критических/предупреждений,
покрытие и пути артефактов.

## Webhook-сервер (для n8n)

```bash
python -m src.cli serve --port 8017
```

Эндпоинты:

- `GET  /health` — живой ли сервис.
- `POST /audit` — тело JSON:

```json
{
  "dataDir":   "C:\\...\\data",
  "docsDir":   "C:\\...\\docs",
  "outDir":    "C:\\...\\examples\\scenario_report",
  "formats":   ["md", "docx", "pptx"],
  "candidate": "Анна Иванова"
}
```

Ответ: `{ok, triggered_by, n_novices, critical, warnings, coverage, artifacts}`.
Ошибки источников — `412`, ошибки исполнения — `500`.

## Настройка n8n

1. Установите роли аудита: `python -m src.cli serve` (фоном, напр. автозагрузка).
2. Импортируйте `n8n/onboarding_audit_trigger.json` (Workflow → Import from file).
3. В узле «Локальный аудит (POST /audit)» укажите реальный адрес сервера,
   если порт/хост отличается (`http://<host>:<port>/audit`).
4. Активируйте workflow. Курлы для проверки:

```bash
curl -X POST http://127.0.0.1:8017/audit \
  -H "Content-Type: application/json" \
  -d @n8n/onboarding_scenario.json
```

5. Запустите workflow из Postman/webhook-тестера n8n или отправьте сценарий
   как есть (см. `n8n/onboarding_scenario.json` — шаблон онлайн-онбординга новичка).

### Назначение

- **Webhook** (`/onboarding-audit`) — принимает сценарий онбординга.
- **Собрать тело запроса** — упаковывает атрибуты в JSON для локального сервиса
  (по умолчанию подставляет `formats=['md','docx','pptx']` и `candidate='n8n-триггер'`).
- **Локальный аудит** — POST на `http://127.0.0.1:8017/audit`.
- **Вернуть результат** — отдаёт клиенту итоги аудита (пути артефактов).

Сервис выполняется локально; n8n лишь инициирует запуск и отдаёт результат.
Для распределённого режима разверните сервис с публичным адресом и поменяйте URL.

## Типовые сбои

| Симптом | Причина | Решение |
|---|---|---|
| `412 Не найден источник данных` | Неверный `dataDir`/путь без файлов xlsx | Укажите правильный `dataDir`, где лежат `onboarding_registry.xlsx` и `novices.xlsx` |
| `500 FileNotFoundError` в ответе | officecli/node не установлены (docx/pptx) | Проверьте `officecli` рядом с python, либо используйте `formats: ["md"]` |
| n8n отвечает `502` | Сервис не запущен или другой порт | Проверьте `GET /health` и адрес в HTTP-узле |
| Битые имена файлов отчётов при повторном запуске | Файл занят другим процессом (Word/просмотр) | Закройте открытый файл, либо используйте новый `outDir` |