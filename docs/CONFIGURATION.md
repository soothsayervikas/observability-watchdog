# Configuration

Copy `.env.example` to `.env` and edit values.

## Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `observability-watchdog` | Application name |
| `APP_ENV` | `local` | `local`/`development` = relaxed, `production` = strict |
| `SECURITY_PROFILE` | `auto` | `auto`, `relaxed`, or `strict` (overrides `APP_ENV`) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DATABASE_URL` | `sqlite:///./data/watchdog.db` | Database connection |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Dashboard CORS origins |
| `API_KEY` | — | API key for production (header: `X-API-Key`) |
| `ANALYSIS_LOOKBACK_HOURS` | `24` | Default analysis window |

### Environment profiles

| `APP_ENV` | Profile | Demo/docs | Rate limits | Payload caps |
|-----------|---------|-----------|-------------|--------------|
| `local`, `development` | relaxed | yes | off | 100 MB |
| `production` | strict | no | on | 10 MB / 8 KB |

Use `.env.production.example` as a template for production deployments.

## Detection

| Variable | Default | Description |
|----------|---------|-------------|
| `DETECTION_WINDOW_MINUTES` | `5` | Time bucket size |
| `DETECTION_BASELINE_BUCKETS` | `12` | Rolling baseline window |
| `DETECTION_Z_THRESHOLD` | `2.5` | Z-score spike threshold |
| `DETECTION_MIN_ERROR_COUNT` | `5` | Minimum errors to flag spike |
| `DETECTION_PER_SERVICE` | `true` | Per-service spike detection |

## Azure OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_CLASSIFIER_ENABLED` | `true` | Enable AI layer |
| `AZURE_OPENAI_ENDPOINT` | — | Azure OpenAI base URL |
| `AZURE_OPENAI_API_KEY` | — | API key (never commit) |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1` | Deployment name |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | API version |
| `AI_MIN_CONFIDENCE` | `0.6` | Min AI confidence for alerts |
| `AI_MAX_LOG_SAMPLES` | `25` | Max error logs sent to AI |

## Webhook

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBHOOK_URL` | `http://127.0.0.1:8765/webhook` | Alert target |
| `WEBHOOK_MAX_RETRIES` | `3` | Max delivery attempts |
| `WEBHOOK_HMAC_SECRET` | — | HMAC-SHA256 signing secret for webhooks |

## Log Sources

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_WATCH_DIR` | `./data/incoming` | Watch directory |
| `LOG_PROCESSED_DIR` | `./data/incoming/processed` | Processed files |
| `LOG_FAILED_DIR` | `./data/incoming/failed` | Failed files |
| `LOG_DEFAULT_SERVICE` | `app-service` | Default service name |
| `LOG_MAX_UPLOAD_MB` | `10` | Max upload size |
| `LOG_MAX_RAW_BODY_MB` | `10` | Max raw JSON request body |
| `LOG_MAX_MESSAGE_CHARS` | `8192` | Max log message length |
| `LOG_MAX_EVENTS_PER_FILE` | `50000` | Max events parsed per file |
| `LOG_MAX_JSONL_LINES` | `100000` | Max lines parsed per file |

## Rate limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable per-IP rate limiting |
| `RATE_LIMIT_INGEST_PER_MINUTE` | `120` | Ingest/upload endpoints |
| `RATE_LIMIT_ANALYZE_PER_MINUTE` | `10` | Analysis endpoint |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | `300` | Other API routes |

## Production

Set `APP_ENV=production` (or `SECURITY_PROFILE=strict`) to enable full hardening and disable `/docs` and `/demo`.

Verify profile at runtime: `GET /api/v1/health`
