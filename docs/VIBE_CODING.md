# Vibe Coding Workflow

## Statement (for submission / presentation)

> **Wolters Kluwer GTS Assessment — Project 3** was built using the required **Vibe Coding** model: I acted as **Lead Architect** and directed a **Cursor AI agent** to implement the entire codebase. Manual code edits were not used during implementation. My contributions were architectural vision, structured prompting, output review, and iterative correction when tests or demos failed. The AI agent produced application code, tests, CI, Docker, and documentation from those prompts. The complete instruction history is in [`prompts.md`](../prompts.md). This deliverable is an **assessment MVP** (local SQLite, demo dashboard, simulated webhooks) that meets Project 3 requirements — intelligent log anomaly detection, AI-assisted analysis, alerting, and health visualization — while demonstrating how platform engineers can orchestrate AI safely with an audit trail.

---

Per Wolters Kluwer assessment requirements, all code was implemented via AI-assisted development (Cursor). No manual code edits were made during implementation.

## Rules followed

1. **No manual edits** — architect prompts; AI implements and fixes
2. **Single tool** — Cursor used end-to-end for consistency
3. **Audit log** — every prompt recorded in [`prompts.md`](../prompts.md)
4. **Opening prompt** — exact assessment template used to start

## Opening prompt (assessment template)

```
Lead Architect mode: ON. We are building a Python-based, API-first Intelligent Observability & Event Watchdog using a free database and a dashboard.

Rules:
1. No Manual Edits: You provide all logic and fixes. I will not edit any code.
2. Audit Log: You must maintain a file named prompts.md. After every turn, update that file with the prompt I just used.
3. Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report 'Elapsed Time' at the end of every response.

Acknowledge and let's start.
```

## Audit trail

Submission prompt log (opening template + build prompts): [`prompts.md`](../prompts.md)

## Related submission artifacts

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — architecture deck source
- [`API.md`](API.md) — API reference
- [`../README.md`](../README.md) — project overview
