import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class APIResponse:
    """Wrapper response class to unify httpx and urllib responses."""
    def __init__(self, status_code: int, data: bytes, headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self._data = data
        self.headers = headers or {}

    def json(self) -> Any:
        if not self._data:
            return None
        return json.loads(self._data.decode("utf-8"))

    @property
    def text(self) -> str:
        return self._data.decode("utf-8") if self._data else ""


class APIClient:
    """Async/Sync REST API helper wrapper for Builder AI backend testing."""
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Synchronous HTTP request executor supporting both httpx and fallback urllib."""
        url = self._url(path)
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                res = client.request(method=method, url=url, json=payload)
                headers = dict(res.headers)
                return APIResponse(status_code=res.status_code, data=res.content, headers=headers)
        else:
            data = json.dumps(payload).encode("utf-8") if payload is not None else None
            req = urllib.request.Request(
                url,
                data=data,
                method=method.upper(),
                headers={"Content-Type": "application/json"} if data else {}
            )
            try:
                with urllib.request.urlopen(req, timeout=10.0) as response:
                    content = response.read()
                    headers = dict(response.headers)
                    return APIResponse(status_code=response.status, data=content, headers=headers)
            except urllib.error.HTTPError as e:
                content = e.read()
                headers = dict(e.headers)
                return APIResponse(status_code=e.code, data=content, headers=headers)
            except urllib.error.URLError as e:
                raise RuntimeError(f"Connection failed to {url}: {e.reason}")

    def health_check(self) -> APIResponse:
        """Check backend server health."""
        try:
            return self.request("GET", "/health")
        except Exception:
            return self.request("GET", "/api/v1/health")

    def create_project(self, name: str, description: str = "") -> APIResponse:
        """POST /api/projects - Create project record and auto-generate 3D model layout."""
        payload = {"name": name}
        if description:
            payload["description"] = description
        return self.request("POST", "/api/projects", payload=payload)

    def list_projects(self) -> APIResponse:
        """GET /api/projects - List all projects."""
        return self.request("GET", "/api/projects")

    def get_model(self, project_id: Any) -> APIResponse:
        """GET /api/projects/{id}/model - Retrieve 3D model layout JSON."""
        return self.request("GET", f"/api/projects/{project_id}/model")

    def patch_element(self, project_id: Any, element_id: str, transform_data: Dict[str, Any]) -> APIResponse:
        """PATCH /api/projects/{id}/elements/{element_id} - Update element transform state."""
        return self.request("PATCH", f"/api/projects/{project_id}/elements/{element_id}", payload=transform_data)

    def delete_project(self, project_id: Any) -> APIResponse:
        """DELETE /api/projects/{id} - Delete project."""
        return self.request("DELETE", f"/api/projects/{project_id}")
