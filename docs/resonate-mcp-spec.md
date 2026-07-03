# Resonate MCP Server Spec

## Purpose

Build a Python MCP server with `FastMCP` that exposes the Resonate2 HTTP API as MCP tools.

This server is an API adapter for Resonate2. It should model the API cleanly for agents and should not take on broader database responsibilities.

## Ground Truth From This Project

The MCP server must reflect the behavior implemented in this repository:

- API routes: `main.py`
- Auth: `auth.py`
- Event schema: `models.py`
- Request/response models: `schemas.py`
- Event normalization and persistence: `services/events.py`
- Image upload processing: `services/images.py`

## Goals

The server should let an external agent:

- authenticate against the admin API
- list public and admin events
- get a single event
- create, update, and delete events
- upload and list event images

## Non-Goals

- no direct database integration
- no generic arbitrary HTTP proxy tool
- no attempt to replace a separate MongoDB MCP server

## Configuration

The MCP server should read configuration from environment variables:

- `RESONATE_API_BASE_URL`
  - Example: `http://localhost:8000`
- `RESONATE_ADMIN_PASSWORD`
- `RESONATE_TIMEOUT_SECONDS` (default: `30`)

## Operating Rules

1. All event operations must go through the HTTP API.
2. Public event reads should prefer `GET /api/public/events` when authentication is not needed.
3. Authenticated event reads should use the admin API.
4. On API `401`, the server should refresh the token once and retry once.

## Backend API Contract

### Authentication

- **Endpoint:** `POST /api/admin/login`
- **Request body:**

```json
{
  "password": "admin-password"
}
```

- **Response body:**

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### Events

- `GET /api/events`
- `GET /api/events/{event_id}`
- `POST /api/events`
- `PUT /api/events/{event_id}`
- `DELETE /api/events/{event_id}`
- `GET /api/public/events`

### Images

- `POST /api/events/{event_id}/images`
- `GET /api/events/{event_id}/images`

## Canonical Event Shape

### API Response Event

```json
{
  "id": "68624d7d9fabcd1234567890",
  "title": "Event title",
  "date": "2026-07-15T19:00:00",
  "points": {
    "type": "MultiPoint",
    "coordinates": [[46.5197, 7.0], [46.52, 7.01]]
  },
  "extra": {
    "category": "news-cluster"
  },
  "images": [
    {
      "filename": "68624d7d9fabcd1234567890_1719745000.1_image.tif",
      "name": "Satellite image",
      "image_type": "optical",
      "bounds": [6.0, 46.0, 8.0, 47.0],
      "preview": "68624d7d9fabcd1234567890_1719745000.1_image_preview.png"
    }
  ],
  "news": [
    {
      "title": "Article title",
      "extra": {
        "source": "Reuters",
        "url": "https://example.com/article"
      }
    }
  ]
}
```

## Validation and Normalization Rules

The MCP server should preserve these backend assumptions:

### Dates

- `date` must be an ISO-8601 string parseable by Python `datetime.fromisoformat(...)`.

### Points

- `points` may be omitted or `null`
- `points` may be:
  - a coordinate list: `[[lat, lng], ...]`
  - a GeoJSON-like object:

```json
{
  "type": "MultiPoint",
  "coordinates": [[46.5, 7.0]]
}
```

- if a list is sent, the backend normalizes it into the GeoJSON-like object
- if an invalid dict is sent without `coordinates`, the API may return `points: null`

### Extra Fields

- `extra` is optional and must fit within roughly 64 KB serialized JSON
- `news[*].extra` follows the same size constraint

### News

- `news` is an optional list of:

```json
{
  "title": "string",
  "extra": {}
}
```

### Images

- upload is multipart form data
- accepted file types are detected by magic bytes, not only filename or content type
- allowed types:
  - PNG
  - JPEG
  - TIFF
- max upload size is 50 MB
- TIFF uploads may generate:
  - `bounds`
  - `preview`

## Recommended MCP Tool Surface

### `resonate_login_admin`

Authenticates with the admin API and caches a bearer token.

**Input**

```json
{}
```

**Output**

```json
{
  "success": true,
  "token_type": "bearer",
  "expires_in_minutes": 15
}
```

### `resonate_list_events`

Lists events from the authenticated or public API.

**Input**

```json
{
  "use_public": false
}
```

**Output**

```json
{
  "events": []
}
```

### `resonate_get_event`

Gets a single event by id.

**Input**

```json
{
  "event_id": "68624d7d9fabcd1234567890"
}
```

**Output**

```json
{
  "event": {}
}
```

### `resonate_create_event`

Creates an event through the API.

**Input**

```json
{
  "title": "Event title",
  "date": "2026-07-15T19:00:00",
  "points": {
    "type": "MultiPoint",
    "coordinates": [[46.5197, 7.0]]
  },
  "extra": {
    "category": "news-cluster"
  },
  "images": [],
  "news": [
    {
      "title": "Article title",
      "extra": {
        "source": "Reuters"
      }
    }
  ]
}
```

**Output**

```json
{
  "event": {}
}
```

### `resonate_update_event`

Updates an event through the API.

The backend uses full update semantics for core event fields. Treat this as replace-style rather than patch-style.

**Input**

```json
{
  "event_id": "68624d7d9fabcd1234567890",
  "title": "Updated title",
  "date": "2026-07-16T20:00:00",
  "points": null,
  "extra": {
    "status": "verified"
  },
  "images": [],
  "news": []
}
```

**Output**

```json
{
  "event": {}
}
```

### `resonate_delete_event`

Deletes an event by id.

**Input**

```json
{
  "event_id": "68624d7d9fabcd1234567890"
}
```

**Output**

```json
{
  "success": true
}
```

### `resonate_list_public_events`

Returns the public event feed.

**Input**

```json
{}
```

**Output**

```json
{
  "events": []
}
```

### `resonate_upload_event_image`

Uploads an image to an event using multipart form data.

Support one of:

- `file_path`
- `file_bytes_base64`

**Input**

```json
{
  "event_id": "68624d7d9fabcd1234567890",
  "file_path": "/absolute/path/to/image.tif",
  "filename": "image.tif",
  "name": "Satellite image",
  "image_type": "optical"
}
```

**Output**

```json
{
  "image": {
    "filename": "stored-file-name.tif",
    "name": "Satellite image",
    "image_type": "optical",
    "bounds": [6.0, 46.0, 8.0, 47.0],
    "preview": "stored-file-name_preview.png"
  }
}
```

### `resonate_get_event_images`

Returns image metadata for an event.

**Input**

```json
{
  "event_id": "68624d7d9fabcd1234567890"
}
```

**Output**

```json
{
  "images": []
}
```

## Error Model

Map HTTP errors into stable MCP-friendly error codes.

Recommended error codes:

- `AUTH_FAILED`
- `AUTH_RATE_LIMITED`
- `NOT_FOUND`
- `VALIDATION_ERROR`
- `FILE_TOO_LARGE`
- `UNSUPPORTED_FILE_TYPE`
- `API_ERROR`
- `CONFIG_ERROR`

Recommended shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "extra field exceeds 64KB limit",
    "details": {}
  }
}
```

## Python Implementation Guidance

### Recommended Stack

- Python 3.12
- `FastMCP`
- `httpx` for API calls
- `pydantic` for local validation and tool schemas

### Suggested Internal Modules

- `server.py`
  - MCP server bootstrap
- `config.py`
  - environment loading and validation
- `api_client.py`
  - HTTP transport and token refresh
- `models.py`
  - Pydantic request and response types
- `tools/events.py`
  - event tools
- `tools/images.py`
  - image tools
- `errors.py`
  - stable error mapping

### Token Management

- keep the bearer token in memory
- acquire lazily on first protected call
- retry once on `401`
- do not expose the token itself in tool outputs

## Acceptance Criteria

The MCP server is complete when it:

- can authenticate successfully with `POST /api/admin/login`
- can create, update, fetch, list, and delete events through the API
- can upload valid PNG/JPEG/TIFF files through the API
- can list event images
- returns compact JSON responses suitable for autonomous agents
