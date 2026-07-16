# Resonate2

A map-based event management application with satellite imagery support. Built with FastAPI, MongoDB, and Vue.js.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose

### Installation

```bash
# Clone the repository
git clone git@github.com:SimWalther/resonate2.git
cd resonate2

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Environment Setup

Copy `.env.example` to `.env` and set your secrets:

```bash
cp .env.example .env
# Edit .env with your secure passwords
```

### Running with Docker (Recommended)

```bash
docker compose up --build
```

- Frontend: http://localhost
- API: http://localhost:8000
- MongoDB: mongodb://localhost:27017 (internal only)

### Running Locally (Development)

```bash
# Terminal 1: API
uv run uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

## Architecture Overview

![Architecture Diagram](docs/diagrams/architecture.svg)

## Component Diagram

![Component Diagram](docs/diagrams/components.svg)

## Authentication Flow

![Auth Flow](docs/diagrams/auth-flow.svg)

## Image Upload Flow

![Upload Flow](docs/diagrams/upload-flow.svg)

## API Documentation

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/admin/login` | POST | None | Login, returns JWT |
| `/api/events` | GET | JWT | List all events |
| `/api/events` | POST | JWT | Create event |
| `/api/events/{id}` | GET | JWT | Get single event |
| `/api/events/{id}` | PUT | JWT | Update event |
| `/api/events/{id}` | DELETE | JWT | Delete event |
| `/api/events/{id}/images` | POST | JWT | Upload georeferenced satellite image |
| `/api/events/{id}/images` | GET | JWT | List uploaded satellite images |
| `/api/events/{id}/satellite-images` | POST | JWT | Alias for uploading georeferenced satellite images |
| `/api/events/{id}/satellite-images` | GET | JWT | Alias for listing uploaded satellite images |
| `/api/events/{id}/satellite-images/{image_id}/access` | GET | JWT | Mint a short-lived URL for an image preview or original |
| `/api/public/events` | GET | None | Public read-only |

Event-list endpoints accept `sort_by=date|added` and `direction=asc|desc`. Each
event includes its immutable `created_at` timestamp and `is_latest`, which is
true only for the most recently added record. Existing records without a stored
timestamp use their MongoDB ObjectId creation time.

### Event Schema

```json
{
  "id": "string",
  "title": "string",
  "date": "ISO 8601 datetime",
  "points": {
    "type": "MultiPoint",
    "coordinates": [[lng, lat], ...]
  },
  "extra": {
    "key": "value"
  },
  "images": [
    {
      "id": "opaque-image-id",
      "filename": "string",
      "name": "string",
      "image_type": "optical|sar",
      "bounds": [west, south, east, north],
      "preview": "string",
      "content_type": "image/png"
    }
  ],
  "news": [
    {
      "title": "string",
      "url": "string",
      "author": "string",
      "extra": {
        "key": "value"
      }
    }
  ],
  "carousel_images": [
    {
      "url": "string",
      "description": "string",
      "source_url": "string"
    }
  ]
}
```

Vocabulary:
- `images`: georeferenced satellite/raster overlays uploaded through the image upload endpoint and positioned on the map with `bounds`
- `carousel_images`: photos and other non-georeferenced reference images shown alongside event analysis

### Upload Validation

- **Allowed types**: PNG, JPEG (detected by magic bytes)
- **Max size**: 50MB
- **Bounds**: Optional, user-provided `west,south,east,north` for map overlay positioning

### Satellite-image access URLs

Authenticated clients obtain an agent/browser-safe, short-lived URL with:

```text
GET /api/events/{event_id}/satellite-images/{image_id}/access?variant=preview
```

`variant` is `preview` (the default) or `original`. The response includes `image_id`,
`event_id`, `variant`, `url`, `filename`, `content_type`, and an ISO-8601 `expires_at`.
The URL is an opaque HMAC-signed backend URL, valid for five minutes by default
(`IMAGE_ACCESS_TTL_SECONDS`, capped at 15 minutes), and does not expose a storage
path, object key, bearer token, or credentials. It can be loaded without an admin
bearer token until it expires. Uploaded PNG/JPEG files use the existing preview
object; a missing preview returns `404 Preview not available`.

Image metadata now always has an opaque `id`. Existing image records are migrated
lazily: the first event or image-list read assigns UUIDs and saves them, so no manual
migration is required. Do not treat `filename` or `preview` as a stable identifier or
public URL.

The map UI also loads existing PNG/JPEG overlays through `/images/{preview}`. In the
Compose deployment, this stable overlay path is protected by the frontend's Nginx
Basic Auth layer; the API's host port is bound to `127.0.0.1` so it cannot bypass that
proxy from the network. Agent and Chainlit integrations should continue to use the
short-lived access endpoint instead.

## Project Structure

```
resonate2/
├── main.py              # FastAPI application & routes (thin layer)
├── auth.py              # JWT & password utilities
├── models.py            # MongoEngine document definitions
├── schemas.py           # Pydantic request/response models
├── services/
│   ├── __init__.py
│   ├── events.py        # Event CRUD logic
│   └── images.py        # Image upload & processing
├── pyproject.toml       # Python dependencies
├── docker-compose.yml   # Docker services
├── Dockerfile           # API container
├── .env.example         # Environment template
├── tests/
│   ├── conftest.py      # Test fixtures
│   └── test_events.py   # API tests (31 tests)
├── docs/
│   └── diagrams/
│       ├── *.puml       # PlantUML source files
│       ├── *.svg        # Rendered diagrams
│       └── render.py    # Render script
└── frontend/
    ├── src/
    │   └── views/
    │       ├── Home.vue     # Public map + timeline
    │       └── Admin.vue    # Event management
    ├── cypress/
    │   ├── e2e/
    │   │   ├── auth.cy.js       # E2E auth tests
    │   │   └── timeline.cy.js   # E2E timeline filter tests
    │   └── support/
    │       ├── e2e.js
    │       └── commands.js # Custom commands
    ├── cypress.config.js   # Cypress configuration
    ├── nginx.conf        # Reverse proxy config
    └── Dockerfile        # Frontend container
```

## Regenerating Diagrams

```bash
uv run python docs/diagrams/render.py
```

This uses the public PlantUML server to render SVGs from `.puml` files.

## Development Workflow

See `AGENTS.md` for the complete development process.

### Quick Start

```bash
# Run tests
uv run pytest tests/ -v

# Build frontend
cd frontend && npm run build

# Start development
docker compose up --build

# Run E2E tests (requires running app)
cd frontend && npm run cy:run
```

## Testing

### Unit & Integration Tests

```bash
uv run pytest tests/ -v
```

30 tests covering CRUD, authentication, validation, image uploads, and more.

### E2E Tests (Cypress)

```bash
cd frontend
npm run cy:run    # headless
npm run cy:open   # interactive UI
```

5 tests covering the admin JWT authentication flow:
- Login with correct/wrong password
- Create and delete events
- Navigation between admin and map
- JWT persistence across page reloads
