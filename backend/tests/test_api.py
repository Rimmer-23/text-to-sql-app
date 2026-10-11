from fastapi.testclient import TestClient


def create_workspace(client: TestClient) -> str:
    response = client.post("/api/workspaces")
    assert response.status_code == 201
    return response.json()["workspace_id"]


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_and_schema(client: TestClient) -> None:
    workspace_id = create_workspace(client)

    response = client.post(
        f"/api/workspaces/{workspace_id}/files",
        files=[
            ("files", ("sales.csv", b"city,amount\nPraha,100\nBrno,250\n", "text/csv")),
            ("files", ("Customers.csv", b"Name;City\nJohn;Prague\n", "text/csv")),
        ],
    )
    assert response.status_code == 200
    uploaded = response.json()["tables"]
    assert [(t["name"], t["source_file"], t["row_count"]) for t in uploaded] == [
        ("sales", "sales.csv", 2),
        ("customers", "Customers.csv", 1),
    ]

    schema = client.get(f"/api/workspaces/{workspace_id}/schema").json()
    assert schema["workspace_id"] == workspace_id
    assert [t["name"] for t in schema["tables"]] == ["customers", "sales"]
    sales = schema["tables"][1]
    assert sales["columns"] == [
        {"name": "city", "original_name": "city", "type": "TEXT"},
        {"name": "amount", "original_name": "amount", "type": "INTEGER"},
    ]
    assert sales["sample_rows"] == [["Praha", 100], ["Brno", 250]]


def test_empty_workspace_schema(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.get(f"/api/workspaces/{workspace_id}/schema")
    assert response.json()["tables"] == []


def test_unknown_workspace(client: TestClient) -> None:
    for workspace_id in ["00000000-0000-0000-0000-000000000000", "not-a-uuid", "..%5C..%5Cetc"]:
        response = client.get(f"/api/workspaces/{workspace_id}/schema")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"


def test_invalid_file_error_format(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.post(
        f"/api/workspaces/{workspace_id}/files",
        files=[("files", ("notes.txt", b"hello", "text/plain"))],
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "INVALID_FILE"
    assert "notes.txt" in error["message"]


def test_upload_size_limit(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    big = b"a\n" + b"1\n" * (1024 * 1024)  # > 1 MB limit from the test settings
    response = client.post(
        f"/api/workspaces/{workspace_id}/files",
        files=[("files", ("big.csv", big, "text/csv"))],
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "INVALID_FILE"


def test_upload_without_files(client: TestClient) -> None:
    workspace_id = create_workspace(client)
    response = client.post(f"/api/workspaces/{workspace_id}/files")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"
