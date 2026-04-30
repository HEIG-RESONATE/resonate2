from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def test_store_and_retrieve():
    """Mock MongoDB and test document storage."""
    # Create mock collection
    mock_collection = MagicMock()
    mock_result = MagicMock()
    mock_result.inserted_id = "mocked-id-123"
    mock_collection.insert_one.return_value = mock_result

    def find_side_effect(query):
        if query.get("_id") == "mocked-id-123":
            return {
                "_id": "mocked-id-123",
                "source": "x",
                "text": "Hello from the farm!",
                "coordinates": {"lat": 46.5, "lng": 7.0},
            }
        return None

    mock_collection.find_one.side_effect = find_side_effect

    # Remove pymongo cache and patch at module level BEFORE importing main
    import sys
    import types

    for key in list(sys.modules.keys()):
        if "pymongo" in key:
            del sys.modules[key]

    fake_pymongo = types.ModuleType("pymongo")
    fake_mongo_client = MagicMock(return_value=MagicMock(documents=MagicMock(document=mock_collection)))
    fake_pymongo.MongoClient = fake_mongo_client
    sys.modules["pymongo"] = fake_pymongo

    # Now import main (it will use the mocked pymongo)
    from main import app

    client = TestClient(app)

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
