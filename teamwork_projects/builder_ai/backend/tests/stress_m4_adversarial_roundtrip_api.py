"""
Adversarial Empirical Stress Test Suite for Milestone 4:
1. 10-Iteration Semantic Round-Trip Invariance ($M -> STEP -> M_1 -> ... -> M_{10}$) with Zero Drift.
2. Hosted Opening Voiding & Filling Relations (IfcRelVoidsElement, IfcRelFillsElement, host_wall_id).
3. FastAPI REST API Endpoints (valid, invalid, edge cases, error propagation).
"""

import copy
import io
import json
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.bim import (
    CanonicalBIMModel,
    BIMProject,
    BIMSite,
    BIMBuilding,
    BIMStorey,
    BIMSpace,
    BIMWall,
    BIMDoor,
    BIMWindow,
    BIMSlab,
    BIMColumn,
    BIMDistributionElement,
    CanonicalBIMEntity,
    PropertySet,
    PropertyItem,
    create_pset_wall_common,
    create_pset_door_common,
    create_pset_window_common,
    create_pset_space_common,
    create_pset_slab_common,
    create_pset_column_common,
    create_pset_flow_segment_common,
)
from app.schemas.spatial import encode_ifc_guid, decode_ifc_guid
from app.services.ifc_compiler import (
    compile_bim_to_ifc4_step,
    parse_ifc4_step_to_bim,
    StepFile,
    StepParser,
    StepSyntaxError,
)

client = TestClient(app)


# ==============================================================================
# Helper to build complex multi-storey BIM model
# ==============================================================================
def create_complex_test_model(name: str = "Test Invariance Project") -> CanonicalBIMModel:
    proj = BIMProject(name=name)
    site = BIMSite(name="Highland Park Site", site_area_sqm=2500.0, elevation_amsl=125.5)
    bldg = BIMBuilding(name="Aurora Tower", typology="MixedUse", total_storeys=3)

    # Storey 0: Ground Floor
    st0 = BIMStorey(name="Ground Floor", storey_index=0, elevation=0.0, height=3.5)
    
    # Walls on Storey 0
    w0_1 = BIMWall(
        name="Ground North Wall",
        position=(0.0, 1.75, -8.0),
        dimensions={"width": 16.0, "height": 3.5, "depth": 0.3},
        thickness=0.3,
        height=3.5,
        is_exterior=True,
        load_bearing=True,
    )
    w0_1.set_property("Pset_WallCommon", "FireRating", "3h", "IfcLabel")
    w0_1.set_property("Pset_WallCommon", "AcousticRating", "55dB", "IfcLabel")
    w0_1.set_property("Pset_WallCommon", "Combustible", False, "IfcBoolean")
    w0_1.set_property("Pset_StructuralEngineering", "RebarDensityKgM3", 120.5, "IfcReal")

    w0_2 = BIMWall(
        name="Ground South Wall",
        position=(0.0, 1.75, 8.0),
        dimensions={"width": 16.0, "height": 3.5, "depth": 0.25},
        thickness=0.25,
        height=3.5,
        is_exterior=True,
        load_bearing=True,
    )

    # Hosted Openings on Wall 1
    d0_1 = BIMDoor(
        name="Grand Pivot Entrance Door",
        host_wall_id=w0_1.global_id,
        position=(2.0, 1.3, -8.0),
        dimensions={"width": 1.4, "height": 2.6, "depth": 0.15},
        width=1.4,
        height=2.6,
        operation_type="SINGLE_SWING_LEFT",
    )
    d0_1.set_property("Pset_DoorCommon", "SecurityRating", "RC4", "IfcLabel")
    d0_1.set_property("Pset_DoorCommon", "FireRating", "2h", "IfcLabel")

    win0_1 = BIMWindow(
        name="Ground Floor Display Window",
        host_wall_id=w0_1.global_id,
        position=(-3.0, 1.75, -8.0),
        dimensions={"width": 3.0, "height": 2.2, "depth": 0.1},
        width=3.0,
        height=2.2,
        sill_height=0.6,
        thermal_transmittance=0.9,
    )

    # Hosted Window on Wall 2
    win0_2 = BIMWindow(
        name="South Garden Window",
        host_wall_id=w0_2.global_id,
        position=(0.0, 1.75, 8.0),
        dimensions={"width": 2.4, "height": 1.8, "depth": 0.1},
        width=2.4,
        height=1.8,
        sill_height=0.9,
        thermal_transmittance=1.1,
    )

    # Space
    sp0_1 = BIMSpace(
        name="Grand Lobby & Reception",
        area_sqm=85.0,
        ceiling_height=3.5,
        room_type="Commercial_Lobby",
        is_exterior=False,
    )
    sp0_1.set_property("Pset_SpaceCommon", "GrossFloorArea", 85.0, "IfcAreaMeasure")
    sp0_1.set_property("Pset_SpaceCommon", "HandicapAccessible", True, "IfcBoolean")

    # Slab and Column
    slab0 = BIMSlab(name="Ground Foundation Mat", thickness=0.45, slab_type="BASESLAB")
    col0_1 = BIMColumn(name="Plaza Column C1", width=0.6, depth=0.6, height=3.5, rebar_ratio=0.03)

    # MEP
    pipe0_1 = BIMDistributionElement(
        name="Main Stormwater Riser",
        entity_type="IfcFlowSegment",
        system_type="SoilWaste",
        nominal_diameter_mm=160.0,
    )

    st0.walls.extend([w0_1, w0_2])
    st0.doors.append(d0_1)
    st0.windows.extend([win0_1, win0_2])
    st0.spaces.append(sp0_1)
    st0.slabs.append(slab0)
    st0.columns.append(col0_1)
    st0.distribution_elements.append(pipe0_1)

    # Storey 1: First Floor
    st1 = BIMStorey(name="First Level Office", storey_index=1, elevation=3.5, height=3.2)
    w1_1 = BIMWall(name="First Floor Curtain Wall Spandrel", position=(0.0, 5.1, -8.0), thickness=0.2, height=3.2)
    sp1_1 = BIMSpace(name="Open Office Suite", area_sqm=120.0, ceiling_height=3.0, room_type="Commercial_Office")
    st1.walls.append(w1_1)
    st1.spaces.append(sp1_1)

    bldg.storeys.extend([st0, st1])
    site.buildings.append(bldg)
    proj.sites.append(site)

    model = CanonicalBIMModel(project=proj, project_name=name)
    model.link_spatial_hierarchy()
    return model


# ==============================================================================
# 1. Ten-Round-Trip Invariance Tests
# ==============================================================================
class TestTenIterationRoundTripInvariance:
    """Stress tests 10 consecutive round-trips M -> STEP -> M1 -> ... -> M10."""

    def test_10_consecutive_roundtrips_zero_drift(self):
        """Verify that 10 consecutive compiles and parses produce identical semantic models with zero drift."""
        m_curr = create_complex_test_model("Adversarial 10-Pass Invariance")
        
        # Snapshot initial state
        initial_proj_guid = m_curr.project.global_id
        initial_site_guid = m_curr.project.sites[0].global_id
        initial_bldg_guid = m_curr.project.sites[0].buildings[0].global_id
        initial_storey_guids = [s.global_id for s in m_curr.all_storeys()]
        initial_walls_guids = [w.global_id for w in m_curr.all_walls()]
        initial_spaces_guids = [s.global_id for s in m_curr.all_spaces()]
        initial_doors_guids = [d.global_id for d in m_curr.all_elements() if d.entity_type == "IfcDoor"]
        initial_windows_guids = [w.global_id for w in m_curr.all_elements() if w.entity_type == "IfcWindow"]
        initial_total_elements = len(m_curr.all_elements())

        # Collect all initial Pset contents
        def extract_psets_summary(model: CanonicalBIMModel) -> Dict[str, Dict[str, Any]]:
            summary = {}
            for el in model.all_elements():
                summary[el.global_id] = {
                    "entity_type": el.entity_type,
                    "name": el.name,
                    "psets": {k: v.to_flat_dict() for k, v in el.property_sets.items()}
                }
            return summary

        initial_summary = extract_psets_summary(m_curr)

        step_history: List[str] = []
        model_history: List[CanonicalBIMModel] = [m_curr]

        for iteration in range(1, 11):
            step_text = compile_bim_to_ifc4_step(m_curr)
            step_history.append(step_text)

            m_next = parse_ifc4_step_to_bim(step_text)
            model_history.append(m_next)

            # Invariant 1: Hierarchy and Project names/GUIDs
            assert m_next.project.global_id == initial_proj_guid, f"Pass {iteration}: Project GUID mutated"
            assert m_next.project.name == "Adversarial 10-Pass Invariance", f"Pass {iteration}: Project Name mutated"
            assert len(m_next.project.sites) == 1, f"Pass {iteration}: Site count changed"
            assert m_next.project.sites[0].global_id == initial_site_guid, f"Pass {iteration}: Site GUID mutated"
            assert m_next.project.sites[0].buildings[0].global_id == initial_bldg_guid, f"Pass {iteration}: Building GUID mutated"

            # Invariant 2: Storeys
            curr_storey_guids = [s.global_id for s in m_next.all_storeys()]
            assert curr_storey_guids == initial_storey_guids, f"Pass {iteration}: Storey GUIDs changed"
            assert len(m_next.all_storeys()) == 2

            # Invariant 3: Element Counts
            assert len(m_next.all_elements()) == initial_total_elements, f"Pass {iteration}: Total element count changed"
            assert [w.global_id for w in m_next.all_walls()] == initial_walls_guids, f"Pass {iteration}: Wall GUIDs changed"
            assert [s.global_id for s in m_next.all_spaces()] == initial_spaces_guids, f"Pass {iteration}: Space GUIDs changed"
            assert [d.global_id for d in m_next.all_elements() if d.entity_type == "IfcDoor"] == initial_doors_guids
            assert [w.global_id for w in m_next.all_elements() if w.entity_type == "IfcWindow"] == initial_windows_guids

            # Invariant 4: Pset and Attribute Invariance
            curr_summary = extract_psets_summary(m_next)
            for gid, initial_data in initial_summary.items():
                assert gid in curr_summary, f"Pass {iteration}: Element {gid} missing in parsed model"
                curr_data = curr_summary[gid]
                assert curr_data["entity_type"] == initial_data["entity_type"]
                assert curr_data["name"] == initial_data["name"]

                # Verify each Pset
                for pset_name, initial_props in initial_data["psets"].items():
                    assert pset_name in curr_data["psets"], f"Pass {iteration}: Pset {pset_name} missing on {gid}"
                    curr_props = curr_data["psets"][pset_name]
                    for p_key, p_val in initial_props.items():
                        assert p_key in curr_props, f"Pass {iteration}: Property {p_key} in {pset_name} missing on {gid}"
                        if isinstance(p_val, float):
                            assert abs(curr_props[p_key] - p_val) < 1e-4, f"Pass {iteration}: Float property {p_key} drifted: {curr_props[p_key]} vs {p_val}"
                        else:
                            assert curr_props[p_key] == p_val, f"Pass {iteration}: Property {p_key} mutated: {curr_props[p_key]} vs {p_val}"

            m_curr = m_next

        # Verify STEP text stability across passes (pass 1 STEP == pass 10 STEP)
        # Note: timestamp in header might vary if generated at current time, but data section lines should be 100% identical.
        def get_data_section(step: str) -> str:
            start = step.find("DATA;")
            end = step.find("ENDSEC;", start)
            return step[start:end]

        data_pass_1 = get_data_section(step_history[0])
        data_pass_10 = get_data_section(step_history[9])
        assert data_pass_1 == data_pass_10, "DATA section of STEP physical file drifted between pass 1 and pass 10!"


# ==============================================================================
# 2. Hosted Opening Voiding & Filling Relations Tests
# ==============================================================================
class TestHostedOpeningVoidingAndFilling:
    """Stress tests topological voiding (IFCRELVOIDSELEMENT) and filling (IFCRELFILLSELEMENT)."""

    def test_hosted_door_and_window_relational_graph_integrity(self):
        """Test walls hosting doors and windows reconstruct IFCRELVOIDSELEMENT, IFCRELFILLSELEMENT, and host_wall_id links."""
        model = CanonicalBIMModel(project_name="Hosted Relations Project")
        storey = BIMStorey(name="Level 1", storey_index=0, elevation=0.0)

        # Host Wall 1 (has 1 door and 2 windows)
        wall1 = BIMWall(
            name="Facade Wall East",
            position=(10.0, 1.5, 0.0),
            dimensions={"width": 12.0, "height": 3.0, "depth": 0.3},
            thickness=0.3,
            height=3.0,
        )
        door1 = BIMDoor(
            name="East Entry Door",
            host_wall_id=wall1.global_id,
            position=(10.0, 1.2, 2.0),
            width=1.2,
            height=2.4,
        )
        win1_1 = BIMWindow(
            name="East Window 1",
            host_wall_id=wall1.global_id,
            position=(10.0, 1.5, -2.0),
            width=2.0,
            height=1.5,
        )
        win1_2 = BIMWindow(
            name="East Window 2",
            host_wall_id=wall1.global_id,
            position=(10.0, 1.5, -5.0),
            width=2.0,
            height=1.5,
        )

        # Host Wall 2 (has 1 door by wall UUID instead of global_id)
        wall2 = BIMWall(
            name="Interior Partition Wall",
            position=(0.0, 1.5, 0.0),
            dimensions={"width": 6.0, "height": 3.0, "depth": 0.15},
            thickness=0.15,
            height=3.0,
        )
        door2 = BIMDoor(
            name="Interior Bedroom Door",
            host_wall_id=wall2.id,  # UUID reference
            position=(0.0, 1.2, 1.0),
            width=0.9,
            height=2.1,
        )

        # Wall 3: Solid Wall without any openings
        wall3 = BIMWall(name="Solid Shear Wall", position=(-10.0, 1.5, 0.0))

        storey.walls.extend([wall1, wall2, wall3])
        storey.doors.extend([door1, door2])
        storey.windows.extend([win1_1, win1_2])

        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        # 1. Compile to STEP
        step_text = compile_bim_to_ifc4_step(model)

        # Verify low-level STEP relations
        step_file = StepFile.from_string(step_text)
        void_rels = step_file.by_type("IfcRelVoidsElement")
        fill_rels = step_file.by_type("IfcRelFillsElement")
        openings = step_file.by_type("IfcOpeningElement")

        # Total 4 hosted openings: door1, win1_1, win1_2, door2
        assert len(openings) == 4, f"Expected 4 IfcOpeningElement, found {len(openings)}"
        assert len(void_rels) == 4, f"Expected 4 IfcRelVoidsElement, found {len(void_rels)}"
        assert len(fill_rels) == 4, f"Expected 4 IfcRelFillsElement, found {len(fill_rels)}"

        # 2. Parse back to CanonicalBIMModel
        reparsed = parse_ifc4_step_to_bim(step_text)

        # Verify all elements exist
        re_walls = {w.global_id: w for w in reparsed.all_walls()}
        re_doors = {d.global_id: d for d in reparsed.all_elements() if d.entity_type == "IfcDoor"}
        re_windows = {w.global_id: w for w in reparsed.all_elements() if w.entity_type == "IfcWindow"}

        assert len(re_walls) == 3
        assert len(re_doors) == 2
        assert len(re_windows) == 2

        # Check host_wall_id reconstruction on parsed doors and windows
        assert re_doors[door1.global_id].host_wall_id == wall1.global_id
        assert re_windows[win1_1.global_id].host_wall_id == wall1.global_id
        assert re_windows[win1_2.global_id].host_wall_id == wall1.global_id
        assert re_doors[door2.global_id].host_wall_id == wall2.global_id

    def test_hosted_openings_multiple_walls_and_unhosted_fallback(self):
        """Test behavior when door has no explicit host_wall_id or references another storey."""
        model = CanonicalBIMModel(project_name="Unhosted Opening Project")
        storey = BIMStorey(name="Level 1", storey_index=0, elevation=0.0)

        wall = BIMWall(name="Main Wall")
        # Door with no host_wall_id specified -> serializer defaults to first wall on storey
        door = BIMDoor(name="Floating Door", host_wall_id=None)

        storey.walls.append(wall)
        storey.doors.append(door)
        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        re_door = [e for e in reparsed.all_elements() if e.entity_type == "IfcDoor"][0]
        assert re_door.host_wall_id == wall.global_id


# ==============================================================================
# 3. FastAPI REST API Endpoint Stress Tests
# ==============================================================================
class TestFastAPIBIMEndpoints:
    """Stress tests /api/v1/bim/* endpoints with valid and invalid payloads."""

    def test_export_ifc_valid_canonical_model(self):
        """Test POST /api/v1/bim/export/ifc with valid CanonicalBIMModel."""
        model = create_complex_test_model("API Export Valid")
        payload = model.model_dump()

        res = client.post("/api/v1/bim/export/ifc", json=payload)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/x-step"
        assert "attachment; filename=" in res.headers["content-disposition"]
        assert "ISO-10303-21;" in res.text
        assert "IFCWALL" in res.text

    def test_export_ifc_valid_legacy_dict(self):
        """Test POST /api/v1/bim/export-ifc with legacy real-estate dictionary format."""
        payload = {
            "name": "Legacy Hotel Tower",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w1", "name": "Facade Wall", "type": "wall", "position": [0, 1.5, 0], "dimensions": {"width": 8, "height": 3, "depth": 0.3}},
                        {"id": "d1", "name": "Main Entrance", "type": "door", "position": [2, 1.2, 0], "dimensions": {"width": 1.2, "height": 2.4, "depth": 0.15}},
                    ]
                }
            }
        }
        res = client.post("/api/v1/bim/export/ifc", json=payload)
        assert res.status_code == 200
        assert "ISO-10303-21;" in res.text
        assert "IFCDOOR" in res.text

    def test_export_ifc_invalid_payloads(self):
        """Test POST /api/v1/bim/export/ifc with malformed / invalid payloads."""
        # Empty string
        res = client.post("/api/v1/bim/export/ifc", data="not json", headers={"Content-Type": "application/json"})
        assert res.status_code in (400, 422)

    def test_import_ifc_file_upload(self):
        """Test POST /api/v1/bim/import/ifc with multipart file upload."""
        model = create_complex_test_model("API Upload Test")
        step_text = compile_bim_to_ifc4_step(model)

        file_obj = io.BytesIO(step_text.encode("utf-8"))
        files = {"file": ("model.ifc", file_obj, "application/x-step")}

        res = client.post("/api/v1/bim/import/ifc", files=files)
        assert res.status_code == 200
        data = res.json()
        assert "canonical_model" in data
        assert data["canonical_model"]["project"]["name"] == "API Upload Test"
        assert len(data["generated_elements"]) >= 5

    def test_import_ifc_raw_text_body(self):
        """Test POST /api/v1/bim/import/ifc with raw step_content body."""
        model = create_complex_test_model("Raw STEP Import")
        step_text = compile_bim_to_ifc4_step(model)

        res = client.post("/api/v1/bim/import/ifc", data=step_text, headers={"Content-Type": "text/plain"})
        assert res.status_code == 200
        data = res.json()
        assert data["canonical_model"]["project"]["name"] == "Raw STEP Import"

    def test_import_ifc_invalid_and_empty_payload(self):
        """Test POST /api/v1/bim/import/ifc with empty or malformed IFC text."""
        # Empty request
        res = client.post("/api/v1/bim/import/ifc")
        assert res.status_code == 400

        # Malformed syntax
        res_bad = client.post("/api/v1/bim/import/ifc", data="NOT A VALID IFC CONTENT", headers={"Content-Type": "text/plain"})
        assert res_bad.status_code == 400
        assert "syntax error" in res_bad.json()["detail"].lower() or "failed" in res_bad.json()["detail"].lower()

    def test_validate_endpoint_valid_step_and_model(self):
        """Test POST /api/v1/bim/validate with valid STEP and model payloads."""
        model = create_complex_test_model("Validate Test Model")
        step_text = compile_bim_to_ifc4_step(model)

        # 1. Test validate with step_content
        res1 = client.post("/api/v1/bim/validate", json={"step_content": step_text})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["valid"] is True
        assert data1["schema_version"] == "IFC4"
        assert data1["roundtrip_passed"] is True
        assert data1["physical_elements_count"] >= 8
        assert data1["errors"] == []

        # 2. Test validate with model json
        res2 = client.post("/api/v1/bim/validate", json={"model": model.model_dump()})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["valid"] is True
        assert data2["roundtrip_passed"] is True

    def test_validate_endpoint_invalid_payloads(self):
        """Test POST /api/v1/bim/validate with corrupted data and empty bodies."""
        # Empty body
        res_empty = client.post("/api/v1/bim/validate", json={})
        assert res_empty.status_code == 200
        assert res_empty.json()["valid"] is False
        assert len(res_empty.json()["errors"]) > 0

        # Corrupted STEP
        res_corrupt = client.post("/api/v1/bim/validate", json={"step_content": "ISO-10303-21; DATA; #1=IFCWALL(; ENDSEC;"})
        assert res_corrupt.status_code == 200
        assert res_corrupt.json()["valid"] is False
        assert len(res_corrupt.json()["errors"]) > 0

    def test_get_spatial_tree_endpoint(self):
        """Test GET /api/v1/bim/{project_id}/spatial-tree with numeric and string IDs."""
        res1 = client.get("/api/v1/bim/1/spatial-tree")
        assert res1.status_code == 200
        data1 = res1.json()
        assert "children" in data1
        assert "Villa Aurora" in str(data1)

        res2 = client.get("/api/v1/bim/project_uuid_99/spatial-tree")
        assert res2.status_code == 200
        data2 = res2.json()
        assert "children" in data2
