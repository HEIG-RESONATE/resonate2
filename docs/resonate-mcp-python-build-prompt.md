# Prompt: Build a Python FastMCP Server for Resonate2

Use this prompt with Codex or Claude Code.

---

Build a Python MCP server named `resonate-mcp` for the Resonate2 project using `FastMCP`.

## Objective

Implement an MCP server that exposes the Resonate2 HTTP API as MCP tools.

This server is an API adapter. Keep it focused on the Resonate2 API surface.

## Backend Contract

The backend being integrated has these routes:

- `POST /api/admin/login`
- `GET /api/events`
- `GET /api/events/{event_id}`
- `POST /api/events`
- `PUT /api/events/{event_id}`
- `DELETE /api/events/{event_id}`
- `POST /api/events/{event_id}/images`
- `GET /api/events/{event_id}/images`
- `GET /api/public/events`

Authentication:

- login with `POST /api/admin/login`
- request body: `{"password":"..."}`
- response body includes `access_token` and `token_type`
- use `Authorization: Bearer <token>`
- token lifetime is 15 minutes
- on `401`, refresh token once and retry once

Event shape:

```json
{
  "id": "string",
  "title": "string",
  "date": "ISO-8601 string",
  "points": {
    "type": "MultiPoint",
    "coordinates": [[46.5, 7.0]]
  },
  "extra": {},
  "images": [],
  "news": [
    {
      "title": "string",
      "extra": {}
    }
  ]
}
```

Validation/behavior that must be preserved:

- `date` must be ISO-8601 parseable
- `points` may be either:
  - `[[lat, lng], ...]`
  - `{"type":"MultiPoint","coordinates":[...]}`
- `extra` and `news[*].extra` should be treated as max ~64KB JSON
- image upload accepts PNG, JPEG, TIFF
- image upload max size is 50MB
- TIFF upload may produce `bounds` and `preview`

## Build Requirements

Use Python 3.12.

Use:

- `FastMCP`
- `httpx`
- `pydantic`

Implement environment-based configuration:

- `RESONATE_API_BASE_URL`
- `RESONATE_ADMIN_PASSWORD`
- `RESONATE_TIMEOUT_SECONDS` (default `30`)

## Required MCP Tools

Implement these tools:

1. `resonate_login_admin`
2. `resonate_list_events`
3. `resonate_get_event`
4. `resonate_create_event`
5. `resonate_update_event`
6. `resonate_delete_event`
7. `resonate_list_public_events`
8. `resonate_upload_event_image`
9. `resonate_get_event_images`

## Tool Semantics

### `resonate_login_admin`

- authenticates using configured admin password
- caches token in memory
- returns success metadata only, not the raw token

### `resonate_list_events`

- input: optional `use_public: bool = false`
- if `use_public` is true, call `GET /api/public/events`
- otherwise call authenticated `GET /api/events`

### `resonate_get_event`

- input: `event_id`
- call authenticated `GET /api/events/{event_id}`

### `resonate_create_event`

- create event through `POST /api/events`
- accept:
  - `title`
  - `date`
  - optional `points`
  - optional `extra`
  - optional `images`
  - optional `news`

### `resonate_update_event`

- update event through `PUT /api/events/{event_id}`
- treat update as replace-style for core fields, not patch-style

### `resonate_delete_event`

- delete through `DELETE /api/events/{event_id}`

### `resonate_list_public_events`

- call `GET /api/public/events`

### `resonate_upload_event_image`

- upload with multipart form data
- accept either:
  - `file_path`
  - or `file_bytes_base64`
- also accept:
  - `filename`
  - `name`
  - optional `image_type` defaulting to `optical`

### `resonate_get_event_images`

- call authenticated `GET /api/events/{event_id}/images`

## Implementation Constraints

- Route all operations through the API
- Do not expose a generic arbitrary HTTP tool
- Return compact JSON responses
- Normalize backend errors into stable machine-readable error codes

## Error Codes

Use these error codes:

- `AUTH_FAILED`
- `AUTH_RATE_LIMITED`
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_FILE_TYPE`
- `API_ERROR`
- `CONFIG_ERROR`

Return errors in this shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "human-readable message",
    "details": {}
  }
}
```

## Suggested Project Structure

Create a clean Python package structure such as:

```text
resonate-mcp/
  pyproject.toml
  README.md
  src/resonate_mcp/
    __init__.py
    server.py
    config.py
    api_client.py
    errors.py
    models.py
    tools/
      __init__.py
      events.py
      images.py
```

## Code Quality Requirements

- use typed Python throughout
- define Pydantic models for tool inputs and outputs
- separate transport, business logic, and tool registration
- keep the API client small and explicit
- add concise docstrings where logic is non-obvious

## Deliverables

Produce:

1. working Python MCP server code
2. `pyproject.toml`
3. `README.md` with setup and environment variables
4. example `.env.example`
5. minimal tests for:
   - auth token refresh behavior
   - event create/list flow with mocked API
   - error mapping

## Validation

Before finishing:

- run tests
- ensure imports are clean
- ensure the tool names exactly match the required names

## Important Design Intent

This MCP server is meant to be the normal control plane for an agent interacting with Resonate2.

Use this policy:

- API only
- keep the server narrow and explicit

If tradeoffs arise, keep the design simple and explicit rather than generic.

---

If useful, you may also generate a short `SPEC.md` inside the new MCP project summarizing the above contract.
