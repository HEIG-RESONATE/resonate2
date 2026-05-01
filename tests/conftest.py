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

    # Disconnect ALL connections before importing main (which connects at module level)
    mongoengine.disconnect_all()

    # Reconnect to mongomock for this test
    import mongomock
    mongoengine.connect(
        "resonate",
        host="localhost",
        mongo_client_class=mongomock.MongoClient,
        uuidRepresentation="pythonLegacy",
    )

    from main import app
    from fastapi.testclient import TestClient
    from auth import create_access_token

    class AuthClient(TestClient):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.token = create_access_token()

        def request(self, *args, **kwargs):
            headers = kwargs.get('headers') or {}
            headers['Authorization'] = f'Bearer {self.token}'
            kwargs['headers'] = headers
            return super().request(*args, **kwargs)

    return AuthClient(app)
