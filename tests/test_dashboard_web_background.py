import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from dashboard.server import DashboardServer


@pytest.fixture(scope="module")
def client():
    return TestClient(DashboardServer().app)


def test_serves_background_asset(client):
    assert client.get("/web_background/index.html").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/web_background/..%2f..%2fdashboard%2fserver.py",
        "/web_background/" + "..%2f" * 12 + "etc%2fpasswd",
        "/web_background/%2fetc%2fpasswd",
        "/web_background//etc/passwd",
        "/web_background/../../dashboard/server.py",
        "/web_background/..%5c..%5cdashboard%5cserver.py",
    ],
)
def test_rejects_path_traversal(client, path):
    resp = client.get(path)
    assert resp.status_code == 404
    assert b"Dashboard" not in resp.content and b"root:" not in resp.content
