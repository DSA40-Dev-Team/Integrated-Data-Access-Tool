import httpx


def test_create_and_get_dsa_question(
    client: httpx.Client, api_prefix: str, unique_id: str
):
    question_id = f"dsa-{unique_id}"
    response = client.post(
        f"{api_prefix}/question",
        json={
            "id": question_id,
            "text": "What is your name?",
            "input_type": "text",
            "help_text": "Full legal name",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = client.get(f"{api_prefix}/question/{question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == question_id
    assert body["help_text"] == "Full legal name"


def test_get_nonexistent_dsa_question_returns_null(
    client: httpx.Client, api_prefix: str
):
    response = client.get(f"{api_prefix}/question/does-not-exist")
    assert response.status_code == 200
    assert response.json() is None


def test_list_dsa_questions(client: httpx.Client, api_prefix: str, unique_id: str):
    question_id = f"dsa-{unique_id}"
    response = client.post(
        f"{api_prefix}/question",
        json={"id": question_id, "text": "Q", "input_type": "text", "help_text": None},
    )
    assert response.status_code == 200

    response = client.get(f"{api_prefix}/question")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(q["id"] == question_id for q in body)


def test_create_duplicate_dsa_question_conflicts(
    client: httpx.Client, api_prefix: str, unique_id: str
):
    question_id = f"dsa-{unique_id}"
    body = {"id": question_id, "text": "Q", "input_type": "text", "help_text": None}
    response = client.post(f"{api_prefix}/question", json=body)
    assert response.status_code == 200

    response = client.post(f"{api_prefix}/question", json=body)
    assert response.status_code == 409


def test_create_dsa_question_malformed_body(client: httpx.Client, api_prefix: str):
    response = client.post(f"{api_prefix}/question", json={"id": "x"})
    assert response.status_code == 422
