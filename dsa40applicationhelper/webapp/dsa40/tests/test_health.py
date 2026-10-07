from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from django.test import Client


def test_hello_world():
    assert True


@pytest.mark.django_db
def test_health(client: Client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"] == "ok"
    assert data["db"] in ("ok", "error")
    assert data["mapping_status"] in ("ok", "error")
    assert isinstance(data["dsa_status"], int) or data["dsa_status"] in ("ok", "error")
