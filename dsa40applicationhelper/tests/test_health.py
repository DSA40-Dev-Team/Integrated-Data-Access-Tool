import httpx


def test_health_returns_expected_shape(client: httpx.Client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["db"] in ("ok", "error")
    assert body["mapping_status"] in ("ok", "error")
    assert isinstance(body["dsa_status"], int) or body["dsa_status"] in ("ok", "error")
