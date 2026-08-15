import math
from typing import Any, Dict, List, Union, Tuple

def assert_http_status(response: Any, expected_status: int, msg: str = ""):
    """Assert HTTP response status code with descriptive message."""
    actual_status = getattr(response, "status_code", None)
    if actual_status is None:
        raise AssertionError(f"Invalid response object: missing status_code attribute.")
    
    text = getattr(response, "text", "")
    assert actual_status == expected_status, (
        f"Expected HTTP status {expected_status}, but got {actual_status}. "
        f"Response body: {text[:300]}. {msg}"
    )

def assert_model_json_schema(model_data: Dict[str, Any]):
    """Assert structured 3D model JSON schema compliance."""
    assert isinstance(model_data, dict), f"Model data must be a JSON object, got {type(model_data)}"
    assert "project_id" in model_data or "id" in model_data, "Model missing project_id key"
    assert "layers" in model_data, "Model missing layers object"
    
    layers = model_data["layers"]
    assert isinstance(layers, dict), f"layers must be a JSON object, got {type(layers)}"
    
    for required_layer in ["structural", "electrical", "plumbing"]:
        assert required_layer in layers, f"layers dictionary missing '{required_layer}' layer"
        assert isinstance(layers[required_layer], list), f"Layer '{required_layer}' must be a list of elements"
        
        for elem in layers[required_layer]:
            assert "element_id" in elem or "id" in elem, f"Element in {required_layer} missing element_id"
            assert "type" in elem, f"Element {elem} missing type"
            assert "position" in elem, f"Element {elem} missing position"

def assert_coordinate_tolerance(
    actual_pos: Union[Dict[str, float], List[float], Tuple[float, float, float]],
    expected_pos: Union[Dict[str, float], List[float], Tuple[float, float, float]],
    tolerance: float = 1e-3,
    msg: str = ""
):
    """Assert 3D coordinate vector [X, Y, Z] equality within specified epsilon tolerance."""
    def _normalize(pos):
        if isinstance(pos, dict):
            return [float(pos.get("x", 0)), float(pos.get("y", 0)), float(pos.get("z", 0))]
        elif isinstance(pos, (list, tuple)):
            return [float(pos[0]), float(pos[1]), float(pos[2])]
        raise ValueError(f"Unrecognized coordinate format: {pos}")

    actual = _normalize(actual_pos)
    expected = _normalize(expected_pos)

    for axis_idx, axis_name in enumerate(["X", "Y", "Z"]):
        diff = abs(actual[axis_idx] - expected[axis_idx])
        assert diff <= tolerance, (
            f"Coordinate mismatch on {axis_name} axis: actual {actual[axis_idx]} vs expected {expected[axis_idx]} "
            f"(diff: {diff} > tolerance {tolerance}). {msg}"
        )

def assert_zero_console_errors(console_errors: List[str]):
    """Assert zero unhandled console errors logged during browser execution."""
    assert len(console_errors) == 0, (
        f"Expected 0 browser console errors, but found {len(console_errors)} errors:\n"
        + "\n".join(f"  - {err}" for err in console_errors)
    )

def assert_pydantic_validation_error(response: Any):
    """Assert response is HTTP 422 Unprocessable Entity with detail field."""
    assert_http_status(response, 422)
    data = response.json()
    assert isinstance(data, dict), "Response body must be JSON object"
    assert "detail" in data, "Validation error response missing 'detail' field"
