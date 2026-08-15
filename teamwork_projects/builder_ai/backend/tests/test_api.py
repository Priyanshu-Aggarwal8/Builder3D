def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_get_project_flow(client):
    # 1. Create project
    create_resp = client.post(
        "/api/projects",
        json={"name": "Api Villa", "plot_size": 500.0, "floors": 2}
    )
    assert create_resp.status_code == 201
    proj_data = create_resp.json()
    project_id = proj_data["id"]
    assert proj_data["name"] == "Api Villa"

    # 2. List projects
    list_resp = client.get("/api/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert len(projects) >= 1

    # 3. Get single project
    get_resp = client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == project_id


def test_get_3d_model_and_patch_element(client):
    # Create project
    create_resp = client.post(
        "/api/projects",
        json={"name": "3D Model Test", "plot_size": 400.0, "floors": 1}
    )
    project_id = create_resp.json()["id"]

    # Fetch 3D Model
    model_resp = client.get(f"/api/projects/{project_id}/model")
    assert model_resp.status_code == 200
    model_data = model_resp.json()
    assert model_data["project_id"] == project_id
    assert "layers" in model_data

    # Pick an element to patch
    elec_elements = model_data["layers"]["electrical"]["elements"]
    assert len(elec_elements) > 0
    target_element_id = elec_elements[0]["id"]

    # Patch element transform
    patch_resp = client.patch(
        f"/api/projects/{project_id}/elements/{target_element_id}",
        json={"position": [1.2, 3.4, 5.6], "name": "Updated Conduit Name"}
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["id"] == target_element_id
    assert patched_data["position"] == [1.2, 3.4, 5.6]
    assert patched_data["name"] == "Updated Conduit Name"


def test_patch_nonexistent_element(client):
    create_resp = client.post(
        "/api/projects",
        json={"name": "Error Test", "plot_size": 200.0, "floors": 1}
    )
    project_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/projects/{project_id}/elements/non_existent_element",
        json={"position": [0.0, 0.0, 0.0]}
    )
    assert patch_resp.status_code == 404
