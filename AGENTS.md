# Resonate2 - Agent Instructions

## Commands
- **Install deps:** `uv sync` (or `uv sync --all-extras` for test deps)
- **Run tests:** `uv run pytest tests/ -v`
- **Run single test:** `uv run pytest tests/test_events.py::test_name -v`
- **Start dev server (API):** `uv run uvicorn main:app --reload`
- **Docker (all services):** `docker compose up --build`
- **Build frontend:** `cd frontend && npm run build`

## Project layout
- **Flat layout** — no `src/`; `main.py` is the FastAPI entrypoint (module-level `app`)
- **Tests** in `tests/`; conftest provides authenticated `client` fixture
- **Frontend** — Vue 3 + Vite SPA in `frontend/`; proxies `/api/*` to backend via Nginx in Docker
- **Python 3.12** enforced by `.python-version`

## API Routes
| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/admin/login` | None | Login, returns JWT |
| `GET /api/events` | JWT | List all events |
| `POST /api/events` | JWT | Create event |
| `GET /api/events/{id}` | JWT | Get single event |
| `PUT /api/events/{id}` | JWT | Update event |
| `DELETE /api/events/{id}` | JWT | Delete event |
| `GET /api/public/events` | None | Public read-only |

## Environment (`.env`)
```
ADMIN_PASSWORD=<set-strong-password>
ADMIN_SECRET_KEY=<random-hex-string>
MONGO_HOST=mongodb
```

## Architecture
- **MongoEngine ODM** — `main.py` defines `Event` document with `GeoPointField`
- **Coordinates**: API accepts/returns `{"lat": float, "lng": float}` dicts; MongoEngine stores `(lat, lng)` tuples. Conversion at endpoint boundaries.

## Testing
- **conftest.py** provides `client` fixture with automatic JWT auth
- Routes use `/api` prefix in tests (e.g., `client.get("/api/events")`)
- Tests use mongomock via `mongo_client_class=mongomock.MongoClient`
- Do NOT use `mongomock://` URIs — removed in mongoengine 0.27+
- `main.py` has connection guard: `if "default" not in mongoengine.connection._connections` — allows test fixtures to pre-connect

## Workflow
1. **TDD**: write failing test first, then minimal implementation
2. Verify with `uv run pytest tests/ -v` before committing
3. Frontend needs rebuild after Vue changes: `cd frontend && npm run build`