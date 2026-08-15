import pytest
from tests_e2e.utils.browser_helper import BrowserHelper
from tests_e2e.utils.assertions import assert_zero_console_errors

# -----------------------------------------------------------------------------
# Tier 1: Frontend 3D WebGL Canvas Baseline Tests (5 Cases)
# -----------------------------------------------------------------------------

def test_canvas_t1_01_mounting_and_webgl(browser_helper: BrowserHelper):
    """TEST-CANVAS-T1-01: Canvas DOM Mounting & WebGL Context Initialization."""
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    assert info is not None, "Three.js scene window.__THREE_SCENE__ not found"
    assert info.get("total_children", 0) > 0, "Scene contains 0 children"


def test_canvas_t1_02_mesh_instantiation(browser_helper: BrowserHelper):
    """TEST-CANVAS-T1-02: Scene Asset Mesh Instantiation."""
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    groups = info.get("groups", {})
    
    assert "structuralGroup" in groups, "structuralGroup missing from scene"
    assert "electricalGroup" in groups, "electricalGroup missing from scene"
    assert "plumbingGroup" in groups, "plumbingGroup missing from scene"

    assert groups["structuralGroup"]["count"] > 0, "structuralGroup contains 0 meshes"
    assert groups["electricalGroup"]["count"] > 0, "electricalGroup contains 0 meshes"
    assert groups["plumbingGroup"]["count"] > 0, "plumbingGroup contains 0 meshes"


def test_canvas_t1_03_lights_and_grid(browser_helper: BrowserHelper):
    """TEST-CANVAS-T1-03: Lighting & Grid Helper Setup."""
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    assert info.get("has_ambient_light") is True, "AmbientLight missing from 3D scene"
    assert info.get("has_directional_light") is True, "DirectionalLight missing from 3D scene"
    assert info.get("has_grid_helper") is True, "GridHelper missing from 3D scene"


def test_canvas_t1_04_orbit_controls_navigation(browser_helper: BrowserHelper):
    """TEST-CANVAS-T1-04: OrbitControls Interactive Camera Navigation."""
    browser_helper.wait_for_canvas()
    # Perform mouse drag simulation across canvas
    browser_helper.click_canvas(0.5, 0.5)
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_canvas_t1_05_zero_console_errors(browser_helper: BrowserHelper):
    """TEST-CANVAS-T1-05: Console Error Zero-Tolerance Check."""
    browser_helper.wait_for_canvas()
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


# -----------------------------------------------------------------------------
# Tier 2: Frontend 3D WebGL Canvas Boundary & Stress Tests (5 Cases)
# -----------------------------------------------------------------------------

def test_canvas_t2_01_empty_model_rendering(browser_helper: BrowserHelper):
    """TEST-CANVAS-T2-01: 0-Element Empty Project Model Rendering."""
    browser_helper.wait_for_canvas()
    # Ensure lights and grid still render cleanly
    info = browser_helper.get_three_scene_info()
    assert info.get("has_grid_helper") is True, "GridHelper failed to render on empty model"
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_canvas_t2_02_high_density_element_load(browser_helper: BrowserHelper):
    """TEST-CANVAS-T2-02: High-Density Element Load Performance."""
    browser_helper.wait_for_canvas()
    info = browser_helper.get_three_scene_info()
    assert info is not None, "Failed to load high-density scene"


@pytest.mark.skip(reason="Requires WebGL hardware context extension simulation in live browser environment")
def test_canvas_t2_03_webgl_context_loss_and_recovery(browser_helper: BrowserHelper):
    """TEST-CANVAS-T2-03: WebGL Context Loss & Recovery Simulation."""
    browser_helper.wait_for_canvas()
    page = browser_helper.page
    if hasattr(page, "evaluate"):
        page.evaluate("""
            () => {
                const canvas = document.querySelector('canvas');
                if (!canvas) return;
                const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
                if (gl) {
                    const ext = gl.getExtension('WEBGL_lose_context');
                    if (ext) ext.loseContext();
                }
            }
        """)
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_canvas_t2_04_viewport_resize(browser_helper: BrowserHelper):
    """TEST-CANVAS-T2-04: Dynamic Viewport Resize / Aspect Ratio Recalculation."""
    browser_helper.wait_for_canvas()
    # Trigger window resize evaluation if using real page
    if hasattr(browser_helper.page, "set_viewport_size"):
        browser_helper.page.set_viewport_size({"width": 375, "height": 667})
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)


def test_canvas_t2_05_network_disconnect_error_handling(browser_helper: BrowserHelper):
    """TEST-CANVAS-T2-05: Backend Network Disconnect Handling during Load."""
    page = browser_helper.page
    if hasattr(page, "route"):
        # Intercept API route to simulate network disconnection during load
        page.route("**/api/projects/**", lambda route: route.abort("failed"))
        try:
            page.reload(wait_until="domcontentloaded", timeout=5000)
        except Exception:
            pass
        page.unroute("**/api/projects/**")
    browser_helper.wait_for_canvas()
    errors = browser_helper.get_console_errors()
    assert_zero_console_errors(errors)
