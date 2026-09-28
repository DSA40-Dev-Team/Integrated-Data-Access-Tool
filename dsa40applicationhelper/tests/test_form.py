import httpx

VALID_ANSWERS = [
    {"question_id": "first-name", "value": "Joseph"},
    {"question_id": "last-name", "value": "Weizenbaum"},
    {"question_id": "email-inst", "value": "joseph@example.invalid"},
    {"question_id": "org-addr-country", "value": "Germany"},
    {"question_id": "data-acc-start", "value": "01-07-1999"},
    {"question_id": "data-acc-end", "value": "01-07-2000"},
    {"question_id": "cv", "value": "cv.pdf"},
    {"question_id": "prev-experience", "value": "No"},
]


def test_applicable_questions_for_known_vlopse(client: httpx.Client, api_prefix: str):
    response = client.get(f"{api_prefix}/questions", params={"vlopse": "mastodon"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    ids = {q["id"] for q in body}
    assert {"first-name", "last-name", "email-inst"}.issubset(ids)


def test_applicable_questions_requires_vlopse(client: httpx.Client, api_prefix: str):
    response = client.get(f"{api_prefix}/questions")
    assert response.status_code == 422


def test_applicable_questions_unknown_vlopse_returns_322(
    client: httpx.Client, api_prefix: str
):
    response = client.get(
        f"{api_prefix}/questions", params={"vlopse": "does-not-exist"}
    )
    assert response.status_code == 322


def test_validate_valid_answers(client: httpx.Client, api_prefix: str):
    response = client.post(
        f"{api_prefix}/validate",
        params={"vlopse": "mastodon"},
        json={"answers": VALID_ANSWERS},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["errors"] == {}


def test_validate_missing_required_answer(client: httpx.Client, api_prefix: str):
    incomplete = [a for a in VALID_ANSWERS if a["question_id"] != "first-name"]
    response = client.post(
        f"{api_prefix}/validate",
        params={"vlopse": "mastodon"},
        json={"answers": incomplete},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["kind"] == "transformation"
    assert "X1" in body["errors"]


def test_validate_requires_body_and_vlopse(client: httpx.Client, api_prefix: str):
    response = client.post(f"{api_prefix}/validate")
    assert response.status_code == 422


def test_transform_valid_answers(client: httpx.Client, api_prefix: str):
    response = client.post(
        f"{api_prefix}/transform",
        params={"vlopse": "mastodon"},
        json={"answers": VALID_ANSWERS},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["by_vlopse"]) == 1
    vlopse_result = body["by_vlopse"][0]
    assert vlopse_result["name"] == "mastodon"

    by_question = {a["question_id"]: a for a in vlopse_result["answers"]}
    assert by_question["X1"]["type"] == "result"
    assert by_question["X1"]["value"] == "Joseph Weizenbaum"
    assert by_question["X3"]["type"] == "result"
    assert by_question["X3"]["value"] == "DEU"


def test_transform_requires_body_and_vlopse(client: httpx.Client, api_prefix: str):
    response = client.post(f"{api_prefix}/transform")
    assert response.status_code == 422


def test_transform_invalid_operator_input_surfaces_as_mapping_error(
    client: httpx.Client, api_prefix: str
):
    answers = [a for a in VALID_ANSWERS if a["question_id"] != "org-addr-country"] + [
        {"question_id": "org-addr-country", "value": "Not A Real Country"}
    ]
    response = client.post(
        f"{api_prefix}/transform",
        params={"vlopse": "mastodon"},
        json={"answers": answers},
    )
    assert response.status_code == 200
    by_question = {
        a["question_id"]: a for a in response.json()["by_vlopse"][0]["answers"]
    }
    assert by_question["X3"]["type"] == "error"


def test_conditions_for_known_vlopse(client: httpx.Client, api_prefix: str):
    response = client.get(f"{api_prefix}/condition", params={"vlopse": "mastodon"})
    assert response.status_code == 200
    body = response.json()
    assert "data-acc-end" in body
    assert body["data-acc-end"][0]["question_id"] == "data-acc-start"


def test_conditions_requires_vlopse(client: httpx.Client, api_prefix: str):
    response = client.get(f"{api_prefix}/condition")
    assert response.status_code == 422
