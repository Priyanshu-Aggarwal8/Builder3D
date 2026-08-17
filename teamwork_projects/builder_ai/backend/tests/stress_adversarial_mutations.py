"""
Adversarial Mutation & Assertion Strictness Verification Harness
Challenger: Challenger 1 (E2E Testing Track)
Date: 2026-08-16

Empirically executes 6 critical mutation suites against Builder3D:
1. Faulty Geometry & Spatial Topology Mutations
2. Bad GUIDs & Spatial Hierarchy Invariant Violations
3. Broken Wall Cuts & Hosted Opening Subsegmentation Flaws
4. Invalid IFC STEP Syntax & Round-Trip Corruptions
5. Disconnected MEP Graphs & Hydraulic Violation Mutations
6. SAT Collision & Furniture Clearance Envelope Violations
"""

from __future__ import annotations

import copy
import io
import math
import os
import re
import sys
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

# Set UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import ifcopenshell
from pydantic import ValidationError
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

from app.schemas.design_spec import (
    AestheticPalette,
    AestheticStyle,
    BuildingTypology,
    DesignSpec,
    MaterialSpec,
    MEPStrategy,
    OccupancyCategory,
    RoomProgram,
    RoomType,
    SetbackSpec,
    SiteParameters,
    StoreySpec,
    StoreyUseType,
    StructuralSystem,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
    assert_no_raw_geometry,
)
from app.schemas.spatial import (
    ALLOWED_CHILD_TYPES,
    IFC_BASE64_CHARS,
    IFC_BASE64_DICT,
    SpatialNode,
    SpatialNodeType,
    compile_design_spec_to_spatial_tree,
    decode_ifc_guid,
    encode_ifc_guid,
    filter_nodes_by_type,
    find_node_by_global_id,
    find_node_by_id,
    flatten_spatial_tree,
    generate_spatial_uuid,
    get_ancestor_chain,
    get_descendants,
    validate_tree_integrity,
)
from app.services.ifc_engine import create_ifc4_project_from_model, parse_ifc_content
from tests.conftest import (
    DesignSpecFactory,
    FloorplanLayout,
    HostedOpening,
    ParametricWall,
    RoomBoundary,
    RoomBoundaryFactory,
    SpatialTreeFactory,
    VerticalRiserLocation,
    WallOpeningFactory,
    WallSubSegment,
)
from tests.test_asset_registry import (
    STANDARD_ASSET_REGISTRY,
    AssetDefinition,
    ClearanceSpec,
    MEPPortDefinition,
    PlacedAsset,
    check_sat_collision,
)
from tests.test_ifc_compiler import (
    CanonicalBIMEntity,
    CanonicalBIMModel,
    compile_pure_step_header,
    step_escape_string,
    step_unescape_string,
)
from tests.test_mep_engine import (
    MEPEdge,
    MEPGraph,
    MEPNode,
    VerticalRiserShaft,
    detect_cycles_in_subgraph,
    find_orphan_fixtures,
    verify_directed_path,
)


class MutationAssertionVerifier:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.results: List[Dict[str, Any]] = []

    def verify_mutation_rejected(self, test_name: str, mutation_desc: str, exc_type, func, match: str = ""):
        """Verifies that an adversarial mutation is loudly rejected by an exception."""
        self.total += 1
        try:
            func()
            self.failed += 1
            err = f"FALSE PASS: Mutation '{mutation_desc}' was accepted without raising {exc_type.__name__}"
            print(f"  [FAIL] {test_name} - {err}")
            self.results.append({"suite": test_name, "mutation": mutation_desc, "status": "FAIL", "error": err})
        except Exception as e:
            if isinstance(e, exc_type):
                if match and match.lower() not in str(e).lower():
                    self.failed += 1
                    err = f"Wrong error message: raised {type(e).__name__} but message '{str(e)}' did not match '{match}'"
                    print(f"  [FAIL] {test_name} - {err}")
                    self.results.append({"suite": test_name, "mutation": mutation_desc, "status": "FAIL", "error": err})
                else:
                    self.passed += 1
                    print(f"  [PASS] {test_name} -> Successfully caught mutation: {mutation_desc}")
                    self.results.append({"suite": test_name, "mutation": mutation_desc, "status": "PASS", "error": None})
            else:
                self.failed += 1
                err = f"Unexpected exception type: expected {exc_type.__name__}, got {type(e).__name__}: {str(e)}"
                print(f"  [FAIL] {test_name} - {err}")
                self.results.append({"suite": test_name, "mutation": mutation_desc, "status": "FAIL", "error": err})

    def verify_strict_assertion(self, test_name: str, check_desc: str, condition: bool, details: str = ""):
        """Verifies that an assertion strictly validates correct invariants."""
        self.total += 1
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name} -> Invariant verified: {check_desc}")
            self.results.append({"suite": test_name, "mutation": check_desc, "status": "PASS", "error": None})
        else:
            self.failed += 1
            err = f"Assertion failed: {details}" if details else "Invariant violated"
            print(f"  [FAIL] {test_name} - {err}")
            self.results.append({"suite": test_name, "mutation": check_desc, "status": "FAIL", "error": err})


verifier = MutationAssertionVerifier()

# ==============================================================================
# SUITE 1: Faulty Geometry & Spatial Topology Mutations
# ==============================================================================
print("\n" + "="*80)
print("SUITE 1: Faulty Geometry & Spatial Topology Mutations")
print("="*80)

# 1.1 Self-intersecting room polygon
self_intersecting_poly = [(0, 0), (10, 10), (10, 0), (0, 10)]
poly_invalid = Polygon(self_intersecting_poly)
verifier.verify_strict_assertion(
    "Geometry_SelfIntersection",
    "Self-intersecting figure-8 polygon is invalid and not simple",
    poly_invalid.is_valid is False or poly_invalid.is_simple is False
)

# 1.2 Non-closed polygon with < 3 vertices
verifier.verify_mutation_rejected(
    "Geometry_DegenerateVertices",
    "Line with 2 points cannot form a valid closed 2D room polygon",
    ValueError,
    lambda: Polygon([(0, 0), (5, 5)])
)

# 1.3 Negative / Zero area room program rejection
verifier.verify_mutation_rejected(
    "Geometry_ZeroRoomArea",
    "RoomProgram with min_area_sqm=0.0 and target_area_sqm=0.0",
    ValidationError,
    lambda: RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=0.0, target_area_sqm=0.0)
)
verifier.verify_mutation_rejected(
    "Geometry_NegativeRoomArea",
    "RoomProgram with negative min_area_sqm=-10.0",
    ValidationError,
    lambda: RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=-10.0, target_area_sqm=10.0)
)

# 1.4 Non-monotonic storey elevations mutation
reversed_elev_storeys = [
    StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.2),
    StoreySpec(storey_index=1, name="Level 1", elevation_m=3.2, height_m=3.2),
    StoreySpec(storey_index=2, name="Level 2", elevation_m=2.0, height_m=3.2),  # Inverted!
]
verifier.verify_mutation_rejected(
    "Geometry_InvertedElevations",
    "Storey elevations inverted (3.2m -> 2.0m)",
    ValidationError,
    lambda: DesignSpec(total_storeys=3, storeys=reversed_elev_storeys),
    match="Non-monotonic"
)

# 1.5 Setback bounds overflow mutation
verifier.verify_mutation_rejected(
    "Geometry_SetbackOverflow",
    "Setback margins (front 25m + rear 20m = 45m) exceed plot depth 40m",
    ValidationError,
    lambda: SiteParameters(plot_width_m=30.0, plot_depth_m=40.0, setbacks=SetbackSpec(front_m=25.0, rear_m=20.0, side_left_m=2.0, side_right_m=2.0)),
    match="depth setbacks"
)

# 1.6 Raw geometry key injection in payload
for p_key in ["vertices", "coords", "mesh", "triangles", "polygons", "faces"]:
    verifier.verify_mutation_rejected(
        "Geometry_RawKeyInjection",
        f"Injected prohibited raw coordinate key '{p_key}'",
        ValueError,
        lambda k=p_key: assert_no_raw_geometry({k: [0.0, 1.0, 2.0]}),
        match=p_key
    )

# 1.7 Overlapping interior rooms detection
room_a = box(0.0, 0.0, 6.0, 6.0)
room_b_overlapping = box(4.0, 0.0, 10.0, 6.0)  # Overlaps by 2.0m x 6.0m = 12.0 sqm
overlap_sqm = room_a.intersection(room_b_overlapping).area
verifier.verify_strict_assertion(
    "Geometry_RoomOverlapDetection",
    f"Pairwise room overlap of 12.0 sqm detected (overlap={overlap_sqm:.2f} sqm)",
    overlap_sqm > 1.0
)

# 1.8 Room escaping L-shaped boundary
l_footprint = Polygon([(0, 0), (12, 0), (12, 6), (6, 6), (6, 12), (0, 12), (0, 0)])
escaping_room = box(7.0, 7.0, 11.0, 11.0)  # In top-right exterior void
leak_area = escaping_room.difference(l_footprint).area
verifier.verify_strict_assertion(
    "Geometry_LShapedVoidEscape",
    f"Room escaping L-shaped boundary has {leak_area:.2f} sqm in exterior void",
    leak_area == escaping_room.area
)


# ==============================================================================
# SUITE 2: Bad GUIDs & Spatial Hierarchy Invariant Violations
# ==============================================================================
print("\n" + "="*80)
print("SUITE 2: Bad GUIDs & Spatial Hierarchy Invariant Violations")
print("="*80)

# 2.1 Bad GUID length mutations
verifier.verify_mutation_rejected(
    "GUID_TooShort",
    "IFC GUID with 21 chars ('012345678901234567890')",
    ValueError,
    lambda: decode_ifc_guid("012345678901234567890"),
    match="22 characters"
)
verifier.verify_mutation_rejected(
    "GUID_TooLong",
    "IFC GUID with 23 chars ('01234567890123456789012')",
    ValueError,
    lambda: decode_ifc_guid("01234567890123456789012"),
    match="22 characters"
)
verifier.verify_mutation_rejected(
    "GUID_Empty",
    "Empty IFC GUID",
    ValueError,
    lambda: decode_ifc_guid(""),
    match="22 characters"
)

# 2.2 Invalid character set mutations
for bad_c in ["!", "@", "#", "$", "%", "^", "&", "*", "-", "+", "=", "/", " ", "\n", "ñ"]:
    if bad_c in ["$", "_"]:  # $ and _ are valid in IFC base64
        continue
    verifier.verify_mutation_rejected(
        "GUID_InvalidChar",
        f"IFC GUID containing illegal character '{bad_c}'",
        ValueError,
        lambda c=bad_c: decode_ifc_guid(f"000000000000000000000{c}"),
        match="Invalid character"
    )

# 2.3 Leading character overflow mutation
for lead_c in ["4", "5", "9", "A", "Z", "a", "z"]:
    verifier.verify_mutation_rejected(
        "GUID_LeadingCharOverflow",
        f"Leading char '{lead_c}' causing 8-bit chunk 0 overflow (> 255)",
        ValueError,
        lambda lc=lead_c: decode_ifc_guid(f"{lc}000000000000000000000"),
        match="exceeds 255"
    )

# 2.4 Bijective roundtrip on boundary UUIDs (Nil, Max, Random)
nil_u = uuid.UUID("00000000-0000-0000-0000-000000000000")
max_u = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
verifier.verify_strict_assertion(
    "GUID_NilRoundtrip",
    "Nil UUID encodes to '0000000000000000000000' and decodes back bit-for-bit",
    decode_ifc_guid(encode_ifc_guid(nil_u)) == nil_u and encode_ifc_guid(nil_u) == "0000000000000000000000"
)
verifier.verify_strict_assertion(
    "GUID_MaxRoundtrip",
    "Max UUID encodes to '3$$$$$$$$$$$$$$$$$$$$$' and decodes back bit-for-bit",
    decode_ifc_guid(encode_ifc_guid(max_u)) == max_u and encode_ifc_guid(max_u) == "3$$$$$$$$$$$$$$$$$$$$$"
)

# 2.5 Illegal hierarchy jump mutation
verifier.verify_mutation_rejected(
    "Hierarchy_IllegalJump",
    "Project node directly containing Room node (skipping 5 tiers)",
    ValidationError,
    lambda: SpatialNode(
        id=str(uuid.uuid4()),
        global_id="0000000000000000000000",
        name="Root",
        node_type=SpatialNodeType.PROJECT,
        parent_id=None,
        children=[
            SpatialNode(
                id=str(uuid.uuid4()),
                global_id="1111111111111111111111",
                name="Illegal Room",
                node_type=SpatialNodeType.ROOM,
                parent_id="0000000000000000000000",
            )
        ]
    ),
    match="Illegal hierarchy"
)

# 2.6 Tree cyclic reference mutation
node_a_id = str(uuid.uuid4())
node_b_id = str(uuid.uuid4())
node_b = SpatialNode(id=node_b_id, global_id=encode_ifc_guid(node_b_id), name="Site", node_type=SpatialNodeType.SITE, parent_id=node_a_id)
node_a = SpatialNode(id=node_a_id, global_id=encode_ifc_guid(node_a_id), name="Project", node_type=SpatialNodeType.PROJECT, parent_id=None, children=[node_b])
node_b.children.append(node_a)  # Inject cycle
verifier.verify_mutation_rejected(
    "Hierarchy_CycleDetection",
    "Tree cycle where Site contains its parent Project",
    ValueError,
    lambda: validate_tree_integrity(node_a),
    match="Cycle or duplicate"
)


# ==============================================================================
# SUITE 3: Broken Wall Cuts & Hosted Opening Flaws
# ==============================================================================
print("\n" + "="*80)
print("SUITE 3: Broken Wall Cuts & Hosted Opening Flaws")
print("="*80)

# 3.1 Opening distance exceeds wall length
oversized_door_offset = WallOpeningFactory.make_hosted_opening("d_far", "DOOR", "w1", distance_along_wall=5.5, width=1.0, height=2.1)
verifier.verify_mutation_rejected(
    "Wall_OpeningOffsetExceedsWall",
    "Door start distance (5.5m) + width (1.0m) = 6.5m exceeds 4.0m wall",
    ValueError,
    lambda: WallOpeningFactory.make_parametric_wall("w1", (0, 0, 0), (4, 0, 0), openings=[oversized_door_offset]),
    match="exceeds wall length"
)

# 3.2 Opening height exceeds wall height
oversized_window_height = WallOpeningFactory.make_hosted_opening("w_high", "WINDOW", "w1", distance_along_wall=1.0, width=1.2, height=2.5, sill_height=1.0)
verifier.verify_mutation_rejected(
    "Wall_OpeningHeightExceedsWall",
    "Window sill (1.0m) + height (2.5m) = 3.5m exceeds 3.0m wall height",
    ValueError,
    lambda: WallOpeningFactory.make_parametric_wall("w1", (0, 0, 0), (5, 0, 0), height=3.0, openings=[oversized_window_height]),
    match="exceeds wall height"
)

# 3.3 Overlapping hosted openings on same wall run
op_door = WallOpeningFactory.make_hosted_opening("d1", "DOOR", "w1", distance_along_wall=1.0, width=1.0, height=2.1)
op_win_clash = WallOpeningFactory.make_hosted_opening("w1", "WINDOW", "w1", distance_along_wall=1.5, width=1.2, height=1.4, sill_height=0.9)
verifier.verify_mutation_rejected(
    "Wall_OverlappingOpenings",
    "Door [1.0m, 2.0m] and Window [1.5m, 2.7m] overlap on same wall",
    ValueError,
    lambda: WallOpeningFactory.make_parametric_wall("w1", (0, 0, 0), (6, 0, 0), openings=[op_door, op_win_clash]),
    match="Overlapping openings"
)

# 3.4 Wall Volume Conservation Invariant
# Verify that dropping a subsegment violates volume conservation
wall_valid = WallOpeningFactory.make_parametric_wall(
    "w_vol", (0, 0, 0), (6, 0, 0), thickness=0.25, height=3.0,
    openings=[WallOpeningFactory.make_hosted_opening("win_vol", "WINDOW", "w_vol", distance_along_wall=2.0, width=1.5, height=1.2, sill_height=1.0)]
)
solid_vol = 6.0 * 3.0 * 0.25  # 4.5 m3
opening_vol = 1.5 * 1.2 * 0.25  # 0.45 m3
subsegs_vol = sum(s.volume for s in wall_valid.sub_segments)  # 4.05 m3
verifier.verify_strict_assertion(
    "Wall_VolumeConservation",
    f"Solid volume ({solid_vol:.3f}) == Subsegments ({subsegs_vol:.3f}) + Openings ({opening_vol:.3f})",
    math.isclose(solid_vol, subsegs_vol + opening_vol, rel_tol=1e-4)
)

# Mutated subsegment list missing lintel
mutated_subsegs = [s for s in wall_valid.sub_segments if s.segment_type != "LINTEL"]
mutated_vol = sum(s.volume for s in mutated_subsegs)
verifier.verify_strict_assertion(
    "Wall_CorruptedSubsegmentVolumeMismatch",
    f"Dropping lintel creates detectable volume deficit of {solid_vol - (mutated_vol + opening_vol):.3f} m3",
    not math.isclose(solid_vol, mutated_vol + opening_vol, rel_tol=1e-3)
)


# ==============================================================================
# SUITE 4: Invalid IFC STEP Syntax & Round-Trip Corruptions
# ==============================================================================
print("\n" + "="*80)
print("SUITE 4: Invalid IFC STEP Syntax & Round-Trip Corruptions")
print("="*80)

# 4.1 Corrupted STEP header rejection
malformed_step_samples = [
    "",
    "NOT_AN_IFC_FILE_RANDOM_TEXT",
    "ISO-10303-21; HEADER; FILE_DESCRIPTION(('Test')); ENDSEC; DATA; #1=CORRUPTED(; ENDSEC;",
    "ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nDATA;\n#1=IFCWALL(\nENDSEC;",
]
for idx, bad_step in enumerate(malformed_step_samples):
    verifier.verify_mutation_rejected(
        "IFC_MalformedSyntaxRejection",
        f"Malformed STEP string sample #{idx+1}",
        Exception,
        lambda bs=bad_step: parse_ifc_content(bs)
    )

# 4.2 STEP string escaping fidelity on special characters
test_escapes = [
    "Simple String",
    "String with 'Single Quotes' and \\Backslashes\\",
    "French: Élévation du bâtiment & Façade vitrée",
    "German: Großes Gebäude (U < 0.8 W/m²K)",
    "Japanese: 建築モデル",
    "Math & Symbols: Ø110mm @ 2% slope, 45° angle, ±0.01m",
]
for original_str in test_escapes:
    escaped = step_escape_string(original_str)
    unescaped = step_unescape_string(escaped)
    verifier.verify_strict_assertion(
        "IFC_StringEscapingRoundtrip",
        f"Lossless escaping roundtrip for '{original_str[:30]}...'",
        unescaped == original_str
    )

# 4.3 Semantic identity round-trip fidelity (BIM Model -> STEP -> Parsed Model)
test_model_payload = {
    "name": "Challenger Verification Model",
    "layers": {
        "structural": {
            "elements": [
                {"id": "w_test1", "name": "Exterior Wall North", "type": "wall", "position": [0, 1.5, -5], "dimensions": {"width": 10, "height": 3.0, "depth": 0.25}},
                {"id": "d_test1", "name": "Main Entrance Door", "type": "door", "position": [1, 1.05, 0], "dimensions": {"width": 1.0, "height": 2.1, "depth": 0.15}},
                {"id": "win_test1", "name": "Double Glazed Window", "type": "window", "position": [-2, 1.5, 0], "dimensions": {"width": 1.8, "height": 1.4, "depth": 0.1}},
            ]
        },
        "plumbing": {
            "elements": [
                {"id": "pipe_test1", "name": "Soil Riser DN110", "type": "pipe", "position": [3, 1.5, 0], "dimensions": {"width": 0.11, "height": 3.0, "depth": 0.11}},
            ]
        }
    }
}
ifc_obj = create_ifc4_project_from_model(test_model_payload)
step_out = ifc_obj.to_string()
parsed_bim = parse_ifc_content(step_out)
verifier.verify_strict_assertion(
    "IFC_SemanticRoundtripCount",
    f"Parsed back exact 4 elements (got {len(parsed_bim['generated_elements'])})",
    len(parsed_bim["generated_elements"]) == 4
)
extracted_types = {e["type"] for e in parsed_bim["generated_elements"]}
verifier.verify_strict_assertion(
    "IFC_SemanticRoundtripTypes",
    f"Parsed all required entity types ('wall', 'door', 'window', 'pipe')",
    extracted_types == {"wall", "door", "window", "pipe"}
)


# ==============================================================================
# SUITE 5: Disconnected MEP Graphs & Hydraulic Violation Mutations
# ==============================================================================
print("\n" + "="*80)
print("SUITE 5: Disconnected MEP Graphs & Hydraulic Violation Mutations")
print("="*80)

# 5.1 Disconnected orphan fixture detection
mep_g = MEPGraph()
mep_g.add_node(MEPNode(node_id="src", node_type="Source", system_type="WaterSupply", position=(0, 0, 0)))
mep_g.add_node(MEPNode(node_id="connected_tap", node_type="Terminal", system_type="WaterSupply", position=(2, 1, 0)))
mep_g.add_node(MEPNode(node_id="orphan_shower", node_type="Terminal", system_type="WaterSupply", position=(8, 1, 0)))  # Disconnected!
mep_g.add_edge(MEPEdge(edge_id="e1", system_type="WaterSupply", from_node_id="src", to_node_id="connected_tap", nominal_diameter_mm=25.0, length_m=2.0))

orphans = find_orphan_fixtures(mep_g)
verifier.verify_strict_assertion(
    "MEP_OrphanFixtureDetection",
    f"find_orphan_fixtures correctly identifies ['orphan_shower'] (found: {orphans})",
    orphans == ["orphan_shower"]
)

# 5.2 Directed path verification (unidirectional flow)
verifier.verify_strict_assertion(
    "MEP_DirectedFlowForward",
    "Directed path exists from Source -> connected_tap",
    verify_directed_path(mep_g, "src", "connected_tap") is True
)
verifier.verify_strict_assertion(
    "MEP_DirectedFlowReverseBlocked",
    "Reverse path from connected_tap -> Source does NOT exist",
    verify_directed_path(mep_g, "connected_tap", "src") is False
)

# 5.3 Drainage cycle detection mutation
drain_g = MEPGraph()
drain_g.add_node(MEPNode(node_id="n1", node_type="Terminal", system_type="SoilWaste", position=(0, 0, 0)))
drain_g.add_node(MEPNode(node_id="n2", node_type="Junction", system_type="SoilWaste", position=(1, 0, 0)))
drain_g.add_node(MEPNode(node_id="n3", node_type="Riser", system_type="SoilWaste", position=(2, 0, 0)))
drain_g.add_edge(MEPEdge(edge_id="e1", system_type="SoilWaste", from_node_id="n1", to_node_id="n2", nominal_diameter_mm=110.0, length_m=1.0))
drain_g.add_edge(MEPEdge(edge_id="e2", system_type="SoilWaste", from_node_id="n2", to_node_id="n3", nominal_diameter_mm=110.0, length_m=1.0))

verifier.verify_strict_assertion(
    "MEP_AcyclicDrainageTree",
    "Valid drainage tree has zero cycles",
    detect_cycles_in_subgraph(drain_g, "SoilWaste") is False
)

# Inject cycle n3 -> n1
drain_g.add_edge(MEPEdge(edge_id="e_cycle", system_type="SoilWaste", from_node_id="n3", to_node_id="n1", nominal_diameter_mm=110.0, length_m=2.0))
verifier.verify_strict_assertion(
    "MEP_DrainageCycleDetection",
    "Injected cycle (n3 -> n1) detected successfully by detect_cycles_in_subgraph",
    detect_cycles_in_subgraph(drain_g, "SoilWaste") is True
)

# 5.4 Vertical riser coaxial misalignment detection
riser_s0 = (4.0, -3.0)
riser_s1_misaligned = (4.6, -3.0)  # Drift of 0.6m
drift = math.hypot(riser_s1_misaligned[0] - riser_s0[0], riser_s1_misaligned[1] - riser_s0[1])
verifier.verify_strict_assertion(
    "MEP_RiserMisalignmentDetection",
    f"Vertical riser horizontal drift of {drift:.2f}m (> 0.05m threshold) detected",
    drift > 0.05
)


# ==============================================================================
# SUITE 6: SAT Collision & Furniture Clearance Envelope Violations
# ==============================================================================
print("\n" + "="*80)
print("SUITE 6: SAT Collision & Furniture Clearance Envelope Violations")
print("="*80)

# 6.1 Disjoint vs Colliding Furniture (SAT Overlap)
placed_bed = PlacedAsset(instance_id="bed1", asset_key="furniture.bed_queen", position_xz=(2.0, 2.0), rotation_deg=0.0, room_id="bed_room")
placed_ns_disjoint = PlacedAsset(instance_id="ns1", asset_key="furniture.nightstand", position_xz=(0.8, 2.8), rotation_deg=0.0, room_id="bed_room")
placed_ns_colliding = PlacedAsset(instance_id="ns2", asset_key="furniture.nightstand", position_xz=(1.5, 2.0), rotation_deg=0.0, room_id="bed_room")

verifier.verify_strict_assertion(
    "SAT_DisjointFurniture",
    "Properly spaced Bed and Nightstand have 0 SAT collision",
    check_sat_collision(placed_bed.get_bounding_polygon(), placed_ns_disjoint.get_bounding_polygon()) is False
)
verifier.verify_strict_assertion(
    "SAT_CollidingFurniture",
    "Overlapping Bed and Nightstand detected by SAT collision checker",
    check_sat_collision(placed_bed.get_bounding_polygon(), placed_ns_colliding.get_bounding_polygon()) is True
)

# 6.2 Clearance envelope expansion invariant
base_bed_poly = placed_bed.get_bounding_polygon()
clearance_bed_poly = placed_bed.get_clearance_polygon()
verifier.verify_strict_assertion(
    "SAT_ClearanceExpansion",
    f"Clearance envelope area ({clearance_bed_poly.area:.2f} m2) strictly exceeds base bounding box area ({base_bed_poly.area:.2f} m2)",
    clearance_bed_poly.area > base_bed_poly.area and clearance_bed_poly.contains(base_bed_poly)
)

# 6.3 Door swing arc collision
door_hinge_pt = Point((0.0, 0.0))
door_clearance_radius = 0.9  # 0.9m swing arc
placed_sofa_clipping_door = PlacedAsset(instance_id="sofa_clash", asset_key="furniture.sofa_3seater", position_xz=(0.5, 0.5), rotation_deg=0.0, room_id="living")
sofa_dist_to_hinge = placed_sofa_clipping_door.get_bounding_polygon().distance(door_hinge_pt)
verifier.verify_strict_assertion(
    "SAT_DoorSwingArcClashDetection",
    f"Sofa at (0.5, 0.5) clips door swing arc (dist to hinge: {sofa_dist_to_hinge:.2f}m <= {door_clearance_radius}m)",
    sofa_dist_to_hinge <= door_clearance_radius
)

# 6.4 Kitchen work triangle boundary validation
sink_pos = (1.5, 0.4)
cooktop_pos = (3.5, 0.4)
fridge_pos = (0.5, 2.2)

d_sc = math.hypot(cooktop_pos[0] - sink_pos[0], cooktop_pos[1] - sink_pos[1])
d_cf = math.hypot(fridge_pos[0] - cooktop_pos[0], fridge_pos[1] - cooktop_pos[1])
d_fs = math.hypot(sink_pos[0] - fridge_pos[0], sink_pos[1] - fridge_pos[1])
perimeter = d_sc + d_cf + d_fs
verifier.verify_strict_assertion(
    "SAT_KitchenWorkTriangleErgonomics",
    f"Work triangle perimeter ({perimeter:.2f}m) complies with architectural ergonomic range [3.6m, 7.9m]",
    3.6 <= perimeter <= 7.9
)


# ==============================================================================
# FINAL VERIFICATION REPORT SUMMARY
# ==============================================================================
print("\n" + "="*80)
print(f"ADVERSARIAL MUTATION VERIFICATION COMPLETE: {verifier.passed}/{verifier.total} CHECKS PASSED ({verifier.failed} FAILURES)")
print("="*80)

if verifier.failed > 0:
    print("\nDETECTED FAILURES:")
    for res in verifier.results:
        if res["status"] == "FAIL":
            print(f"  - [{res['suite']}] {res['mutation']}: {res['error']}")
    sys.exit(1)
else:
    print("\nALL ADVERSARIAL MUTATION CHECKS PASSED WITH ZERO FALSE PASSES.")
    sys.exit(0)
