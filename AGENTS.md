# Resonate2 - Agent Instructions

## Commands (always `uv run` — never bare `python` or `pytest`)
- **Install deps:** `uv sync` (or `uv sync --all-extras` for test deps)
- **Run tests:** `uv run pytest tests/ -v`
- **Run single test:** `uv run pytest tests/test_documents.py -v`
- **Start dev server (API):** `uv run uvicorn main:app --reload`
- **Docker (both services):** `docker compose up --build`

## Project layout
- **Flat layout** — no `src/`; `main.py` is the FastAPI entrypoint (module-level `app`)
- **Tests** import from root via `conftest.py` sys.path patch
- **Frontend** — Vue 3 + Vite SPA in `frontend/`; proxies `/api/*` to backend via Nginx in Docker
- **Python 3.12** enforced by `.python-version`

## Architecture
- **MongoEngine ODM** (not raw pymongo) — `main.py` defines a `Document` model with `GeoPointField`
- **Coordinates**: API accepts/returns `{"lat": float, "lng": float}` dicts, but MongoEngine stores `(lat, lng)` tuples. Conversion happens at endpoint boundaries.

## Testing quirks
- **Test deps are optional** — run `uv sync --all-extras` first if pytest/mongomock aren't installed
- **conftest.py** has an `autouse=True` `setup_mongo` fixture that connects mongoengine to mongomock via `mongo_client_class=mongomock.MongoClient`. Tests use a real in-memory DB, no manual mocking needed.
- **Do NOT use `mongomock://` URIs** — removed in mongoengine 0.27+. Always use `mongo_client_class=mongomock.MongoClient`.
- Use the `client` fixture from conftest (returns `TestClient(app)`) — don't construct your own.

## Workflow rules
1. **TDD (RED → GREEN → REFACTOR):** write failing test first, then minimal implementation, then refactor.
2. **Brainstorm when possible:** explore alternatives before coding.
