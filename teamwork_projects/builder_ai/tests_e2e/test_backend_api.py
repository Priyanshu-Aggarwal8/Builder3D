import pytest
import concurrent.futures
from tests_e2e.utils.api_client import APIClient
from tests_e2e.utils.assertions import (
    assert_http_status,
    assert_model_json_schema,
    assert_coordinate_tolerance,
    assert_pydantic_validation_error
)

# -----------------------------------------------------------------------------
# Tier 1: Baseline REST Backend API Feature Tests (6 Cases)
# -----------------------------------------------------------------------------

def test_t1_01_healthcheck(api_client: APIClient):
    """TEST-API-T1-01: Healthcheck Endpoint Availability."""
    res = api_client.health_check()
    assert_http_status(res, 200, "Health check failed")
    data = res.json()
    assert data.get("status") == "ok", f"Expected status 'ok', got {data}"


def test_t1_02_create_project(api_client: APIClient):
    """TEST-API-T1-02: Project Creation (POST /api/projects)."""
    res = api_client.create_project(name="Commercial Complex", description="Tier 1 Test Project")
    assert_http_status(res, 201, "Project creation failed")
    data = res.json()
    assert "id" in data, "Created project response missing 'id'"
    assert data.get("name") == "Commercial Complex", f"Project name mismatch: {data}"


def test_t1_03_list_projects(api_client: APIClient):
    """TEST-API-T1-03: Project Listing (GET /api/projects)."""
    # Ensure at least one project exists
    api_client.create_project(name="List Test Project")
    res = api_client.list_projects()
    assert_http_status(res, 200, "Project listing failed")
    projects = res.json()
    assert isinstance(projects, list), "Expected array of projects"
    assert len(projects) > 0, "Projects list is empty"


def test_t1_04_get_model(api_client: APIClient):
    """TEST-API-T1-04: 3D Model JSON Structure (GET /api/projects/{id}/model)."""
    create_res = api_client.create_project(name="Model Test Project")
    proj_id = create_res.json()["id"]

    res = api_client.get_model(proj_id)
    assert_http_status(res, 200, "Get model failed")
    model_data = res.json()
    assert_model_json_schema(model_data)


def test_t1_05_patch_element(api_client: APIClient):
    """TEST-API-T1-05: Real-Time Element Transformation (PATCH /api/projects/{id}/elements/{element_id})."""
    create_res = api_client.create_project(name="Patch Test Project")
    proj_id = create_res.json()["id"]
    model_res = api_client.get_model(proj_id)
    model_data = model_res.json()

    # Target structural element
    elem = model_data["layers"]["structural"][0]
    elem_id = elem.get("element_id") or elem.get("id")

    new_transform = {
        "position": {"x": 10.5, "y": 2.0, "z": -5.0},
        "rotation": {"x": 0.0, "y": 1.57, "z": 0.0}
    }
    patch_res = api_client.patch_element(proj_id, elem_id, new_transform)
    assert_http_status(patch_res, 200, "Patch element failed")
    updated_elem = patch_res.json()

    assert_coordinate_tolerance(updated_elem["position"], new_transform["position"])


def test_t1_06_delete_project(api_client: APIClient):
    """TEST-API-T1-06: Project Deletion (DELETE /api/projects/{id})."""
    create_res = api_client.create_project(name="Delete Test Project")
    proj_id = create_res.json()["id"]

    del_res = api_client.delete_project(proj_id)
    assert del_res.status_code in [200, 204], f"Expected 200/204 on delete, got {del_res.status_code}"

    # Verify subsequent GET returns 404
    get_res = api_client.get_model(proj_id)
    assert_http_status(get_res, 404, "Deleted project model still accessible")


# -----------------------------------------------------------------------------
# Tier 2: Boundary Value & Error Cases (6 Cases)
# -----------------------------------------------------------------------------

def test_t2_01_get_model_nonexistent_id(api_client: APIClient):
    """TEST-API-T2-01: Non-Existent Project ID Query."""
    res = api_client.get_model("99999")
    assert_http_status(res, 404, "Expected 404 for non-existent project ID")


def test_t2_02_patch_nonexistent_element(api_client: APIClient):
    """TEST-API-T2-02: Patch Non-Existent Element ID."""
    create_res = api_client.create_project(name="Valid Proj")
    proj_id = create_res.json()["id"]

    res = api_client.patch_element(proj_id, "invalid-elem-999", {"position": {"x": 1, "y": 1, "z": 1}})
    assert_http_status(res, 404, "Expected 404 for non-existent element ID")


def test_t2_03_patch_malformed_payload(api_client: APIClient):
    """TEST-API-T2-03: Malformed Patch Payload Types."""
    create_res = api_client.create_project(name="Malformed Payload Proj")
    proj_id = create_res.json()["id"]
    model_data = api_client.get_model(proj_id).json()
    elem_id = model_data["layers"]["structural"][0].get("element_id") or model_data["layers"]["structural"][0].get("id")

    res = api_client.patch_element(proj_id, elem_id, {"position": "not-a-vector"})
    assert_pydantic_validation_error(res)


def test_t2_04_patch_extreme_coordinates_or_negative_dimensions(api_client: APIClient):
    """TEST-API-T2-04: Negative Dimensions Validation."""
    create_res = api_client.create_project(name="Negative Dim Proj")
    proj_id = create_res.json()["id"]
    model_data = api_client.get_model(proj_id).json()
    elem_id = model_data["layers"]["structural"][0].get("element_id") or model_data["layers"]["structural"][0].get("id")

    res = api_client.patch_element(proj_id, elem_id, {"dimensions": {"width": -5.0, "height": 3.0, "depth": 0.3}})
    assert_pydantic_validation_error(res)


def test_t2_05_create_project_empty_name(api_client: APIClient):
    """TEST-API-T2-05: Empty & Whitespace Project Name Validation."""
    res = api_client.create_project(name="   ")
    assert res.status_code in [400, 422], f"Expected 400/422 for whitespace project name, got {res.status_code}"


def test_t2_06_concurrent_patching(api_client: APIClient):
    """TEST-API-T2-06: Concurrent Element Patching Race Condition."""
    create_res = api_client.create_project(name="Concurrent Patch Proj")
    proj_id = create_res.json()["id"]
    model_data = api_client.get_model(proj_id).json()
    elem_id = model_data["layers"]["structural"][0].get("element_id") or model_data["layers"]["structural"][0].get("id")

    def send_patch(idx):
        return api_client.patch_element(proj_id, elem_id, {"position": {"x": float(idx), "y": 1.5, "z": 0.0}})

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_patch, i) for i in range(5)]
        results = [f.result() for f in futures]

    for res in results:
        assert_http_status(res, 200, "Concurrent patch request failed")
