# API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

Interactive docs: http://127.0.0.1:8000/docs

## Health & Metrics

| Method | Endpoint | Auth (strict) | Description |
|--------|----------|---------------|-------------|
| `GET` | `/health` | Public | Liveness probe |
| `GET` | `/health/ready` | Public | Readiness probe (DB connectivity) |
| `GET` | `/health/summary` | API key | Health score, log counts, open alerts |
| `GET` | `/metrics/trends` | API key | Time-bucketed error rate trends |

Prometheus metrics (not under `/api/v1`): `GET /metrics` — public scrape endpoint.

### Authentication (production / strict)

Set `API_KEY` in `.env` and send header `X-API-Key: <key>` on protected routes. Public: `/health`, `/health/ready`, `/metrics`.

## Logs & Ingestion

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/logs/ingest` | Batch ingest JSON log events |
| `POST` | `/logs/upload` | Upload log file (multipart form) |
| `POST` | `/logs/ingest/raw` | Ingest raw log text body |
| `GET` | `/logs` | Query ingested logs |

## Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sources/pending` | List files in `data/incoming/` |
| `POST` | `/sources/scan` | Ingest pending files |

## Analysis & Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze/run` | Run hybrid detection |
| `GET` | `/alerts` | List alerts (supports `severity`, `status`, `limit`, `offset`) |
| `PATCH` | `/alerts/{id}` | Update alert status (`ACKNOWLEDGED`, `RESOLVED`) |

## Webhooks & Demo

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/webhooks/deliveries` | Webhook audit trail (`?include_payload=true` for full payload) |
| `POST` | `/demo/seed?dataset=error_spike` | Load sample dataset |

## Examples

### Ingest JSON logs

```bash
curl -X POST http://127.0.0.1:8000/api/v1/logs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "timestamp": "2026-06-08T12:03:00Z",
      "level": "ERROR",
      "service": "payment-api",
      "message": "Database connection timeout"
    }]
  }'
```

### Upload file (Swagger or curl)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/logs/upload \
  -F "file=@data/incoming/sample-app.log" \
  -F "default_service=payment-api"
```

### Run analysis

```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze/run
```

### Analyze response

```json
{
  "alerts_created": 2,
  "buckets_analyzed": 13,
  "ai_enabled": true,
  "ai_assessment": "Critical error spike detected.",
  "detection_method": "hybrid_statistical_ai"
}
```
