from fastapi.testclient import TestClient

from main import app


def test_get_health(client: TestClient) -> None:
    resp = client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
