import httpx


def test_create_and_list_vlopse_question(
    client: httpx.Client, api_prefix: str, vlopse: str, unique_id: str
):
    question_id = f"vq-{unique_id}"
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse}/question",
        json={
            "id": question_id,
            "text": "Are you affiliated with an academic institution?",
            "required": True,
            "input_type": "selection",
            "config": {"type": "selection", "options": ["Yes", "No"]},
            "details": None,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = client.get(f"{api_prefix}/vlopse/{vlopse}/question")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(q["id"] == question_id for q in body)


def test_get_single_vlopse_question(
    client: httpx.Client, api_prefix: str, vlopse: str, unique_id: str
):
    question_id = f"vq-{unique_id}"
    response = client.post(
        f"{api_prefix}/vlopse/{vlopse}/question",
        json={
            "id": question_id,
            "text": "Some question",
            "required": False,
            "input_type": "text",
            "config": None,
            "details": None,
        },
    )
    assert response.status_code == 200

    response = client.get(f"{api_prefix}/vlopse/{vlopse}/question/{question_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == question_id
    assert body["vlopse"] == vlopse
    assert body["required"] is False


def test_get_nonexistent_vlopse_question(
    client: httpx.Client, api_prefix: str, vlopse: str
):
    response = client.get(f"{api_prefix}/vlopse/{vlopse}/question/does-not-exist")
    assert response.status_code == 404


def test_create_duplicate_vlopse_question_conflicts(
    client: httpx.Client, api_prefix: str, vlopse: str, unique_id: str
):
    question_id = f"vq-{unique_id}"
    body = {
        "id": question_id,
        "text": "Some question",
        "required": False,
        "input_type": "text",
        "config": None,
        "details": None,
    }
    response = client.post(f"{api_prefix}/vlopse/{vlopse}/question", json=body)
    assert response.status_code == 200

    response = client.post(f"{api_prefix}/vlopse/{vlopse}/question", json=body)
    assert response.status_code == 409


def test_create_vlopse_question_malformed_body(
    client: httpx.Client, api_prefix: str, vlopse: str
):
    response = client.post(f"{api_prefix}/vlopse/{vlopse}/question", json={"id": "x"})
    assert response.status_code == 422
