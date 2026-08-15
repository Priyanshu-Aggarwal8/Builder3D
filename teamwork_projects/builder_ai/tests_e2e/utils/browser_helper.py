from typing import List, Dict, Any, Optional

class BrowserHelper:
    """Playwright browser automation and WebGL 3D Canvas inspection helper."""
    def __init__(self, page):
        self.page = page
        self.console_errors: List[str] = []
        self._listener_attached = False

    def start_console_listener(self):
        """Listen to console error and page crash events."""
        if self._listener_attached:
            return

        def handle_console(msg):
            if msg.type == "error":
                text = msg.text
                # Filter out minor browser warnings if needed
                self.console_errors.append(text)

        def handle_page_error(error):
            self.console_errors.append(str(error))

        self.page.on("console", handle_console)
        self.page.on("pageerror", handle_page_error)
        self._listener_attached = True

    def get_console_errors(self) -> List[str]:
        """Return all logged console errors."""
        return list(self.console_errors)

    def clear_console_errors(self):
        """Clear captured console errors."""
        self.console_errors.clear()

    def wait_for_canvas(self, timeout_ms: int = 10000):
        """Wait for WebGL canvas and Three.js scene initialization in DOM."""
        self.page.wait_for_selector("canvas, #viewport", timeout=timeout_ms)
        # Wait until window.__THREE_SCENE__ is initialized
        self.page.wait_for_function("() => window.__THREE_SCENE__ !== undefined", timeout=timeout_ms)

    def get_three_scene_info(self) -> Dict[str, Any]:
        """Evaluate window.__THREE_SCENE__ in browser context and return scene graph metadata."""
        js_script = """
        () => {
            const scene = window.__THREE_SCENE__;
            if (!scene) return null;

            const info = {
                has_ambient_light: false,
                has_directional_light: false,
                has_grid_helper: false,
                total_children: scene.children ? scene.children.length : 0,
                groups: {}
            };

            if (scene.children) {
                for (const child of scene.children) {
                    if (child.type === 'AmbientLight' || child.isAmbientLight) info.has_ambient_light = true;
                    if (child.type === 'DirectionalLight' || child.isDirectionalLight) info.has_directional_light = true;
                    if (child.type === 'GridHelper' || child.isGridHelper) info.has_grid_helper = true;

                    if (child.name && (child.name.endsWith('Group') || child.type === 'Group')) {
                        const layerKey = child.name;
                        const childrenCount = child.children ? child.children.length : 0;
                        info.groups[layerKey] = {
                            name: child.name,
                            visible: child.visible !== false,
                            count: childrenCount,
                            children: (child.children || []).map(c => ({
                                element_id: c.element_id || c.name,
                                visible: c.visible !== false,
                                position: c.position ? {x: c.position.x, y: c.position.y, z: c.position.z} : null
                            }))
                        };
                    }
                }
            }
            return info;
        }
        """
        return self.page.evaluate(js_script)

    def toggle_layer(self, layer_name: str, enable: Optional[bool] = None) -> bool:
        """Click DOM toggle switch for layer (structural, electrical, plumbing)."""
        selector = f'[data-layer="{layer_name}"], #toggle-{layer_name}, input[name="{layer_name}"]'
        element = self.page.query_selector(selector)
        if element:
            is_checked = element.is_checked() if hasattr(element, "is_checked") else True
            if enable is None or enable != is_checked:
                element.click()
                return True
        return False

    def is_layer_visible_in_scene(self, group_name: str) -> bool:
        """Check Three.js group visibility state directly from window.__THREE_SCENE__."""
        info = self.get_three_scene_info()
        if not info or "groups" not in info:
            return False
        group = info["groups"].get(group_name)
        if not group:
            return False
        return group.get("visible", False)

    def click_canvas(self, x_ratio: float = 0.5, y_ratio: float = 0.5):
        """Click on canvas viewport at fractional ratio coordinates."""
        canvas = self.page.query_selector("canvas, #viewport")
        if canvas:
            box = canvas.bounding_box()
            if box:
                click_x = box["x"] + box["width"] * x_ratio
                click_y = box["y"] + box["height"] * y_ratio
                self.page.mouse.click(click_x, click_y)

    def get_property_inspector_values(self) -> Dict[str, Any]:
        """Fetch input values displayed in Property Inspector DOM sidebar."""
        return self.page.evaluate("""
        () => {
            const inspector = document.querySelector('#property-inspector');
            if (!inspector) return {};
            const getVal = (id) => {
                const el = document.querySelector(id);
                return el ? el.value || el.textContent : null;
            };
            return {
                element_id: getVal('#inspector-element-id'),
                name: getVal('#inspector-name'),
                layer: getVal('#inspector-layer'),
                pos_x: getVal('#inspector-pos-x'),
                pos_y: getVal('#inspector-pos-y'),
                pos_z: getVal('#inspector-pos-z'),
                width: getVal('#inspector-width'),
                height: getVal('#inspector-height'),
                depth: getVal('#inspector-depth')
            };
        }
        """)

    def set_property_inspector_field(self, field_selector: str, value: str):
        """Type value into Property Inspector input field and press Enter."""
        field = self.page.query_selector(field_selector)
        if field:
            try:
                field.fill(str(value))
                if hasattr(field, "press"):
                    field.press("Enter")
            except Exception:
                pass
            if hasattr(self.page, "evaluate"):
                try:
                    self.page.evaluate("""
                    (selector) => {
                        const el = document.querySelector(selector);
                        if (el) {
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    }
                    """, field_selector)
                except Exception:
                    pass
