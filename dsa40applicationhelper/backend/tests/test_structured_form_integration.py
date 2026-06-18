"""Integration tests for structured-form fixes (platform tabs, multi-select, funding)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.core.answer_projection import expand_primary_answer_map
from app.core.structured_schemas import validate_repeatable_answer
from app.main import app
from tests.support.platform_combo_harness import (
    build_answers,
    composite_payload,
    sample_field_value,
    sample_question_value,
)

client = TestClient(app)


def test_funding_schema_includes_gate_field_for_google():
    response = client.get(
        "/api/schemas/funding-profile",
        params={"vlopse": ["google"]},
    )
    assert response.status_code == 200
    field_ids = [field["id"] for field in response.json()["fields"]]
    assert "funding-received" in field_ids
    assert "funding-evidence" in field_ids


def test_funding_evidence_hidden_until_funding_received_yes():
    from app.services.condition_service import ConditionService

    conditions = ConditionService().get_merged_conditions(["google"])
    assert "funding-evidence" in conditions
    assert conditions["funding-evidence"][0][0].question_id == "funding-received"
    assert conditions["funding-evidence"][0][0].value == "Yes"


def test_schema_returns_scoped_platforms_for_data_requested():
    response = client.get(
        "/api/schemas/data-request-profile",
        params={"vlopse": ["meta", "snap", "google"]},
    )
    assert response.status_code == 200

    fields = {field["id"]: field for field in response.json()["fields"]}
    assert fields["data-requested"]["granularity"] == "platform_specific"
    assert set(fields["data-requested"]["scoped_platforms"]) == {"meta", "snap", "google"}


def test_schema_returns_scoped_platforms_for_profile_platform():
    response = client.get(
        "/api/schemas/person-profile",
        params={"vlopse": ["linkedin", "bing"]},
    )
    assert response.status_code == 200

    fields = {field["id"]: field for field in response.json()["fields"]}
    assert fields["profile-platform"]["granularity"] == "platform_specific"
    assert set(fields["profile-platform"]["scoped_platforms"]) == {"linkedin", "bing"}


def test_schema_returns_scoped_platforms_for_prev_experience():
    response = client.get(
        "/api/schemas/person-profile",
        params={"vlopse": ["bing", "linkedin", "google", "youtube"]},
    )
    assert response.status_code == 200

    fields = {field["id"]: field for field in response.json()["fields"]}
    assert fields["prev-experience"]["granularity"] == "platform_specific"
    assert set(fields["prev-experience"]["scoped_platforms"]) == {
        "bing",
        "linkedin",
        "google",
        "youtube",
    }


def test_schema_country_fields_include_options():
    response = client.get("/api/schemas/person-profile")
    assert response.status_code == 200

    fields = {field["id"]: field for field in response.json()["fields"]}
    assert "Germany" in fields["researcher-addr-country"]["options"]


def test_orcid_validation_rejects_invalid_checksum():
    response = client.post(
        "/api/validate",
        params={"vlopse": ["meta"]},
        json={
            "answers": [
                {
                    "question_id": "primary-person",
                    "value": json.dumps({"orcid": "0000-0000-0000-0000"}),
                }
            ]
        },
    )
    assert response.status_code == 200
    assert "orcid" in str(response.json().get("errors", "")).lower()


def test_standalone_platform_questions_include_group_text():
    response = client.get("/api/questions", params={"vlopse": ["google", "meta"]})
    assert response.status_code == 200

    scoped = [q for q in response.json() if q.get("source_general_id") == "tech-client-scrape-method"]
    assert scoped
    assert all(q.get("group_text") for q in scoped)


def test_multi_select_validates_inside_research_composite():
    research_payload = json.dumps(
        {
            "research-title": "Election monitoring study",
            "research-summary": "Summary",
            "research-keywords": "misinformation; elections",
            "research-sysrisk-categories": "Illegal content; Fundamental rights",
        }
    )
    response = client.post(
        "/api/validate",
        params={"vlopse": ["google"]},
        json={
            "answers": [
                {
                    "question_id": "primary-organisation",
                    "value": json.dumps(
                        {
                            "org-name": "Example University",
                            "org-type": "Academic institution",
                            "org-addr-country": "Germany",
                        }
                    ),
                },
                {"question_id": "research-project", "value": research_payload},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "research-project" not in str(body.get("errors", ""))
    assert "multi_select" not in str(body.get("errors", "")).lower()


def test_funding_entries_repeatable_validates_restored_fields():
    entry = {
        field_id: sample_field_value(field_id, ["apple"])
        for field_id in [
            "funding-source-name",
            "funding-source-type",
            "funding-amount",
            "funding-grant-year",
            "funding-duration",
            "funding-percentage",
            "funding-terms",
            "funding-notes",
        ]
    }
    error = validate_repeatable_answer(
        json.dumps([entry]),
        schema_name="funding-entry-profile",
    )
    assert error is None


def test_data_requested_per_platform_projects_and_transforms_meta():
    data_request = json.dumps(
        {
            "data-requested": {"meta": "Public Page Posts"},
            "data-expl": "Analysis only",
        }
    )

    expanded = expand_primary_answer_map(
        {"data-request": data_request},
        vlopses=["meta"],
    )
    assert expanded.get("data-requested__meta") == "Public Page Posts"

    questions = client.get("/api/questions", params={"vlopse": ["meta"]}).json()
    answers = [
        {"question_id": question["id"], "value": sample_question_value(question, ["meta"])}
        for question in questions
    ]
    for answer in answers:
        if answer["question_id"] == "data-request":
            answer["value"] = data_request

    transform = client.post(
        "/api/transform",
        params={"vlopse": ["meta"]},
        json={"answers": answers},
    )
    assert transform.status_code == 200

    meta_answers = transform.json()["by_vlopse"][0]["answers"]
    data_results = [
        answer
        for answer in meta_answers
        if answer.get("type") == "result" and answer.get("question_id") == "M21"
    ]
    assert data_results
    assert data_results[0]["value"] == "Public Page Posts"


def test_collab_list_derived_from_structured_team_when_apple_selected():
    researchers = json.dumps(
        [
            {
                "person": {
                    "first-name": "Alex",
                    "last-name": "Helper",
                    "email-inst": "alex@uni.edu",
                },
                "affiliations": [
                    {
                        "organisation_id": "primary",
                        "org-role": "Researcher",
                        "org-department": "CS",
                    }
                ],
            }
        ]
    )
    expanded = expand_primary_answer_map(
        {
            "collab-binary": "Yes",
            "collab-researchers": researchers,
            "primary-person": json.dumps({"first-name": "Jane", "last-name": "Doe"}),
            "primary-organisation": json.dumps({"org-name": "Example University"}),
        },
        vlopses=["apple", "google"],
    )
    assert expanded.get("collab-list")
    assert "Alex Helper" in str(expanded.get("collab-list"))


def test_collab_list_falls_back_to_principal_when_no_team_members():
    expanded = expand_primary_answer_map(
        {
            "collab-binary": "Yes",
            "collab-researchers": "[]",
            "primary-person": json.dumps({"first-name": "Jane", "last-name": "Doe"}),
            "primary-organisation": json.dumps(
                {"org-name": "Example University", "org-type": "Academic institution"}
            ),
            "primary-affiliation": json.dumps({"org-role": "Professor"}),
        },
        vlopses=["apple", "google"],
    )
    assert expanded.get("collab-list") == "Jane Doe, Example University, Professor"


@pytest.mark.parametrize(
    "composite_id",
    ["data-request", "primary-person"],
)
def test_composite_payload_includes_platform_specific_dicts(composite_id: str):
    payload = composite_payload(composite_id, ["meta", "google"])
    if composite_id == "data-request":
        assert isinstance(payload["data-requested"], dict)
        assert "meta" in payload["data-requested"]
    if composite_id == "primary-person":
        assert isinstance(payload["profile-platform"], dict)
        assert isinstance(payload["prev-experience"], dict)


def test_transform_skips_optional_bing_profile_link_without_answer():
    answers = build_answers(client, ["bing"])
    answers_by_id = {entry["question_id"]: entry["value"] for entry in answers}
    person = json.loads(answers_by_id["primary-person"])
    person.pop("profile-platform", None)
    answers_by_id["primary-person"] = json.dumps(person)
    payload = {"answers": [{"question_id": k, "value": v} for k, v in answers_by_id.items()]}
    result = client.post("/api/validate", params={"vlopse": ["bing"]}, json=payload)
    assert result.status_code == 200
    body = result.json()
    assert body.get("ok") is True, body.get("errors")


def test_transform_skips_tiktok_u18_when_org_type_is_academic():
    answers = build_answers(client, ["tiktok"])
    answers_by_id = {entry["question_id"]: entry["value"] for entry in answers}
    org = json.loads(answers_by_id["primary-organisation"])
    org["org-type"] = "Academic institution"
    answers_by_id["primary-organisation"] = json.dumps(org)
    data = json.loads(answers_by_id["data-request"])
    data.pop("data-requested-U18", None)
    answers_by_id["data-request"] = json.dumps(data)
    payload = {"answers": [{"question_id": k, "value": v} for k, v in answers_by_id.items()]}
    result = client.post("/api/validate", params={"vlopse": ["tiktok"]}, json=payload)
    assert result.status_code == 200
    body = result.json()
    assert body.get("ok") is True, body.get("errors")
