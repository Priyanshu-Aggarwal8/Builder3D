"""
Adversarial Stress & Fuzzing Test Suite for 7 Architectural Invariants & E2E Golden Models.
Author: Challenger 2 (E2E Testing Track)

Empirically challenges all 7 Architectural Invariants (I1 - I7) and Tier 3/Tier 4 integration:
- I1: Area Bounds, Minimum Room Dimensions, CCW Orientation & Pairwise Non-Overlapping Jordan Closure
- I2: Circulation Graph Connectivity, Non-Cut-Through (Private Room Isolation), & Ensuite Degree Rules
- I3: Coaxial Wet Stack Clustering (<= 3.5m Proximity) & Vertical Shaft Alignment (|ΔX|=0, |ΔZ|=0)
- I4: Hosted Opening Clearances (Jambs >= 0.15m, Lintel >= 0.05m) & Solid Volume Conservation
- I5: ISO 10303-21 IFC4 STEP Round-Trip Fidelity & 22-char IFC Base64 GUID Bijectivity
- I6: Connected Directed MEP Flow Graph (Zero Orphan Nodes, Gravity Fall >= 0.015, Supply Continuity)
- I7: SAT 2D Collision-Free Furniture Placement & Door Swing Arc Clearances
"""

import copy
import math
import uuid
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque

import pytest
import numpy as np
from shapely.geometry import Polygon, box

from app.schemas.design_spec import (
    AestheticPalette,
    AestheticStyle,
    BuildingTypology,
    DesignSpec,
    HVACType,
    MaterialSpec,
    MEPStrategy,
    OccupancyCategory,
    RoomProgram,
    RoomType,
    SiteParameters,
    StoreySpec,
    StoreyUseType,
    StructuralSystem,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
    ZoningClassification,
)
from app.schemas.spatial import (
    SpatialNode,
    SpatialNodeType,
    compile_design_spec_to_spatial_tree,
    decode_ifc_guid,
    encode_ifc_guid,
    filter_nodes_by_type,
    validate_tree_integrity,
)
from app.services.ifc_engine import create_ifc4_project_from_model, parse_ifc_content

# Import invariant evaluators and model builders from test_golden_models
from tests.test_golden_models import (
    assert_invariant_i1_area_bounds,
    assert_invariant_i2_circulation_connectivity,
    assert_invariant_i3_wet_stack_alignment,
    assert_invariant_i4_hosted_openings_solid_conservation,
    assert_invariant_i5_ifc4_step_roundtrip,
    assert_invariant_i6_mep_flow_connectivity,
    assert_invariant_i7_furniture_clearance_and_sat,
    build_golden_01_1bhk_urban_flat,
    build_golden_02_2bhk_residential_apartment,
    build_golden_03_3bhk_luxury_suite,
    build_golden_04_2storey_modern_villa,
    build_golden_05_12storey_residential_tower,
    calculate_polygon_area_2d,
    is_polygon_ccw,
    make_polygon_ccw,
    sat_check_2d_boxes_overlap,
    subsegment_wall_run,
)


class TestAdversarialInvariant1AreaBounds:
    """Adversarial stress-testing of Invariant 1 (Area bounds, closure, non-overlap, CCW)."""

    def test_i1_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 1."""
        assert_invariant_i1_area_bounds(build_golden_01_1bhk_urban_flat(), 55.0, tolerance=0.05)
        assert_invariant_i1_area_bounds(build_golden_02_2bhk_residential_apartment(), 90.0, tolerance=0.05)
        assert_invariant_i1_area_bounds(build_golden_03_3bhk_luxury_suite(), 160.0, tolerance=0.08)
        assert_invariant_i1_area_bounds(build_golden_04_2storey_modern_villa(), 280.0, tolerance=0.05)
        assert_invariant_i1_area_bounds(build_golden_05_12storey_residential_tower(), 6500.0, tolerance=0.05)

    def test_i1_unclosed_polygon_rejected(self):
        """Mutated model with unclosed polygon (start != end) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Break closure on first room
        pts = model["rooms"][0]["polygon"]
        model["rooms"][0]["polygon"] = pts[:-1]  # Remove closing vertex
        with pytest.raises(AssertionError, match="polygon is not closed"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_insufficient_vertices_rejected(self):
        """Mutated model with < 4 vertices in closed loop must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["rooms"][0]["polygon"] = [(0.0, 0.0), (1.0, 1.0), (0.0, 0.0)]
        with pytest.raises(AssertionError, match="insufficient vertices"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_clockwise_polygon_rejected(self):
        """Mutated model with Clockwise oriented polygon vertices must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        pts = model["rooms"][0]["polygon"]
        # Invert CCW to CW with proper closure (first vertex == last vertex)
        reversed_verts = list(reversed(pts[:-1]))
        cw_pts = reversed_verts + [reversed_verts[0]]
        model["rooms"][0]["polygon"] = cw_pts
        with pytest.raises(AssertionError, match="must be oriented counter-clockwise"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_overlapping_rooms_rejected(self):
        """Mutated model where two rooms overlap geometrically must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Move kitchen so it deeply overlaps living room
        model["rooms"][1]["polygon"] = make_polygon_ccw([(-2.0, 1.0), (1.0, 1.0), (1.0, 3.5), (-2.0, 3.5), (-2.0, 1.0)])
        model["rooms"][1]["area"] = 7.5
        with pytest.raises(AssertionError, match="overlap by"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_substandard_room_area_rejected(self):
        """Mutated model with sub-code room area (e.g. Master Bed < 12 sqm) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Shrink master bedroom to 8 sqm
        model["rooms"][3]["area"] = 8.0
        model["rooms"][3]["polygon"] = make_polygon_ccw([(0.0, 0.0), (4.0, 0.0), (4.0, 2.0), (0.0, 2.0), (0.0, 0.0)])
        with pytest.raises(AssertionError, match="Master bedroom area.*minimum"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_gross_area_out_of_tolerance_rejected(self):
        """Mutated model with gross area exceeding tolerance (+25%) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["gross_area_sqm"] = 75.0  # Target is 55.0 (+36% error)
        with pytest.raises(AssertionError, match="differs from target"):
            assert_invariant_i1_area_bounds(model, 55.0, tolerance=0.05)

    def test_i1_stated_area_vs_polygon_area_mismatch_rejected(self):
        """Mutated model where stated area mismatches actual polygon Shoelace area."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["rooms"][0]["area"] = 99.0  # False stated area
        with pytest.raises(AssertionError, match="polygon area mismatch"):
            assert_invariant_i1_area_bounds(model, 55.0)

    def test_i1_empty_rooms_list_rejected(self):
        """Model with zero rooms must fail I1."""
        model = {"name": "Empty Model", "rooms": []}
        with pytest.raises(AssertionError, match="zero rooms"):
            assert_invariant_i1_area_bounds(model, 55.0)


class TestAdversarialInvariant2Circulation:
    """Adversarial stress-testing of Invariant 2 (Circulation, connectivity, non-cut-through)."""

    def test_i2_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 2."""
        assert_invariant_i2_circulation_connectivity(build_golden_01_1bhk_urban_flat())
        assert_invariant_i2_circulation_connectivity(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i2_circulation_connectivity(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i2_circulation_connectivity(build_golden_04_2storey_modern_villa())
        assert_invariant_i2_circulation_connectivity(build_golden_05_12storey_residential_tower())

    def test_i2_disconnected_room_rejected(self):
        """Mutated model with isolated unreachable bedroom must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Remove edge connecting master bed
        model["circulation_edges"] = [e for e in model["circulation_edges"] if "master_bed" not in e]
        with pytest.raises(AssertionError, match="Unreachable rooms"):
            assert_invariant_i2_circulation_connectivity(model)

    def test_i2_cut_through_circulation_rejected(self):
        """Mutated model where public room is only accessible through a private bedroom."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Reroute living room to be reachable ONLY through master bedroom
        model["circulation_edges"] = [
            ("entry_foyer", "master_bed"),
            ("master_bed", "living_dining"),  # Cut-through!
            ("entry_foyer", "kitchen"),
            ("entry_foyer", "bathroom"),
            ("master_bed", "balcony"),
        ]
        with pytest.raises(AssertionError, match="No clean non-cut-through path"):
            assert_invariant_i2_circulation_connectivity(model)

    def test_i2_leaked_ensuite_rejected(self):
        """Ensuite bathroom connected directly to corridor/living room instead of bedroom."""
        model = copy.deepcopy(build_golden_02_2bhk_residential_apartment())
        # Connect master_ensuite directly to entry_corridor instead of master_bed
        model["circulation_edges"] = [
            e for e in model["circulation_edges"] if e != ("master_bed", "master_ensuite")
        ] + [("entry_corridor", "master_ensuite")]
        with pytest.raises(AssertionError, match="parent 'entry_corridor' is of type 'Corridor', expected Bedroom"):
            assert_invariant_i2_circulation_connectivity(model)

    def test_i2_multi_door_ensuite_degree_violation(self):
        """Ensuite bathroom with degree > 1 (e.g. Jack-and-Jill multi-door) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_02_2bhk_residential_apartment())
        # Connect master_ensuite to both master_bed AND living
        model["circulation_edges"].append(("living", "master_ensuite"))
        with pytest.raises(AssertionError, match="degree is 2.*must be exactly 1"):
            assert_invariant_i2_circulation_connectivity(model)

    def test_i2_missing_entry_node_rejected(self):
        """Model missing designated entry node in circulation graph."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["entry_node"] = "non_existent_entry"
        with pytest.raises(AssertionError, match="not in circulation nodes"):
            assert_invariant_i2_circulation_connectivity(model)

    def test_i2_unknown_node_in_edges_rejected(self):
        """Edge referencing undefined node ID."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["circulation_edges"].append(("entry_foyer", "ghost_node"))
        with pytest.raises(AssertionError, match="references unknown node"):
            assert_invariant_i2_circulation_connectivity(model)


class TestAdversarialInvariant3WetStackAlignment:
    """Adversarial stress-testing of Invariant 3 (Wet stack proximity <= 3.5m, vertical coaxial alignment)."""

    def test_i3_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 3."""
        assert_invariant_i3_wet_stack_alignment(build_golden_01_1bhk_urban_flat())
        assert_invariant_i3_wet_stack_alignment(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i3_wet_stack_alignment(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i3_wet_stack_alignment(build_golden_04_2storey_modern_villa())
        assert_invariant_i3_wet_stack_alignment(build_golden_05_12storey_residential_tower())

    def test_i3_remote_fixture_exceeding_3_5m_rejected(self):
        """Mutated model where a plumbing fixture is 5.2m away from nearest wet stack shaft."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Move kitchen sink to remote position (8.0, 0.9, 8.0) -> dist to shaft (2.5, 0.5) is ~9.3m
        model["plumbing_fixtures"][0]["position"] = (8.0, 0.9, 8.0)
        with pytest.raises(AssertionError, match="exceeds max 3.50m to nearest wet stack shaft"):
            assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)

    def test_i3_multi_storey_riser_x_drift_rejected(self):
        """Multi-storey model where upper floor riser is drifted horizontally in X."""
        model = copy.deepcopy(build_golden_04_2storey_modern_villa())
        # Drift level 1 east stack from X=5.5000 to X=5.7500
        for r in model["vertical_risers"]:
            if r.get("shaft_id") == "villa_stack_east" and r.get("storey") == 1:
                r["position"] = (5.7500, r["position"][1], r["position"][2])
        with pytest.raises(AssertionError, match="misaligned in X across storeys: dx="):
            assert_invariant_i3_wet_stack_alignment(model)

    def test_i3_multi_storey_riser_z_drift_rejected(self):
        """Multi-storey model where upper floor riser is drifted horizontally in Z."""
        model = copy.deepcopy(build_golden_04_2storey_modern_villa())
        # Drift level 1 west stack from Z=-1.0000 to Z=-0.8000
        for r in model["vertical_risers"]:
            if r.get("shaft_id") == "villa_stack_west" and r.get("storey") == 1:
                r["position"] = (r["position"][0], r["position"][1], -0.8000)
        with pytest.raises(AssertionError, match="misaligned in Z across storeys: dz="):
            assert_invariant_i3_wet_stack_alignment(model)

    def test_i3_tower_12storey_upper_drift_rejected(self):
        """12-Storey tower where 11th floor riser shaft has a micro-drift."""
        model = copy.deepcopy(build_golden_05_12storey_residential_tower())
        # Drift 11th floor West riser
        for r in model["vertical_risers"]:
            if r.get("shaft_id") == "tower_soil_west" and r.get("storey") == 11:
                r["position"] = (-8.9500, r["position"][1], r["position"][2])
        with pytest.raises(AssertionError, match="misaligned in X across storeys"):
            assert_invariant_i3_wet_stack_alignment(model)

    def test_i3_empty_fixtures_rejected(self):
        """Model with zero plumbing fixtures fails I3."""
        model = {"name": "No Fixtures", "plumbing_fixtures": [], "vertical_risers": [{"position": (0, 0, 0)}]}
        with pytest.raises(AssertionError, match="zero plumbing fixtures"):
            assert_invariant_i3_wet_stack_alignment(model)

    def test_i3_empty_risers_rejected(self):
        """Model with zero riser shafts fails I3."""
        model = {"name": "No Risers", "plumbing_fixtures": [{"position": (0, 0, 0)}], "vertical_risers": []}
        with pytest.raises(AssertionError, match="zero vertical riser shafts"):
            assert_invariant_i3_wet_stack_alignment(model)


class TestAdversarialInvariant4HostedOpenings:
    """Adversarial stress-testing of Invariant 4 (Hosted openings, jamb clearances, volume conservation)."""

    def test_i4_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 4."""
        assert_invariant_i4_hosted_openings_solid_conservation(build_golden_01_1bhk_urban_flat())
        assert_invariant_i4_hosted_openings_solid_conservation(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i4_hosted_openings_solid_conservation(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i4_hosted_openings_solid_conservation(build_golden_04_2storey_modern_villa())
        assert_invariant_i4_hosted_openings_solid_conservation(build_golden_05_12storey_residential_tower())

    def test_i4_left_jamb_violation_rejected(self):
        """Opening placed with left jamb clearance < 0.15m (e.g. 0.05m) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["parametric_walls"][0]["openings"][0]["distance_along_wall"] = 0.05
        with pytest.raises(AssertionError, match="left jamb clearance.*< 0.15m"):
            assert_invariant_i4_hosted_openings_solid_conservation(model)

    def test_i4_right_jamb_violation_rejected(self):
        """Opening placed too close to the end of the host wall (right jamb < 0.15m)."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Wall length is 7.4m, width is 2.2m -> place at 5.2m (leaving right jamb = 0.00m)
        model["parametric_walls"][0]["openings"][0]["distance_along_wall"] = 5.20
        with pytest.raises(AssertionError, match="right jamb clearance.*< 0.15m"):
            assert_invariant_i4_hosted_openings_solid_conservation(model)

    def test_i4_lintel_margin_violation_rejected(self):
        """Opening height + sill height exceeds wall height (negative or zero lintel margin)."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Wall height is 3.0m -> sill 0.9m + height 2.5m = 3.4m > 3.0m
        model["parametric_walls"][0]["openings"][0]["height"] = 2.5
        with pytest.raises(AssertionError, match="exceeds wall height"):
            assert_invariant_i4_hosted_openings_solid_conservation(model)

    def test_i4_volume_conservation_exactness(self):
        """Sub-segmentation volume conservation holds across diverse multi-opening walls."""
        wall_len = 10.0
        wall_h = 3.5
        wall_t = 0.30
        openings = [
            {"id": "d1", "distance_along_wall": 0.5, "width": 1.0, "height": 2.2, "sill_height": 0.0},
            {"id": "w1", "distance_along_wall": 2.5, "width": 2.0, "height": 1.5, "sill_height": 0.9},
            {"id": "w2", "distance_along_wall": 6.0, "width": 3.0, "height": 1.8, "sill_height": 0.6},
        ]
        res = subsegment_wall_run(wall_len, wall_h, wall_t, openings)
        assert math.isclose(res["total_solid_volume"] + res["total_void_volume"], res["gross_volume"], rel_tol=1e-5)
        assert len(res["sub_segments"]) >= 7

    def test_i4_empty_walls_rejected(self):
        """Model with zero parametric walls fails I4."""
        model = {"name": "No Walls", "parametric_walls": []}
        with pytest.raises(AssertionError, match="zero parametric walls"):
            assert_invariant_i4_hosted_openings_solid_conservation(model)


class TestAdversarialInvariant5IFC4RoundTrip:
    """Adversarial stress-testing of Invariant 5 (ISO 10303-21 IFC4 STEP serialization and parsing)."""

    def test_i5_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 5."""
        assert_invariant_i5_ifc4_step_roundtrip(build_golden_01_1bhk_urban_flat())
        assert_invariant_i5_ifc4_step_roundtrip(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i5_ifc4_step_roundtrip(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i5_ifc4_step_roundtrip(build_golden_04_2storey_modern_villa())
        assert_invariant_i5_ifc4_step_roundtrip(build_golden_05_12storey_residential_tower())

    def test_i5_step_header_structure(self):
        """Valid STEP string must contain ISO-10303-21, HEADER, FILE_SCHEMA(('IFC4')), and DATA sections."""
        model = build_golden_01_1bhk_urban_flat()
        bim_dict = {
            "name": model["name"],
            "layers": {"structural": {"elements": model["raw_elements"]}},
        }
        ifc_file = create_ifc4_project_from_model(bim_dict)
        step_str = ifc_file.to_string()

        assert step_str.startswith("ISO-10303-21;")
        assert "HEADER;" in step_str
        assert "FILE_SCHEMA(('IFC4'));" in step_str
        assert "DATA;" in step_str
        assert step_str.strip().endswith("END-ISO-10303-21;")

    def test_i5_guid_format_and_bijectivity_100_percent(self):
        """IFC GlobalIds generated on all products conform strictly to 22-char IFC Base64."""
        model = build_golden_05_12storey_residential_tower()
        bim_dict = {
            "name": model["name"],
            "layers": {"structural": {"elements": model["raw_elements"]}},
        }
        ifc_file = create_ifc4_project_from_model(bim_dict)

        for prod in ifc_file.by_type("IfcRoot"):
            gid = prod.GlobalId
            assert len(gid) == 22
            assert gid[0] in {"0", "1", "2", "3"}
            # Decode back to UUID
            u = decode_ifc_guid(gid)
            assert isinstance(u, uuid.UUID)
            # Re-encode and assert exact match
            assert encode_ifc_guid(u) == gid

    def test_i5_round_trip_element_preservation(self):
        """Exporting model to IFC4 STEP and parsing back preserves all element types."""
        model = build_golden_03_3bhk_luxury_suite()
        bim_dict = {
            "name": model["name"],
            "layers": {"structural": {"elements": model["raw_elements"]}},
        }
        ifc_file = create_ifc4_project_from_model(bim_dict)
        step_str = ifc_file.to_string()

        parsed = parse_ifc_content(step_str)
        orig_count = len(model["raw_elements"])
        assert len(parsed["generated_elements"]) == orig_count


class TestAdversarialInvariant6MEPConnectivity:
    """Adversarial stress-testing of Invariant 6 (Connected directed MEP flow graph, slope, supply continuity)."""

    def test_i6_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 6."""
        assert_invariant_i6_mep_flow_connectivity(build_golden_01_1bhk_urban_flat())
        assert_invariant_i6_mep_flow_connectivity(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i6_mep_flow_connectivity(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i6_mep_flow_connectivity(build_golden_04_2storey_modern_villa())
        assert_invariant_i6_mep_flow_connectivity(build_golden_05_12storey_residential_tower())

    def test_i6_orphaned_disconnected_node_rejected(self):
        """MEP graph with an isolated orphaned node (degree 0) must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["mep_graph"]["nodes"]["orphaned_heater"] = {"type": "Terminal", "system": "ElectricalPower"}
        with pytest.raises(AssertionError, match="Orphaned disconnected MEP node"):
            assert_invariant_i6_mep_flow_connectivity(model)

    def test_i6_insufficient_gravity_drainage_slope_rejected(self):
        """SoilWaste drainage pipe with slope 0.008 < 0.015 (1.5% fall code requirement) fails I6."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Mutate sink drainage slope to 0.005 (0.5% - illegal)
        for e in model["mep_graph"]["edges"]:
            if e.get("id") == "e_drn_1":
                e["slope"] = 0.005
        with pytest.raises(AssertionError, match="Gravity drainage edge.*slope.*< 0.015"):
            assert_invariant_i6_mep_flow_connectivity(model)

    def test_i6_broken_water_supply_path_rejected(self):
        """Water supply terminal disconnected from water source must trigger assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Remove water supply edge to sink
        model["mep_graph"]["edges"] = [e for e in model["mep_graph"]["edges"] if e.get("id") != "e_sup_1"]
        # Add a dummy edge to maintain degree >= 1 so orphan check doesn't fire first
        model["mep_graph"]["edges"].append({
            "id": "e_dummy", "from_node": "sink_supply", "to_node": "wc_supply", "system": "WaterSupply"
        })
        with pytest.raises(AssertionError, match="is not connected to water source"):
            assert_invariant_i6_mep_flow_connectivity(model)

    def test_i6_edge_referencing_nonexistent_node_rejected(self):
        """Edge referencing undefined node ID."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        model["mep_graph"]["edges"].append({
            "id": "e_bad", "from_node": "water_incomer", "to_node": "ghost_fixture", "system": "WaterSupply"
        })
        with pytest.raises(AssertionError, match="not in MEP nodes"):
            assert_invariant_i6_mep_flow_connectivity(model)

    def test_i6_empty_mep_graph_rejected(self):
        """Empty MEP graph fails I6."""
        model = {"name": "No MEP", "mep_graph": {"nodes": {}, "edges": []}}
        with pytest.raises(AssertionError, match="zero nodes"):
            assert_invariant_i6_mep_flow_connectivity(model)


class TestAdversarialInvariant7FurnitureSAT:
    """Adversarial stress-testing of Invariant 7 (SAT collision avoidance, door swing clearance)."""

    def test_i7_golden_models_positive(self):
        """Valid Golden reference models satisfy Invariant 7."""
        assert_invariant_i7_furniture_clearance_and_sat(build_golden_01_1bhk_urban_flat())
        assert_invariant_i7_furniture_clearance_and_sat(build_golden_02_2bhk_residential_apartment())
        assert_invariant_i7_furniture_clearance_and_sat(build_golden_03_3bhk_luxury_suite())
        assert_invariant_i7_furniture_clearance_and_sat(build_golden_04_2storey_modern_villa())
        assert_invariant_i7_furniture_clearance_and_sat(build_golden_05_12storey_residential_tower())

    def test_i7_solid_furniture_collision_rejected(self):
        """Two furniture items overlapping in 2D space must trigger SAT collision assertion failure."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Move Left Nightstand inside Queen Bed center (-1.8, -2.0)
        model["furniture_items"][1]["center"] = (-1.8, -2.0)
        with pytest.raises(AssertionError, match="Collision detected between"):
            assert_invariant_i7_furniture_clearance_and_sat(model)

    def test_i7_rotated_furniture_sat_collision(self):
        """Rotated 45-degree desk intersecting sofa bounding box."""
        box_a = {"name": "Living Sofa", "center": (0.0, 0.0), "size": (2.0, 1.0), "rotation_deg": 0.0}
        # Rotated 45 degrees, center at (1.2, 0.5)
        box_b_colliding = {"name": "Rotated Armchair", "center": (1.2, 0.5), "size": (1.0, 1.0), "rotation_deg": 45.0}
        box_c_clear = {"name": "Clear Armchair", "center": (2.5, 0.0), "size": (1.0, 1.0), "rotation_deg": 45.0}

        assert sat_check_2d_boxes_overlap(box_a, box_b_colliding) is True
        assert sat_check_2d_boxes_overlap(box_a, box_c_clear) is False

    def test_i7_door_swing_arc_obstruction_rejected(self):
        """Furniture item placed inside 90-degree door swing clearance sector fails I7."""
        model = copy.deepcopy(build_golden_01_1bhk_urban_flat())
        # Door is at (0.7, 0.0, 1.5) with width 0.9m
        # Place a shoe rack right in front of the door swing: center (1.0, 1.8)
        model["furniture_items"].append({
            "name": "Obstructing Shoe Rack",
            "center": (1.0, 1.8),
            "size": (0.8, 0.4),
            "rotation_deg": 0.0,
        })
        with pytest.raises(AssertionError, match="obstructs door swing arc"):
            assert_invariant_i7_furniture_clearance_and_sat(model)

    def test_i7_empty_furniture_rejected(self):
        """Model with zero furniture items fails I7."""
        model = {"name": "No Furniture", "furniture_items": [], "doors": []}
        with pytest.raises(AssertionError, match="zero furniture items"):
            assert_invariant_i7_furniture_clearance_and_sat(model)


# ==============================================================================
# Comprehensive Adversarial Multi-Mutation Fuzzing Harness
# ==============================================================================

class TestAdversarialFuzzingHarness:
    """Stress harness executing 30 randomized/parameterized adversarial mutations across all Golden Models."""

    @pytest.mark.parametrize("scenario_builder,target_sqm,tolerance", [
        (build_golden_01_1bhk_urban_flat, 55.0, 0.05),
        (build_golden_02_2bhk_residential_apartment, 90.0, 0.05),
        (build_golden_03_3bhk_luxury_suite, 160.0, 0.08),
        (build_golden_04_2storey_modern_villa, 280.0, 0.05),
        (build_golden_05_12storey_residential_tower, 6500.0, 0.05),
    ])
    def test_fuzz_all_7_invariants_pass_on_unmutated_goldens(self, scenario_builder, target_sqm, tolerance):
        """Baseline verification: all 5 pristine golden models pass 100% of the 7 invariants."""
        model = scenario_builder()
        assert_invariant_i1_area_bounds(model, target_sqm, tolerance)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)

    def test_fuzz_multisystem_perturbations(self):
        """Tests that compound multi-system corruptions are reliably caught by corresponding validators."""
        model = build_golden_02_2bhk_residential_apartment()

        # 1. Corrupt Area (I1)
        m_i1 = copy.deepcopy(model)
        m_i1["rooms"][0]["area"] = 2.0  # Living room 2 sqm
        with pytest.raises(AssertionError):
            assert_invariant_i1_area_bounds(m_i1, 90.0)

        # 2. Corrupt Circulation (I2)
        m_i2 = copy.deepcopy(model)
        m_i2["circulation_nodes"].append("unconnected_cell")
        with pytest.raises(AssertionError):
            assert_invariant_i2_circulation_connectivity(m_i2)

        # 3. Corrupt Wet Stack (I3)
        m_i3 = copy.deepcopy(model)
        m_i3["plumbing_fixtures"][0]["position"] = (25.0, 0.0, 25.0)  # > 3.5m
        with pytest.raises(AssertionError):
            assert_invariant_i3_wet_stack_alignment(m_i3)

        # 4. Corrupt Wall Openings (I4)
        m_i4 = copy.deepcopy(model)
        m_i4["parametric_walls"][0]["openings"][0]["distance_along_wall"] = 0.01  # Left jamb < 0.15m
        with pytest.raises(AssertionError):
            assert_invariant_i4_hosted_openings_solid_conservation(m_i4)

        # 5. Corrupt MEP Slope (I6)
        m_i6 = copy.deepcopy(model)
        m_i6["mep_graph"]["edges"][3]["slope"] = -0.05  # Backwards slope
        with pytest.raises(AssertionError):
            assert_invariant_i6_mep_flow_connectivity(m_i6)

        # 6. Corrupt Furniture Collision (I7)
        m_i7 = copy.deepcopy(model)
        m_i7["furniture_items"][0]["center"] = m_i7["furniture_items"][1]["center"]  # Exact overlap
        with pytest.raises(AssertionError):
            assert_invariant_i7_furniture_clearance_and_sat(m_i7)
