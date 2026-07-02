from fastapi.testclient import TestClient


def test_store_and_retrieve(client):
    """Test event storage and retrieval."""
    payload = {
        "title": "Concert in the park",
        "date": "2026-07-15T19:00:00",
        "points": {"type": "MultiPoint", "coordinates": [[46.5197, 7.0], [46.52, 7.01]]},
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.json()}"
    body = resp.json()

    event_id = body["id"]
    assert body["title"] == "Concert in the park"

    resp = client.get(f"/api/events/{event_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == event_id


def test_list_events(client):
    """Test listing all events."""
    payload = {
        "title": "Test Event",
        "date": "2026-07-15T19:00:00",
        "points": None,
    }

    client.post("/api/events", json=payload)

    resp = client.get("/api/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1


def test_update_event(client):
    """Test updating an event."""
    payload = {
        "title": "Original Title",
        "date": "2026-07-15T19:00:00",
        "points": None,
    }

    resp = client.post("/api/events", json=payload)
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated Title",
        "date": "2026-07-16T20:00:00",
        "points": {"type": "MultiPoint", "coordinates": [[46.5, 7.0]]},
    }

    resp = client.put(f"/api/events/{event_id}", json=update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"


def test_delete_event(client):
    """Test deleting an event."""
    payload = {
        "title": "To Delete",
        "date": "2026-07-15T19:00:00",
        "points": None,
    }

    resp = client.post("/api/events", json=payload)
    event_id = resp.json()["id"]

    resp = client.delete(f"/api/events/{event_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/events/{event_id}")
    assert resp.status_code == 404


def test_create_event_with_extra_fields(client):
    """Test creating an event with extra fields."""
    payload = {
        "title": "Event with Extras",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "extra": {"organizer": "John Doe", "capacity": "100"},
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["extra"]["organizer"] == "John Doe"
    assert body["extra"]["capacity"] == "100"


def test_update_event_extra_fields(client):
    """Test updating extra fields on an event."""
    payload = {
        "title": "Original",
        "date": "2026-07-15T19:00:00",
        "extra": {"old": "value"},
    }

    resp = client.post("/api/events", json=payload)
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated",
        "date": "2026-07-15T19:00:00",
        "extra": {"new": "field", "another": "value"},
    }

    resp = client.put(f"/api/events/{event_id}", json=update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["extra"]["new"] == "field"
    assert "old" not in body["extra"]


def test_public_events_endpoint(client):
    """Test public events endpoint without auth."""
    payload = {
        "title": "Public Event",
        "date": "2026-07-15T19:00:00",
        "points": None,
    }

    client.post("/api/events", json=payload)

    resp = client.get("/api/public/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert any(e["title"] == "Public Event" for e in events)


def test_public_events_with_extra_fields(client):
    """Test public endpoint includes extra fields."""
    payload = {
        "title": "Special Event",
        "date": "2026-07-15T19:00:00",
        "extra": {"secret": "info"},
    }

    client.post("/api/events", json=payload)

    resp = client.get("/api/public/events")
    assert resp.status_code == 200
    events = resp.json()
    event = next(e for e in events if e["title"] == "Special Event")
    assert event["extra"]["secret"] == "info"


def test_admin_login(client):
    """Test admin login endpoint."""
    resp = client.post("/api/admin/login", json={"password": "admin"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_admin_login_wrong_password(client):
    """Test admin login with wrong password."""
    resp = client.post("/api/admin/login", json={"password": "wrong"})
    assert resp.status_code == 401


def test_events_require_auth(client):
    """Test that events endpoints require authentication."""
    from fastapi.testclient import TestClient
    from main import app

    public_client = TestClient(app)

    resp = public_client.get("/api/events")
    assert resp.status_code == 401

    resp = public_client.post("/api/events", json={
        "title": "Test",
        "date": "2026-07-15T19:00:00",
    })
    assert resp.status_code == 401


def test_points_normalization_list(client):
    """Test that points are stored as GeoJSON."""
    payload = {
        "title": "Point Test",
        "date": "2026-07-15T19:00:00",
        "points": [[46.5, 7.0], [46.6, 7.1]],
    }

    resp = client.post("/api/events", json=payload)
    body = resp.json()

    assert body["points"]["type"] == "MultiPoint"
    assert body["points"]["coordinates"][0] == [46.5, 7.0]
    assert body["points"]["coordinates"][1] == [46.6, 7.1]


def test_upload_rejects_invalid_content_type(client):
    """Test that upload rejects files with disallowed content types."""
    resp = client.post("/api/events", json={
        "title": "Upload Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
        data={"name": "malware", "image_type": "optical"},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_upload_rejects_oversized_file(client):
    """Test that upload rejects files exceeding the size limit."""
    resp = client.post("/api/events", json={
        "title": "Upload Size Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    large_content = b"x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte
    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("big.tif", large_content, "image/tiff")},
        data={"name": "big image", "image_type": "optical"},
    )
    assert resp.status_code == 413
    assert "exceeds" in resp.json()["detail"]


def test_upload_accepts_valid_png(client):
    """Test that upload accepts a valid PNG file."""
    resp = client.post("/api/events", json={
        "title": "PNG Upload Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.png", png_content, "image/png")},
        data={"name": "test image", "image_type": "optical"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["image"]["filename"].endswith("_test.png")


def test_login_rate_limit(client):
    """Test that login endpoint enforces rate limiting."""
    for _ in range(15):
        resp = client.post("/api/admin/login", json={"password": "wrong"})
        assert resp.status_code == 401

    resp = client.post("/api/admin/login", json={"password": "wrong"})
    assert resp.status_code == 429


def test_token_revocation(client):
    """Test that revoked tokens are rejected."""
    from auth import create_access_token, revoke_token, jwt, SECRET_KEY, ALGORITHM
    from fastapi.testclient import TestClient as PlainTestClient
    from main import app

    token = create_access_token()
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    revoke_token(payload["jti"])

    plain_client = PlainTestClient(app)
    resp = plain_client.get("/api/events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_extra_field_size_limit(client):
    """Test that extra field rejects payloads over 64KB."""
    large_extra = {"data": "x" * 65537}
    resp = client.post("/api/events", json={
        "title": "Big Extra",
        "date": "2026-07-15T19:00:00",
        "extra": large_extra,
    })
    assert resp.status_code == 422


def test_upload_rejects_magic_byte_mismatch(client):
    """Test that upload rejects file where magic bytes don't match Content-Type."""
    resp = client.post("/api/events", json={
        "title": "Magic Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("fake.png", b"NOT_A_REAL_PNG_FILE", "image/png")},
        data={"name": "fake", "image_type": "optical"},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"] or "Unable to determine" in resp.json()["detail"]


def test_get_event_images(client):
    """Test retrieving images for an event."""
    resp = client.post("/api/events", json={
        "title": "Images Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.png", png_content, "image/png")},
        data={"name": "test image", "image_type": "optical"},
    )

    resp = client.get(f"/api/events/{event_id}/images")
    assert resp.status_code == 200
    body = resp.json()
    assert "images" in body
    assert len(body["images"]) == 1
    assert body["images"][0]["name"] == "test image"


def test_get_event_images_not_found(client):
    """Test that get_event_images returns 404 for non-existent event."""
    resp = client.get("/api/events/000000000000000000000000/images")
    assert resp.status_code == 404


def test_format_points_returns_none_for_empty(client):
    """Test that empty points are normalized to None."""
    payload = {
        "title": "Empty Points",
        "date": "2026-07-15T19:00:00",
        "points": {},
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["points"] is None


def test_format_points_returns_none_for_invalid_dict(client):
    """Test that points dict without coordinates returns None."""
    payload = {
        "title": "Invalid Dict Points",
        "date": "2026-07-15T19:00:00",
        "points": {"type": "MultiPoint"},
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["points"] is None


def test_update_event_with_images(client):
    """Test updating an event's images field."""
    resp = client.post("/api/events", json={
        "title": "Update Images Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated with Images",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "images": [{"filename": "test.tif", "name": "test", "image_type": "optical"}],
    }

    resp = client.put(f"/api/events/{event_id}", json=update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["images"] is not None
    assert len(body["images"]) == 1


def test_invalid_token_rejected(client):
    """Test that invalid JWT tokens are rejected."""
    from fastapi.testclient import TestClient as PlainTestClient
    from main import app

    plain_client = PlainTestClient(app)
    resp = plain_client.get("/api/events", headers={"Authorization": "Bearer invalid_token"})
    assert resp.status_code == 401


def test_upload_to_nonexistent_event(client):
    """Test that upload to non-existent event returns 404."""
    resp = client.post(
        "/api/events/000000000000000000000000/images",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        data={"name": "test", "image_type": "optical"},
    )
    assert resp.status_code == 404


def test_upload_with_bounds(client):
    """Test that upload with bounds stores them correctly."""
    resp = client.post("/api/events", json={
        "title": "Bounds Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        data={"name": "satellite image", "image_type": "optical", "bounds": "6.0,46.0,8.0,47.0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["image"]["bounds"] == [6.0, 46.0, 8.0, 47.0]


def test_upload_rejects_tiff(client):
    """Test that TIFF files are rejected."""
    resp = client.post("/api/events", json={
        "title": "TIFF Reject",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.tif", b"II*\x00" + b"\x00" * 100, "image/tiff")},
        data={"name": "satellite image", "image_type": "optical"},
    )
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_create_event_with_news(client):
    """Test creating an event with news items."""
    payload = {
        "title": "Event with News",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "news": [
            {"title": "First news article", "extra": {"source": "Reuters"}},
            {"title": "Second news article", "extra": None},
        ],
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["news"] is not None
    assert len(body["news"]) == 2
    assert body["news"][0]["title"] == "First news article"
    assert body["news"][0]["extra"]["source"] == "Reuters"
    assert body["news"][1]["title"] == "Second news article"
    assert body["news"][1]["extra"] is None


def test_update_event_with_news(client):
    """Test updating an event's news items."""
    resp = client.post("/api/events", json={
        "title": "Original",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated with News",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "news": [{"title": "Updated news", "extra": {"url": "https://example.com"}}],
    }

    resp = client.put(f"/api/events/{event_id}", json=update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["news"] is not None
    assert len(body["news"]) == 1
    assert body["news"][0]["title"] == "Updated news"


def test_event_news_in_public_endpoint(client):
    """Test that news items are included in public endpoint."""
    payload = {
        "title": "Public News Event",
        "date": "2026-07-15T19:00:00",
        "news": [{"title": "Public news", "extra": {"category": "politics"}}],
    }

    client.post("/api/events", json=payload)

    resp = client.get("/api/public/events")
    assert resp.status_code == 200
    events = resp.json()
    event = next(e for e in events if e["title"] == "Public News Event")
    assert event["news"] is not None
    assert len(event["news"]) == 1
    assert event["news"][0]["title"] == "Public news"


def test_parse_bounds_invalid_count(client):
    """Test that bounds with wrong number of values are rejected."""
    resp = client.post("/api/events", json={
        "title": "Bad Bounds",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        data={"name": "img", "image_type": "optical", "bounds": "1.0,2.0,3.0"},
    )
    assert resp.status_code == 400
    assert "exactly 4 values" in resp.json()["detail"]


def test_parse_bounds_non_numeric(client):
    """Test that bounds with non-numeric values are rejected."""
    resp = client.post("/api/events", json={
        "title": "Bad Bounds",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    resp = client.post(
        f"/api/events/{event_id}/images",
        files={"file": ("test.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        data={"name": "img", "image_type": "optical", "bounds": "a,b,c,d"},
    )
    assert resp.status_code == 400
    assert "Invalid bounds format" in resp.json()["detail"]


def test_event_str_representation(setup_mongo):
    """Test that Event.__str__ returns the title."""
    from datetime import datetime
    from models import Event
    doc = Event(title="Test Event", date=datetime(2026, 7, 15)).save()
    assert str(doc) == "Test Event"


def test_create_event_with_news_extra_size_limit(client):
    """Test that news items with oversized extra fields are rejected."""
    huge_extra = {"data": "x" * 70000}
    resp = client.post("/api/events", json={
        "title": "News Extra Limit",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "news": [{"title": "Oversized", "extra": huge_extra}],
    })
    assert resp.status_code == 422


def test_create_event_with_carousel_images(client):
    """Test creating an event with carousel images."""
    payload = {
        "title": "Carousel Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "carousel_images": [
            {"url": "https://example.com/photo1.jpg", "description": "Before", "source_url": "https://example.com"},
            {"url": "https://example.com/photo2.jpg", "description": "After"},
        ],
    }

    resp = client.post("/api/events", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["carousel_images"]) == 2
    assert body["carousel_images"][0]["url"] == "https://example.com/photo1.jpg"
    assert body["carousel_images"][0]["description"] == "Before"
    assert body["carousel_images"][0]["source_url"] == "https://example.com"
    assert body["carousel_images"][1]["url"] == "https://example.com/photo2.jpg"
    assert body["carousel_images"][1]["description"] == "After"
    assert body["carousel_images"][1]["source_url"] is None


def test_update_event_carousel_images(client):
    """Test updating an event's carousel images."""
    resp = client.post("/api/events", json={
        "title": "Original",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated",
        "date": "2026-07-15T19:00:00",
        "points": None,
        "carousel_images": [{"url": "https://example.com/new.jpg", "description": "Updated view", "source_url": "https://source.com"}],
    }

    resp = client.put(f"/api/events/{event_id}", json=update_payload)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["carousel_images"]) == 1
    assert body["carousel_images"][0]["url"] == "https://example.com/new.jpg"
    assert body["carousel_images"][0]["description"] == "Updated view"
    assert body["carousel_images"][0]["source_url"] == "https://source.com"


def test_carousel_images_in_public_endpoint(client):
    """Test that carousel images are included in public endpoint."""
    payload = {
        "title": "Public Carousel",
        "date": "2026-07-15T19:00:00",
        "carousel_images": [{"url": "https://example.com/pub.jpg", "description": "Public photo"}],
    }

    client.post("/api/events", json=payload)

    resp = client.get("/api/public/events")
    events = resp.json()
    event = next(e for e in events if e["title"] == "Public Carousel")
    assert event["carousel_images"][0]["url"] == "https://example.com/pub.jpg"
    assert event["carousel_images"][0]["description"] == "Public photo"
