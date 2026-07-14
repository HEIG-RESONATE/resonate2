import sys
import os
import tempfile
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


@pytest.fixture(scope="session", autouse=True)
def set_images_dir(tmp_path_factory):
    """Use one temp directory because FastAPI mounts static files once per process."""
    os.environ["IMAGES_DIR"] = str(tmp_path_factory.mktemp("images") / "uploads")
    yield
    os.environ.pop("IMAGES_DIR", None)


@pytest.fixture(autouse=True)
def reset_rate_limiter(set_images_dir):
    """Reset the rate limiter between tests."""
    from main import limiter
    limiter._storage.reset()
    yield


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
