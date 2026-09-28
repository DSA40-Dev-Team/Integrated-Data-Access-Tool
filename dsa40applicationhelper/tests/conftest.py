import os
import uuid

import httpx
import pytest


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_prefix() -> str:
    return os.environ.get("API_PREFIX", "/api")


@pytest.fixture
def client(base_url: str):
    with httpx.Client(base_url=base_url, timeout=10.0) as c:
        yield c


@pytest.fixture
def unique_id():
    return uuid.uuid4()


@pytest.fixture
def vlopse(client: httpx.Client, api_prefix: str, unique_id: str):
    name = f"vlopse-test-{unique_id}"
    info = {
        "name": name,
        "account_required": False,
        "application_link": "https://example.invalid/apply",
        "modality": "form",
    }
    response = client.post(f"{api_prefix}/vlopse", json={"id": name, "info": info})
    assert response.status_code == 200, response.text
    yield name
    client.delete(f"{api_prefix}/vlopse/{name}")
