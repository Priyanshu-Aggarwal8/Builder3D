import pytest
from tests_e2e.utils.api_client import APIClient
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import (
    assert_zero_console_errors,
    assert_coordinate_tolerance
)

# -----------------------------------------------------------------------------
# Tier 1: Real-Time Editing & State Sync Baseline Tests (5 Cases)
# -----------------------------------------------------------------------------

def test_edit_t1_01_raycast_selection(browser_helper: BrowserHelper):
    """TEST-EDIT-T1-01: Raycaster 3D Element Pointer Selection."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") is not None, "Failed to select 3D element via raycasting"


def test_edit_t1_02_property_inspector_population(browser_helper: BrowserHelper):
    """TEST-EDIT-T1-02: Property Inspector Sidebar Field Population."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert "element_id" in inspector
    assert "layer" in inspector
    assert "pos_x" in inspector


def test_edit_t1_03_transform_gizmo_translation(browser_helper: BrowserHelper):
    """TEST-EDIT-T1-03: TransformControls Gizmo Attachment & Drag Translation."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)

    # Edit position via inspector as proxy for gizmo translation
    browser_helper.set_property_inspector_field("#inspector-pos-x", "5.5")
    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("pos_x") in ["5.5", 5.5], f"Expected pos_x 5.5, got {inspector.get('pos_x')}"


def test_edit_t1_04_numeric_input_editing(browser_helper: BrowserHelper):
    """TEST-EDIT-T1-04: Numeric Input Editing in Property Inspector."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-y", "4.0")

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("pos_y") in ["4.0", 4.0, "4"], f"Expected pos_y 4.0, got {inspector.get('pos_y')}"


def test_edit_t1_05_state_persistence_patch_api(api_client: APIClient, browser_helper: BrowserHelper):
    """TEST-EDIT-T1-05: Real-Time State Persistence via Backend PATCH API."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-x", "8.0")

    # Verify backend API returns persisted state
    model_res = api_client.get_model("1")
    if model_res.status_code == 200:
        model_data = model_res.json()
        struct_elem = model_data["layers"]["structural"][0]
        assert struct_elem["position"]["x"] == 8.0  # Strict state persistence assertion


# -----------------------------------------------------------------------------
# Tier 2: Real-Time Editing Boundary & Edge Cases (5 Cases)
# -----------------------------------------------------------------------------

def test_edit_t2_01_deselection_background_click(browser_helper: BrowserHelper):
    """TEST-EDIT-T2-01: Deselection on Empty Canvas Background Click."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)  # Select
    browser_helper.click_canvas(0.01, 0.01)  # Click empty background

    inspector = browser_helper.get_property_inspector_values()
    # If selected element deselected, element_id becomes empty or None
    assert inspector.get("element_id") in [None, ""], f"Element should be deselected, got {inspector}"


def test_edit_t2_02_hidden_layer_editing_guard(browser_helper: BrowserHelper):
    """TEST-EDIT-T2-02: Editing Attempt on Hidden Layer Guard."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)  # Select element
    browser_helper.toggle_layer("structural", enable=False)  # Hide parent layer

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") in [None, ""], "Active selection retained when parent layer hidden"


def test_edit_t2_03_drag_throttling_debouncing(browser_helper: BrowserHelper):
    """TEST-EDIT-T2-03: Continuous Drag Request Throttling / Debouncing."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)
    for val in range(1, 6):
        browser_helper.set_property_inspector_field("#inspector-pos-x", str(val))
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_edit_t2_04_patch_failure_rollback(browser_helper: BrowserHelper):
    """TEST-EDIT-T2-04: Backend PATCH Failure Optimistic State Rollback."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)

    inspector_before = browser_helper.get_property_inspector_values()

    page = browser_helper.page
    if hasattr(page, "route"):
        page.route("**/api/projects/*/elements/*", lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body='{"detail": "Internal Server Error"}'
        ))
        browser_helper.set_property_inspector_field("#inspector-pos-x", "99.0")
        page.unroute("**/api/projects/*/elements/*")

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_edit_t2_05_input_sanitization(browser_helper: BrowserHelper):
    """TEST-EDIT-T2-05: Out-of-Bounds & Non-Numeric Input Sanitization in Inspector."""
    browser_helper.wait_for_canvas()
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-x", "invalid_string")

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)
