# Session 001 — 2026-04-14

## Goal
Apply the 20% Rule for hexagonal architecture, then write the domain layer: entities and ports.

---

## Completed

- `backend/domain/__init__.py` — module marker with dependency rule reminder
- `backend/domain/entities.py` — core domain entities
- `backend/domain/ports.py` — abstract port interfaces
- `docs/sessions/session-001.md` — this file

---

## Decisions made

- **`PriceHistory` added as a separate entity** — the rolling average calculation needs a time-series of observations per Search. Storing this as its own entity (vs. a field on Flight) keeps concerns separated and allows flexible windowing.
- **`Alert.is_significant()` as a domain method** — the rule "does this drop meet the threshold?" is pure business logic, so it lives on the entity, not in the use case.
- **`TripType` and `AlertStatus` as `str, Enum`** — inheriting from `str` makes JSON serialization transparent and avoids adapter-layer conversion boilerplate.
- **`date | None` syntax for `return_date`** — uses Python 3.10+ union syntax consistently throughout; no `Optional[]` import needed.
- **No `field(default_factory=...)` on mutable defaults** — all entities are constructed explicitly; no hidden mutation risk.

---

## Concepts covered

**[ARCHITECTURE] Hexagonal Architecture (Ports & Adapters)**
- What: Three concentric layers — domain (pure data + rules), application (use-case orchestration via ports), infrastructure (concrete I/O adapters). Dependencies point inward only.
- Why: Lets you swap any infrastructure component (scraper, DB, notification provider) without touching business logic. Enables full unit testing with fake adapters.
- Where: Every file in this project respects this boundary. `domain/` has zero external imports. `ports.py` defines what the app *needs*; `infrastructure/` defines what *satisfies* those needs.

**[DOMAIN] Dataclasses as entities**
- What: `@dataclass` generates `__init__`, `__repr__`, `__eq__` automatically. No ORM annotations, no serialization logic.
- Why: Keeps entities as pure data holders. The domain layer has no dependency on any framework.
- Where: `User`, `Flight`, `Search`, `PriceHistory`, `Alert` in `entities.py`.

**[DOMAIN] Abstract base classes as ports**
- What: `ABC` + `@abstractmethod` define a contract without an implementation. Any class that inherits and implements all abstract methods satisfies the port.
- Why: The application layer depends on the *interface*, not the *implementation*. Concrete adapters are injected by the composition root (infrastructure layer).
- Where: All classes in `ports.py`.

---

## Pending

- Nothing from this session's scope is pending.

---

## Next session starts at

`backend/application/` — define use cases: `CreateSearch`, `RunPriceScrape`, `EvaluatePriceDrop`, `SendAlertNotification`.

Apply 20% Rule for: **Use Cases / Command Pattern in the application layer**.
