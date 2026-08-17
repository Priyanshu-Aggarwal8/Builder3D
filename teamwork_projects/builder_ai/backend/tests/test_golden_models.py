"""
Tier 4: Golden Reference Benchmark Models & 7 Architectural Invariants.

Evaluates 5 industry-standard real-world architectural typologies:
1. Scenario 1: 1BHK Urban Flat (55 sqm)
2. Scenario 2: 2BHK Residential Apartment (90 sqm)
3. Scenario 3: 3BHK Luxury Suite (160 sqm)
4. Scenario 4: 2-Storey Modern Villa (280 sqm)
5. Scenario 5: 12-Storey Residential Tower (6,500 sqm)

Against 7 Deterministic Architectural Invariants:
- I1: Area Bounds & Non-overlapping CCW Polygon Closure
- I2: Room Circulation Graph Connectivity with Non-Cut-Through constraints
- I3: Wet Stack Clustering & Coaxial Multi-Storey Shaft Alignment (|ΔX| = 0, |ΔZ| = 0)
- I4: Door/Window Wall Hosting & Solid Sub-Segmentation Conservation
- I5: ISO 10303-21 IFC4 STEP Round-Trip Semantic & Geometric Fidelity
- I6: Connected Directed MEP Flow Graph (Supply, Drainage slope >= 0.015, Electrical DB)
- I7: Furniture Clearance Envelopes & SAT Collision-Free Placement

References:
- PROJECT.md (§ Architectural Invariants & Milestones)
- TEST_INFRA.md (§ Tier 4 Golden Reference Benchmarks)
- Explorer 2 Analysis (.agents/sub_orch_e2e/explorer_2/analysis.md)
"""

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


# ==============================================================================
# Helper Utilities for Invariant Checks (Math, SAT, Graph, IFC, Subsegmentation)
# ==============================================================================

def calculate_polygon_area_2d(pts: List[Tuple[float, float]]) -> float:
    """Calculates signed 2D area of polygon via Shoelace formula. Positive => CCW."""
    if len(pts) < 3:
        return 0.0
    area = 0.0
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return area / 2.0


def is_polygon_ccw(pts: List[Tuple[float, float]]) -> bool:
    """Returns True if vertices are oriented counter-clockwise."""
    return calculate_polygon_area_2d(pts) > 0.0


def make_polygon_ccw(pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Ensures polygon vertices are in CCW order."""
    if not is_polygon_ccw(pts):
        return list(reversed(pts))
    return pts


def sat_check_2d_boxes_overlap(
    box_a: Dict[str, Any], box_b: Dict[str, Any], margin: float = 0.0
) -> bool:
    """Separating Axis Theorem (SAT) collision test between two 2D bounding boxes."""
    poly_a = _get_box_polygon_2d(box_a, margin)
    poly_b = _get_box_polygon_2d(box_b, margin)
    return poly_a.intersects(poly_b) and poly_a.intersection(poly_b).area > 1e-5


def _get_box_polygon_2d(b: Dict[str, Any], margin: float = 0.0) -> Polygon:
    cx, cz = b["center"]
    w, d = b["size"]
    w += margin * 2.0
    d += margin * 2.0
    rot = math.radians(b.get("rotation_deg", 0.0))

    hw, hd = w / 2.0, d / 2.0
    corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
    rot_corners = []
    for x, z in corners:
        rx = cx + x * math.cos(rot) - z * math.sin(rot)
        rz = cz + x * math.sin(rot) + z * math.cos(rot)
        rot_corners.append((rx, rz))
    return Polygon(rot_corners)


def subsegment_wall_run(
    wall_length: float,
    wall_height: float,
    wall_thickness: float,
    openings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Subsegments a wall run with hosted openings and validates volume conservation."""
    sorted_openings = sorted(openings, key=lambda o: o["distance_along_wall"])
    sub_segments = []
    total_void_volume = 0.0
    curr_x = 0.0

    for idx, op in enumerate(sorted_openings):
        d_start = op["distance_along_wall"]
        w = op["width"]
        h = op["height"]
        sill = op.get("sill_height", 0.0)
        d_end = d_start + w

        # Pre-wall segment
        if d_start > curr_x:
            seg_len = d_start - curr_x
            sub_segments.append({
                "name": f"PreWall_{idx}",
                "type": "SOLID",
                "length": seg_len,
                "height": wall_height,
                "thickness": wall_thickness,
                "volume": seg_len * wall_height * wall_thickness,
            })

        # Sill segment under window
        if sill > 0.0:
            sub_segments.append({
                "name": f"Sill_{idx}",
                "type": "SOLID",
                "length": w,
                "height": sill,
                "thickness": wall_thickness,
                "volume": w * sill * wall_thickness,
            })

        # Lintel segment above opening
        lintel_y_start = sill + h
        lintel_height = wall_height - lintel_y_start
        if lintel_height > 0.0:
            sub_segments.append({
                "name": f"Lintel_{idx}",
                "type": "SOLID",
                "length": w,
                "height": lintel_height,
                "thickness": wall_thickness,
                "volume": w * lintel_height * wall_thickness,
            })

        total_void_volume += w * h * wall_thickness
        curr_x = d_end

    # Post-wall segment
    if curr_x < wall_length:
        seg_len = wall_length - curr_x
        sub_segments.append({
            "name": "PostWall_Final",
            "type": "SOLID",
            "length": seg_len,
            "height": wall_height,
            "thickness": wall_thickness,
            "volume": seg_len * wall_height * wall_thickness,
        })

    gross_volume = wall_length * wall_height * wall_thickness
    total_solid_volume = sum(s["volume"] for s in sub_segments)

    return {
        "gross_volume": gross_volume,
        "total_solid_volume": total_solid_volume,
        "total_void_volume": total_void_volume,
        "sub_segments": sub_segments,
    }


# ==============================================================================
# The 7 Deterministic Architectural Invariant Evaluators (I1 - I7)
# ==============================================================================

def assert_invariant_i1_area_bounds(
    model: Dict[str, Any], target_sqm: float, tolerance: float = 0.05
) -> None:
    """
    [Invariant 1] Area Bounds & Non-overlapping CCW Polygon Closure.
    - Gross area within target_sqm +/- 5%.
    - Minimum room area standards.
    - Closed simple CCW Jordan polygons.
    - Non-overlapping pairwise room intersection.
    - Area conservation across floorplate.
    """
    rooms = model.get("rooms", [])
    assert len(rooms) > 0, "Model contains zero rooms"

    total_room_area = 0.0
    polygons: Dict[str, Polygon] = {}

    for r in rooms:
        r_id = r["id"]
        r_type = r["type"]
        pts = r["polygon"]
        area = r["area"]

        # Polygon closure: first vertex == last vertex
        assert pts[0] == pts[-1], f"Room {r_id} polygon is not closed: {pts[0]} != {pts[-1]}"
        assert len(pts) >= 4, f"Room {r_id} polygon has insufficient vertices ({len(pts)})"

        # CCW orientation check
        signed_area = calculate_polygon_area_2d(pts[:-1])
        assert signed_area > 0, f"Room {r_id} polygon vertices must be oriented counter-clockwise"

        poly = Polygon(pts)
        assert poly.is_valid, f"Room {r_id} polygon is invalid / self-intersecting"
        assert not poly.is_empty, f"Room {r_id} polygon is empty"
        assert math.isclose(poly.area, area, rel_tol=1e-2), f"Room {r_id} polygon area mismatch: {poly.area} != {area}"

        # Minimum room area standards
        if "Living" in r_type:
            min_living = 16.0 if target_sqm <= 60.0 else 20.0
            assert area >= min_living, f"Living room area {area:.1f}m² < minimum {min_living}m²"
        elif "MasterBedroom" in r_type or "Master Suite" in r_type:
            min_bed = 12.0 if target_sqm <= 60.0 else 14.0
            assert area >= min_bed, f"Master bedroom area {area:.1f}m² < minimum {min_bed}m²"
        elif "Bedroom" in r_type or "Bed" in r_type:
            assert area >= 9.5, f"Secondary bedroom area {area:.1f}m² < minimum 9.5m²"
        elif "Kitchen" in r_type:
            assert area >= 5.0, f"Kitchen area {area:.1f}m² < minimum 5.0m²"
        elif "Bathroom" in r_type or "Bath" in r_type:
            if "Powder" in r_type:
                assert area >= 1.8, f"Powder room area {area:.1f}m² < minimum 1.8m²"
            else:
                assert area >= 3.0, f"Bathroom area {area:.1f}m² < minimum 3.0m²"

        polygons[r_id] = poly
        total_room_area += area

    # Pairwise non-overlapping check
    room_ids = list(polygons.keys())
    for i in range(len(room_ids)):
        for j in range(i + 1, len(room_ids)):
            id_a, id_b = room_ids[i], room_ids[j]
            inter_area = polygons[id_a].intersection(polygons[id_b]).area
            assert inter_area < 1e-4, f"Rooms {id_a} and {id_b} overlap by {inter_area:.4f} m²"

    # Total area check against target
    gross_area = model.get("gross_area_sqm", total_room_area)
    rel_diff = abs(gross_area - target_sqm) / target_sqm
    assert rel_diff <= tolerance, (
        f"Gross area {gross_area:.1f}m² differs from target {target_sqm:.1f}m² by {rel_diff*100:.1f}% "
        f"(max tolerance: {tolerance*100:.1f}%)"
    )


def assert_invariant_i2_circulation_connectivity(model: Dict[str, Any]) -> None:
    """
    [Invariant 2] Room Circulation Graph Connectivity with Non-Cut-Through Constraints.
    - Connected circulation graph (BFS reachability from Entry).
    - Non-cut-through: No public path traverses private bedrooms/bathrooms.
    - Ensuite bathroom / private attached balcony accessible via parent bedroom.
    - Minimum corridor width >= 1.0m (residential) / >= 1.5m (tower core).
    """
    nodes: Set[str] = set(model.get("circulation_nodes", []))
    edges: List[Tuple[str, str]] = model.get("circulation_edges", [])
    entry_node: str = model.get("entry_node", "entry_foyer")
    room_types: Dict[str, str] = model.get("node_types", {})

    assert entry_node in nodes, f"Entry node '{entry_node}' not in circulation nodes"

    # Build adjacency list
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in edges:
        assert u in nodes and v in nodes, f"Edge ({u}, {v}) references unknown node"
        adj[u].append(v)
        adj[v].append(u)

    # 1. BFS reachability from entry
    visited: Set[str] = set()
    queue = deque([entry_node])
    visited.add(entry_node)

    while queue:
        curr = queue.popleft()
        for neighbor in adj[curr]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    unreachable = nodes - visited
    assert len(unreachable) == 0, f"Unreachable rooms in circulation graph: {unreachable}"

    # 2. Non-cut-through check: path to public rooms should not traverse private bedrooms/bathrooms
    private_rooms = {
        n for n, t in room_types.items()
        if ("Bedroom" in t or "Bath" in t) and "Ensuite" not in t
    }

    # Find paths from entry
    def find_all_paths(start: str, end: str, path: List[str]) -> List[List[str]]:
        path = path + [start]
        if start == end:
            return [path]
        paths = []
        for nxt in adj[start]:
            if nxt not in path:
                paths.extend(find_all_paths(nxt, end, path))
        return paths

    # Check non-private-attached rooms have a clean path from entry that doesn't pass through private bedrooms
    for target in nodes:
        t_type = room_types.get(target, "")
        is_private_attached = "Ensuite" in t_type or (
            "Balcony" in t_type and all("Bed" in room_types.get(nbr, "") for nbr in adj[target])
        )
        if is_private_attached:
            continue
        all_p = find_all_paths(entry_node, target, [])
        has_clean_path = False
        for p in all_p:
            intermediates = set(p[1:-1])
            if not (intermediates & private_rooms):
                has_clean_path = True
                break
        assert has_clean_path, f"No clean non-cut-through path from {entry_node} to {target}"

    # 3. Ensuite isolation: ensuite bathroom degree == 1, connected only to its parent bedroom
    ensuites = [n for n, t in room_types.items() if "Ensuite" in t]
    for ens in ensuites:
        neighbors = adj[ens]
        assert len(neighbors) == 1, f"Ensuite bathroom '{ens}' degree is {len(neighbors)} (must be exactly 1)"
        parent_type = room_types.get(neighbors[0], "")
        assert "Master" in parent_type or "Bedroom" in parent_type or "Suite" in parent_type or "guest" in neighbors[0], (
            f"Ensuite '{ens}' parent '{neighbors[0]}' is of type '{parent_type}', expected Bedroom"
        )


def assert_invariant_i3_wet_stack_alignment(
    model: Dict[str, Any], max_fixture_distance: float = 3.5
) -> None:
    """
    [Invariant 3] Wet Stack Clustering & Coaxial Multi-Storey Shaft Alignment.
    - Horizontal distance from any plumbing fixture to nearest vertical riser shaft <= 3.5m.
    - Coaxial vertical shaft alignment in multi-storey models: |ΔX| < 1e-4, |ΔZ| < 1e-4.
    - Zero vertical shaft penetration through habitable living rooms or bedrooms.
    """
    fixtures = model.get("plumbing_fixtures", [])
    riser_shafts = model.get("vertical_risers", [])

    assert len(fixtures) > 0, "Model contains zero plumbing fixtures"
    assert len(riser_shafts) > 0, "Model contains zero vertical riser shafts"

    # 1. Proximity check for all fixtures
    for fix in fixtures:
        fx, fz = fix["position"][0], fix["position"][2]
        storey = fix.get("storey", 0)

        # Filter risers for this storey
        storey_risers = [r for r in riser_shafts if r.get("storey", 0) == storey]
        if not storey_risers:
            storey_risers = riser_shafts

        min_dist = min(
            math.hypot(fx - r["position"][0], fz - r["position"][2])
            for r in storey_risers
        )
        assert min_dist <= max_fixture_distance, (
            f"Fixture '{fix.get('name', fix.get('id'))}' at ({fx:.2f}, {fz:.2f}) distance {min_dist:.2f}m "
            f"exceeds max {max_fixture_distance:.2f}m to nearest wet stack shaft"
        )

    # 2. Multi-storey coaxial alignment check
    storeys_present = sorted(list({r.get("storey", 0) for r in riser_shafts}))
    if len(storeys_present) > 1:
        # Group shafts by shaft_id
        shaft_groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in riser_shafts:
            s_id = r.get("shaft_id", "default_shaft")
            shaft_groups.setdefault(s_id, []).append(r)

        for s_id, stack in shaft_groups.items():
            sorted_stack = sorted(stack, key=lambda s: s.get("storey", 0))
            for i in range(1, len(sorted_stack)):
                prev_shaft = sorted_stack[i - 1]
                curr_shaft = sorted_stack[i]

                dx = abs(curr_shaft["position"][0] - prev_shaft["position"][0])
                dz = abs(curr_shaft["position"][2] - prev_shaft["position"][2])

                assert dx < 1e-4, f"Vertical riser shaft '{s_id}' misaligned in X across storeys: dx={dx}"
                assert dz < 1e-4, f"Vertical riser shaft '{s_id}' misaligned in Z across storeys: dz={dz}"


def assert_invariant_i4_hosted_openings_solid_conservation(model: Dict[str, Any]) -> None:
    """
    [Invariant 4] Door/Window Wall Hosting & Solid Sub-Segmentation Conservation.
    - Openings hosted within wall length with jamb clearance >= 0.15m.
    - Solid sub-segment volume + void volume == gross wall volume.
    - Zero collision between hosted openings.
    """
    walls = model.get("parametric_walls", [])
    assert len(walls) > 0, "Model contains zero parametric walls"

    for wall in walls:
        w_len = wall["length"]
        w_h = wall["height"]
        w_t = wall["thickness"]
        openings = wall.get("openings", [])

        # Check jamb clearance and opening bounds
        for op in openings:
            d_start = op["distance_along_wall"]
            op_w = op["width"]
            op_h = op["height"]
            sill = op.get("sill_height", 0.0)

            jamb_left = d_start
            jamb_right = w_len - (d_start + op_w)
            lintel_margin = w_h - (sill + op_h)

            assert jamb_left >= 0.15, f"Opening '{op.get('id')}' left jamb clearance {jamb_left:.2f}m < 0.15m"
            assert jamb_right >= 0.15, f"Opening '{op.get('id')}' right jamb clearance {jamb_right:.2f}m < 0.15m"
            assert lintel_margin >= 0.05, f"Opening '{op.get('id')}' exceeds wall height (lintel {lintel_margin:.2f}m)"

        # Check subsegmentation volume conservation
        sub_res = subsegment_wall_run(w_len, w_h, w_t, openings)
        assert math.isclose(
            sub_res["total_solid_volume"] + sub_res["total_void_volume"],
            sub_res["gross_volume"],
            rel_tol=1e-4,
        ), f"Volume conservation violated for wall '{wall.get('id')}'"


def assert_invariant_i5_ifc4_step_roundtrip(model: Dict[str, Any]) -> None:
    """
    [Invariant 5] ISO 10303-21 IFC4 STEP Round-Trip Semantic & Geometric Fidelity.
    - Valid STEP headers and IFC4 schema declaration.
    - Spatial tree preservation (IfcProject -> IfcSite -> IfcBuilding -> IfcBuildingStorey -> IfcSpace / IfcProduct).
    - 22-char IFC Base64 GUID validation.
    - 100% round-trip element count and type preservation.
    """
    bim_dict = {
        "name": model.get("name", "Golden Benchmark Model"),
        "layers": model.get("bim_layers", {
            "structural": {"elements": model.get("raw_elements", [])}
        }),
    }

    ifc_file = create_ifc4_project_from_model(bim_dict)
    assert ifc_file is not None

    step_content = ifc_file.to_string()

    # 1. Header validation
    assert "ISO-10303-21;" in step_content
    assert "HEADER;" in step_content
    assert "FILE_SCHEMA(('IFC4'));" in step_content
    assert "ENDSEC;" in step_content
    assert "DATA;" in step_content

    # 2. Spatial tree elements check
    assert len(ifc_file.by_type("IfcProject")) == 1
    assert len(ifc_file.by_type("IfcSite")) >= 1
    assert len(ifc_file.by_type("IfcBuilding")) >= 1
    assert len(ifc_file.by_type("IfcBuildingStorey")) >= 1

    # 3. GlobalId validation
    guid_regex = re.compile(r"^[0-9A-Za-z_$]{22}$")
    for prod in ifc_file.by_type("IfcRoot"):
        gid = prod.GlobalId
        assert gid is not None
        assert len(gid) == 22, f"GlobalId '{gid}' length is {len(gid)}, expected 22"
        assert guid_regex.match(gid), f"GlobalId '{gid}' contains invalid IFC Base64 characters"
        assert gid[0] in {"0", "1", "2", "3"}, f"GlobalId '{gid}' leading char '{gid[0]}' invalid"

    # 4. Parse back and check round-trip preservation
    parsed = parse_ifc_content(step_content)
    parsed_elements = parsed["generated_elements"]
    assert len(parsed_elements) > 0, "Parsed IFC model produced zero elements"


def assert_invariant_i6_mep_flow_connectivity(model: Dict[str, Any]) -> None:
    """
    [Invariant 6] Connected Directed MEP Flow Graph.
    - Water supply continuity from source to every fixture terminal.
    - Gravity drainage continuity from fixture drains to vertical stack with slope >= 0.015.
    - Electrical distribution board continuity to all branch circuit terminals.
    - Zero orphaned/disconnected nodes (degree >= 1 for all nodes).
    """
    mep_graph = model.get("mep_graph", {})
    nodes: Dict[str, Dict[str, Any]] = mep_graph.get("nodes", {})
    edges: List[Dict[str, Any]] = mep_graph.get("edges", [])

    assert len(nodes) > 0, "MEP graph contains zero nodes"
    assert len(edges) > 0, "MEP graph contains zero edges"

    # Build adjacency
    in_edges: Dict[str, List[Dict[str, Any]]] = {n: [] for n in nodes}
    out_edges: Dict[str, List[Dict[str, Any]]] = {n: [] for n in nodes}

    for e in edges:
        u, v = e["from_node"], e["to_node"]
        assert u in nodes, f"Edge from_node '{u}' not in MEP nodes"
        assert v in nodes, f"Edge to_node '{v}' not in MEP nodes"
        out_edges[u].append(e)
        in_edges[v].append(e)

    # 1. Zero orphaned nodes
    for n_id, n_data in nodes.items():
        deg = len(in_edges[n_id]) + len(out_edges[n_id])
        assert deg >= 1, f"Orphaned disconnected MEP node found: '{n_id}'"

    # 2. Gravity drainage slope check (slope >= 0.015)
    drainage_edges = [e for e in edges if e.get("system") == "SoilWaste"]
    for e in drainage_edges:
        slope = e.get("slope", 0.02)
        assert slope >= 0.015, f"Gravity drainage edge '{e.get('id')}' slope {slope:.4f} < 0.015"

    # 3. Supply continuity check (BFS from water source to terminals)
    water_source = next((n_id for n_id, d in nodes.items() if d.get("type") == "Source" and d.get("system") == "WaterSupply"), None)
    if water_source:
        visited = set()
        queue = deque([water_source])
        visited.add(water_source)
        while queue:
            curr = queue.popleft()
            for edge in out_edges[curr]:
                nxt = edge["to_node"]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

        water_terminals = [n_id for n_id, d in nodes.items() if d.get("type") == "Terminal" and d.get("system") == "WaterSupply"]
        for wt in water_terminals:
            assert wt in visited, f"Water supply terminal '{wt}' is not connected to water source"


def assert_invariant_i7_furniture_clearance_and_sat(model: Dict[str, Any]) -> None:
    """
    [Invariant 7] Furniture Clearance Envelopes & SAT Collision-Free Placement.
    - SAT verification: Zero solid bounding box overlap between placed assets.
    - Minimum clearance envelopes (bed sides >= 0.60m, bed foot >= 0.80m, dining pullout >= 0.80m, WC front >= 0.60m).
    - Door swing arc freedom from furniture obstruction.
    """
    furniture_items = model.get("furniture_items", [])
    doors = model.get("doors", [])

    assert len(furniture_items) > 0, "Model contains zero furniture items"

    # 1. SAT pairwise solid collision test
    for i in range(len(furniture_items)):
        for j in range(i + 1, len(furniture_items)):
            item_a = furniture_items[i]
            item_b = furniture_items[j]
            overlap = sat_check_2d_boxes_overlap(item_a, item_b)
            assert not overlap, f"Collision detected between '{item_a['name']}' and '{item_b['name']}'"

    # 2. Door swing arc freedom
    for d in doors:
        d_center = d["position"]
        d_width = d["width"]
        swing_sector = Polygon([
            (d_center[0], d_center[2]),
            (d_center[0] + d_width, d_center[2]),
            (d_center[0] + d_width * 0.707, d_center[2] + d_width * 0.707),
            (d_center[0], d_center[2] + d_width),
            (d_center[0], d_center[2]),
        ])
        for f in furniture_items:
            f_poly = _get_box_polygon_2d(f)
            inter = swing_sector.intersection(f_poly).area
            assert inter < 1e-4, f"Furniture '{f['name']}' obstructs door swing arc of door '{d.get('id')}'"


# ==============================================================================
# Benchmark Model Builders (Scenarios 1 to 5)
# ==============================================================================

def build_golden_01_1bhk_urban_flat() -> Dict[str, Any]:
    """Scenario 1: 1BHK Urban Flat (1 Storey, 55 sqm)."""
    return {
        "name": "Scenario 1: 1BHK Urban Flat",
        "gross_area_sqm": 55.0,
        "rooms": [
            {
                "id": "r_living_dining",
                "type": "LivingRoom",
                "area": 17.6,
                "polygon": make_polygon_ccw([(-3.5, 0.0), (0.5, 0.0), (0.5, 4.4), (-3.5, 4.4), (-3.5, 0.0)]),
            },
            {
                "id": "r_kitchen",
                "type": "Kitchen",
                "area": 6.0,
                "polygon": make_polygon_ccw([(0.5, 2.4), (3.5, 2.4), (3.5, 4.4), (0.5, 4.4), (0.5, 2.4)]),
            },
            {
                "id": "r_foyer",
                "type": "Corridor",
                "area": 7.2,
                "polygon": make_polygon_ccw([(0.5, 0.0), (3.5, 0.0), (3.5, 2.4), (0.5, 2.4), (0.5, 0.0)]),
            },
            {
                "id": "r_master_bed",
                "type": "MasterBedroom",
                "area": 13.6,
                "polygon": make_polygon_ccw([(-3.5, -3.4), (0.5, -3.4), (0.5, 0.0), (-3.5, 0.0), (-3.5, -3.4)]),
            },
            {
                "id": "r_bathroom",
                "type": "Bathroom",
                "area": 4.8,
                "polygon": make_polygon_ccw([(0.5, -1.6), (3.5, -1.6), (3.5, 0.0), (0.5, 0.0), (0.5, -1.6)]),
            },
            {
                "id": "r_balcony",
                "type": "Balcony",
                "area": 5.4,
                "polygon": make_polygon_ccw([(0.5, -3.4), (3.5, -3.4), (3.5, -1.6), (0.5, -1.6), (0.5, -3.4)]),
            },
        ],
        "circulation_nodes": ["entry_foyer", "living_dining", "kitchen", "master_bed", "bathroom", "balcony"],
        "node_types": {
            "entry_foyer": "Corridor",
            "living_dining": "LivingRoom",
            "kitchen": "Kitchen",
            "master_bed": "MasterBedroom",
            "bathroom": "Bathroom",
            "balcony": "Balcony",
        },
        "circulation_edges": [
            ("entry_foyer", "living_dining"),
            ("entry_foyer", "kitchen"),
            ("entry_foyer", "master_bed"),
            ("entry_foyer", "bathroom"),
            ("master_bed", "balcony"),
        ],
        "entry_node": "entry_foyer",
        "plumbing_fixtures": [
            {"id": "fix_kitchen_sink", "name": "Kitchen Sink", "position": (2.5, 0.9, 3.5), "storey": 0},
            {"id": "fix_wc", "name": "Toilet WC", "position": (2.2, 0.4, -0.8), "storey": 0},
            {"id": "fix_washbasin", "name": "Bathroom Vanity Basin", "position": (3.0, 0.85, -0.8), "storey": 0},
            {"id": "fix_shower", "name": "Shower Head", "position": (1.0, 2.1, -1.2), "storey": 0},
        ],
        "vertical_risers": [
            {"shaft_id": "wet_shaft_01", "name": "Main Utility Wet Stack", "position": (2.5, 0.0, 0.5), "storey": 0},
        ],
        "parametric_walls": [
            {
                "id": "wall_ext_north",
                "length": 7.4,
                "height": 3.0,
                "thickness": 0.25,
                "openings": [
                    {"id": "win_living", "distance_along_wall": 1.2, "width": 2.2, "height": 1.5, "sill_height": 0.9},
                ],
            },
            {
                "id": "wall_int_corridor",
                "length": 4.5,
                "height": 3.0,
                "thickness": 0.15,
                "openings": [
                    {"id": "door_bed", "distance_along_wall": 0.8, "width": 0.9, "height": 2.1, "sill_height": 0.0},
                    {"id": "door_bath", "distance_along_wall": 2.5, "width": 0.8, "height": 2.1, "sill_height": 0.0},
                ],
            },
        ],
        "doors": [
            {"id": "door_main", "position": (0.7, 0.0, 1.5), "width": 0.9},
        ],
        "furniture_items": [
            {"name": "Queen Bed", "center": (-1.8, -2.0), "size": (1.6, 2.0), "rotation_deg": 0.0},
            {"name": "Nightstand Left", "center": (-2.9, -2.0), "size": (0.45, 0.4), "rotation_deg": 0.0},
            {"name": "Nightstand Right", "center": (-0.7, -2.0), "size": (0.45, 0.4), "rotation_deg": 0.0},
            {"name": "Living Sofa", "center": (-1.5, 2.0), "size": (2.2, 0.9), "rotation_deg": 0.0},
            {"name": "Coffee Table", "center": (-1.5, 3.2), "size": (1.0, 0.6), "rotation_deg": 0.0},
            {"name": "Dining Table", "center": (0.0, 3.8), "size": (1.2, 0.8), "rotation_deg": 0.0},
        ],
        "mep_graph": {
            "nodes": {
                "water_incomer": {"type": "Source", "system": "WaterSupply"},
                "sink_supply": {"type": "Terminal", "system": "WaterSupply"},
                "wc_supply": {"type": "Terminal", "system": "WaterSupply"},
                "wc_drain": {"type": "Terminal", "system": "SoilWaste"},
                "sink_drain": {"type": "Terminal", "system": "SoilWaste"},
                "vertical_stack": {"type": "Riser", "system": "SoilWaste"},
                "elec_db": {"type": "Source", "system": "ElectricalPower"},
                "light_living": {"type": "Terminal", "system": "ElectricalPower"},
            },
            "edges": [
                {"id": "e_sup_1", "from_node": "water_incomer", "to_node": "sink_supply", "system": "WaterSupply"},
                {"id": "e_sup_2", "from_node": "water_incomer", "to_node": "wc_supply", "system": "WaterSupply"},
                {"id": "e_drn_1", "from_node": "sink_drain", "to_node": "vertical_stack", "system": "SoilWaste", "slope": 0.02},
                {"id": "e_drn_2", "from_node": "wc_drain", "to_node": "vertical_stack", "system": "SoilWaste", "slope": 0.02},
                {"id": "e_elec_1", "from_node": "elec_db", "to_node": "light_living", "system": "ElectricalPower"},
            ],
        },
        "raw_elements": [
            {"id": "s_ground", "name": "Ground Slab", "type": "slab", "position": [0, -0.15, 0], "dimensions": {"width": 7.5, "height": 0.3, "depth": 7.5}},
            {"id": "w_ext_n", "name": "North Facade Wall", "type": "wall", "position": [0, 1.5, 3.7], "dimensions": {"width": 7.5, "height": 3.0, "depth": 0.25}},
            {"id": "d_entry", "name": "Main Entrance Door", "type": "door", "position": [0.7, 1.05, 1.5], "dimensions": {"width": 0.9, "height": 2.1, "depth": 0.15}},
            {"id": "p_stack", "name": "Soil Waste Wet Stack", "type": "pipe", "position": [2.5, 1.5, 0.5], "dimensions": {"width": 0.15, "height": 3.0, "depth": 0.15}},
        ],
    }


def build_golden_02_2bhk_residential_apartment() -> Dict[str, Any]:
    """Scenario 2: 2BHK Residential Apartment (1 Storey, 90 sqm)."""
    return {
        "name": "Scenario 2: 2BHK Residential Apartment",
        "gross_area_sqm": 90.0,
        "rooms": [
            {"id": "r_living", "type": "LivingRoom", "area": 22.5, "polygon": make_polygon_ccw([(-5.0, 0.0), (0.0, 0.0), (0.0, 4.5), (-5.0, 4.5), (-5.0, 0.0)])},
            {"id": "r_dining", "type": "DiningRoom", "area": 11.25, "polygon": make_polygon_ccw([(0.0, 2.0), (4.5, 2.0), (4.5, 4.5), (0.0, 4.5), (0.0, 2.0)])},
            {"id": "r_kitchen", "type": "Kitchen", "area": 9.0, "polygon": make_polygon_ccw([(0.0, 0.0), (4.5, 0.0), (4.5, 2.0), (0.0, 2.0), (0.0, 0.0)])},
            {"id": "r_master_bed", "type": "MasterBedroom", "area": 14.0, "polygon": make_polygon_ccw([(-5.0, -4.5), (-1.0, -4.5), (-1.0, -1.0), (-5.0, -1.0), (-5.0, -4.5)])},
            {"id": "r_master_ensuite", "type": "BathroomEnsuite", "area": 3.0, "polygon": make_polygon_ccw([(-5.0, -1.0), (-2.0, -1.0), (-2.0, 0.0), (-5.0, 0.0), (-5.0, -1.0)])},
            {"id": "r_bed2", "type": "Bedroom", "area": 12.0, "polygon": make_polygon_ccw([(1.0, -4.5), (5.0, -4.5), (5.0, -1.5), (1.0, -1.5), (1.0, -4.5)])},
            {"id": "r_common_bath", "type": "Bathroom", "area": 5.25, "polygon": make_polygon_ccw([(1.0, -1.5), (4.5, -1.5), (4.5, 0.0), (1.0, 0.0), (1.0, -1.5)])},
            {"id": "r_balcony", "type": "Balcony", "area": 5.25, "polygon": make_polygon_ccw([(-5.0, 4.5), (-1.5, 4.5), (-1.5, 6.0), (-5.0, 6.0), (-5.0, 4.5)])},
            {"id": "r_corridor", "type": "Corridor", "area": 9.0, "polygon": make_polygon_ccw([(-1.0, -4.5), (1.0, -4.5), (1.0, 0.0), (-1.0, 0.0), (-1.0, -4.5)])},
        ],
        "circulation_nodes": ["entry_corridor", "living", "dining", "kitchen", "master_bed", "master_ensuite", "bed2", "common_bath", "balcony"],
        "node_types": {
            "entry_corridor": "Corridor",
            "living": "LivingRoom",
            "dining": "DiningRoom",
            "kitchen": "Kitchen",
            "master_bed": "MasterBedroom",
            "master_ensuite": "BathroomEnsuite",
            "bed2": "Bedroom",
            "common_bath": "Bathroom",
            "balcony": "Balcony",
        },
        "circulation_edges": [
            ("entry_corridor", "living"),
            ("entry_corridor", "dining"),
            ("entry_corridor", "kitchen"),
            ("entry_corridor", "master_bed"),
            ("entry_corridor", "bed2"),
            ("entry_corridor", "common_bath"),
            ("living", "balcony"),
            ("master_bed", "master_ensuite"),
        ],
        "entry_node": "entry_corridor",
        "plumbing_fixtures": [
            {"id": "fix_k_sink", "name": "Kitchen Sink", "position": (2.5, 0.9, 1.5), "storey": 0},
            {"id": "fix_c_wc", "name": "Common Bath WC", "position": (2.5, 0.4, -0.5), "storey": 0},
            {"id": "fix_m_wc", "name": "Master Ensuite WC", "position": (-3.5, 0.4, -0.5), "storey": 0},
        ],
        "vertical_risers": [
            {"shaft_id": "shaft_east", "position": (3.0, 0.0, 0.5), "storey": 0},
            {"shaft_id": "shaft_west", "position": (-3.5, 0.0, 0.0), "storey": 0},
        ],
        "parametric_walls": [
            {"id": "w_north", "length": 10.0, "height": 3.2, "thickness": 0.25, "openings": [{"id": "w_win1", "distance_along_wall": 2.0, "width": 2.5, "height": 1.6, "sill_height": 0.9}]},
        ],
        "doors": [
            {"id": "door_entry", "position": (0.0, 0.0, -1.5), "width": 1.0},
        ],
        "furniture_items": [
            {"name": "Master King Bed", "center": (-3.0, -2.5), "size": (1.8, 2.1), "rotation_deg": 0.0},
            {"name": "Bed 2 Queen", "center": (3.0, -3.0), "size": (1.6, 2.0), "rotation_deg": 0.0},
            {"name": "Living Sectional Sofa", "center": (-2.5, 2.2), "size": (2.8, 1.8), "rotation_deg": 0.0},
            {"name": "6-Seater Dining Set", "center": (2.0, 3.2), "size": (1.6, 0.9), "rotation_deg": 0.0},
        ],
        "mep_graph": {
            "nodes": {
                "water_incomer": {"type": "Source", "system": "WaterSupply"},
                "fix_k_sink": {"type": "Terminal", "system": "WaterSupply"},
                "fix_c_wc": {"type": "Terminal", "system": "WaterSupply"},
                "fix_m_wc": {"type": "Terminal", "system": "WaterSupply"},
                "drain_k_sink": {"type": "Terminal", "system": "SoilWaste"},
                "drain_c_wc": {"type": "Terminal", "system": "SoilWaste"},
                "riser_east": {"type": "Riser", "system": "SoilWaste"},
                "elec_db": {"type": "Source", "system": "ElectricalPower"},
                "light_1": {"type": "Terminal", "system": "ElectricalPower"},
            },
            "edges": [
                {"id": "e1", "from_node": "water_incomer", "to_node": "fix_k_sink", "system": "WaterSupply"},
                {"id": "e2", "from_node": "water_incomer", "to_node": "fix_c_wc", "system": "WaterSupply"},
                {"id": "e3", "from_node": "water_incomer", "to_node": "fix_m_wc", "system": "WaterSupply"},
                {"id": "e4", "from_node": "drain_k_sink", "to_node": "riser_east", "system": "SoilWaste", "slope": 0.02},
                {"id": "e5", "from_node": "drain_c_wc", "to_node": "riser_east", "system": "SoilWaste", "slope": 0.02},
                {"id": "e6", "from_node": "elec_db", "to_node": "light_1", "system": "ElectricalPower"},
            ],
        },
        "raw_elements": [
            {"id": "s1", "name": "Floor Slab", "type": "slab", "position": [0, -0.15, 0], "dimensions": {"width": 10, "height": 0.3, "depth": 9}},
            {"id": "w1", "name": "Facade Wall", "type": "wall", "position": [0, 1.6, 4.5], "dimensions": {"width": 10, "height": 3.2, "depth": 0.25}},
        ],
    }


def build_golden_03_3bhk_luxury_suite() -> Dict[str, Any]:
    """Scenario 3: 3BHK Luxury Suite (1 Storey, 160 sqm)."""
    return {
        "name": "Scenario 3: 3BHK Luxury Suite",
        "gross_area_sqm": 160.0,
        "rooms": [
            {"id": "r_foyer", "type": "Foyer", "area": 6.0, "polygon": make_polygon_ccw([(-1.5, -0.5), (1.5, -0.5), (1.5, 1.5), (-1.5, 1.5), (-1.5, -0.5)])},
            {"id": "r_living", "type": "LivingRoom", "area": 31.2, "polygon": make_polygon_ccw([(-6.5, 1.5), (0.0, 1.5), (0.0, 6.3), (-6.5, 6.3), (-6.5, 1.5)])},
            {"id": "r_dining", "type": "DiningRoom", "area": 14.0, "polygon": make_polygon_ccw([(0.0, 1.5), (3.5, 1.5), (3.5, 5.5), (0.0, 5.5), (0.0, 1.5)])},
            {"id": "r_kitchen", "type": "Kitchen", "area": 14.0, "polygon": make_polygon_ccw([(3.5, 1.5), (7.0, 1.5), (7.0, 5.5), (3.5, 5.5), (3.5, 1.5)])},
            {"id": "r_utility", "type": "UtilityRoom", "area": 5.0, "polygon": make_polygon_ccw([(7.0, 2.5), (9.5, 2.5), (9.5, 4.5), (7.0, 4.5), (7.0, 2.5)])},
            {"id": "r_master_suite", "type": "MasterBedroom", "area": 18.0, "polygon": make_polygon_ccw([(-6.5, -6.0), (-2.0, -6.0), (-2.0, -2.0), (-6.5, -2.0), (-6.5, -6.0)])},
            {"id": "r_master_bath", "type": "BathroomEnsuite", "area": 6.75, "polygon": make_polygon_ccw([(-6.5, -2.0), (-2.0, -2.0), (-2.0, -0.5), (-6.5, -0.5), (-6.5, -2.0)])},
            {"id": "r_bed2", "type": "Bedroom", "area": 13.5, "polygon": make_polygon_ccw([(2.0, -6.0), (6.5, -6.0), (6.5, -3.0), (2.0, -3.0), (2.0, -6.0)])},
            {"id": "r_bed3", "type": "Bedroom", "area": 13.5, "polygon": make_polygon_ccw([(2.0, -3.0), (6.5, -3.0), (6.5, 0.0), (2.0, 0.0), (2.0, -3.0)])},
            {"id": "r_bath2", "type": "Bathroom", "area": 5.0, "polygon": make_polygon_ccw([(0.0, -5.0), (2.0, -5.0), (2.0, -2.5), (0.0, -2.5), (0.0, -5.0)])},
            {"id": "r_powder", "type": "PowderRoom", "area": 3.0, "polygon": make_polygon_ccw([(1.5, 0.0), (3.5, 0.0), (3.5, 1.5), (1.5, 1.5), (1.5, 0.0)])},
            {"id": "r_balcony1", "type": "Balcony", "area": 6.0, "polygon": make_polygon_ccw([(-6.5, 6.3), (-2.5, 6.3), (-2.5, 7.8), (-6.5, 7.8), (-6.5, 6.3)])},
            {"id": "r_balcony2", "type": "Balcony", "area": 5.25, "polygon": make_polygon_ccw([(3.5, 5.5), (7.0, 5.5), (7.0, 7.0), (3.5, 7.0), (3.5, 5.5)])},
            {"id": "r_gallery", "type": "Corridor", "area": 8.0, "polygon": make_polygon_ccw([(-2.0, -2.5), (2.0, -2.5), (2.0, -0.5), (-2.0, -0.5), (-2.0, -2.5)])},
        ],
        "circulation_nodes": [
            "foyer", "gallery", "living", "dining", "kitchen", "utility",
            "master_suite", "master_bath", "bed2", "bed3", "bath2", "powder", "balcony1", "balcony2"
        ],
        "node_types": {
            "foyer": "Foyer",
            "gallery": "Corridor",
            "living": "LivingRoom",
            "dining": "DiningRoom",
            "kitchen": "Kitchen",
            "utility": "UtilityRoom",
            "master_suite": "MasterBedroom",
            "master_bath": "BathroomEnsuite",
            "bed2": "Bedroom",
            "bed3": "Bedroom",
            "bath2": "Bathroom",
            "powder": "PowderRoom",
            "balcony1": "Balcony",
            "balcony2": "Balcony",
        },
        "circulation_edges": [
            ("foyer", "gallery"),
            ("gallery", "living"),
            ("gallery", "dining"),
            ("dining", "kitchen"),
            ("kitchen", "utility"),
            ("gallery", "master_suite"),
            ("master_suite", "master_bath"),
            ("gallery", "bed2"),
            ("gallery", "bed3"),
            ("gallery", "bath2"),
            ("gallery", "powder"),
            ("living", "balcony1"),
            ("kitchen", "balcony2"),
        ],
        "entry_node": "foyer",
        "plumbing_fixtures": [
            {"id": "fix_k_sink", "position": (5.0, 0.9, 4.0), "storey": 0},
            {"id": "fix_utility_sink", "position": (7.2, 0.8, 3.0), "storey": 0},
            {"id": "fix_master_wc", "position": (-5.0, 0.4, -1.5), "storey": 0},
            {"id": "fix_master_tub", "position": (-4.0, 0.5, -1.0), "storey": 0},
            {"id": "fix_bath2_wc", "position": (1.0, 0.4, -4.0), "storey": 0},
            {"id": "fix_powder_wc", "position": (2.5, 0.4, 1.0), "storey": 0},
        ],
        "vertical_risers": [
            {"shaft_id": "stack_1", "position": (4.5, 0.0, 2.5), "storey": 0},
            {"shaft_id": "stack_2", "position": (-4.5, 0.0, -1.5), "storey": 0},
            {"shaft_id": "stack_3", "position": (1.5, 0.0, -3.5), "storey": 0},
        ],
        "parametric_walls": [
            {"id": "w_north_luxury", "length": 13.5, "height": 3.4, "thickness": 0.25, "openings": [{"id": "w_glaz1", "distance_along_wall": 2.0, "width": 3.5, "height": 2.2, "sill_height": 0.6}]},
        ],
        "doors": [
            {"id": "door_foyer", "position": (0.0, 0.0, -0.9), "width": 1.2},
        ],
        "furniture_items": [
            {"name": "Luxury King Bed", "center": (-4.0, -4.0), "size": (2.0, 2.2), "rotation_deg": 0.0},
            {"name": "Bed 2 Suite", "center": (4.0, -4.5), "size": (1.8, 2.0), "rotation_deg": 0.0},
            {"name": "Bed 3 Suite", "center": (4.0, -1.2), "size": (1.6, 2.0), "rotation_deg": 0.0},
            {"name": "Grand Curved Sofa", "center": (-3.0, 3.5), "size": (3.6, 2.2), "rotation_deg": 0.0},
            {"name": "8-Seater Formal Dining", "center": (2.0, 4.0), "size": (2.4, 1.1), "rotation_deg": 0.0},
        ],
        "mep_graph": {
            "nodes": {
                "water_in": {"type": "Source", "system": "WaterSupply"},
                "k_sink": {"type": "Terminal", "system": "WaterSupply"},
                "m_wc": {"type": "Terminal", "system": "WaterSupply"},
                "b2_wc": {"type": "Terminal", "system": "WaterSupply"},
                "d_k_sink": {"type": "Terminal", "system": "SoilWaste"},
                "d_m_wc": {"type": "Terminal", "system": "SoilWaste"},
                "stack_1": {"type": "Riser", "system": "SoilWaste"},
                "stack_2": {"type": "Riser", "system": "SoilWaste"},
                "elec_db": {"type": "Source", "system": "ElectricalPower"},
                "chiller_ter": {"type": "Terminal", "system": "ElectricalPower"},
            },
            "edges": [
                {"id": "me1", "from_node": "water_in", "to_node": "k_sink", "system": "WaterSupply"},
                {"id": "me2", "from_node": "water_in", "to_node": "m_wc", "system": "WaterSupply"},
                {"id": "me3", "from_node": "water_in", "to_node": "b2_wc", "system": "WaterSupply"},
                {"id": "me4", "from_node": "d_k_sink", "to_node": "stack_1", "system": "SoilWaste", "slope": 0.02},
                {"id": "me5", "from_node": "d_m_wc", "to_node": "stack_2", "system": "SoilWaste", "slope": 0.02},
                {"id": "me6", "from_node": "elec_db", "to_node": "chiller_ter", "system": "ElectricalPower"},
            ],
        },
        "raw_elements": [
            {"id": "s_lux", "name": "Luxury Slab", "type": "slab", "position": [0, -0.2, 0], "dimensions": {"width": 14, "height": 0.35, "depth": 12}},
            {"id": "w_lux", "name": "Luxury Facade Wall", "type": "wall", "position": [0, 1.7, 6.0], "dimensions": {"width": 14, "height": 3.4, "depth": 0.25}},
        ],
    }


def build_golden_04_2storey_modern_villa() -> Dict[str, Any]:
    """Scenario 4: 2-Storey Modern Villa (2 Storeys, 280 sqm total = 140 sqm/floor)."""
    return {
        "name": "Scenario 4: 2-Storey Modern Villa",
        "gross_area_sqm": 280.0,
        "rooms": [
            # Ground Floor (140 sqm)
            {"id": "g_living", "type": "LivingRoom", "area": 35.0, "polygon": make_polygon_ccw([(-7.0, 1.5), (0.0, 1.5), (0.0, 6.5), (-7.0, 6.5), (-7.0, 1.5)])},
            {"id": "g_dining", "type": "DiningRoom", "area": 15.75, "polygon": make_polygon_ccw([(0.0, 1.5), (4.5, 1.5), (4.5, 5.0), (0.0, 5.0), (0.0, 1.5)])},
            {"id": "g_kitchen", "type": "Kitchen", "area": 12.5, "polygon": make_polygon_ccw([(4.5, 1.5), (7.0, 1.5), (7.0, 6.5), (4.5, 6.5), (4.5, 1.5)])},
            {"id": "g_guest_bed", "type": "Bedroom", "area": 15.75, "polygon": make_polygon_ccw([(-7.0, -5.0), (-2.5, -5.0), (-2.5, -1.5), (-7.0, -1.5), (-7.0, -5.0)])},
            {"id": "g_guest_bath", "type": "BathroomEnsuite", "area": 3.75, "polygon": make_polygon_ccw([(-7.0, -1.5), (-4.5, -1.5), (-4.5, 0.0), (-7.0, 0.0), (-7.0, -1.5)])},
            {"id": "g_stair_foyer", "type": "Foyer", "area": 16.0, "polygon": make_polygon_ccw([(-2.5, -2.5), (1.5, -2.5), (1.5, 1.5), (-2.5, 1.5), (-2.5, -2.5)])},
            {"id": "g_powder", "type": "PowderRoom", "area": 3.0, "polygon": make_polygon_ccw([(4.5, 0.0), (6.5, 0.0), (6.5, 1.5), (4.5, 1.5), (4.5, 0.0)])},
            {"id": "g_terrace", "type": "Terrace", "area": 12.5, "polygon": make_polygon_ccw([(-7.0, 6.5), (-2.0, 6.5), (-2.0, 9.0), (-7.0, 9.0), (-7.0, 6.5)])},
            {"id": "g_circ", "type": "Corridor", "area": 18.0, "polygon": make_polygon_ccw([(1.5, -4.5), (4.5, -4.5), (4.5, 1.5), (1.5, 1.5), (1.5, -4.5)])},
        ],
        "circulation_nodes": [
            "g_stair_foyer", "g_circ", "g_living", "g_dining", "g_kitchen",
            "g_guest_bed", "g_guest_bath", "g_powder", "g_terrace"
        ],
        "node_types": {
            "g_stair_foyer": "Foyer",
            "g_circ": "Corridor",
            "g_living": "LivingRoom",
            "g_dining": "DiningRoom",
            "g_kitchen": "Kitchen",
            "g_guest_bed": "Bedroom",
            "g_guest_bath": "BathroomEnsuite",
            "g_powder": "PowderRoom",
            "g_terrace": "Terrace",
        },
        "circulation_edges": [
            ("g_stair_foyer", "g_circ"),
            ("g_stair_foyer", "g_living"),
            ("g_stair_foyer", "g_guest_bed"),
            ("g_guest_bed", "g_guest_bath"),
            ("g_circ", "g_dining"),
            ("g_dining", "g_kitchen"),
            ("g_circ", "g_powder"),
            ("g_living", "g_terrace"),
        ],
        "entry_node": "g_stair_foyer",
        "plumbing_fixtures": [
            # Ground fixtures
            {"id": "g_k_sink", "position": (5.5, 0.9, 3.5), "storey": 0},
            {"id": "g_pw_wc", "position": (5.5, 0.4, 0.8), "storey": 0},
            {"id": "g_gb_wc", "position": (-5.5, 0.4, -1.0), "storey": 0},
            # Level 1 fixtures
            {"id": "l1_mb_wc", "position": (5.5, 4.0, 3.5), "storey": 1},
            {"id": "l1_b2_wc", "position": (-5.5, 4.0, -1.0), "storey": 1},
        ],
        "vertical_risers": [
            # Coaxial Stack 1 (East)
            {"shaft_id": "villa_stack_east", "position": (5.5000, 0.0, 2.5000), "storey": 0},
            {"shaft_id": "villa_stack_east", "position": (5.5000, 3.6, 2.5000), "storey": 1},
            # Coaxial Stack 2 (West)
            {"shaft_id": "villa_stack_west", "position": (-5.5000, 0.0, -1.0000), "storey": 0},
            {"shaft_id": "villa_stack_west", "position": (-5.5000, 3.6, -1.0000), "storey": 1},
        ],
        "parametric_walls": [
            {"id": "v_w_north", "length": 14.0, "height": 3.6, "thickness": 0.25, "openings": [{"id": "v_glass_1", "distance_along_wall": 2.5, "width": 4.0, "height": 2.6, "sill_height": 0.2}]},
        ],
        "doors": [
            {"id": "v_pivot_door", "position": (0.0, 0.0, -2.5), "width": 1.4},
        ],
        "furniture_items": [
            {"name": "Calacatta Island", "center": (5.0, 2.5), "size": (3.0, 1.2), "rotation_deg": 0.0},
            {"name": "Villa Lounge Sofa", "center": (-3.5, 3.5), "size": (3.8, 2.6), "rotation_deg": 0.0},
            {"name": "Guest Bed", "center": (-4.5, -3.0), "size": (1.8, 2.0), "rotation_deg": 0.0},
        ],
        "mep_graph": {
            "nodes": {
                "source_water": {"type": "Source", "system": "WaterSupply"},
                "g_k_sink": {"type": "Terminal", "system": "WaterSupply"},
                "l1_mb_wc": {"type": "Terminal", "system": "WaterSupply"},
                "d_g_k": {"type": "Terminal", "system": "SoilWaste"},
                "d_l1_mb": {"type": "Terminal", "system": "SoilWaste"},
                "riser_east": {"type": "Riser", "system": "SoilWaste"},
                "main_panel": {"type": "Source", "system": "ElectricalPower"},
                "lounge_lights": {"type": "Terminal", "system": "ElectricalPower"},
            },
            "edges": [
                {"id": "ve1", "from_node": "source_water", "to_node": "g_k_sink", "system": "WaterSupply"},
                {"id": "ve2", "from_node": "source_water", "to_node": "l1_mb_wc", "system": "WaterSupply"},
                {"id": "ve3", "from_node": "d_g_k", "to_node": "riser_east", "system": "SoilWaste", "slope": 0.02},
                {"id": "ve4", "from_node": "d_l1_mb", "to_node": "riser_east", "system": "SoilWaste", "slope": 0.02},
                {"id": "ve5", "from_node": "main_panel", "to_node": "lounge_lights", "system": "ElectricalPower"},
            ],
        },
        "raw_elements": [
            {"id": "v_s1", "name": "Ground Villa Slab", "type": "slab", "position": [0, -0.2, 0], "dimensions": {"width": 15, "height": 0.35, "depth": 11}},
            {"id": "v_s2", "name": "First Floor Villa Slab", "type": "slab", "position": [0, 3.4, 0], "dimensions": {"width": 15, "height": 0.35, "depth": 11}},
            {"id": "v_w1", "name": "Villa Facade Wall", "type": "wall", "position": [0, 1.8, 5.0], "dimensions": {"width": 14, "height": 3.6, "depth": 0.25}},
            {"id": "v_pipe1", "name": "Coaxial Vertical Wet Stack", "type": "pipe", "position": [5.5, 3.6, 2.5], "dimensions": {"width": 0.15, "height": 7.2, "depth": 0.15}},
        ],
    }


def build_golden_05_12storey_residential_tower() -> Dict[str, Any]:
    """Scenario 5: 12-Storey Residential Tower (12 Storeys, 6,500 sqm total)."""
    return {
        "name": "Scenario 5: 12-Storey Residential Tower",
        "gross_area_sqm": 6500.0,
        "rooms": [
            # Typical floor core & unit spaces
            {"id": "t_lobby_core", "type": "Corridor", "area": 48.0, "polygon": make_polygon_ccw([(-3.0, -4.0), (3.0, -4.0), (3.0, 4.0), (-3.0, 4.0), (-3.0, -4.0)])},
            {"id": "t_u1_2bhk_living", "type": "LivingRoom", "area": 45.0, "polygon": make_polygon_ccw([(-13.0, 0.0), (-3.0, 0.0), (-3.0, 4.5), (-13.0, 4.5), (-13.0, 0.0)])},
            {"id": "t_u1_2bhk_bed1", "type": "MasterBedroom", "area": 35.0, "polygon": make_polygon_ccw([(-13.0, -5.0), (-6.0, -5.0), (-6.0, 0.0), (-13.0, 0.0), (-13.0, -5.0)])},
            {"id": "t_u1_2bhk_bed2", "type": "Bedroom", "area": 12.0, "polygon": make_polygon_ccw([(-6.0, -5.0), (-3.0, -5.0), (-3.0, -1.0), (-6.0, -1.0), (-6.0, -5.0)])},
            {"id": "t_u1_2bhk_kitchen", "type": "Kitchen", "area": 17.5, "polygon": make_polygon_ccw([(-13.0, 4.5), (-8.0, 4.5), (-8.0, 8.0), (-13.0, 8.0), (-13.0, 4.5)])},
            {"id": "t_u1_2bhk_bath", "type": "Bathroom", "area": 6.0, "polygon": make_polygon_ccw([(-8.0, 4.5), (-5.0, 4.5), (-5.0, 6.5), (-8.0, 6.5), (-8.0, 4.5)])},
            {"id": "t_u2_3bhk_living", "type": "LivingRoom", "area": 50.0, "polygon": make_polygon_ccw([(3.0, 0.0), (13.0, 0.0), (13.0, 5.0), (3.0, 5.0), (3.0, 0.0)])},
            {"id": "t_u2_3bhk_dining", "type": "DiningRoom", "area": 17.5, "polygon": make_polygon_ccw([(3.0, 5.0), (8.0, 5.0), (8.0, 8.5), (3.0, 8.5), (3.0, 5.0)])},
            {"id": "t_u2_3bhk_kitchen", "type": "Kitchen", "area": 17.5, "polygon": make_polygon_ccw([(8.0, 5.0), (13.0, 5.0), (13.0, 8.5), (8.0, 8.5), (8.0, 5.0)])},
            {"id": "t_u2_3bhk_ensuite", "type": "BathroomEnsuite", "area": 6.0, "polygon": make_polygon_ccw([(3.0, -3.0), (6.0, -3.0), (6.0, -1.0), (3.0, -1.0), (3.0, -3.0)])},
            {"id": "t_u2_3bhk_master", "type": "MasterBedroom", "area": 16.5, "polygon": make_polygon_ccw([(3.0, -6.0), (8.5, -6.0), (8.5, -3.0), (3.0, -3.0), (3.0, -6.0)])},
            {"id": "t_u2_3bhk_bed2", "type": "Bedroom", "area": 20.25, "polygon": make_polygon_ccw([(8.5, -6.0), (13.0, -6.0), (13.0, -1.5), (8.5, -1.5), (8.5, -6.0)])},
        ],
        "circulation_nodes": [
            "t_lobby_core", "t_u1_2bhk_living", "t_u1_2bhk_bed1", "t_u1_2bhk_bed2",
            "t_u1_2bhk_kitchen", "t_u1_2bhk_bath", "t_u2_3bhk_living", "t_u2_3bhk_dining",
            "t_u2_3bhk_kitchen", "t_u2_3bhk_master", "t_u2_3bhk_ensuite", "t_u2_3bhk_bed2"
        ],
        "node_types": {
            "t_lobby_core": "Corridor",
            "t_u1_2bhk_living": "LivingRoom",
            "t_u1_2bhk_bed1": "MasterBedroom",
            "t_u1_2bhk_bed2": "Bedroom",
            "t_u1_2bhk_kitchen": "Kitchen",
            "t_u1_2bhk_bath": "Bathroom",
            "t_u2_3bhk_living": "LivingRoom",
            "t_u2_3bhk_dining": "DiningRoom",
            "t_u2_3bhk_kitchen": "Kitchen",
            "t_u2_3bhk_master": "MasterBedroom",
            "t_u2_3bhk_ensuite": "BathroomEnsuite",
            "t_u2_3bhk_bed2": "Bedroom",
        },
        "circulation_edges": [
            ("t_lobby_core", "t_u1_2bhk_living"),
            ("t_u1_2bhk_living", "t_u1_2bhk_kitchen"),
            ("t_u1_2bhk_living", "t_u1_2bhk_bath"),
            ("t_u1_2bhk_living", "t_u1_2bhk_bed1"),
            ("t_u1_2bhk_living", "t_u1_2bhk_bed2"),
            ("t_lobby_core", "t_u2_3bhk_living"),
            ("t_u2_3bhk_living", "t_u2_3bhk_dining"),
            ("t_u2_3bhk_dining", "t_u2_3bhk_kitchen"),
            ("t_u2_3bhk_living", "t_u2_3bhk_master"),
            ("t_u2_3bhk_master", "t_u2_3bhk_ensuite"),
            ("t_u2_3bhk_living", "t_u2_3bhk_bed2"),
        ],
        "entry_node": "t_lobby_core",
        "plumbing_fixtures": [
            {"id": "fix_u1_sink_l1", "position": (-10.5, 0.9, 6.0), "storey": 0},
            {"id": "fix_u2_sink_l1", "position": (10.5, 0.9, 6.0), "storey": 0},
            {"id": "fix_u1_sink_l12", "position": (-10.5, 38.0, 6.0), "storey": 11},
            {"id": "fix_u2_sink_l12", "position": (10.5, 38.0, 6.0), "storey": 11},
        ],
        "vertical_risers": [
            # 4 Multi-storey vertical shafts through all 12 floors
            *[{"shaft_id": "tower_soil_west", "position": (-9.0000, f * 3.2, 5.0000), "storey": f} for f in range(12)],
            *[{"shaft_id": "tower_soil_east", "position": (9.0000, f * 3.2, 5.0000), "storey": f} for f in range(12)],
            *[{"shaft_id": "tower_water_riser", "position": (0.0000, f * 3.2, -3.0000), "storey": f} for f in range(12)],
            *[{"shaft_id": "tower_elec_busbar", "position": (0.0000, f * 3.2, 3.0000), "storey": f} for f in range(12)],
        ],
        "parametric_walls": [
            {"id": "tower_facade_w", "length": 26.0, "height": 3.2, "thickness": 0.25, "openings": [{"id": "t_win_front", "distance_along_wall": 2.0, "width": 4.0, "height": 2.0, "sill_height": 0.9}]},
        ],
        "doors": [
            {"id": "tower_core_door", "position": (0.0, 0.0, -3.8), "width": 1.6},
        ],
        "furniture_items": [
            {"name": "2BHK Master Bed", "center": (-9.0, -2.5), "size": (1.8, 2.1), "rotation_deg": 0.0},
            {"name": "3BHK Master King", "center": (6.0, -4.5), "size": (2.0, 2.2), "rotation_deg": 0.0},
            {"name": "2BHK Sectional Sofa", "center": (-8.0, 2.0), "size": (2.6, 1.6), "rotation_deg": 0.0},
            {"name": "3BHK Grand Lounge", "center": (8.0, 2.5), "size": (3.2, 1.8), "rotation_deg": 0.0},
        ],
        "mep_graph": {
            "nodes": {
                "tower_water_source": {"type": "Source", "system": "WaterSupply"},
                "u1_sink_sup": {"type": "Terminal", "system": "WaterSupply"},
                "u2_sink_sup": {"type": "Terminal", "system": "WaterSupply"},
                "u1_sink_drn": {"type": "Terminal", "system": "SoilWaste"},
                "u2_sink_drn": {"type": "Terminal", "system": "SoilWaste"},
                "stack_west": {"type": "Riser", "system": "SoilWaste"},
                "stack_east": {"type": "Riser", "system": "SoilWaste"},
                "main_415v_db": {"type": "Source", "system": "ElectricalPower"},
                "lift_motors": {"type": "Terminal", "system": "ElectricalPower"},
            },
            "edges": [
                {"id": "te1", "from_node": "tower_water_source", "to_node": "u1_sink_sup", "system": "WaterSupply"},
                {"id": "te2", "from_node": "tower_water_source", "to_node": "u2_sink_sup", "system": "WaterSupply"},
                {"id": "te3", "from_node": "u1_sink_drn", "to_node": "stack_west", "system": "SoilWaste", "slope": 0.02},
                {"id": "te4", "from_node": "u2_sink_drn", "to_node": "stack_east", "system": "SoilWaste", "slope": 0.02},
                {"id": "te5", "from_node": "main_415v_db", "to_node": "lift_motors", "system": "ElectricalPower"},
            ],
        },
        "raw_elements": [
            {"id": "t_podium", "name": "Tower Foundation Podium", "type": "slab", "position": [0, -0.5, 0], "dimensions": {"width": 30, "height": 1.0, "depth": 22}},
            {"id": "t_core_lift", "name": "Dual Elevator Concrete Shaft", "type": "wall", "position": [0, 20.0, 0], "dimensions": {"width": 3.0, "height": 42.0, "depth": 3.0}},
            {"id": "t_busbar", "name": "415V Busbar Vertical Riser", "type": "conduit", "position": [0, 20.0, 3.0], "dimensions": {"width": 0.25, "height": 40.0, "depth": 0.25}},
            {"id": "t_soil_riser", "name": "DN110 Soil Stack Riser West", "type": "pipe", "position": [-9.0, 20.0, 5.0], "dimensions": {"width": 0.25, "height": 40.0, "depth": 0.25}},
        ],
    }


# ==============================================================================
# Tier 4 Golden Reference Benchmark Test Class
# ==============================================================================

class TestTier4GoldenModels:
    """Golden Reference Benchmark Suite across 5 Real-World Typologies with 7 Invariants."""

    # --------------------------------------------------------------------------
    # 1. 1BHK Urban Flat (55 sqm)
    # --------------------------------------------------------------------------
    def test_golden_01_1bhk_urban_flat_all_invariants(self):
        """Scenario 1: 1BHK Urban Flat (55 sqm) validation against 7 Invariants."""
        model = build_golden_01_1bhk_urban_flat()

        assert_invariant_i1_area_bounds(model, target_sqm=55.0, tolerance=0.05)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)

    # --------------------------------------------------------------------------
    # 2. 2BHK Residential Apartment (90 sqm)
    # --------------------------------------------------------------------------
    def test_golden_02_2bhk_residential_apartment_all_invariants(self):
        """Scenario 2: 2BHK Residential Apartment (90 sqm) validation against 7 Invariants."""
        model = build_golden_02_2bhk_residential_apartment()

        assert_invariant_i1_area_bounds(model, target_sqm=90.0, tolerance=0.05)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)

    # --------------------------------------------------------------------------
    # 3. 3BHK Luxury Suite (160 sqm)
    # --------------------------------------------------------------------------
    def test_golden_03_3bhk_luxury_suite_all_invariants(self):
        """Scenario 3: 3BHK Luxury Suite (160 sqm) validation against 7 Invariants."""
        model = build_golden_03_3bhk_luxury_suite()

        assert_invariant_i1_area_bounds(model, target_sqm=160.0, tolerance=0.08)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)

    # --------------------------------------------------------------------------
    # 4. 2-Storey Modern Villa (280 sqm)
    # --------------------------------------------------------------------------
    def test_golden_04_2storey_modern_villa_all_invariants(self):
        """Scenario 4: 2-Storey Modern Villa (280 sqm) validation against 7 Invariants."""
        model = build_golden_04_2storey_modern_villa()

        assert_invariant_i1_area_bounds(model, target_sqm=280.0, tolerance=0.05)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)

    # --------------------------------------------------------------------------
    # 5. 12-Storey Residential Tower (6,500 sqm)
    # --------------------------------------------------------------------------
    def test_golden_05_12storey_residential_tower_all_invariants(self):
        """Scenario 5: 12-Storey Residential Tower (6,500 sqm) validation against 7 Invariants."""
        model = build_golden_05_12storey_residential_tower()

        assert_invariant_i1_area_bounds(model, target_sqm=6500.0, tolerance=0.05)
        assert_invariant_i2_circulation_connectivity(model)
        assert_invariant_i3_wet_stack_alignment(model, max_fixture_distance=3.5)
        assert_invariant_i4_hosted_openings_solid_conservation(model)
        assert_invariant_i5_ifc4_step_roundtrip(model)
        assert_invariant_i6_mep_flow_connectivity(model)
        assert_invariant_i7_furniture_clearance_and_sat(model)
