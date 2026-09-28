import httpx


def _info(name: str) -> dict:
    return {
        "name": name,
        "account_required": False,
        "application_link": "https://example.invalid/apply",
        "modality": "form",
    }


def test_list_vlopses(client: httpx.Client):
    # TODO(t1): Adjust this as soon as db is removed from version control
    response = client.get("api/vlopse")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert all({"id", "info"}.issubset(item) for item in body)


def test_create_and_delete_vlopse(client: httpx.Client, unique_id: str):
    name = f"vlopse-{unique_id}"
    response = client.post("api/vlopse", json={"id": name, "info": _info(name)})
    assert response.status_code == 200
    assert response.json() == {"success": True}

    response = client.get("api/vlopse")
    assert any(v["id"] == name for v in response.json())

    response = client.delete(f"api/vlopse/{name}")
    assert response.status_code == 200

    response = client.get("api/vlopse")
    assert not any(v["id"] == name for v in response.json())


def test_create_vlopse_malformed_body(client: httpx.Client):
    response = client.post("api/vlopse", json={"not": "valid"})
    assert response.status_code == 422


def test_create_duplicate_vlopse_conflicts(client: httpx.Client, vlopse: str):
    response = client.post("api/vlopse", json={"id": vlopse, "info": _info(vlopse)})
    assert response.status_code == 409


def test_rename_vlopse(client: httpx.Client, vlopse: str):
    new_name = f"{vlopse}-renamed"
    response = client.put(f"api/vlopse/{vlopse}", json={"new_name": new_name})
    assert response.status_code == 200
    client.delete(f"api/vlopse/{new_name}")


def test_rename_nonexistent_vlopse(client: httpx.Client, unique_id: str):
    response = client.put(
        f"api/vlopse/does-not-exist-{unique_id}",
        json={"new_name": "irrelevant"},
    )
    assert response.status_code == 404


def test_rename_to_existing_name_conflicts(
    client: httpx.Client, vlopse: str, unique_id: str
):
    other = f"contract-{unique_id}-other"
    response = client.post("api/vlopse", json={"id": other, "info": _info(other)})
    assert response.status_code == 200
    try:
        response = client.put(f"api/vlopse/{vlopse}", json={"new_name": other})
        assert response.status_code == 409
    finally:
        client.delete(f"api/vlopse/{other}")


def test_rename_missing_body(client: httpx.Client, vlopse: str):
    response = client.put(f"api/vlopse/{vlopse}")
    assert response.status_code == 422


def test_delete_nonexistent_vlopse(client: httpx.Client, unique_id: str):
    response = client.delete(f"api/vlopse/does-not-exist-{unique_id}")
    assert response.status_code == 404
