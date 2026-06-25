# Resonate2 - Agent Instructions

## Development Workflow

**Every change must follow this cycle:**

1. **Understand the architecture** — Before writing code, understand the system context:
   - How does this change affect the overall architecture?
   - What are the security implications?
   - What components are affected?
   - Is there an existing pattern to follow?

2. **Write tests first (TDD)** — Define expected behavior:
   - Write failing tests that specify the desired outcome
   - Keep tests small and focused
   - Run tests to confirm they fail

3. **Implement minimally** — Write the simplest code that passes tests:
   - Follow existing code patterns
   - Don't over-engineer
   - Don't add features not covered by tests

4. **Verify tests pass** — Ensure implementation is correct:
   - Run `uv run pytest tests/ -v`
   - All tests must pass
   - No regressions in existing functionality

5. **Document and refactor** — Clean up and explain:
   - Add docstrings/comments where logic is complex
   - Refactor if code smells emerge
   - Update README/AGENTS.md if architecture changed
   - Ensure API documentation is current
   - **Update PlantUML diagrams** if architecture changed (see below)

6. **Update diagrams** — Keep architecture docs in sync:
   - Review `docs/diagrams/*.puml` for accuracy
   - Edit `.puml` files if components, flows, or schemas changed
   - Run `uv run python docs/diagrams/render.py` to regenerate SVGs
   - Commit both `.puml` and `.svg` files

## Architectural Principles

- **Security first** — Every endpoint must be evaluated against OWASP Top 10
- **Defense in depth** — Multiple validation layers (client + server + database)
- **Fail securely** — Errors must not leak implementation details
- **Least privilege** — Minimal permissions, explicit authentication
- **Separation of concerns** — Auth, business logic, and data access are distinct

## Commands

- **Install deps:** `uv sync` (or `uv sync --all-extras` for test deps)
- **Run tests:** `uv run pytest tests/ -v`
- **Run single test:** `uv run pytest tests/test_events.py::test_name -v`
- **Start dev server (API):** `uv run uvicorn main:app --reload`
- **Docker (all services):** `docker compose up --build`
- **Build frontend:** `cd frontend && npm run build`

## Project Layout

- **Flat layout** — no `src/`; `main.py` is the FastAPI entrypoint (module-level `app`)
- **Tests** in `tests/`; conftest provides authenticated `client` fixture
- **Frontend** — Vue 3 + Vite SPA in `frontend/`; proxies `/api/*` to backend via Nginx in Docker
- **Python 3.12** enforced by `.python-version`

## Architecture Diagrams

PlantUML diagrams are in `docs/diagrams/` and rendered as SVGs for the README.

| File | Content |
|------|---------|
| `architecture.puml` | System component overview |
| `components.puml` | Data model class diagram |
| `auth-flow.puml` | Authentication sequence |
| `upload-flow.puml` | Image upload sequence |

**Always do when making architectural changes:**
1. **Check** — Read the relevant `.puml` file to understand current state
2. **Update** — Edit the `.puml` if components, flows, or schemas changed
3. **Render** — Run `uv run python docs/diagrams/render.py`
4. **Verify** — Open `docs/diagrams/*.svg` to confirm diagrams look correct
5. **Commit** — Include both `.puml` and `.svg` files

## API Routes

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/admin/login` | None | Login, returns JWT (rate-limited: 5/min) |
| `GET /api/events` | JWT | List all events |
| `POST /api/events` | JWT | Create event |
| `GET /api/events/{id}` | JWT | Get single event |
| `PUT /api/events/{id}` | JWT | Update event |
| `DELETE /api/events/{id}` | JWT | Delete event |
| `POST /api/events/{id}/images` | JWT | Upload image (PNG/JPEG/TIFF, max 50MB) |
| `GET /api/events/{id}/images` | JWT | List event images |
| `GET /api/public/events` | None | Public read-only |

## Environment (`.env`)

```
ADMIN_PASSWORD=<set-strong-password>
ADMIN_SECRET_KEY=<random-hex-string>
MONGO_PASSWORD=<set-strong-password>
MONGO_HOST=mongodb://resonate:${MONGO_PASSWORD}@mongodb:27017/resonate?authSource=admin
```

## Architecture

- **MongoEngine ODM** — `main.py` defines `Event` document
- **Coordinates**: API accepts/returns `{"lat": float, "lng": float}` dicts; MongoEngine stores `(lat, lng)` tuples. Conversion at endpoint boundaries.
- **Auth**: JWT (HS256, 15min expiry) + Argon2id password hashing
- **Uploads**: Magic byte validation via `filetype` library, rasterio for TIF processing

## Testing

- **conftest.py** provides `client` fixture with automatic JWT auth
- Routes use `/api` prefix in tests (e.g., `client.get("/api/events")`)
- Tests use mongomock via `mongo_client_class=mongomock.MongoClient`
- Do NOT use `mongomock://` URIs — removed in mongoengine 0.27+
- `main.py` has connection guard: `if "default" not in mongoengine.connection._connections` — allows test fixtures to pre-connect
- Rate limiter is reset between tests via `reset_rate_limiter` fixture

## Code Review Checklist

Before merging any change, verify:

- [ ] Tests written and passing
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user-supplied data
- [ ] Error messages don't leak implementation details
- [ ] No new OWASP vulnerabilities introduced
- [ ] Code follows existing patterns
- [ ] Documentation updated if architecture changed
