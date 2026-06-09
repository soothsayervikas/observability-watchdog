# Log Ingestion Guide

## Methods

| Method | Endpoint / Tool | Use case |
|--------|-----------------|----------|
| JSON API | `POST /api/v1/logs/ingest` | Apps, agents |
| File upload | `POST /api/v1/logs/upload` | Swagger, dashboard |
| Raw text | `POST /api/v1/logs/ingest/raw` | Streaming agents |
| Watch directory | `POST /api/v1/sources/scan` | Drop files in `data/incoming/` |
| Collector agent | `scripts/log_collector.py` | Background watcher |
| Demo seed | `POST /api/v1/demo/seed` | Quick demo |

## Supported formats

**Plain text:**
```text
2026-06-08T12:03:00Z ERROR [payment-api] - Database connection timeout
```

**Python logging:**
```text
2026-06-08 12:47:04 [INFO] app.main: HTTP GET /api/v1/health
```

**JSON batch:** `{ "events": [ { "timestamp": "...", "level": "ERROR", ... } ] }`

**JSONL:** One JSON object per line (`.jsonl`, `.ndjson`)

## Canonical schema

```json
{
  "timestamp": "2026-06-08T10:15:00Z",
  "level": "ERROR",
  "service": "payment-api",
  "message": "Database connection timeout",
  "metadata": { "host": "app-01" }
}
```

## Do not upload

- `data/runtime/server.log` — backend internal log
- `data/app.log` (legacy path) — server log, not application logs

## Collector agent

```bash
python scripts/log_collector.py --mode scan
python scripts/log_collector.py --mode watch --interval 15
python scripts/log_collector.py --mode upload --file data/incoming/sample-app.log
```
