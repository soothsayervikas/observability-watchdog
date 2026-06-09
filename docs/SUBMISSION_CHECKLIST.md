# Pre-Submission Checklist

Use this before pushing to GitHub and submitting the Wolters Kluwer assessment.

## Required artifacts

| Item | Status | Location |
|------|--------|----------|
| Public GitHub repo | ☑ | Update URL in `README.md` |
| `prompts.md` | ☑ | Root — vibe-coding audit log |
| `README.md` | ☑ | Setup, demo, environment profiles |
| Architecture deck | ☑ | Export `docs/ARCHITECTURE.md` → PDF/PPT |
| Tagle.ai Tag summary | ☐ | https://tagle.ai (manual — see `docs/images/README.md`) |
| Tagle quiz | ☐ | https://tagle.ai/quiz (manual) |
| Dashboard screenshot | ☑ | `docs/images/dashboard.png` |

## Post-review improvements (implemented)

| Improvement | Status |
|-------------|--------|
| Readiness probe returns 503 when DB down | ☑ |
| SSRF DNS pinning for webhooks | ☑ |
| SQL-side log bucketing (memory-efficient analysis) | ☑ |
| Redis distributed analysis lock + CI Redis tests | ☑ |
| Pydantic message length aligned with security profile | ☑ |
| Webhook HTTP 207/502 on partial/total delivery failure | ☑ |
| AI severity guardrails (no downgrade below statistical) | ☑ |
| AI analysis Prometheus metric | ☑ |
| Full `mypy app` in CI | ☑ |
| Dashboard component tests (Vitest + Testing Library) | ☑ |
| Production deployment guide | ☑ [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) |
| Analysis lock race fix (`analysis_guard`) | ☑ |
| Per-endpoint rate limit keys | ☑ |
| Full pytest suite under strict profile in CI | ☑ |
| DB session released before AI enrichment | ☑ |
| Webhook FK migration (`002_webhook_fk`) | ☑ |

## Do NOT commit

| File / folder | Why |
|---------------|-----|
| `.env` | May contain Azure OpenAI API key |
| `data/watchdog.db` | Local SQLite database |
| `data/runtime/`, `*.log` | Server runtime logs |
| `node_modules/`, `.venv/` | Dependencies |
| `.pytest_cache/`, `*.egg-info/` | Build/cache artifacts |
| `data/incoming/processed/*` | Ingested file artifacts |

## Safe to commit

- `.env.example`, `.env.production.example`
- `data/samples/*.json`
- `data/incoming/sample-app.log`
- `data/incoming/processed/.gitkeep`, `data/incoming/failed/.gitkeep`

## Pre-push commands

```bash
pytest -q --cov=app
ruff check app tests scripts
mypy app
python scripts/check_secrets.py
cd dashboard && npm test && npm run build
make docker
```

## Local demo (recommended)

```bash
# Terminal 1
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2
python scripts/mock_webhook.py

# Terminal 3
cd dashboard && npm run dev
```

Open http://127.0.0.1:5173 → Load Sample Data → Run Analysis → capture screenshot.

## Docker full-stack demo

```bash
copy .env.example .env
docker compose up --build
```

Open http://127.0.0.1:8000 (API + built dashboard).
