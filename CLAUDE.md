# SkyAlert — Claude Code Instructions

## Project
Flight price monitoring SaaS. Watches Google Flights every 5 minutes, detects price drops below a configurable threshold vs. historical average, and notifies users via email and WhatsApp. Users can trigger automatic purchase upon alert confirmation.

## Stack
- Backend: Python, FastAPI, Celery, Redis, PostgreSQL
- Scraping: Playwright (Google Flights)
- Notifications: SendGrid (email), Twilio (WhatsApp)
- Frontend: HTML + Tailwind CSS

## Architecture
Strict hexagonal (ports & adapters):
- `domain/` → entities and abstract ports only. Zero infrastructure imports. Ever.
- `application/` → use cases only. Orchestrates domain ports. Zero infrastructure imports. Ever.
- `infrastructure/` → concrete implementations only.
- Dependency direction: `infrastructure` → `application` → `domain`. Never reversed.

## Code Standards
- All code, comments, variable names, and documentation in English
- Type hints on every function
- Docstring on every function and module
- Max 200 lines per file — split into modules if needed
- Never hardcode secrets or API keys
- Never skip error handling
- Use `.env` for all credentials

## How We Work
- Before writing any file: explain what you are about to do and why, break it into steps, wait for OK
- After writing code: explain what each part does
- Never generate code the developer cannot explain
- If something is complex, suggest simpler alternatives first
- Be direct — say when something is wrong or has a better approach

## 20% Rule
At the start of each session, before writing any code:
- Identify the one core concept this session depends on most
- Teach the 20% of that concept that explains 80% of what matters
- Ask: "What are the most common misconceptions about this?"
- One core concept per session. Never overload.

## Session Log Protocol
At the end of every session, generate `docs/sessions/session-00X.md` with this structure:

```
# Session 00X — YYYY-MM-DD

## Goal
What we set out to do this session.

---

## Completed
- list of files written or modified

---

## Decisions made
- **Decision** — reason why

---

## Concepts covered

**[TAG] Concept name**
- What: internal mechanics
- Why: motivation
- Where: practical application in this project

---

## Pending
- What was not completed and why

---

## Next session starts at
Exact file and task to begin with. Apply 20% Rule for: [concept name].
```
