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


def test_upload_tif_with_bounds(client):
    """Test that TIF upload extracts bounds and creates preview."""
    import rasterio
    import numpy as np
    import tempfile
    import os

    resp = client.post("/api/events", json={
        "title": "TIF Test",
        "date": "2026-07-15T19:00:00",
        "points": None,
    })
    event_id = resp.json()["id"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name
        try:
            with rasterio.open(
                tmp_path,
                "w",
                driver="GTiff",
                height=100,
                width=100,
                count=3,
                dtype=np.uint8,
                crs="EPSG:4326",
                transform=rasterio.transform.from_bounds(6.0, 46.0, 8.0, 47.0, 100, 100),
            ) as dst:
                data = np.random.randint(0, 255, (3, 100, 100), dtype=np.uint8)
                dst.write(data)

            with open(tmp_path, "rb") as f:
                tif_content = f.read()

            resp = client.post(
                f"/api/events/{event_id}/images",
                files={"file": ("test.tif", tif_content, "image/tiff")},
                data={"name": "satellite image", "image_type": "optical"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["status"] == "ok"
            assert body["image"]["bounds"] is not None
            assert len(body["image"]["bounds"]) == 4
            assert body["image"]["preview"] is not None

        finally:
            os.unlink(tmp_path)
