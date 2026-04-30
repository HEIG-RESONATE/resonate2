import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_mongo():
    """Use mongomock for all tests."""
    import mongoengine

    # Disconnect any existing connection
    try:
        mongoengine.disconnect()
    except Exception:
        pass

    # Connect using mongomock
    import mongomock

    mongoengine.disconnect(alias="resonate")
    mongoengine.connect(
        "resonate",
        host="localhost",
        mongo_client_class=mongomock.MongoClient,
        uuidRepresentation="pythonLegacy",
    )

    yield

    # Cleanup
    mongoengine.disconnect()


@pytest.fixture
def client(setup_mongo) -> TestClient:
    """Return test client with mocked MongoDB."""
    import mongoengine

    # Disconnect all before importing main (which connects at module level)
    try:
        mongoengine.disconnect()
    except Exception:
        pass

    # Reconnect to mongomock for this test
    import mongomock
    mongoengine.connect(
        "resonate",
        host="localhost",
        mongo_client_class=mongomock.MongoClient,
        uuidRepresentation="pythonLegacy",
    )

    from main import app

    return TestClient(app)
