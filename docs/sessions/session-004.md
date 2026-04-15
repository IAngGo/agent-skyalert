# Session 004 — 2026-04-14

## Goal
Build the HTML + Tailwind CSS frontend: dashboard, new search form, and alert detail page.

---

## Completed

- `backend/infrastructure/api/main.py` — added `StaticFiles` mount at `/app`
- `frontend/js/api.js` — all `fetch()` calls in one module (ES module, same-origin)
- `frontend/css/custom.css` — fade-in animation + alert status badge colors
- `frontend/index.html` — dashboard: search cards with inline alert rows
- `frontend/search.html` — new search form with trip-type toggle
- `frontend/alert.html` — alert detail: price comparison, flight info, confirm/buy buttons
- `docs/sessions/session-004.md` — this file

---

## Decisions made

- **Tailwind Play CDN — no build step** — MVP priority is speed and explainability.
  The CDN adds ~350kb; acceptable for a SaaS with low initial traffic.
  Can be replaced with the Tailwind CLI build when traffic warrants it.
- **ES modules (`type="module"`) for JS** — enables `import`/`export` without a bundler.
  `api.js` is imported by each page independently; no global namespace pollution.
- **`localStorage` for user ID** — no auth yet. User pastes their UUID once and it
  persists across pages. Replace with a proper session when auth is added.
- **`<template>` elements for card/row cloning** — avoids innerHTML string injection
  (XSS risk) and is more readable than manual `createElement` chains.
- **Alert detail linked from email/WhatsApp** — `alert.html?id=UUID` is the URL
  included in notifications. The page reads the `id` query param on load.
- **`StaticFiles(html=True)`** — FastAPI serves `index.html` automatically for
  directory requests to `/app/`, so the user can navigate to `/app/` directly.

---

## Concepts covered

**[FRONTEND] Tailwind utility-first CSS**
- What: Classes like `bg-white rounded-xl shadow-sm p-5` compose styles directly in HTML
  without writing a separate stylesheet. Each class maps to one CSS declaration.
- Why: No context-switching between HTML and CSS files. No naming things. Styles are
  co-located with the markup they affect.
- Where: All three HTML pages.

**[FRONTEND] ES Modules without a bundler**
- What: `<script type="module">` enables `import`/`export` in the browser natively.
  No Webpack, Vite, or Rollup needed.
- Why: Keeps the stack simple. `api.js` is a single source of truth for all API calls.
- Where: `api.js` exports functions; each HTML page imports only what it needs.

**[FRONTEND] `<template>` for safe DOM cloning**
- What: Content inside `<template>` is inert (not rendered, not executed). JS clones it
  with `tpl.content.cloneNode(true)` and populates it before inserting into the DOM.
- Why: Safer than `innerHTML` (no XSS from user data), more readable than `createElement`.
- Where: `index.html` — `searchCardTpl` and `alertRowTpl`.

---

## Pending

- **Auth** — user ID is stored in localStorage as a plain UUID. Replace with
  proper login/session when ready.
- **Register page** — no UI to create a user yet; users must call `POST /users` directly.
- **Tests** — no tests written yet.
- **Google Flights URL construction** — scraper `_build_url()` still has placeholder encoding.

---

## Next session starts at

`tests/` — pytest suite with in-memory fake adapters for all use cases.

Apply 20% Rule for: **Testing with fakes vs. mocks**.
