import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(mocker) -> TestClient:
    """Mock MongoDB and return test client."""
    from unittest.mock import MagicMock
    import types

    # Create mock collection with proper setup
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

    # Create fake pymongo module
    fake_pymongo = types.ModuleType("pymongo")
    fake_mongo_client = MagicMock(return_value=MagicMock(documents=MagicMock(document=mock_collection)))
    fake_pymongo.MongoClient = fake_mongo_client

    # Patch pymongo before importing main
    sys.modules["pymongo"] = fake_pymongo

    # Now import main (it will use the mocked pymongo)
    from main import app, get_db  # noqa: E402

    # Also patch get_db to return our mock collection directly
    mocker.patch("main.get_db", return_value=mock_collection)

    return TestClient(app)
