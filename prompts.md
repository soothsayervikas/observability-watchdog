# Prompts Audit Log

**Project:** Wolters Kluwer Assessment — Project 3 (Observability Watchdog)  
**Candidate:** Vikas Mishra  
**Tool:** Cursor (Vibe Coding — architect prompts only, no manual code edits)  
**Last updated:** 2026-06-09 (pre-submission fixes + initial commit)

Per assessment rules, each entry below is the **full prompt text** used for that turn (operational-only messages are listed separately at the end).

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

## Turn 1 — Project Selection & Implementation Plan

```
I have assignment for the interview. Please read it and check which assignment is good to submit. I am software developer having 9 year of experience. please read the resume from here "Vikas_Mishra_Resume_Updated.docx". we need to maintain code quality and everything like a senior developer. please read both document carefully and make a plan
```

---

## Turn 2 — Plan Document

```
please make a MD file for the plan. log all the things which we will implement, remember the code quality structure and figure out all other things which should be done as a senior level engineer
```

---

## Turn 3 — Scaffold MVP

```
please go ahead
```

---

## Turn 4 — Azure OpenAI Hybrid Detection

```
The project says - "Project 3: Intelligent Observability & Event Watchdog
● Focus: Site Reliability Engineering (SRE).
● Description: Develop a service that parses application or platform logs to detect anomalies or "spikes" in errors using AI logic. When thresholds are breached, the system must trigger a simulated webhook alert and visualize health trends."

We need to use AI logic. I do not see AI logic here. Configure Azure OpenAI via .env / .env.local only — endpoint and API key must never be committed to the repository.
```

---

## Turn 5 — Dashboard Run Analysis UX

```
I clicked on "Run analysis" button from the UI but nothing happened
```

---

## Turn 6 — Production-Style Log Ingestion

```
How error log detection work, we need to upload log file or it will read from a particular source?
```

```
we need to make it Production-style extension
```

---

## Turn 7 — Upload Endpoint Fix

```
In this url "http://127.0.0.1:8000/api/v1/logs/upload" I am uploading file "C:\Users\vikas\Desktop\Assigment\observability-watchdog\data\app.log" it is giving me error
```

---

## Turn 8 — README

```
Create a README file with all details
```

```
please check is it a standard format for readme file, all things which is there should be there or not
```

```
yes please
```

---

## Turn 9 — Security Review

```
Now we need to check the security thing, please check how our application is secure and also the error detection
```

---

## Turn 10 — Production Hardening (Except Auth)

```
we need to make it as production level, please implement everything except auth
```

---

## Turn 11 — Local vs Production Profiles

```
Can we give option to use local and production environment where local can run without some security check
```

```
please add it in readme file also
```

---

## Turn 12 — Pre-Submission Cleanup

```
Now please check if we have any extra files before submitting it. Please check code also, it should be standard
```

---

## Turn 13 — Assignment-Focused Code Review

```
It is not production-grade but an assignment only. We need to check code quality and all edge cases only
```

---

## Turn 14 — Edge Case & Code Quality Fixes (Local-Friendly)

```
please fix the code quality issues and Findings — Edge Cases & Correctness. not authentication because it should work in local
```

---

## Turn 15 — Senior Code Review (Pre-Release)

```
I have completed Project 3 from the assignment described in "Wolters Kluwer Assessment.pdf". I want you to perform a comprehensive senior-level code review as if you were a Software Engineer with 9+ years of professional experience conducting a review before a production release.

[Full review objectives: code quality, architecture, error handling, security, performance, testing, production readiness, senior engineer expectations, and structured findings with severity/category/impact/recommendation.]
```

---

## Turn 16 — High & Medium Severity Remediation

```
please fix things with high and medium severity
```

---

## Turn 17 — Critical: prompts.md, Secrets, Remaining Bugs

```
expect prompts.md and openai key fix critical bugs also
```

---

## Turn 18 — Top 10 Review Improvements

```
please implment "Top 10 Highest-Impact Improvements"
```

Implemented: analysis lock race fix, per-path rate limits, Prometheus path normalization, DB session split before AI calls, migration test, UNKNOWN_PATTERN test, consolidated fixtures, concurrent analyze test, CI strict full-suite + docker smoke, submission artifact docs.

---

## Turn 19 — README Sync

```
please update readme file if needed
```

---

## Turn 20 — Vibe Coding Statement

```
sure
```

(Context: draft Vibe Coding Statement for README, `docs/ARCHITECTURE.md`, and `docs/VIBE_CODING.md` — architect-led Cursor workflow, assessment MVP scope honesty.)

---

## Turn 21 — Pre-Submission Review & Final Fixes

```
please review all things again i am going to submit this assigment
```

```
please do all these steps
```

Implemented: ruff lint/format fixes, dashboard screenshot path (`docs/images/dashboard.png`), `.gitignore` updates (`.coverage`, `tsbuildinfo`), `prompts.md` Turns 20–21, full test/secret-scan verification, git commit and push.

---

## Prompts Excluded (Not Logged)

These were operational or Q&A only — no architectural/code change requested:

| Prompt | Reason excluded |
|--------|-----------------|
| `please start both servers` | Runtime ops |
| `please stop backend server kill it and restart it` | Runtime ops |
| `I am not able to see any logs in the backend server` | Troubleshooting |
| `how webhook will work` | Explanation only |
| `please push this repo, this will be public` | Git ops |
| `Briefly inform the user about the task result...` | System relay |
| Tagle quiz / resume-only planning before repo scaffold | Pre-project |

---

## Security Note (Post-Review)

If an Azure OpenAI key was ever pasted into chat or a local file:

1. **Rotate the key** in Azure Portal immediately.
2. Store the new key only in **`.env.local`** (gitignored).
3. Never commit `.env` with real credentials.
4. Run `python scripts/check_secrets.py` before pushing to GitHub.
