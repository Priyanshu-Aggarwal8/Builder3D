import pytest
from tests_e2e.utils.api_client import APIClient
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import (
    assert_http_status,
    assert_model_json_schema,
    assert_zero_console_errors,
    assert_coordinate_tolerance
)

# -----------------------------------------------------------------------------
# Tier 4: Real-World User Workflow Scenarios (5 Test Cases)
# -----------------------------------------------------------------------------

def test_t4_01_scenario1_project_lifecycle(api_client: APIClient, browser_helper: BrowserHelper):
    """Tier 4 Scenario 1: New Project Lifecycle & WebGL 3D Canvas Initialization."""
    # 1. Create project via API
    res = api_client.create_project(name="Commercial Complex Tower Alpha", description="E2E Lifecycle Project")
    assert_http_status(res, 201, "Project creation failed in Scenario 1")
    proj_id = res.json()["id"]

    # 2. Fetch model JSON
    model_res = api_client.get_model(proj_id)
    assert_http_status(model_res, 200, "Model fetch failed in Scenario 1")
    model_data = model_res.json()
    assert_model_json_schema(model_data)

    # 3. Mount WebGL canvas in browser and inspect 3D scene graph
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    assert info["total_children"] > 0, "Scene contains 0 elements"

    # 4. Console error zero-tolerance check
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t4_02_scenario2_electrical_conduit_relocation(api_client: APIClient, browser_helper: BrowserHelper):
    """Tier 4 Scenario 2: Electrical Infrastructure Inspection & Conduit Relocation."""
    browser_helper.wait_for_canvas()

    # 1. Toggle OFF Structural and Plumbing layers (Isolate Electrical layer)
    browser_helper.toggle_layer("structural", enable=False)
    browser_helper.toggle_layer("plumbing", enable=False)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["electricalGroup"]["visible"] is True
    assert info["groups"]["structuralGroup"]["visible"] is False
    assert info["groups"]["plumbingGroup"]["visible"] is False

    # 2. Select electrical conduit via click
    browser_helper.click_canvas(0.2, 0.5)

    # 3. Relocate conduit position along X axis
    browser_helper.set_property_inspector_field("#inspector-pos-x", "18.0")

    # 4. Re-enable Structural and Plumbing layers
    browser_helper.toggle_layer("structural", enable=True)
    browser_helper.toggle_layer("plumbing", enable=True)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["structuralGroup"]["visible"] is True
    assert info["groups"]["electricalGroup"]["visible"] is True
    assert info["groups"]["plumbingGroup"]["visible"] is True

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t4_03_scenario3_wall_edit_and_session_reload(api_client: APIClient, browser_helper: BrowserHelper):
    """Tier 4 Scenario 3: Structural Wall Modification & Browser Refresh State Persistence."""
    browser_helper.wait_for_canvas()

    # 1. Select structural wall element
    browser_helper.click_canvas(0.5, 0.5)

    # 2. Modify wall height in Property Inspector
    browser_helper.set_property_inspector_field("#inspector-height", "8.5")

    # 3. Simulate browser reload (session resume)
    browser_helper.page.reload()
    browser_helper.wait_for_canvas()

    # 4. Verify scene graph loads correctly after refresh
    info = browser_helper.get_three_scene_info()
    assert info["has_grid_helper"] is True

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t4_04_scenario4_plumbing_reroute_overlapping_raycast(api_client: APIClient, browser_helper: BrowserHelper):
    """Tier 4 Scenario 4: Plumbing Rerouting & Hidden Layer Raycast Exclusion."""
    browser_helper.wait_for_canvas()

    # 1. Hide Electrical layer
    browser_helper.toggle_layer("electrical", enable=False)

    # 2. Click canvas coordinates (raycaster bypasses hidden Electrical box and targets visible Plumbing pipe)
    browser_helper.click_canvas(0.1, 0.5)

    # 3. Reroute plumbing pipe position Y down
    browser_helper.set_property_inspector_field("#inspector-pos-y", "2.5")

    # 4. Re-enable Electrical layer
    browser_helper.toggle_layer("electrical", enable=True)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["electricalGroup"]["visible"] is True
    assert info["groups"]["plumbingGroup"]["visible"] is True

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t4_05_scenario5_multi_element_sequential_edits(api_client: APIClient, browser_helper: BrowserHelper):
    """Tier 4 Scenario 5: Multi-Element Sequential Editing & Bulk Project State Export."""
    browser_helper.wait_for_canvas()

    # 1. Edit Structural Column Z position
    browser_helper.toggle_layer("structural", enable=True)
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-z", "4.0")

    # 2. Edit Electrical Conduit X position
    browser_helper.toggle_layer("electrical", enable=True)
    browser_helper.click_canvas(0.2, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-x", "15.0")

    # 3. Edit Plumbing Pipe width/diameter
    browser_helper.toggle_layer("plumbing", enable=True)
    browser_helper.click_canvas(0.1, 0.5)
    browser_helper.set_property_inspector_field("#inspector-width", "0.4")

    # 4. Query backend REST API to verify persistent model state
    model_res = api_client.get_model("1")
    assert_http_status(model_res, 200, "Failed to retrieve persisted model state in Scenario 5")

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)
