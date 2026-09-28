import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c
