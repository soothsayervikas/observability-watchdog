# Production Deployment Guide

## Supported topologies

| Topology | Use case | Requirements |
|----------|----------|--------------|
| **Single-process local** | Dev / demo / assessment review | SQLite, `APP_ENV=local` |
| **Hardened single node** | Small production pilot | SQLite or Postgres, `APP_ENV=production`, `API_KEY`, `WEBHOOK_HMAC_SECRET` |
| **Scaled production** | Multi-worker / HA | **Postgres** + **Redis** + reverse proxy |

## Single-worker constraint (SQLite)

SQLite allows **one writer at a time**. Run **one uvicorn worker** when using SQLite:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Do **not** use `--workers N` with SQLite — you will see lock errors and duplicate analysis runs.

## Scaled production (recommended)

```env
APP_ENV=production
SECURITY_PROFILE=strict
DATABASE_URL=postgresql+psycopg2://user:pass@db:5432/watchdog
REDIS_URL=redis://redis:6379/0
API_KEY=<strong-random-key>
WEBHOOK_HMAC_SECRET=<strong-random-secret>
TRUSTED_PROXY=true
```

- **Postgres** — concurrent writers, durable storage
- **Redis** — distributed analysis lock + rate limiting across workers
- **Reverse proxy** — TLS termination, set `TRUSTED_PROXY=true` for accurate rate-limit keys

## Health probes

| Endpoint | Expected | Purpose |
|----------|----------|---------|
| `GET /api/v1/health` | 200 | Liveness |
| `GET /api/v1/health/ready` | 200 when DB up, **503** when DB down | Readiness |
| `GET /metrics` | 200 | Prometheus scrape (restrict by network policy) |

## Docker

```bash
copy .env.production.example .env
# Edit API_KEY, WEBHOOK_HMAC_SECRET, DATABASE_URL
docker compose up --build
```

For strict-profile validation in CI, see `.github/workflows/ci.yml` (`test-strict`, `docker-smoke`).

## Dashboard API key

When `APP_KEY` is required, build the dashboard with the same key:

```bash
VITE_API_KEY=your-api-key npm run build
```

Prefer serving the dashboard behind the same origin or a BFF proxy in true production — browser-exposed keys are acceptable for internal demos only.
