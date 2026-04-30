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
