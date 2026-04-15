# Session 002 — 2026-04-14

## Goal
Build the full application and infrastructure layers: use cases, repositories, notification adapters, Celery tasks, Playwright scraper, and FastAPI routes.

---

## Completed

- `backend/application/__init__.py`
- `backend/application/commands.py` — frozen command dataclasses for all use cases
- `backend/application/exceptions.py` — domain exception hierarchy (8 types)
- `backend/application/use_cases/__init__.py`
- `backend/application/use_cases/create_search.py`
- `backend/application/use_cases/run_price_scrape.py`
- `backend/application/use_cases/evaluate_price_drop.py`
- `backend/application/use_cases/send_alert_notification.py`
- `backend/application/use_cases/confirm_alert.py`
- `backend/infrastructure/__init__.py`
- `backend/infrastructure/persistence/__init__.py`
- `backend/infrastructure/persistence/database.py`
- `backend/infrastructure/persistence/models.py`
- `backend/infrastructure/persistence/mappers.py`
- `backend/infrastructure/persistence/user_repository.py`
- `backend/infrastructure/persistence/search_repository.py`
- `backend/infrastructure/persistence/price_history_repository.py`
- `backend/infrastructure/persistence/alert_repository.py`
- `backend/infrastructure/notifications/__init__.py`
- `backend/infrastructure/notifications/sendgrid_service.py`
- `backend/infrastructure/notifications/twilio_service.py`
- `backend/infrastructure/notifications/composite_service.py`
- `backend/infrastructure/tasks/__init__.py`
- `backend/infrastructure/tasks/celery_app.py`
- `backend/infrastructure/tasks/scrape_tasks.py`
- `backend/infrastructure/tasks/notify_tasks.py`
- `backend/infrastructure/scraper/__init__.py`
- `backend/infrastructure/scraper/google_flights.py`
- `backend/infrastructure/api/__init__.py`
- `backend/infrastructure/api/schemas.py`
- `backend/infrastructure/api/exception_handlers.py`
- `backend/infrastructure/api/main.py`
- `backend/infrastructure/api/routers/__init__.py`
- `backend/infrastructure/api/routers/users.py`
- `backend/infrastructure/api/routers/searches.py`
- `backend/infrastructure/api/routers/alerts.py`
- `backend/infrastructure/purchases/__init__.py`
- `backend/infrastructure/purchases/stub_purchase.py`
- `backend/__init__.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `docs/sessions/session-002.md`

---

## Decisions made

- **`frozen=True` on all command dataclasses** — commands are inputs, they must be immutable once constructed. Prevents accidental mutation inside use cases.
- **Mapper functions instead of ORM model methods** — keeps the boundary clean: ORM models have zero knowledge of domain entities.
- **`session.merge()` for upsert** — avoids "instance already in session" conflicts on repeated saves without a separate INSERT/UPDATE branch.
- **`CompositeNotificationService` as the injected adapter** — use cases depend on a single `NotificationService` port; the composite pattern lets us add/remove channels without touching use cases.
- **`StubPurchaseService` returns False always** — makes the port satisfied without fake success; callers know purchase was not completed and can act accordingly.
- **`scrape_all_searches` as a fan-out task** — one beat task per 5 min enqueues N individual `scrape_search` tasks. Prevents one slow scrape from blocking all others.
- **`autoretry_for` on scrape and notify tasks** — Celery retries on transient failures automatically. Max 2 retries for scraping, 3 for notifications.
- **`worker_prefetch_multiplier=1`** — each Celery worker processes one task at a time; important for Playwright which is not thread-safe.
- **Flight snapshot denormalized into AlertModel** — Flights are point-in-time; a separate flights table would require joins with no benefit. Denormalizing keeps alert reads fast and self-contained.

---

## Concepts covered

**[APPLICATION] Use Case Pattern**
- What: One class, one `execute()` method, receives ports via `__init__`. Returns domain entities or raises domain exceptions.
- Why: Prevents God-object service classes. Makes each business action independently testable.
- Where: All 5 use cases in `backend/application/use_cases/`.

**[APPLICATION] Command Objects**
- What: Frozen dataclasses that carry transport-agnostic input into use cases.
- Why: Decouples the HTTP request body from the use case signature. Use cases never see Pydantic or FastAPI.
- Where: `backend/application/commands.py`.

**[INFRASTRUCTURE] Mapper Pattern**
- What: Pure functions that translate between ORM models and domain entities.
- Why: The only place where infrastructure and domain touch. Everything else is pure on both sides.
- Where: `backend/infrastructure/persistence/mappers.py`.

**[INFRASTRUCTURE] Composite Pattern for notifications**
- What: A service that wraps N services and tries each in sequence.
- Why: Lets the use case depend on one port while the infrastructure layer fans out to multiple channels.
- Where: `backend/infrastructure/notifications/composite_service.py`.

**[INFRASTRUCTURE] Celery fan-out**
- What: A beat task enqueues one task per item; each item task is independent.
- Why: Scrapes and notifications can run in parallel across workers without blocking each other.
- Where: `scrape_all_searches` → `scrape_search`, `dispatch_pending_alerts` → `send_alert_notification`.

---

## Pending

- **Alembic migrations** — database tables exist as SQLAlchemy models but no migration files yet. Required before the app can run.
- **Google Flights URL construction** — `_build_url()` in the scraper has placeholder URLs; the real Google Flights URL encoding (tfs parameter) needs to be implemented and tested.
- **Frontend** — HTML + Tailwind CSS dashboard not started.
- **Docker Compose** — no containerization yet; required to run PostgreSQL + Redis + Celery locally.
- **Tests** — no tests written yet. Application layer is fully testable with in-memory fake adapters.

---

## Next session starts at

`backend/infrastructure/persistence/` — run Alembic init and generate the first migration from the SQLAlchemy models.

Apply 20% Rule for: **Database migrations with Alembic**.
