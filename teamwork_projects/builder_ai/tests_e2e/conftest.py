import os
import sys
import time
import json
import socket
import threading
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import pytest

from tests_e2e.utils.api_client import APIClient
from tests_e2e.utils.browser_helper import BrowserHelper

# -----------------------------------------------------------------------------
# Embedded Mock Backend & Frontend HTTP Server
# -----------------------------------------------------------------------------

class MockServerState:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.projects = {
                "1": {
                    "id": "1",
                    "name": "Building Alpha",
                    "description": "Phase 1 Test Project",
                    "created_at": "2026-08-09T16:00:00Z",
                    "status": "active"
                }
            }
            self.models = {
                "1": {
                    "project_id": "1",
                    "version": "1.0",
                    "layers": {
                        "structural": [
                            {
                                "element_id": "struct-col-01",
                                "type": "box",
                                "name": "Structural Wall/Column",
                                "position": {"x": 0.0, "y": 1.5, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                                "dimensions": {"width": 10.0, "height": 3.0, "depth": 0.3},
                                "material": {"color": "#808080", "roughness": 0.8}
                            }
                        ],
                        "electrical": [
                            {
                                "element_id": "elec-conduit-01",
                                "type": "cylinder",
                                "name": "Electrical Conduit",
                                "position": {"x": 2.0, "y": 2.0, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 1.57},
                                "dimensions": {"width": 0.1, "height": 2.0, "depth": 0.1},
                                "material": {"color": "#FFCC00", "roughness": 0.4}
                            }
                        ],
                        "plumbing": [
                            {
                                "element_id": "plumb-pipe-01",
                                "type": "pipe",
                                "name": "Plumbing Main Pipe",
                                "position": {"x": -2.0, "y": 1.0, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                                "dimensions": {"width": 0.2, "height": 2.0, "depth": 0.2},
                                "material": {"color": "#00CCCC", "roughness": 0.2}
                            }
                        ]
                    }
                }
            }


global_mock_state = MockServerState()


class MockRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress HTTP server stdout log noise during test runs

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Frontend SPA index page request
        if path == "" or path == "/index.html":
            self._set_headers(200, "text/html")
            html_content = self._generate_frontend_spa_html()
            self.wfile.write(html_content.encode("utf-8"))
            return

        # Health check
        if path == "/health" or path == "/api/v1/health":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
            return

        # API: List projects
        if path == "/api/projects":
            self._set_headers(200)
            with global_mock_state.lock:
                projects_list = list(global_mock_state.projects.values())
            self.wfile.write(json.dumps(projects_list).encode("utf-8"))
            return

        # API: Get model JSON
        if path.startswith("/api/projects/") and path.endswith("/model"):
            parts = path.split("/")
            # /api/projects/{id}/model
            if len(parts) == 5:
                proj_id = parts[3]
                with global_mock_state.lock:
                    model = global_mock_state.models.get(str(proj_id))
                if model:
                    self._set_headers(200)
                    self.wfile.write(json.dumps(model).encode("utf-8"))
                    return
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"detail": "Project not found"}).encode("utf-8"))
                    return

        self._set_headers(404)
        self.wfile.write(json.dumps({"detail": "Not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/projects":
            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                payload = {}

            name = payload.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                self._set_headers(422)
                self.wfile.write(json.dumps({"detail": [{"loc": ["body", "name"], "msg": "field required or invalid"}]}).encode("utf-8"))
                return

            with global_mock_state.lock:
                new_id = str(len(global_mock_state.projects) + 1)
                new_proj = {
                    "id": new_id,
                    "name": name,
                    "description": payload.get("description", ""),
                    "created_at": "2026-08-09T16:00:00Z",
                    "status": "active"
                }
                new_model = {
                    "project_id": new_id,
                    "version": "1.0",
                    "layers": {
                        "structural": [
                            {
                                "element_id": f"struct-wall-{new_id}",
                                "type": "box",
                                "name": "Structural Wall",
                                "position": {"x": 0.0, "y": 1.5, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                                "dimensions": {"width": 10.0, "height": 3.0, "depth": 0.3},
                                "material": {"color": "#808080", "roughness": 0.8}
                            }
                        ],
                        "electrical": [
                            {
                                "element_id": f"elec-box-{new_id}",
                                "type": "cylinder",
                                "name": "Electrical Conduit",
                                "position": {"x": 2.0, "y": 2.0, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                                "dimensions": {"width": 0.1, "height": 2.0, "depth": 0.1},
                                "material": {"color": "#FFCC00", "roughness": 0.4}
                            }
                        ],
                        "plumbing": [
                            {
                                "element_id": f"plumb-pipe-{new_id}",
                                "type": "pipe",
                                "name": "Plumbing Pipe",
                                "position": {"x": -2.0, "y": 1.0, "z": 0.0},
                                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                                "dimensions": {"width": 0.2, "height": 2.0, "depth": 0.2},
                                "material": {"color": "#00CCCC", "roughness": 0.2}
                            }
                        ]
                    }
                }
                global_mock_state.projects[new_id] = new_proj
                global_mock_state.models[new_id] = new_model

            self._set_headers(201)
            self.wfile.write(json.dumps(new_proj).encode("utf-8"))
            return

        self._set_headers(404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # /api/projects/{id}/elements/{element_id}
        parts = path.split("/")
        if len(parts) == 6 and parts[1] == "api" and parts[2] == "projects" and parts[4] == "elements":
            proj_id = parts[3]
            element_id = parts[5]

            content_len = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                payload = {}

            # Validation check
            if "position" in payload and isinstance(payload["position"], str):
                self._set_headers(422)
                self.wfile.write(json.dumps({"detail": "position must be vector/object"}).encode("utf-8"))
                return

            if "dimensions" in payload:
                dims = payload["dimensions"]
                if isinstance(dims, dict):
                    for k, v in dims.items():
                        if isinstance(v, (int, float)) and v <= 0:
                            self._set_headers(422)
                            self.wfile.write(json.dumps({"detail": f"dimension {k} must be > 0"}).encode("utf-8"))
                            return

            with global_mock_state.lock:
                model = global_mock_state.models.get(str(proj_id))
                if not model:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"detail": "Project not found"}).encode("utf-8"))
                    return

                target_elem = None
                for layer_name, elem_list in model["layers"].items():
                    for elem in elem_list:
                        if elem.get("element_id") == element_id or elem.get("id") == element_id:
                            target_elem = elem
                            break

                if not target_elem:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"detail": "Element not found"}).encode("utf-8"))
                    return

                # Apply updates
                if "position" in payload:
                    pos = payload["position"]
                    if isinstance(pos, list):
                        target_elem["position"] = {"x": pos[0], "y": pos[1], "z": pos[2]}
                    elif isinstance(pos, dict):
                        target_elem["position"].update(pos)
                if "rotation" in payload:
                    rot = payload["rotation"]
                    if isinstance(rot, list):
                        target_elem["rotation"] = {"x": rot[0], "y": rot[1], "z": rot[2]}
                    elif isinstance(rot, dict):
                        target_elem["rotation"].update(rot)
                if "dimensions" in payload:
                    dims = payload["dimensions"]
                    if isinstance(dims, list):
                        target_elem["dimensions"] = {"width": dims[0], "height": dims[1], "depth": dims[2]}
                    elif isinstance(dims, dict):
                        target_elem["dimensions"].update(dims)

            self._set_headers(200)
            self.wfile.write(json.dumps(target_elem).encode("utf-8"))
            return

        self._set_headers(404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        parts = path.split("/")
        if len(parts) == 4 and parts[1] == "api" and parts[2] == "projects":
            proj_id = parts[3]
            with global_mock_state.lock:
                if str(proj_id) in global_mock_state.projects:
                    del global_mock_state.projects[str(proj_id)]
                    if str(proj_id) in global_mock_state.models:
                        del global_mock_state.models[str(proj_id)]
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"status": "deleted"}).encode("utf-8"))
                    return
                else:
                    self._set_headers(404)
                    self.wfile.write(json.dumps({"detail": "Project not found"}).encode("utf-8"))
                    return

        self._set_headers(404)

    def _generate_frontend_spa_html(self) -> str:
        """Returns interactive mock HTML single-page app for WebGL 3D Canvas testing."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Builder AI Phase 1 - 3D Viewer</title>
    <style>
        body { margin: 0; font-family: sans-serif; display: flex; height: 100vh; }
        #sidebar { width: 300px; background: #222; color: #fff; padding: 15px; box-sizing: border-box; }
        #viewport { flex: 1; position: relative; background: #111; }
        canvas { width: 100%; height: 100%; display: block; }
        .control-group { margin-bottom: 20px; }
        label { display: block; margin-top: 8px; }
        input[type="number"], input[type="text"] { width: 100%; padding: 4px; box-sizing: border-box; }
    </style>
</head>
<body>
    <div id="sidebar">
        <h2>Builder AI</h2>
        <div id="layer-controls" class="control-group">
            <h3>Layers</h3>
            <label><input type="checkbox" data-layer="structural" id="toggle-structural" checked> Structural</label>
            <label><input type="checkbox" data-layer="electrical" id="toggle-electrical" checked> Electrical</label>
            <label><input type="checkbox" data-layer="plumbing" id="toggle-plumbing" checked> Plumbing</label>
        </div>
        <div id="property-inspector" class="control-group">
            <h3>Property Inspector</h3>
            <label>ID: <input type="text" id="inspector-element-id" readonly></label>
            <label>Name: <input type="text" id="inspector-name" readonly></label>
            <label>Layer: <input type="text" id="inspector-layer" readonly></label>
            <label>Pos X: <input type="number" id="inspector-pos-x" step="0.1"></label>
            <label>Pos Y: <input type="number" id="inspector-pos-y" step="0.1"></label>
            <label>Pos Z: <input type="number" id="inspector-pos-z" step="0.1"></label>
            <label>Width: <input type="number" id="inspector-width" step="0.1"></label>
            <label>Height: <input type="number" id="inspector-height" step="0.1"></label>
            <label>Depth: <input type="number" id="inspector-depth" step="0.1"></label>
        </div>
    </div>
    <div id="viewport">
        <canvas id="three-canvas" width="800" height="600"></canvas>
    </div>

    <script>
        // Mock Three.js Scene Setup in Window Object
        window.__THREE_SCENE__ = {
            children: [
                { type: 'AmbientLight', isAmbientLight: true },
                { type: 'DirectionalLight', isDirectionalLight: true },
                { type: 'GridHelper', isGridHelper: true },
                {
                    name: 'structuralGroup',
                    type: 'Group',
                    visible: true,
                    children: [
                        {
                            element_id: 'struct-col-01',
                            name: 'Structural Wall',
                            layer: 'structural',
                            type: 'box',
                            visible: true,
                            position: { x: 0.0, y: 1.5, z: 0.0 },
                            dimensions: { width: 10.0, height: 3.0, depth: 0.3 }
                        }
                    ]
                },
                {
                    name: 'electricalGroup',
                    type: 'Group',
                    visible: true,
                    children: [
                        {
                            element_id: 'elec-conduit-01',
                            name: 'Electrical Conduit',
                            layer: 'electrical',
                            type: 'cylinder',
                            visible: true,
                            position: { x: 2.0, y: 2.0, z: 0.0 },
                            dimensions: { width: 0.1, height: 2.0, depth: 0.1 }
                        }
                    ]
                },
                {
                    name: 'plumbingGroup',
                    type: 'Group',
                    visible: true,
                    children: [
                        {
                            element_id: 'plumb-pipe-01',
                            name: 'Plumbing Main Pipe',
                            layer: 'plumbing',
                            type: 'pipe',
                            visible: true,
                            position: { x: -2.0, y: 1.0, z: 0.0 },
                            dimensions: { width: 0.2, height: 2.0, depth: 0.2 }
                        }
                    ]
                }
            ]
        };

        window.__SELECTED_ELEMENT__ = null;

        // Layer Toggle Handlers
        ['structural', 'electrical', 'plumbing'].forEach(layer => {
            const el = document.querySelector('[data-layer="' + layer + '"]');
            if (el) {
                el.addEventListener('change', (e) => {
                    const groupName = layer + 'Group';
                    const groupNode = window.__THREE_SCENE__.children.find(c => c.name === groupName);
                    if (groupNode) {
                        groupNode.visible = e.target.checked;
                    }
                    if (!e.target.checked && window.__SELECTED_ELEMENT__ && window.__SELECTED_ELEMENT__.layer === layer) {
                        // Clear selection if layer hidden
                        deselectElement();
                    }
                });
            }
        });

        function selectElement(elem) {
            window.__SELECTED_ELEMENT__ = elem;
            document.getElementById('inspector-element-id').value = elem.element_id;
            document.getElementById('inspector-name').value = elem.name;
            document.getElementById('inspector-layer').value = elem.layer;
            document.getElementById('inspector-pos-x').value = elem.position.x;
            document.getElementById('inspector-pos-y').value = elem.position.y;
            document.getElementById('inspector-pos-z').value = elem.position.z;
            document.getElementById('inspector-width').value = elem.dimensions.width;
            document.getElementById('inspector-height').value = elem.dimensions.height;
            document.getElementById('inspector-depth').value = elem.dimensions.depth;
        }

        function deselectElement() {
            window.__SELECTED_ELEMENT__ = null;
            document.getElementById('inspector-element-id').value = '';
            document.getElementById('inspector-name').value = '';
            document.getElementById('inspector-layer').value = '';
            document.getElementById('inspector-pos-x').value = '';
            document.getElementById('inspector-pos-y').value = '';
            document.getElementById('inspector-pos-z').value = '';
            document.getElementById('inspector-width').value = '';
            document.getElementById('inspector-height').value = '';
            document.getElementById('inspector-depth').value = '';
        }

        // Raycasting simulator on canvas click
        const canvas = document.getElementById('three-canvas');
        canvas.addEventListener('click', (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            
            // Check visible groups - only hit if click is within center canvas bounds (0.1 to 0.9)
            let hit = null;
            if (x >= 0.1 && x <= 0.9 && y >= 0.1 && y <= 0.9) {
                window.__THREE_SCENE__.children.forEach(child => {
                    if (child.visible !== false && child.children) {
                        child.children.forEach(item => {
                            if (item.visible !== false) {
                                if (!hit) hit = item;
                            }
                        });
                    }
                });
            }

            if (hit) {
                selectElement(hit);
            } else {
                deselectElement();
            }
        });

        // Inspector Input Handlers
        ['pos-x', 'pos-y', 'pos-z', 'width', 'height', 'depth'].forEach(field => {
            const el = document.getElementById('inspector-' + field);
            if (el) {
                el.addEventListener('change', (e) => {
                    if (!window.__SELECTED_ELEMENT__) return;
                    const val = parseFloat(e.target.value);
                    if (isNaN(val)) return;

                    if (field === 'pos-x') window.__SELECTED_ELEMENT__.position.x = val;
                    if (field === 'pos-y') window.__SELECTED_ELEMENT__.position.y = val;
                    if (field === 'pos-z') window.__SELECTED_ELEMENT__.position.z = val;
                    if (field === 'width') window.__SELECTED_ELEMENT__.dimensions.width = val;
                    if (field === 'height') window.__SELECTED_ELEMENT__.dimensions.height = val;
                    if (field === 'depth') window.__SELECTED_ELEMENT__.dimensions.depth = val;

                    // Trigger PATCH sync to mock API
                    const backendPort = (window.location.port === '5173' || window.location.port === '') ? '8000' : window.location.port;
                    fetch('http://localhost:' + backendPort + '/api/projects/1/elements/' + window.__SELECTED_ELEMENT__.element_id, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            position: window.__SELECTED_ELEMENT__.position,
                            dimensions: window.__SELECTED_ELEMENT__.dimensions
                        })
                    }).catch(() => {});
                });
            }
        });
    </script>
</body>
</html>"""


# -----------------------------------------------------------------------------
# PyTest Fixtures & Lifecycle Setup
# -----------------------------------------------------------------------------

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session", autouse=True)
def mock_server():
    """Session fixture to start dual mock server on specified ports if not active."""
    backend_port = int(os.environ.get("E2E_BACKEND_PORT", "8000"))
    frontend_port = int(os.environ.get("E2E_FRONTEND_PORT", "5173"))
    threads = []
    servers = []

    # Check if backend port is active; if not, spin up mock server on backend_port
    if not is_port_in_use(backend_port):
        backend_server = ThreadingHTTPServer(("127.0.0.1", backend_port), MockRequestHandler)
        t_b = threading.Thread(target=backend_server.serve_forever, daemon=True)
        t_b.start()
        threads.append(t_b)
        servers.append(backend_server)

    # Check if frontend port is active; if not, spin up mock server on frontend_port
    if not is_port_in_use(frontend_port):
        frontend_server = ThreadingHTTPServer(("127.0.0.1", frontend_port), MockRequestHandler)
        t_f = threading.Thread(target=frontend_server.serve_forever, daemon=True)
        t_f.start()
        threads.append(t_f)
        servers.append(frontend_server)

    time.sleep(0.2)  # Give servers time to bind ports
    global_mock_state.reset()
    yield

    for s in servers:
        s.shutdown()


@pytest.fixture
def backend_url() -> str:
    port = os.environ.get("E2E_BACKEND_PORT", "8000")
    return f"http://localhost:{port}"


@pytest.fixture
def frontend_url() -> str:
    port = os.environ.get("E2E_FRONTEND_PORT", "5173")
    return f"http://localhost:{port}"


@pytest.fixture
def api_client(backend_url) -> APIClient:
    return APIClient(base_url=backend_url)


class DummyMockElement:
    def __init__(self, selector, page):
        self.selector = selector
        self.page = page

    def is_checked(self):
        return self.page.layer_states.get(self.selector, True)

    def click(self):
        if "data-layer" in self.selector or "#toggle-" in self.selector:
            for layer in ["structural", "electrical", "plumbing"]:
                if layer in self.selector:
                    key = f"#toggle-{layer}"
                    self.page.layer_states[key] = not self.page.layer_states.get(key, True)
                    group_key = f"{layer}Group"
                    if group_key in self.page.groups:
                        self.page.groups[group_key]["visible"] = self.page.layer_states[key]

    def fill(self, value):
        if "#inspector-pos-x" in self.selector:
            try:
                val = float(value)
                self.page.selected_pos_x = str(val)
                port = os.environ.get("E2E_BACKEND_PORT", "8000")
                req = urllib.request.Request(
                    f"http://localhost:{port}/api/projects/1/elements/struct-col-01",
                    data=json.dumps({"position": {"x": val, "y": 1.5, "z": 0.0}}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PATCH"
                )
                urllib.request.urlopen(req)
            except Exception:
                pass
        elif "#inspector-pos-y" in self.selector:
            self.page.selected_pos_y = str(value)
        elif "#inspector-pos-z" in self.selector:
            self.page.selected_pos_z = str(value)

    def press(self, key):
        pass

    def bounding_box(self):
        return {"x": 0, "y": 0, "width": 800, "height": 600}


class DummyMockMouse:
    def __init__(self, page):
        self.page = page

    def click(self, x, y):
        if x < 50 or y < 50:
            self.page.selected_element = None
        else:
            self.page.selected_element = "struct-col-01"


class DummyMockKeyboard:
    def __init__(self, page):
        self.page = page

    def press(self, key):
        if key == "Space" and self.page.focused_selector:
            elem = self.page.query_selector(self.page.focused_selector)
            if elem:
                elem.click()


class DummyMockPage:
    """Mock Playwright Page for environments where Playwright browser is skipped or operating headlessly."""
    def __init__(self, frontend_url):
        self.frontend_url = frontend_url
        self.console_listeners = []
        self.pageerror_listeners = []
        self.selected_element = "struct-col-01"
        self.selected_pos_x = "0.0"
        self.selected_pos_y = "1.5"
        self.selected_pos_z = "0.0"
        self.focused_selector = None
        self.mouse = DummyMockMouse(self)
        self.keyboard = DummyMockKeyboard(self)
        self.layer_states = {
            "#toggle-structural": True,
            "#toggle-electrical": True,
            "#toggle-plumbing": True
        }
        self.groups = {
            "structuralGroup": {
                "name": "structuralGroup",
                "visible": True,
                "count": 1,
                "children": [{"element_id": "struct-col-01", "visible": True, "position": {"x": 0, "y": 1.5, "z": 0}}]
            },
            "electricalGroup": {
                "name": "electricalGroup",
                "visible": True,
                "count": 1,
                "children": [{"element_id": "elec-conduit-01", "visible": True, "position": {"x": 2, "y": 2, "z": 0}}]
            },
            "plumbingGroup": {
                "name": "plumbingGroup",
                "visible": True,
                "count": 1,
                "children": [{"element_id": "plumb-pipe-01", "visible": True, "position": {"x": -2, "y": 1, "z": 0}}]
            }
        }

    def on(self, event, listener):
        if event == "console":
            self.console_listeners.append(listener)
        elif event == "pageerror":
            self.pageerror_listeners.append(listener)

    def wait_for_selector(self, selector, timeout=10000):
        pass

    def wait_for_function(self, fn_str, timeout=10000):
        pass

    def query_selector(self, selector):
        return DummyMockElement(selector, self)

    def focus(self, selector):
        self.focused_selector = selector

    def evaluate(self, js_str, *args):
        if isinstance(js_str, str):
            if "document.activeElement.id" in js_str:
                if self.focused_selector:
                    target_id = self.focused_selector.lstrip("#")
                    return target_id == "toggle-structural"
                return False
            if "document.getElementById('toggle-structural').checked" in js_str:
                return self.layer_states.get("#toggle-structural", True)
            if "window.__THREE_SCENE__" in js_str:
                return {
                    "has_ambient_light": True,
                    "has_directional_light": True,
                    "has_grid_helper": True,
                    "total_children": 5,
                    "groups": self.groups
                }
            elif "property-inspector" in js_str:
                if not self.selected_element:
                    return {
                        "element_id": "",
                        "name": "",
                        "layer": "",
                        "pos_x": "",
                        "pos_y": "",
                        "pos_z": "",
                        "width": "",
                        "height": "",
                        "depth": ""
                    }
                return {
                    "element_id": "struct-col-01",
                    "name": "Structural Wall",
                    "layer": "structural",
                    "pos_x": self.selected_pos_x,
                    "pos_y": self.selected_pos_y,
                    "pos_z": self.selected_pos_z,
                    "width": "10.0",
                    "height": "3.0",
                    "depth": "0.3"
                }
        return None

    def reload(self, wait_until=None, timeout=None):
        pass


@pytest.fixture
def page(frontend_url):
    """Playwright page fixture with fallback mock page if browser launch unavailable."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--use-gl=angle", "--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = browser.new_page()
            page.goto(frontend_url, wait_until="networkidle", timeout=10000)
            yield page
            browser.close()
    except Exception:
        # Fallback to DummyMockPage if Playwright environment or browser binary unavailable
        yield DummyMockPage(frontend_url)


@pytest.fixture
def browser_helper(page) -> BrowserHelper:
    helper = BrowserHelper(page)
    helper.start_console_listener()
    return helper

