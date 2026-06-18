import pytest
from fastapi.testclient import TestClient

from app.core.models import Answer
from app.main import app
from app.routers.form import AnswerRequest

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    # FIXME: uses comitted database correctly. Don't.
    assert response.json() == {
        "api": "ok",
        "db": "ok",
        "dsa_status": 116,
        "mapping_status": "ok",
    }


def test_questions_no_vlopse_selected():
    response = client.get("/api/questions")
    assert response.status_code == 422


def test_required_fields_no_vlopse_selected():
    response = client.get("/api/required-fields")
    assert response.status_code == 422


def test_required_fields_for_linkedin():
    response = client.get("/api/required-fields?vlopse=linkedin")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) > 0
    ids = {item["id"] for item in payload}
    assert "first-name" in ids
    assert all("id" in item and "label" in item for item in payload)


def test_transformation_wo_questions_wo_vlopses():
    response = client.post("/api/transform")
    assert response.status_code == 422


def test_transformation_wo_questions():
    response = client.post("/api/transform?vlopse=tiktok&vlopse=meta")
    assert response.status_code == 422


@pytest.mark.skip(reason="Not implemented yet")
def test_transformation_id_not_in_all_targets():
    # FIXME: first-name will be in all probably, so find another one
    answers = AnswerRequest(answers=[Answer(question_id="first-name", value="Joseph")])

    response = client.post(
        "/api/transform?vlopse=tiktok&vlopse=meta", json=answers.model_dump()
    )
    assert response.status_code == 200
    response = response.json()
    print(response)


@pytest.mark.skip(reason="Not implemented yet")
def test_transformation_invalid_id():
    # FIXME: first-name will be in all probably, so find another one
    answers = AnswerRequest(answers=[Answer(question_id="doesntexist", value="Joseph")])

    response = client.post(
        "/api/transform?vlopse=tiktok&vlopse=meta", json=answers.model_dump()
    )
    assert response.status_code == 322  # FIXME


@pytest.mark.skip(reason="Not implemented yet")
def test_transformation_invalid_vlopse():
    # FIXME: first-name will be in all probably, so find another one
    answers = AnswerRequest(answers=[Answer(question_id="first-name", value="Joseph")])

    response = client.post(
        "/api/transform?vlopse=deadlock&vlopse=meta", json=answers.model_dump()
    )
    assert response.status_code == 322  # FIXME
