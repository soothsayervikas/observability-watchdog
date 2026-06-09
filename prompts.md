# Prompts Audit Log

**Project:** Wolters Kluwer GTS Assessment — Project 3 (Intelligent Observability & Event Watchdog)  
**Candidate:** Vikas Mishra  
**AI Tool:** Cursor (single tool, end-to-end)  
**Workflow:** Vibe Coding — architect prompts only; no manual code edits  
**Last updated:** 2026-06-09 (dashboard UI polish)

This file is the **full audit log of instructions** given to the AI agent, as required by the assessment. Each numbered turn records the prompt used for that session. Turn 0 uses the **exact opening template** from the assessment PDF.

---

## Turn index

| Turn | Focus |
|------|--------|
| 0 | Opening template (assessment-required) |
| 1 | MVP scaffold |
| 2 | Azure OpenAI hybrid detection |
| 3 | Dashboard — Run Analysis |
| 4 | Log ingestion (upload, watch dir, parsers) |
| 5 | Upload endpoint fix |
| 6 | README & documentation |
| 7 | Security review |
| 8 | Production hardening |
| 9 | Local vs production profiles |
| 10 | Edge cases & code quality |
| 11 | Senior code review |
| 12 | Review remediation |
| 13 | Secrets, prompts audit, critical bugs |
| 14 | Top improvements (CI, locks, tests) |
| 15 | README final sync |
| 16 | Vibe coding statement |
| 17 | Pre-submission review & fixes |
| 18 | Dashboard header — Trend window alignment |

---

## Turn 0 — Opening Prompt (Assessment Template)

```
Lead Architect mode: ON. We are building a Python-based, API-first Intelligent Observability & Event Watchdog using a free database and a dashboard.

Rules:
1. No Manual Edits: You provide all logic and fixes. I will not edit any code.
2. Audit Log: You must maintain a file named prompts.md. After every turn, update that file with the prompt I just used.
3. Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report 'Elapsed Time' at the end of every response.

Acknowledge and let's start.
```

---

## Turn 1 — MVP Scaffold

```
Proceed with the MVP implementation for Project 3 (Observability Watchdog):

- Python 3.11, FastAPI, API-first design
- SQLite database (free tier)
- Log ingestion API and file parsing
- Statistical error-spike detection with configurable thresholds
- Simulated webhook alert on breach
- React dashboard for health trends and alerts
- Layered architecture (API → services → repositories)
- pytest test suite and README quick start

Maintain senior-level code quality. Update prompts.md after this turn.
```

---

## Turn 2 — Azure OpenAI Hybrid Detection

```
The assessment requires AI logic for anomaly detection. Add Azure OpenAI integration:

- Hybrid pipeline: statistical spike detection first, then AI enrichment for root-cause hints
- Configure credentials only via .env / .env.local — never commit API keys
- Graceful fallback to statistical-only when AI is disabled or unavailable
- Document configuration in README

Project requirement: "Develop a service that parses application or platform logs to detect anomalies or spikes in errors using AI logic. When thresholds are breached, trigger a simulated webhook alert and visualize health trends."
```

---

## Turn 3 — Dashboard Run Analysis

```
The dashboard "Run Analysis" button does not trigger analysis or show feedback. Fix the React client to call POST /api/v1/analyze/run, handle errors, and refresh health metrics and alerts after a successful run.
```

---

## Turn 4 — Log Ingestion

```
Clarify and implement production-style log ingestion:

- How should operators supply logs — API push, file upload, or watched directory?
- Support JSON, JSONL, and plain-text application log formats
- Add a collector/watch workflow for data/incoming/
- Document ingestion options in docs/INGESTION.md
```

---

## Turn 5 — Upload Endpoint Fix

```
POST /api/v1/logs/upload returns an error when uploading the backend server log (uvicorn/app.log) instead of an application log file. Improve parser validation and return clear error messages that distinguish unsupported files from parse failures. Hint users to upload application logs or use Load Sample Data.
```

---

## Turn 6 — README

```
Create a complete README for submission: quick start, architecture summary, API overview, configuration (.env / .env.local for Azure OpenAI), demo steps (Load Sample Data → Run Analysis), testing commands, and project structure. Follow standard open-source README conventions for a technical assessment repo.
```

---

## Turn 7 — Security Review

```
Perform a security review of the application: input validation, webhook URL safety, upload limits, injection risks, secrets handling, and detection logic correctness. List findings with severity and implement high-priority fixes. Document security controls in README.
```

---

## Turn 8 — Production Hardening

```
Harden the application for a production-style profile: rate limiting, request body size limits, security headers, webhook HMAC signing, and structured logging. Keep local/demo mode usable without all checks enabled.
```

---

## Turn 9 — Environment Profiles

```
Add local vs production environment profiles:

- Local/relaxed: open docs, demo seed route, no API key required — for assessment demo
- Production/strict: API key auth, rate limits, hidden docs, required webhook secret
- Control via APP_ENV and SECURITY_PROFILE in .env
- Document both profiles in README with example commands
```

---

## Turn 10 — Edge Cases & Code Quality

```
Fix code quality and edge-case issues from review: deduplication keys, ingest limits, health summary lookback window, parser edge cases, and concurrent analysis handling. Keep local profile working without API key for demo.
```

---

## Turn 11 — Senior Code Review

```
I have completed Project 3 per Wolters Kluwer Assessment.pdf. Perform a comprehensive senior-level code review covering architecture, security, error handling, performance, testing, and production readiness. For each finding provide severity, category, issue, impact, and recommendation. End with scores and top 10 improvements.
```

---

## Turn 12 — Review Remediation

```
Implement fixes for all high and medium severity findings from the code review.
```

---

## Turn 13 — Audit Log, Secrets & Critical Bugs

```
Ensure prompts.md is complete and accurate. Add a secret-scan script for CI. Fix any remaining critical bugs before public GitHub submission. Confirm no Azure OpenAI keys in tracked files.
```

---

## Turn 14 — Top Improvements

```
Implement the top 10 highest-impact improvements: distributed analysis lock, per-endpoint rate limits, Prometheus metrics, DB session handling before AI calls, Alembic migration tests, hybrid AI tests, concurrent analyze test, strict-profile CI job, Docker smoke test, and submission checklist docs.
```

---

## Turn 15 — README Sync

```
Review and update README so it matches the final feature set, environment profiles, test commands, and submission checklist.
```

---

## Turn 16 — Vibe Coding Statement

```
Add a Vibe Coding Statement to README, docs/ARCHITECTURE.md, and docs/VIBE_CODING.md explaining the architect-led Cursor workflow, no manual edits rule, prompts.md audit trail, and honest assessment MVP scope.
```

---

## Turn 17 — Pre-Submission Review

```
Perform a final pre-submission review of the entire project before I submit to Wolters Kluwer. Verify assignment requirements, tests, secrets, screenshot, git readiness, and submission checklist. Fix any remaining blockers (lint, screenshot path, .gitignore).
```

---

## Turn 18 — Dashboard Trend Window Alignment

```
The dashboard header has a layout issue: the "Trend window" label and dropdown are vertically misaligned compared to the action buttons (Refresh, Upload Log File, Scan Incoming, Load Sample Data, Run Analysis). See the attached screenshot.

Fix the header CSS so the Trend window control sits on the same horizontal baseline as the buttons — consistent height, padding, and vertical alignment. Keep the dark theme and responsive behavior intact.
```

---

