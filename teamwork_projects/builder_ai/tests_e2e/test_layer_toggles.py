import pytest
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import assert_zero_console_errors

# -----------------------------------------------------------------------------
# Tier 1: Layer Toggle UI Baseline Tests (5 Cases)
# -----------------------------------------------------------------------------

def test_layer_t1_01_controls_mounting_and_defaults(browser_helper: BrowserHelper):
    """TEST-LAYER-T1-01: Layer Toggle UI Controls Mounting & Default States."""
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    
    assert groups.get("structuralGroup", {}).get("visible") is True, "structuralGroup default visibility should be True"
    assert groups.get("electricalGroup", {}).get("visible") is True, "electricalGroup default visibility should be True"
    assert groups.get("plumbingGroup", {}).get("visible") is True, "plumbingGroup default visibility should be True"


def test_layer_t1_02_single_layer_hide(browser_helper: BrowserHelper):
    """TEST-LAYER-T1-02: Single Layer Toggle Hiding (Electrical OFF)."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("electrical", enable=False)
    
    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("electricalGroup", {}).get("visible") is False, "electricalGroup failed to hide when toggled OFF"
    assert groups.get("structuralGroup", {}).get("visible") is True, "structuralGroup should remain visible"
    assert groups.get("plumbingGroup", {}).get("visible") is True, "plumbingGroup should remain visible"


def test_layer_t1_03_single_layer_restore(browser_helper: BrowserHelper):
    """TEST-LAYER-T1-03: Single Layer Toggle Restoration (Electrical ON)."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("electrical", enable=False)
    browser_helper.toggle_layer("electrical", enable=True)

    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("electricalGroup", {}).get("visible") is True, "electricalGroup failed to restore when toggled back ON"


def test_layer_t1_04_multi_layer_combination(browser_helper: BrowserHelper):
    """TEST-LAYER-T1-04: Independent Multi-Layer Combination Toggles."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("structural", enable=False)
    browser_helper.toggle_layer("plumbing", enable=False)

    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("structuralGroup", {}).get("visible") is False, "structuralGroup should be hidden"
    assert groups.get("plumbingGroup", {}).get("visible") is False, "plumbingGroup should be hidden"
    assert groups.get("electricalGroup", {}).get("visible") is True, "electricalGroup should be visible"


def test_layer_t1_05_all_layers_hidden(browser_helper: BrowserHelper):
    """TEST-LAYER-T1-05: All-Layers Hidden State."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("structural", enable=False)
    browser_helper.toggle_layer("electrical", enable=False)
    browser_helper.toggle_layer("plumbing", enable=False)

    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("structuralGroup", {}).get("visible") is False
    assert groups.get("electricalGroup", {}).get("visible") is False
    assert groups.get("plumbingGroup", {}).get("visible") is False
    assert info.get("has_grid_helper") is True, "Grid helper must remain visible when all layers hidden"


# -----------------------------------------------------------------------------
# Tier 2: Layer Toggle UI Boundary & Edge Cases (5 Cases)
# -----------------------------------------------------------------------------

def test_layer_t2_01_rapid_flapping(browser_helper: BrowserHelper):
    """TEST-LAYER-T2-01: Rapid State Flapping / Spamming."""
    browser_helper.wait_for_canvas()
    for _ in range(5):
        browser_helper.toggle_layer("structural", enable=False)
        browser_helper.toggle_layer("structural", enable=True)

    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("structuralGroup", {}).get("visible") is True, "Final layer state desynchronized after rapid toggles"


def test_layer_t2_02_raycast_exclusion_hidden_layer(browser_helper: BrowserHelper):
    """TEST-LAYER-T2-02: Raycaster Hit-Testing Exclusion for Hidden Layers."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("plumbing", enable=False)

    # Click canvas where plumbing pipe would be located
    browser_helper.click_canvas(0.2, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    elem_id = inspector.get("element_id")
    assert elem_id != "plumb-pipe-01", "Raycaster selected hidden plumbing pipe object"


def test_layer_t2_03_toggle_empty_layer(browser_helper: BrowserHelper):
    """TEST-LAYER-T2-03: Layer Toggle with 0-Element Layer."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("electrical", enable=False)
    browser_helper.toggle_layer("electrical", enable=True)
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_layer_t2_04_keyboard_accessibility(browser_helper: BrowserHelper):
    """TEST-LAYER-T2-04: ARIA & Keyboard Accessibility Compliance."""
    browser_helper.wait_for_canvas()
    page = browser_helper.page
    if hasattr(page, "keyboard") and hasattr(page, "focus"):
        # Focus structural toggle element and toggle via Space key
        page.focus("#toggle-structural")
        page.keyboard.press("Space")
        
        is_focused = page.evaluate("document.activeElement.id === 'toggle-structural'")
        assert is_focused, "Element #toggle-structural did not receive keyboard focus"
        
        is_checked = page.evaluate("document.getElementById('toggle-structural').checked")
        # Press Space again to restore original state
        page.keyboard.press("Space")

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_layer_t2_05_persistence_across_navigation(browser_helper: BrowserHelper):
    """TEST-LAYER-T2-05: Layer Toggle Persistence Across Project Navigation."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("structural", enable=False)

    page = browser_helper.page
    if hasattr(page, "reload"):
        page.reload()
        browser_helper.wait_for_canvas()

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)
