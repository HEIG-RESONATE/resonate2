from fastapi.testclient import TestClient


def test_store_and_retrieve(client):
    """Test document storage and retrieval."""
    payload = {
        "source": "x",
        "text": "Hello from the farm!",
        "coordinates": {"lat": 46.5, "lng": 7.0},
    }

    resp = client.post("/documents", json=payload)
    assert resp.status_code == 201
    body = resp.json()

    doc_id = body["id"]
    assert body["source"] == "x"
    assert body["text"] == "Hello from the farm!"

    resp = client.get(f"/documents/{doc_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == doc_id
