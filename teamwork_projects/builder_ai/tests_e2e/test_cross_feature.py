import pytest
from tests_e2e.utils.api_client import APIClient
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import assert_zero_console_errors, assert_http_status

# -----------------------------------------------------------------------------
# Tier 3: Cross-Feature Pairwise Combinatorial Matrix (18 Test Cases)
# -----------------------------------------------------------------------------

def setup_layer_state(browser_helper: BrowserHelper, struct: bool, elec: bool, plumb: bool):
    """Helper to configure layer visibility toggles."""
    browser_helper.wait_for_canvas()
    browser_helper.toggle_layer("structural", enable=struct)
    browser_helper.toggle_layer("electrical", enable=elec)
    browser_helper.toggle_layer("plumbing", enable=plumb)


def test_t3_01_struct_on_wall_gizmo(api_client: APIClient, browser_helper: BrowserHelper):
    """T3_01: Struct ON | Structural Wall | Gizmo Translate X+5."""
    setup_layer_state(browser_helper, struct=True, elec=False, plumb=False)
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-x", "5.0")

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["structuralGroup"]["visible"] is True
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t3_02_struct_on_elec_click_hidden(browser_helper: BrowserHelper):
    """T3_02: Struct ON | Electrical Box | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=True, elec=False, plumb=False)
    browser_helper.click_canvas(0.2, 0.5)  # Click at electrical box location

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "elec-conduit-01", "Hidden electrical element selected by raycaster"


def test_t3_03_struct_on_plumb_click_hidden(browser_helper: BrowserHelper):
    """T3_03: Struct ON | Plumbing Pipe | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=True, elec=False, plumb=False)
    browser_helper.click_canvas(0.1, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "plumb-pipe-01", "Hidden plumbing element selected by raycaster"


def test_t3_04_struct_elec_on_inspector_edit(browser_helper: BrowserHelper):
    """T3_04: Struct+Elec ON | Structural Col | Inspector Dimension Edit."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=False)
    browser_helper.click_canvas(0.5, 0.5)
    browser_helper.set_property_inspector_field("#inspector-height", "4.5")

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("height") in ["4.5", 4.5]


def test_t3_05_struct_elec_on_elec_gizmo(browser_helper: BrowserHelper):
    """T3_05: Struct+Elec ON | Electrical Conduit | Gizmo Translate."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=False)
    browser_helper.click_canvas(0.2, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-z", "-2.0")

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["structuralGroup"]["visible"] is True
    assert info["groups"]["electricalGroup"]["visible"] is True


def test_t3_06_struct_elec_on_plumb_click_hidden(browser_helper: BrowserHelper):
    """T3_06: Struct+Elec ON | Plumbing Riser | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=False)
    browser_helper.click_canvas(0.1, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "plumb-pipe-01"


def test_t3_07_all_on_toggle_off_during_selection(browser_helper: BrowserHelper):
    """T3_07: All Layers ON | Structural Wall | Toggle Layer OFF during selection."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=True)
    browser_helper.click_canvas(0.5, 0.5)  # Select structural wall
    browser_helper.toggle_layer("structural", enable=False)  # Toggle layer OFF

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") in [None, ""], "Inspector retained selection of hidden element"


def test_t3_08_all_on_elec_edit_toggle_cycle(browser_helper: BrowserHelper):
    """T3_08: All Layers ON | Electrical Box | Edit -> Toggle OFF -> Toggle ON."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=True)
    browser_helper.click_canvas(0.2, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-y", "3.5")

    browser_helper.toggle_layer("electrical", enable=False)
    browser_helper.toggle_layer("electrical", enable=True)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["electricalGroup"]["visible"] is True


def test_t3_09_all_on_plumb_gizmo(api_client: APIClient, browser_helper: BrowserHelper):
    """T3_09: All Layers ON | Plumbing Pipe | Gizmo Translate."""
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=True)
    browser_helper.click_canvas(0.1, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-x", "-5.0")

    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_t3_10_elec_on_struct_click_hidden(browser_helper: BrowserHelper):
    """T3_10: Elec ON | Structural Col | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=True, plumb=False)
    browser_helper.click_canvas(0.5, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "struct-col-01"


def test_t3_11_elec_on_elec_inspector_edit(browser_helper: BrowserHelper):
    """T3_11: Elec ON | Electrical Conduit | Inspector Dimension Edit."""
    setup_layer_state(browser_helper, struct=False, elec=True, plumb=False)
    browser_helper.click_canvas(0.2, 0.5)
    browser_helper.set_property_inspector_field("#inspector-width", "0.3")

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("width") in ["0.3", 0.3]


def test_t3_12_elec_on_plumb_click_hidden(browser_helper: BrowserHelper):
    """T3_12: Elec ON | Plumbing Riser | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=True, plumb=False)
    browser_helper.click_canvas(0.1, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "plumb-pipe-01"


def test_t3_13_plumb_on_struct_click_hidden(browser_helper: BrowserHelper):
    """T3_13: Plumb ON | Structural Wall | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=True)
    browser_helper.click_canvas(0.5, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "struct-col-01"


def test_t3_14_plumb_on_elec_click_hidden(browser_helper: BrowserHelper):
    """T3_14: Plumb ON | Electrical Box | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=True)
    browser_helper.click_canvas(0.2, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") != "elec-conduit-01"


def test_t3_15_plumb_on_plumb_edit_toggle_cycle(browser_helper: BrowserHelper):
    """T3_15: Plumb ON | Plumbing Pipe | Edit -> Toggle OFF -> Toggle ON."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=True)
    browser_helper.click_canvas(0.1, 0.5)
    browser_helper.set_property_inspector_field("#inspector-pos-z", "1.0")

    browser_helper.toggle_layer("plumbing", enable=False)
    browser_helper.toggle_layer("plumbing", enable=True)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["plumbingGroup"]["visible"] is True


def test_t3_16_all_off_struct_click_hidden(browser_helper: BrowserHelper):
    """T3_16: All Layers OFF | Structural Col | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=False)
    browser_helper.click_canvas(0.5, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") in [None, ""]


def test_t3_17_all_off_elec_click_hidden(browser_helper: BrowserHelper):
    """T3_17: All Layers OFF | Electrical Conduit | Click Hidden Element."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=False)
    browser_helper.click_canvas(0.2, 0.5)

    inspector = browser_helper.get_property_inspector_values()
    assert inspector.get("element_id") in [None, ""]


def test_t3_18_all_off_plumb_restore_all(browser_helper: BrowserHelper):
    """T3_18: All Layers OFF | Restore All Layers."""
    setup_layer_state(browser_helper, struct=False, elec=False, plumb=False)
    setup_layer_state(browser_helper, struct=True, elec=True, plumb=True)

    info = browser_helper.get_three_scene_info()
    assert info["groups"]["structuralGroup"]["visible"] is True
    assert info["groups"]["electricalGroup"]["visible"] is True
    assert info["groups"]["plumbingGroup"]["visible"] is True
