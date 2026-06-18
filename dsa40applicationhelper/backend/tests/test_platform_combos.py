"""Platform-combination smoke tests using the shared combo harness."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.support.platform_combo_harness import (
    build_answers,
    combos_56,
    mapping_errors,
    transform_combo,
    validate_combo,
)

client = TestClient(app)


@pytest.mark.parametrize("vlopses", combos_56(), ids=lambda v: ",".join(v))
def test_platform_combo_loads_questions(vlopses: list[str]):
    response = client.get("/api/questions", params={"vlopse": vlopses})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


@pytest.mark.parametrize("vlopses", combos_56(), ids=lambda v: ",".join(v))
def test_platform_combo_field_validation(vlopses: list[str]):
    result = validate_combo(client, vlopses)
    assert result["kind"] in {"validation", "transformation"}
    if result["kind"] == "validation":
        assert result["ok"] is True, result.get("errors")


@pytest.mark.parametrize("vlopses", combos_56(), ids=lambda v: ",".join(v))
def test_platform_combo_validate_never_500(vlopses: list[str]):
    payload = {"answers": build_answers(client, vlopses)}
    response = client.post("/api/validate", params={"vlopse": vlopses}, json=payload)
    assert response.status_code == 200
    body = response.json()
    errors = str(body.get("errors", ""))
    assert "multi_select" not in errors.lower()
    assert "Unknown field 'funding-" not in errors


@pytest.mark.parametrize("vlopses", combos_56(), ids=lambda v: ",".join(v))
def test_platform_combo_transform_passes(vlopses: list[str]):
    result = validate_combo(client, vlopses)
    assert result["ok"] is True, result.get("errors")
    assert result["kind"] == "transformation"

    transform = transform_combo(client, vlopses)
    errors = mapping_errors(transform)
    assert errors == []
