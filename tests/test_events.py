from fastapi.testclient import TestClient


def test_store_and_retrieve(client):
    """Test event storage and retrieval."""
    payload = {
        "title": "Concert in the park",
        "date": "2026-07-15T19:00:00",
        "points": {"type": "MultiPoint", "coordinates": [[46.5197, 7.0], [46.52, 7.01]]},
    }

    resp = client.post("/events", json=payload)
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.json()}"
    body = resp.json()

    event_id = body["id"]
    assert body["title"] == "Concert in the park"

    resp = client.get(f"/events/{event_id}")
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

    client.post("/events", json=payload)

    resp = client.get("/events")
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

    resp = client.post("/events", json=payload)
    event_id = resp.json()["id"]

    update_payload = {
        "title": "Updated Title",
        "date": "2026-07-16T20:00:00",
        "points": {"type": "MultiPoint", "coordinates": [[46.5, 7.0]]},
    }

    resp = client.put(f"/events/{event_id}", json=update_payload)
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

    resp = client.post("/events", json=payload)
    event_id = resp.json()["id"]

    resp = client.delete(f"/events/{event_id}")
    assert resp.status_code == 204

    resp = client.get(f"/events/{event_id}")
    assert resp.status_code == 404
