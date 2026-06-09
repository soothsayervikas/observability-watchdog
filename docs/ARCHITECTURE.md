# Architecture — Observability Watchdog

## 1. Problem Statement

Platform teams need lightweight tooling to detect abnormal error spikes in application logs and notify on-call engineers before incidents escalate. This project delivers an API-first observability watchdog with statistical anomaly detection, webhook alerting, and a health dashboard.

## 2. System Context

```
Reviewer / Operator
        │
        ├──► Dashboard (React) ──► REST API
        ├──► Log upload scripts ──► REST API
        └──► Mock webhook receiver ◄── Alert dispatcher
                                      │
                                      ▼
                                 SQLite DB
```

## 3. Component Architecture

| Layer | Responsibility |
|-------|----------------|
| API (`app/api/v1`) | HTTP routing, validation, response mapping |
| Services | Business logic: ingest, analyze, alert, webhook, metrics |
| Repositories | Database access abstraction |
| Detection engine | Time-bucket aggregation + spike detection |
| Models | Pydantic schemas + SQLAlchemy ORM |

## Detection Engine

Hybrid **statistical + Azure OpenAI** pipeline:

1. **Statistical layer** — time-bucket aggregation, rolling baseline, z-score spike detection.
2. **AI layer (Azure OpenAI)** — analyzes error log samples + bucket metrics + statistical findings.
3. **Hybrid merge** — AI enriches spike alerts with root-cause hints; AI-only findings create `UNKNOWN_PATTERN` alerts.
4. **Webhook** — simulated alert dispatch with audit trail.

Configure Azure in `.env`:

```env
AI_CLASSIFIER_ENABLED=true
AZURE_OPENAI_ENDPOINT=https://your-resource.services.ai.azure.com
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
```

## 5. Data Model

- **log_events** — normalized ingested logs
- **alerts** — detected anomalies with metrics payload
- **health_metrics** — aggregated time buckets for trends
- **webhook_deliveries** — delivery audit with retry attempts

## 6. Alert & Webhook Flow

1. `POST /api/v1/analyze/run` loads recent logs.
2. Detection engine creates deduplicated alerts.
3. Webhook service POSTs JSON payload to configured URL.
4. Retries with bounded attempts; all attempts persisted.

## 7. Tradeoffs

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | SQLite | Zero-cost local demo; swappable via `DATABASE_URL` |
| Detection | Statistical primary | Deterministic, testable, no API key required |
| Dashboard | React + API | Matches senior full-stack profile; decoupled UI |
| AI classifier | Azure OpenAI hybrid | Meets assessment AI logic requirement |

## 8. Production Hardening

| Control | Implementation |
|---------|----------------|
| Rate limiting | Per-IP sliding window on ingest/analyze |
| Payload limits | Message size, body size, file line/event caps |
| Path traversal | Demo seed validates dataset names |
| Webhook signing | HMAC-SHA256 via `X-Webhook-Signature` |
| Security headers | nosniff, DENY frame, no-store cache |
| Per-service detection | Independent spike analysis per service |
| Production mode | `APP_ENV=production` hides docs + demo |

Authentication uses API key middleware (`X-API-Key`) when `APP_ENV=production` or `SECURITY_PROFILE=strict` and `API_KEY` is set. Startup fails fast if hardening is enabled without `API_KEY`. The `/api/v1/health` liveness probe remains public.

## 9. Operations

| Capability | Implementation |
|------------|----------------|
| CI | GitHub Actions — pytest + ruff on push/PR |
| Migrations | Alembic (`alembic upgrade head`) for file-backed SQLite/Postgres |
| Logging | JSON structured logs with `request_id` correlation |
| Rate limiting | In-memory default; optional Redis via `REDIS_URL` |
| Alert lifecycle | `PATCH /api/v1/alerts/{id}` — OPEN → ACKNOWLEDGED → RESOLVED |

## 10. Future Enhancements

- Azure Monitor / Application Insights integration
- Postgres deployment profile
- OAuth2 / SSO for dashboard users
- Prometheus `/metrics` exporter

## 11. Vibe Coding Process (Wolters Kluwer Assessment)

This solution was delivered using the mandated **Vibe Coding** workflow:

- **Architect (candidate):** defined requirements, chose the stack, directed security and detection design, validated demos, and issued fix prompts when behavior was wrong.
- **Engineer (Cursor AI agent):** implemented all code, tests, and docs from those prompts — **no manual source edits** during the build.
- **Audit trail:** every prompt is recorded in [`prompts.md`](../prompts.md), including the assessment opening template.

**Scope honesty:** This is an **assessment MVP** — optimized for reviewer demo (SQLite, local profiles, mock webhook). Production-oriented patterns (API key auth, rate limits, HMAC signing, SSRF-safe webhooks) illustrate SRE thinking; full multi-region HA is out of scope for this challenge.

**Interview/demo tip:** Walk reviewers from `prompts.md` Turn 0 → hybrid AI Turn 4 → security Turn 9–11 → submission fixes Turn 18 to show architect-led iteration, not one-shot code generation.
