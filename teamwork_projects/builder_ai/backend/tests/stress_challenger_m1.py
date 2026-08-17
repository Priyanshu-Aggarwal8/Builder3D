"""
Empirical Adversarial Stress & Fuzzing Suite for Milestone 1 (M1: DesignSpec & Canonical Spatial Hierarchy)
Challenger Agent: challenger_m1_2

Tests 4 critical dimensions:
1. Coordinate Injection Attacks (Prohibited geometry keys)
2. Boundary Property Violations (Negative/impossible parameters)
3. Graph Corruption Attacks (Cycles, hierarchy jumps, broken pointers, duplicate IDs, IFC GUID encoding/decoding)
4. Extreme & Adversarial Natural Language Prompt Fuzzing
"""

import sys
import os
import io

# Set stdout/stderr encoding to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import re
import uuid
import json
import traceback
from typing import List, Dict, Any, Tuple, Optional, Set, Union

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError

from app.schemas.design_spec import (
    PROHIBITED_GEOMETRY_KEYS,
    AestheticPalette,
    AestheticStyle,
    BuildingTypology,
    CorePlacementStrategy,
    DesignSpec,
    ElectricalDistributionType,
    FireProtectionType,
    HVACType,
    MaterialSpec,
    MEPStrategy,
    OccupancyCategory,
    PlumbingSystemType,
    RooftopMEPType,
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
    ZoningClassification,
    assert_no_raw_geometry,
)
from app.schemas.spatial import (
    ALLOWED_CHILD_TYPES,
    IFC_BASE64_CHARS,
    IFC_BASE64_DICT,
    BuildingProperties,
    DevelopmentProperties,
    ProjectProperties,
    RoomProperties,
    SiteProperties,
    SpatialNode,
    SpatialNodeType,
    StoreyProperties,
    UnitProperties,
    compile_design_spec_to_spatial_tree,
    decode_ifc_guid,
    encode_ifc_guid,
    filter_nodes_by_type,
    find_node_by_global_id,
    find_node_by_id,
    find_node_by_path,
    flatten_spatial_tree,
    generate_spatial_uuid,
    get_ancestor_chain,
    get_descendants,
    ifc_guid_to_uuid,
    uuid_to_ifc_guid,
    validate_tree_integrity,
)
from app.services.meta_agent import parse_prompt_to_design_spec, compile_design_spec_to_spatial_hierarchy


class TestResultTracker:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.failures: List[Dict[str, Any]] = []

    def assert_true(self, condition: bool, test_name: str, details: str = ""):
        self.total += 1
        if condition:
            self.passed += 1
            print(f"  [PASS] {test_name}")
        else:
            self.failed += 1
            msg = f"Assertion failed: {details}" if details else "Assertion failed"
            print(f"  [FAIL] {test_name} - {msg}")
            self.failures.append({"test": test_name, "error": msg})

    def assert_raises(self, exc_type, func, test_name: str, match: str = ""):
        self.total += 1
        try:
            func()
            self.failed += 1
            msg = f"Expected exception {exc_type.__name__}, but NO exception was raised"
            print(f"  [FAIL] {test_name} - {msg}")
            self.failures.append({"test": test_name, "error": msg})
        except Exception as e:
            if isinstance(e, exc_type):
                if match and match.lower() not in str(e).lower():
                    self.failed += 1
                    msg = f"Raised {type(e).__name__} but message '{str(e)}' did not contain '{match}'"
                    print(f"  [FAIL] {test_name} - {msg}")
                    self.failures.append({"test": test_name, "error": msg})
                else:
                    self.passed += 1
                    print(f"  [PASS] {test_name} (Correctly caught {type(e).__name__})")
            else:
                self.failed += 1
                msg = f"Expected {exc_type.__name__}, but got {type(e).__name__}: {str(e)}"
                print(f"  [FAIL] {test_name} - {msg}")
                self.failures.append({"test": test_name, "error": msg})


tracker = TestResultTracker()


# ==============================================================================
# 1. Coordinate Injection Attacks (Prohibited Geometry Keys)
# ==============================================================================
print("\n" + "="*80)
print("DIMENSION 1: Coordinate Injection Attacks (Prohibited Geometry Keys)")
print("="*80)

prohibited_keys = [
    "vertices", "vertex_list", "coords", "coordinates", "points",
    "faces", "triangles", "polygons", "mesh", "geometry",
    "mesh_data", "bounding_box_min", "bounding_box_max"
]

# Test 1.1: Direct assertion on each prohibited key
for key in prohibited_keys:
    payload = {key: [0.0, 1.0, 2.0]}
    tracker.assert_raises(
        ValueError,
        lambda p=payload: assert_no_raw_geometry(p),
        f"assert_no_raw_geometry rejects top-level key '{key}'",
        match=key
    )

# Test 1.2: Case insensitivity and varied capitalizations
cased_keys = ["VERTICES", "Points", "Mesh_Data", "TriAngles", "COORDS", "PolyGons", "GEOMETRY"]
for key in cased_keys:
    payload = {key: [[0, 0], [1, 1]]}
    tracker.assert_raises(
        ValueError,
        lambda p=payload: assert_no_raw_geometry(p),
        f"assert_no_raw_geometry rejects mixed-case key '{key}'",
        match=key.lower()
    )

# Test 1.3: Deeply nested injection within valid DesignSpec dictionary payload
deep_injection_payload = {
    "project_name": "Injected Payload Project",
    "site": {
        "plot_width_m": 30.0,
        "plot_depth_m": 40.0,
        "setbacks": {"front_m": 4.5, "rear_m": 3.0, "side_left_m": 2.5, "side_right_m": 2.5},
    },
    "storeys": [
        {
            "storey_index": 0,
            "name": "Ground Floor",
            "elevation_m": 0.0,
            "height_m": 3.2,
            "unit_mix": [
                {
                    "target_area_sqm": 90.0,
                    "required_rooms": [
                        {
                            "room_type": "LivingRoom",
                            "min_area_sqm": 20.0,
                            "target_area_sqm": 24.0,
                            # INJECTED GEOMETRY HERE:
                            "nested_intent": {
                                "sub_levels": [
                                    {"name": "zone_a", "triangles": [1, 2, 3]}
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ]
}

tracker.assert_raises(
    ValueError,
    lambda: assert_no_raw_geometry(deep_injection_payload),
    "assert_no_raw_geometry detects deeply nested 'triangles' in 6th nesting tier",
    match="triangles"
)

# Test 1.4: DesignSpec model_validate rejects payload with prohibited geometry key
tracker.assert_raises(
    ValidationError,
    lambda: DesignSpec.model_validate({"project_name": "Injection", "vertices": [1, 2, 3]}),
    "DesignSpec.model_validate rejects top-level 'vertices'",
    match="vertices"
)

# Test 1.5: DesignSpec model_validate rejects extra/injected fields (extra='forbid')
tracker.assert_raises(
    ValidationError,
    lambda: DesignSpec.model_validate({"project_name": "ExtraField", "arbitrary_mesh_array": [1, 2, 3]}),
    "DesignSpec.model_validate rejects unknown extra field (extra='forbid')"
)

# Test 1.6: AestheticPalette with injected geometry
tracker.assert_raises(
    ValueError,
    lambda: assert_no_raw_geometry({"aesthetic_palette": {"exterior_wall": {"points": [1, 2, 3]}}}),
    "assert_no_raw_geometry rejects 'points' inside aesthetic_palette"
)

# Test 1.7: Valid pure semantic payload passes assert_no_raw_geometry without error
valid_payload = {
    "project_name": "Pure Semantic Villa",
    "site": {"plot_width_m": 30.0, "plot_depth_m": 40.0},
    "total_storeys": 2,
    "building_typology": "Villa",
    "mep_strategy": {"hvac_type": "VRF_MultiSplit"},
    "aesthetic_palette": {"style": "JapandiScandinavian"}
}
try:
    assert_no_raw_geometry(valid_payload)
    tracker.assert_true(True, "assert_no_raw_geometry succeeds on pure semantic payload")
except Exception as e:
    tracker.assert_true(False, "assert_no_raw_geometry succeeds on pure semantic payload", str(e))


# ==============================================================================
# 2. Boundary Property Violations
# ==============================================================================
print("\n" + "="*80)
print("DIMENSION 2: Boundary Property Violations")
print("="*80)

# Test 2.1: Negative and zero plot dimensions
tracker.assert_raises(
    ValidationError,
    lambda: SiteParameters(plot_width_m=-10.0, plot_depth_m=40.0),
    "SiteParameters rejects negative plot_width_m"
)
tracker.assert_raises(
    ValidationError,
    lambda: SiteParameters(plot_width_m=30.0, plot_depth_m=0.0),
    "SiteParameters rejects zero plot_depth_m (gt=0)"
)
tracker.assert_raises(
    ValidationError,
    lambda: SiteParameters(total_area_sqm=-500.0),
    "SiteParameters rejects negative total_area_sqm"
)

# Test 2.2: Setback margins exceeding or equal to plot dimensions
tracker.assert_raises(
    ValidationError,
    lambda: SiteParameters(
        plot_width_m=30.0, plot_depth_m=40.0,
        setbacks=SetbackSpec(front_m=20.0, rear_m=20.0, side_left_m=2.0, side_right_m=2.0)
    ),
    "SiteParameters rejects front + rear setbacks equal to plot depth (40m == 40m)",
    match="depth setbacks"
)
tracker.assert_raises(
    ValidationError,
    lambda: SiteParameters(
        plot_width_m=30.0, plot_depth_m=40.0,
        setbacks=SetbackSpec(front_m=4.0, rear_m=4.0, side_left_m=16.0, side_right_m=15.0)
    ),
    "SiteParameters rejects left + right setbacks exceeding plot width (31m > 30m)",
    match="width setbacks"
)
tracker.assert_raises(
    ValidationError,
    lambda: SetbackSpec(front_m=-2.0),
    "SetbackSpec rejects negative front_m"
)

# Test 2.3: Non-monotonic storey elevations
reversed_storeys = [
    StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.2),
    StoreySpec(storey_index=1, name="Level 1", elevation_m=3.2, height_m=3.2),
    StoreySpec(storey_index=2, name="Level 2", elevation_m=2.8, height_m=3.2),  # Decreasing!
]
tracker.assert_raises(
    ValidationError,
    lambda: DesignSpec(total_storeys=3, storeys=reversed_storeys),
    "DesignSpec rejects non-monotonic decreasing storey elevations",
    match="Non-monotonic"
)

equal_elev_storeys = [
    StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.2),
    StoreySpec(storey_index=1, name="Level 1", elevation_m=3.2, height_m=3.2),
    StoreySpec(storey_index=2, name="Level 2", elevation_m=3.2, height_m=3.2),  # Equal!
]
tracker.assert_raises(
    ValidationError,
    lambda: DesignSpec(total_storeys=3, storeys=equal_elev_storeys),
    "DesignSpec rejects identical consecutive storey elevations",
    match="Non-monotonic"
)

# Test 2.4: Storey count mismatch
tracker.assert_raises(
    ValidationError,
    lambda: DesignSpec(
        total_storeys=5,
        basement_storeys=1,
        storeys=[
            StoreySpec(storey_index=-1, name="Basement", elevation_m=-3.0, height_m=3.0, is_basement=True),
            StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.6, is_ground=True),
        ]  # Only 2 storeys provided, expected 6
    ),
    "DesignSpec rejects storey count mismatch (expected 6, got 2)",
    match="Storey count mismatch"
)

# Test 2.5: Room area violations
tracker.assert_raises(
    ValidationError,
    lambda: RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=25.0, target_area_sqm=20.0),
    "RoomProgram rejects target_area_sqm < min_area_sqm",
    match="target_area_sqm"
)
tracker.assert_raises(
    ValidationError,
    lambda: RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=-5.0, target_area_sqm=10.0),
    "RoomProgram rejects negative min_area_sqm"
)
tracker.assert_raises(
    ValidationError,
    lambda: RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=8.0, target_area_sqm=0.0),
    "RoomProgram rejects zero target_area_sqm"
)

# Test 2.6: UnitRequirement sum of room areas exceeding target area
overloaded_rooms = [
    RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=30.0, target_area_sqm=35.0),
    RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=25.0, target_area_sqm=30.0),
    RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=20.0, target_area_sqm=25.0),
]  # Min room sum = 75.0 m2, target = 60.0 m2 (75 > 60 * 1.05 = 63)
tracker.assert_raises(
    ValidationError,
    lambda: UnitRequirement(unit_type=UnitType.BHK2, target_area_sqm=60.0, required_rooms=overloaded_rooms),
    "UnitRequirement rejects sum of room min areas exceeding target area",
    match="exceeds unit target area"
)

# Test 2.7: MaterialSpec color hex regex and optical bounds
invalid_hexes = ["#GGGGGG", "red", "#12345", "#1234567", "", "123456", "#FFF1"]
for bad_hex in invalid_hexes:
    tracker.assert_raises(
        ValidationError,
        lambda h=bad_hex: MaterialSpec(name="BadMat", color_hex=h),
        f"MaterialSpec rejects invalid color hex '{bad_hex}'"
    )

tracker.assert_raises(
    ValidationError,
    lambda: MaterialSpec(roughness=1.5),
    "MaterialSpec rejects roughness > 1.0"
)
tracker.assert_raises(
    ValidationError,
    lambda: MaterialSpec(metalness=-0.1),
    "MaterialSpec rejects metalness < 0.0"
)
tracker.assert_raises(
    ValidationError,
    lambda: MaterialSpec(opacity=2.0),
    "MaterialSpec rejects opacity > 1.0"
)

# Test 2.8: Extreme floor heights
tracker.assert_raises(
    ValidationError,
    lambda: StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=1.5),
    "StoreySpec rejects floor height < 2.2m"
)
tracker.assert_raises(
    ValidationError,
    lambda: StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=25.0),
    "StoreySpec rejects floor height > 12.0m"
)


# ==============================================================================
# 3. Graph Corruption Attacks & Spatial Tree Invariants
# ==============================================================================
print("\n" + "="*80)
print("DIMENSION 3: Graph Corruption Attacks & Spatial Tree Invariants")
print("="*80)

# Helper function to create a minimal node
def make_node(node_type: SpatialNodeType, name: str, parent_id: Optional[str] = None, node_id: Optional[str] = None) -> SpatialNode:
    n_id = node_id or str(uuid.uuid4())
    n_guid = encode_ifc_guid(n_id)
    return SpatialNode(
        id=n_id,
        global_id=n_guid,
        name=name,
        node_type=node_type,
        parent_id=parent_id,
        children=[],
        properties={},
    )

# Test 3.1: Illegal parent-child hierarchy jumps
# Jump: Project -> Room (skipping Site, Dev, Bldg, Storey, Unit)
proj = make_node(SpatialNodeType.PROJECT, "Project Root")
room = make_node(SpatialNodeType.ROOM, "Jumped Room", parent_id=proj.id)
proj.children = [room]
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode.model_validate(proj.model_dump()),
    "SpatialNode rejects Project -> Room illegal jump",
    match="Illegal hierarchy"
)

# Jump: Site -> Storey (skipping Dev, Bldg)
site = make_node(SpatialNodeType.SITE, "Site", parent_id=str(uuid.uuid4()))
storey = make_node(SpatialNodeType.STOREY, "Jumped Storey", parent_id=site.id)
site.children = [storey]
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode.model_validate(site.model_dump()),
    "SpatialNode rejects Site -> Storey illegal jump",
    match="Illegal hierarchy"
)

# Jump: Building -> Room (skipping Storey, Unit)
bldg = make_node(SpatialNodeType.BUILDING, "Building", parent_id=str(uuid.uuid4()))
bldg.children = [make_node(SpatialNodeType.ROOM, "Jumped Room", parent_id=bldg.id)]
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode.model_validate(bldg.model_dump()),
    "SpatialNode rejects Building -> Room illegal jump",
    match="Illegal hierarchy"
)

# Room containing children (Room must be leaf)
leaf_room = make_node(SpatialNodeType.ROOM, "Master Bedroom", parent_id=str(uuid.uuid4()))
child_room = make_node(SpatialNodeType.ROOM, "Sub Room", parent_id=leaf_room.id)
leaf_room.children = [child_room]
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode.model_validate(leaf_room.model_dump()),
    "SpatialNode rejects children inside leaf Room node",
    match="Illegal hierarchy"
)

# Test 3.2: Broken parent-child pointer references
parent_node = make_node(SpatialNodeType.BUILDING, "Main Bldg", parent_id=str(uuid.uuid4()))
child_node = make_node(SpatialNodeType.STOREY, "Ground Storey", parent_id=str(uuid.uuid4())) # WRONG parent_id!
parent_node.children = [child_node]
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode.model_validate(parent_node.model_dump()),
    "SpatialNode rejects child with mismatched parent_id",
    match="Broken parent reference"
)

# Test 3.3: Project root with parent_id != None
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode(
        id=str(uuid.uuid4()),
        global_id="0000000000000000000000",
        name="Bad Root",
        node_type=SpatialNodeType.PROJECT,
        parent_id=str(uuid.uuid4()), # Must be None!
    ),
    "SpatialNode rejects Project root with parent_id != None",
    match="parent_id=None"
)

# Test 3.4: Non-root node with parent_id = None
tracker.assert_raises(
    ValidationError,
    lambda: SpatialNode(
        id=str(uuid.uuid4()),
        global_id="0000000000000000000000",
        name="Orphan Unit",
        node_type=SpatialNodeType.UNIT,
        parent_id=None, # Must have parent_id!
    ),
    "SpatialNode rejects non-root node with parent_id=None",
    match="must have a parent_id"
)

# Test 3.5: Tree integrity: Duplicate node UUIDs
root_proj = make_node(SpatialNodeType.PROJECT, "Project")
site1 = make_node(SpatialNodeType.SITE, "Site 1", parent_id=root_proj.id)
# Create duplicate child with exact same ID
site2 = make_node(SpatialNodeType.SITE, "Site 2", parent_id=root_proj.id, node_id=site1.id)
root_proj.children = [site1, site2]
tracker.assert_raises(
    ValueError,
    lambda: validate_tree_integrity(root_proj),
    "validate_tree_integrity detects duplicate node ID in tree",
    match="duplicate node ID"
)

# Test 3.6: Tree integrity: Duplicate IFC GUIDs
root_proj2 = make_node(SpatialNodeType.PROJECT, "Project 2")
site_a = make_node(SpatialNodeType.SITE, "Site A", parent_id=root_proj2.id)
site_b = make_node(SpatialNodeType.SITE, "Site B", parent_id=root_proj2.id)
site_b.global_id = site_a.global_id # Forced duplicate GUID
root_proj2.children = [site_a, site_b]
tracker.assert_raises(
    ValueError,
    lambda: validate_tree_integrity(root_proj2),
    "validate_tree_integrity detects duplicate IFC GUID in tree",
    match="Duplicate IFC GUID"
)

# Test 3.7: Tree integrity: Exceeding maximum allowed 7 tree levels
def make_deep_chain() -> SpatialNode:
    p = make_node(SpatialNodeType.PROJECT, "Proj")
    s = make_node(SpatialNodeType.SITE, "Site", parent_id=p.id)
    d = make_node(SpatialNodeType.DEVELOPMENT, "Dev", parent_id=s.id)
    b = make_node(SpatialNodeType.BUILDING, "Bldg", parent_id=d.id)
    st = make_node(SpatialNodeType.STOREY, "Storey", parent_id=b.id)
    u = make_node(SpatialNodeType.UNIT, "Unit", parent_id=st.id)
    r = make_node(SpatialNodeType.ROOM, "Room", parent_id=u.id)
    # 8th level illegal node (manually appended bypassing validation for integrity test)
    r_sub = make_node(SpatialNodeType.ROOM, "DeepRoom", parent_id=r.id)
    r.children = [r_sub]
    u.children = [r]
    st.children = [u]
    b.children = [st]
    d.children = [b]
    s.children = [d]
    p.children = [s]
    return p

tracker.assert_raises(
    ValueError,
    lambda: validate_tree_integrity(make_deep_chain()),
    "validate_tree_integrity rejects tree depth exceeding 7 levels",
    match="exceeded maximum allowed 7 levels"
)

# Test 3.9: Advanced Mathematical Vectors for IFC GUID Bijectivity
# Test all 128 single-bit positions (walking 1s)
walking_bit_success = True
for bit_pos in range(128):
    val = 1 << bit_pos
    u = uuid.UUID(int=val)
    g = encode_ifc_guid(u)
    decoded = decode_ifc_guid(g)
    if decoded != u or len(g) != 22:
        walking_bit_success = False
        break
tracker.assert_true(walking_bit_success, "IFC GUID Bijectivity: All 128 walking single-bit vectors pass")

# Test all 128 walking 0s (inverted mask)
walking_zero_success = True
mask128 = (1 << 128) - 1
for bit_pos in range(128):
    val = mask128 ^ (1 << bit_pos)
    u = uuid.UUID(int=val)
    g = encode_ifc_guid(u)
    decoded = decode_ifc_guid(g)
    if decoded != u or len(g) != 22:
        walking_zero_success = False
        break
tracker.assert_true(walking_zero_success, "IFC GUID Bijectivity: All 128 walking zero-bit vectors pass")

# Test 10,000 random UUIDs
large_fuzz_success = True
for _ in range(10000):
    u = uuid.uuid4()
    g = encode_ifc_guid(u)
    if decode_ifc_guid(g) != u:
        large_fuzz_success = False
        break
tracker.assert_true(large_fuzz_success, "IFC GUID Bijectivity: 10,000 random UUID round-trips pass with 100% fidelity")

# Test 3.10: Tree lookup and traversal edge cases
sample_spec = parse_prompt_to_design_spec("3-story building with 2BHK units")
sample_tree = compile_design_spec_to_spatial_tree(sample_spec)

# Non-existent lookups
tracker.assert_true(find_node_by_id(sample_tree, "non-existent-uuid") is None, "find_node_by_id returns None for non-existent UUID")
tracker.assert_true(find_node_by_global_id(sample_tree, "0000000000000000000000") is None, "find_node_by_global_id returns None for non-existent GUID")
tracker.assert_true(find_node_by_path(sample_tree, "project:invalid/path") is None, "find_node_by_path returns None for non-existent path")
tracker.assert_true(get_ancestor_chain(sample_tree, "non-existent-id") is None, "get_ancestor_chain returns None for non-existent target ID")

# Ancestor chain on root itself
root_chain = get_ancestor_chain(sample_tree, sample_tree.id)
tracker.assert_true(root_chain == [sample_tree], "get_ancestor_chain on root returns [root]")

# Tree flattening count matches descendants + 1
flattened = flatten_spatial_tree(sample_tree)
descendants = get_descendants(sample_tree)
tracker.assert_true(len(flattened) == len(descendants) + 1, "flatten_spatial_tree count == len(descendants) + 1")

# High-density tower scalability (36 storeys)
tall_spec = parse_prompt_to_design_spec("36-story residential tower with 2BHK and 3BHK")
tall_tree = compile_design_spec_to_spatial_tree(tall_spec)
tall_storeys = filter_nodes_by_type(tall_tree, SpatialNodeType.STOREY)
tracker.assert_true(len(tall_storeys) == 36, "36-story mega-tree compiles exactly 36 storeys")
tracker.assert_true(validate_tree_integrity(tall_tree), "36-story mega-tree validates tree integrity successfully")

# Malformed IFC GUID length
tracker.assert_raises(
    ValueError,
    lambda: decode_ifc_guid(""),
    "decode_ifc_guid rejects empty string",
    match="22 characters"
)
tracker.assert_raises(
    ValueError,
    lambda: decode_ifc_guid("012345678901234567890"),  # 21 chars
    "decode_ifc_guid rejects 21-char string",
    match="22 characters"
)
tracker.assert_raises(
    ValueError,
    lambda: decode_ifc_guid("01234567890123456789012"), # 23 chars
    "decode_ifc_guid rejects 23-char string",
    match="22 characters"
)

# Malformed IFC GUID invalid character set
invalid_ifc_chars = ["!", "@", "#", "%", "^", "&", "*", "(", ")", "-", "+", "=", "/", " ", "\n", "\t", "ñ", "Ω"]
for bad_c in invalid_ifc_chars:
    bad_guid = f"000000000000000000000{bad_c}"
    tracker.assert_raises(
        ValueError,
        lambda bg=bad_guid: decode_ifc_guid(bg),
        f"decode_ifc_guid rejects invalid character {repr(bad_c)}",
        match="Invalid character"
    )

# First chunk overflow characters ('4' through '$' exceed 255 in 8-bit chunk 0)
overflow_leading_chars = ["4", "5", "8", "9", "A", "M", "Z", "a", "k", "z", "_", "$"]
for lead_c in overflow_leading_chars:
    overflow_guid = f"{lead_c}000000000000000000000"
    tracker.assert_raises(
        ValueError,
        lambda og=overflow_guid: decode_ifc_guid(og),
        f"decode_ifc_guid rejects first-character overflow with leading char '{lead_c}'",
        match="exceeds 255"
    )


# ==============================================================================
# 4. Extreme & Adversarial Natural Language Prompts into parse_prompt_to_design_spec
# ==============================================================================
print("\n" + "="*80)
print("DIMENSION 4: Extreme & Adversarial NL Prompts Fuzzing")
print("="*80)

adversarial_prompts = [
    # 4.1 Empty & Whitespace
    ("", "Empty prompt fallback"),
    ("   \t\n  ", "Whitespace-only prompt fallback"),

    # 4.2 Extreme Floor Counts
    ("Build a 0-storey house with garden", "Zero floor prompt handling"),
    ("A -5 story underground bunker", "Negative floor prompt handling"),
    ("Construct a 9999999999-story super-tall megatall tower", "Extremely huge storey number clamp"),
    ("A 100-story residential skyscraper", "Maximum 100-story residential skyscraper"),
    ("A 3.5 floor duplex with rooftop", "Fractional floor prompt"),

    # 4.3 Injection & Adversarial Strings
    ("' OR '1'='1'; DROP TABLE projects; --", "SQL injection prompt"),
    ("<script>alert('XSS_ATTACK')</script><img src=x onerror=alert(1)>", "XSS injection prompt"),
    ("{{7*7}} ${7*7} #{7*7} <%= 7*7 %>", "Template injection prompt"),
    ("__import__('os').system('rm -rf /')", "Python code injection prompt"),
    ("SELECT * FROM design_specs WHERE 1=1 UNION ALL SELECT username, password FROM users", "SQL UNION injection prompt"),

    # 4.4 Prompt attempting to force raw geometry injection
    (
        "Design a 2-story house with vertices [[0,0,0], [10,0,0], [10,10,0]] and triangles [0,1,2] and mesh data points",
        "Prompt attempting raw geometry injection (must produce pure intent without geometry keys)"
    ),

    # 4.5 Extreme Unicode, Emoji, and Length Attacks
    ("🏢🏠🏬🏢🏨 50 floors 🌟 with swimming pool 🏊‍♂️ and solar panels ☀️", "Emoji-dense prompt"),
    ("Современная 3-этажная вилла в скандинавском стиле с 4 спальнями", "Cyrillic non-ASCII prompt"),
    ("فيلا فاخرة من طابقين مع مسبح لا متناهي وحديقة يابانية", "Arabic RTL non-ASCII prompt"),
    ("超高层36层双子塔豪华公寓", "Chinese character prompt"),
    ("2-story villa " + "very spacious living room " * 500, "Extremely long prompt (500 repetitions)"),

    # 4.6 Conflicting architectural intents
    (
        "Single story commercial skyscraper tower with 100 floors and 1 floor in luxury japandi industrial brutalist style",
        "Multi-conflicting typology and style prompt"
    ),
    (
        "Villa on a 5m x 5m plot with 10m front setback and 10m rear setback and 5 storeys",
        "Plot dimension conflict with impossible setbacks"
    ),

    # 4.7 Standard Typologies for sanity
    ("Studio apartment in contemporary modern style", "Studio apartment prompt"),
    ("1BHK urban flat with balcony", "1BHK flat prompt"),
    ("2-story luxury villa with infinity pool and solar array", "2-story luxury villa prompt"),
    ("12-story high-rise apartment tower with 2BHK and 3BHK units", "12-story tower prompt"),
    ("Commercial office headquarters with central chilled water HVAC", "Commercial office prompt"),
]

for prompt_text, desc in adversarial_prompts:
    try:
        spec = parse_prompt_to_design_spec(prompt_text)

        # Invariant 1: Valid DesignSpec instance
        tracker.assert_true(isinstance(spec, DesignSpec), f"Parser ({desc}): produces valid DesignSpec")

        # Invariant 2: Total storeys within bounds [1, 100]
        tracker.assert_true(1 <= spec.total_storeys <= 100, f"Parser ({desc}): total_storeys {spec.total_storeys} in [1, 100]")

        # Invariant 3: Storey elevation strictly monotonic
        monotonic = True
        for i in range(1, len(spec.storeys)):
            if spec.storeys[i].elevation_m <= spec.storeys[i-1].elevation_m:
                monotonic = False
                break
        tracker.assert_true(monotonic, f"Parser ({desc}): storey elevations are strictly monotonic")

        # Invariant 4: No raw geometry in dump
        assert_no_raw_geometry(spec.model_dump())
        tracker.assert_true(True, f"Parser ({desc}): zero raw geometry keys in DesignSpec dump")

        # Invariant 5: Compiles cleanly into a valid SpatialNode tree with integrity check
        tree = compile_design_spec_to_spatial_tree(spec)
        integrity_ok = validate_tree_integrity(tree)
        tracker.assert_true(integrity_ok, f"Parser ({desc}): compiles to 100% valid SpatialNode tree")

    except Exception as e:
        tracker.assert_true(False, f"Parser ({desc})", f"Failed with exception: {traceback.format_exc()}")


# ==============================================================================
# Summary Report & Output
# ==============================================================================
print("\n" + "="*80)
print(f"STRESS & FUZZING TEST SUITE COMPLETED: {tracker.passed}/{tracker.total} PASSED ({tracker.failed} FAILED)")
print("="*80)

if tracker.failures:
    print("\nFAILURES SUMMARY:")
    for f in tracker.failures:
        print(f"  - {f['test']}: {f['error']}")

sys.exit(0 if tracker.failed == 0 else 1)
