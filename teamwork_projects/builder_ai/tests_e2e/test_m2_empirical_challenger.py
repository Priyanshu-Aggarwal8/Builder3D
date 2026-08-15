import pytest
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import assert_zero_console_errors

def test_m2_dom_selectors_exist(browser_helper: BrowserHelper):
    """Empirical check: Verify required DOM selectors exist and are attached."""
    browser_helper.wait_for_canvas()
    page = browser_helper.page
    
    selectors = [
        "#viewport",
        "#property-inspector",
        "#toggle-structural",
        "#toggle-electrical",
        "#toggle-plumbing"
    ]
    for sel in selectors:
        element = page.query_selector(sel)
        assert element is not None, f"Required DOM selector {sel} was NOT found in document!"

def test_m2_rapid_layer_toggle_stress(browser_helper: BrowserHelper):
    """Empirical check: Rapidly toggle all 3 layers 20 times to stress rendering sync."""
    browser_helper.wait_for_canvas()
    
    for _ in range(20):
        browser_helper.toggle_layer("structural", enable=False)
        browser_helper.toggle_layer("electrical", enable=False)
        browser_helper.toggle_layer("plumbing", enable=False)
        
        browser_helper.toggle_layer("structural", enable=True)
        browser_helper.toggle_layer("electrical", enable=True)
        browser_helper.toggle_layer("plumbing", enable=True)
        
    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    assert groups.get("structuralGroup", {}).get("visible") is True
    assert groups.get("electricalGroup", {}).get("visible") is True
    assert groups.get("plumbingGroup", {}).get("visible") is True
    
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)

def test_m2_offline_resilience_fallback(browser_helper: BrowserHelper):
    """Empirical check: Simulate offline network disconnection and verify UI fallback state."""
    page = browser_helper.page
    if hasattr(page, "route"):
        page.route("**/api/**", lambda route: route.abort("failed"))
        try:
            page.reload(wait_until="domcontentloaded", timeout=5000)
        except Exception:
            pass
        page.unroute("**/api/**")
        
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    assert info is not None, "Canvas failed to load fallback scene when backend was unreachable"
    
    groups = info.get("groups", {})
    assert groups.get("structuralGroup", {}).get("count", 0) > 0
    assert groups.get("electricalGroup", {}).get("count", 0) > 0
    assert groups.get("plumbingGroup", {}).get("count", 0) > 0
    
    # Check fallback UI status badge
    status_text = page.inner_text(".status-pill")
    assert "Mock Data Mode" in status_text, f"Status pill expected 'Mock Data Mode', got '{status_text}'"

def test_m2_webgl_stability_under_resize(browser_helper: BrowserHelper):
    """Empirical check: Rapidly resize viewport and verify WebGL renderer stability."""
    browser_helper.wait_for_canvas()
    page = browser_helper.page
    
    if hasattr(page, "set_viewport_size"):
        sizes = [
            {"width": 1920, "height": 1080},
            {"width": 1024, "height": 768},
            {"width": 768, "height": 1024},
            {"width": 375, "height": 667},
            {"width": 1440, "height": 900}
        ]
        for size in sizes:
            page.set_viewport_size(size)
            
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)
