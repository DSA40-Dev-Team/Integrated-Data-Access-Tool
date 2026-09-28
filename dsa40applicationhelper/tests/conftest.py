import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.fixture
def unique_id():
    return uuid.uuid4()


@pytest.fixture
def vlopse(client: httpx.Client, unique_id: str):
    name = f"vlopse-test-{unique_id}"
    info = {
        "name": name,
        "account_required": False,
        "application_link": "https://example.invalid/apply",
        "modality": "form",
    }
    response = client.post("api/vlopse", json={"id": name, "info": info})
    assert response.status_code == 200
    yield name
    client.delete(f"api/vlopse/{name}")
