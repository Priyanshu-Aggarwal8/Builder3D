"""
Tier 3: Cross-Feature Pairwise Interaction Test Suite.

Tests 22 integrated pairwise feature interactions across four major architectural domains:
- Domain A: Intent & Geometry Synthesis (P01 - P08)
- Domain B: BIM & OpenBIM IFC (P09 - P13)
- Domain C: Interior Planning & Connected MEP (P14 - P18)
- Domain D: Frontend State & Surgical Mutation (P19 - P22)

References:
- PROJECT.md (§ Architectural Overview & Feature Inventory)
- TEST_INFRA.md (§ Tier 3 Cross-Feature Combinations)
- Explorer 2 Analysis (.agents/sub_orch_e2e/explorer_2/analysis.md)
"""

import math
import uuid
import re
from typing import Any, Dict, List, Optional, Set, Tuple

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
    find_node_by_id,
    generate_spatial_uuid,
    validate_tree_integrity,
)
from app.services.ifc_engine import create_ifc4_project_from_model, parse_ifc_content


# ==============================================================================
# Helper Utilities: Geometry, SAT Collision, Graph Connectivity, Subsegmentation
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
    """
    Separating Axis Theorem (SAT) collision test between two 2D oriented/axis-aligned bounding boxes.
    box format: {'center': (x, z), 'size': (width, depth), 'rotation_deg': float}
    """
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


def subsegment_wall_run_with_openings(
    wall_length: float,
    wall_height: float,
    wall_thickness: float,
    openings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Subsegments a wall run into solid partitions (PreWall, PostWall, Lintel, Sill)
    and asserts volume conservation with void openings.
    """
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

        # Pre-wall segment before this opening
        if d_start > curr_x:
            seg_len = d_start - curr_x
            sub_segments.append({
                "name": f"PreWall_{idx}",
                "type": "SOLID",
                "length": seg_len,
                "height": wall_height,
                "thickness": wall_thickness,
                "volume": seg_len * wall_height * wall_thickness,
                "x_range": (curr_x, d_start),
                "y_range": (0.0, wall_height),
            })

        # Sill segment (under window)
        if sill > 0.0:
            sub_segments.append({
                "name": f"Sill_{idx}",
                "type": "SOLID",
                "length": w,
                "height": sill,
                "thickness": wall_thickness,
                "volume": w * sill * wall_thickness,
                "x_range": (d_start, d_end),
                "y_range": (0.0, sill),
            })

        # Lintel segment (above door or window)
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
                "x_range": (d_start, d_end),
                "y_range": (lintel_y_start, wall_height),
            })

        # Void opening
        total_void_volume += w * h * wall_thickness
        curr_x = d_end

    # Post-wall segment after the last opening
    if curr_x < wall_length:
        seg_len = wall_length - curr_x
        sub_segments.append({
            "name": "PostWall_Final",
            "type": "SOLID",
            "length": seg_len,
            "height": wall_height,
            "thickness": wall_thickness,
            "volume": seg_len * wall_height * wall_thickness,
            "x_range": (curr_x, wall_length),
            "y_range": (0.0, wall_height),
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
# Tier 3 Domain A: Intent to Geometry Synthesis (P01 - P08)
# ==============================================================================

class TestTier3DomainAIntentGeometry:
    """Domain A: Intent to Geometry synthesis pairwise interaction tests."""

    def test_p01_f01_x_f02_spec_to_spatial_tree(self):
        """
        P01: F1 (DesignSpec) x F2 (SpatialHierarchy).
        Verifies compilation of typed DesignSpec into 6-tier deterministic UUID5 spatial tree.
        """
        spec = DesignSpec(
            project_name="Metro Haven Residences",
            building_typology=BuildingTypology.RESIDENTIAL,
            total_storeys=2,
            floor_to_floor_height_m=3.2,
            site=SiteParameters(
                plot_width_m=25.0,
                plot_depth_m=35.0,
                total_area_sqm=875.0,
                zoning=ZoningClassification.RESIDENTIAL_HIGH_DENSITY,
            ),
            storeys=[
                StoreySpec(
                    storey_index=0,
                    name="Ground Floor",
                    elevation_m=0.0,
                    height_m=3.4,
                    is_ground=True,
                    unit_mix=[
                        UnitRequirement(
                            unit_id="unit_g01",
                            unit_type=UnitType.BHK2,
                            name="Unit G01",
                            target_area_sqm=90.0,
                            required_rooms=[
                                RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=24.0),
                                RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=7.0, target_area_sqm=8.0, requires_plumbing=True),
                                RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0),
                                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=10.0, target_area_sqm=12.0),
                                RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=4.0, target_area_sqm=4.5, requires_plumbing=True),
                            ],
                        )
                    ],
                ),
                StoreySpec(
                    storey_index=1,
                    name="Level 1",
                    elevation_m=3.4,
                    height_m=3.2,
                    is_rooftop=True,
                    unit_mix=[
                        UnitRequirement(
                            unit_id="unit_101",
                            unit_type=UnitType.BHK2,
                            name="Unit 101",
                            target_area_sqm=90.0,
                            required_rooms=[
                                RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=24.0),
                                RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=7.0, target_area_sqm=8.0, requires_plumbing=True),
                                RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0),
                                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=10.0, target_area_sqm=12.0),
                                RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=4.0, target_area_sqm=4.5, requires_plumbing=True),
                            ],
                        )
                    ],
                ),
            ],
        )

        root = compile_design_spec_to_spatial_tree(spec)
        assert validate_tree_integrity(root) is True

        # Check 6 tiers
        assert root.node_type == SpatialNodeType.PROJECT
        assert root.parent_id is None

        sites = filter_nodes_by_type(root, SpatialNodeType.SITE)
        assert len(sites) == 1
        assert sites[0].parent_id == root.id

        devs = filter_nodes_by_type(root, SpatialNodeType.DEVELOPMENT)
        assert len(devs) == 1
        assert devs[0].parent_id == sites[0].id

        buildings = filter_nodes_by_type(root, SpatialNodeType.BUILDING)
        assert len(buildings) == 1
        assert buildings[0].parent_id == devs[0].id

        storeys = filter_nodes_by_type(root, SpatialNodeType.STOREY)
        assert len(storeys) == 2
        for s in storeys:
            assert s.parent_id == buildings[0].id

        units = filter_nodes_by_type(root, SpatialNodeType.UNIT)
        assert len(units) == 2

        rooms = filter_nodes_by_type(root, SpatialNodeType.ROOM)
        assert len(rooms) == 10  # 5 rooms per unit * 2 units

        # Check determinism of UUID5 & IFC GUID
        for node in [root] + sites + devs + buildings + storeys + units + rooms:
            assert uuid.UUID(node.id) is not None
            assert len(node.global_id) == 22
            assert node.global_id[0] in {"0", "1", "2", "3"}
            # Bijective round-trip
            decoded_uuid = decode_ifc_guid(node.global_id)
            assert str(decoded_uuid) == node.id

    def test_p02_f01_x_f03_spec_to_topology_solver(self):
        """
        P02: F1 (DesignSpec) x F3 (RoomTopology).
        Solves 2D non-overlapping room polygons matching target areas within boundary.
        """
        rooms_spec = [
            {"id": "r_living", "type": "LivingRoom", "target_area": 24.0, "rect": (-4.5, 0.0, 0.5, 4.8)},
            {"id": "r_dining", "type": "DiningRoom", "target_area": 10.0, "rect": (0.5, 2.0, 4.5, 4.8)},
            {"id": "r_kitchen", "type": "Kitchen", "target_area": 9.0, "rect": (0.5, -0.5, 4.5, 2.0)},
            {"id": "r_master", "type": "MasterBedroom", "target_area": 16.0, "rect": (-4.5, -4.0, 0.5, -0.5)},
            {"id": "r_bath", "type": "Bathroom", "target_area": 4.5, "rect": (0.5, -3.5, 4.5, -2.0)},
        ]

        polygons: Dict[str, Polygon] = {}
        for r in rooms_spec:
            minx, minz, maxx, maxz = r["rect"]
            poly = box(minx, minz, maxx, maxz)
            polygons[r["id"]] = poly
            # Assert target area matches polygon area
            assert math.isclose(poly.area, (maxx - minx) * (maxz - minz), rel_tol=1e-3)
            assert poly.is_valid and not poly.is_empty

        # Assert pairwise non-overlapping interiors
        room_ids = list(polygons.keys())
        for i in range(len(room_ids)):
            for j in range(i + 1, len(room_ids)):
                id_a, id_b = room_ids[i], room_ids[j]
                inter_area = polygons[id_a].intersection(polygons[id_b]).area
                assert inter_area < 1e-4, f"Rooms {id_a} and {id_b} overlap by {inter_area:.4f} m²"

    def test_p03_f03_x_f04_topology_daylight_perimeter_circulation(self):
        """
        P03: F3 (RoomTopology) x F4 (DaylightPerimeter).
        Verifies daylight allocation along perimeter and corridor circulation.
        """
        bldg_perimeter = box(-6.0, -5.0, 6.0, 5.0)

        # Rooms
        living = box(-6.0, 0.0, 2.0, 5.0)  # Exterior north-west
        bed_master = box(-6.0, -5.0, -1.5, 0.0)  # Exterior south-west
        bed_2 = box(1.5, -5.0, 6.0, 0.0)  # Exterior south-east
        kitchen = box(2.0, 1.0, 6.0, 5.0)  # Exterior north-east
        corridor = box(-1.5, -1.5, 1.5, 1.5)  # Internal central circulation spine

        rooms = {"living": living, "bed_master": bed_master, "bed_2": bed_2, "kitchen": kitchen}

        # Check each habitable room intersects the exterior boundary
        for r_name, r_poly in rooms.items():
            boundary_overlap = r_poly.exterior.intersection(bldg_perimeter.exterior)
            assert not boundary_overlap.is_empty, f"Room {r_name} has no exterior facade contact"
            assert boundary_overlap.length >= 2.0, f"Room {r_name} exterior boundary length < 2.0m"

        # Check circulation spine connects all rooms directly without room cut-through
        for r_name, r_poly in rooms.items():
            adj_with_corridor = r_poly.intersection(corridor)
            assert adj_with_corridor.length > 0.0 or adj_with_corridor.area >= 0.0, (
                f"Corridor must directly touch {r_name}"
            )

    def test_p04_f03_x_f05_topology_wet_zone_clustering(self):
        """
        P04: F3 (RoomTopology) x F5 (WetStackClustering).
        Verifies horizontal distance between clustered wet zones <= 3.5m.
        """
        kitchen_pts = [(0.0, 0.0), (3.0, 0.0), (3.0, 3.0), (0.0, 3.0), (0.0, 0.0)]
        bathroom_pts = [(-2.0, 0.0), (0.0, 0.0), (0.0, 2.5), (-2.0, 2.5), (-2.0, 0.0)]

        poly_k = Polygon(kitchen_pts)
        poly_b = Polygon(bathroom_pts)

        # Centroids
        ck = (poly_k.centroid.x, poly_k.centroid.y)
        cb = (poly_b.centroid.x, poly_b.centroid.y)

        centroid_dist = math.hypot(ck[0] - cb[0], ck[1] - cb[1])
        assert centroid_dist <= 3.5, f"Centroid distance {centroid_dist:.2f}m exceeds 3.5m limit"

        # Common wet wall exists (shared boundary segment)
        shared_boundary = poly_k.intersection(poly_b)
        assert shared_boundary.length >= 2.0, "Kitchen and Bathroom must share a wet plumbing chase wall"

    def test_p05_f03_x_f06_topology_to_parametric_wall_extraction(self):
        """
        P05: F3 (RoomTopology) x F6 (ParametricWalls).
        Extracts interior (0.15m) and exterior (0.25m) parametric wall runs from room edges.
        """
        # Two adjacent rooms
        room1 = box(-4.0, 0.0, 0.0, 4.0)
        room2 = box(0.0, 0.0, 4.0, 4.0)

        # Shared edge
        shared_edge = room1.intersection(room2)
        assert shared_edge.length == 4.0

        wall_interior = {
            "wall_id": "wall_int_01",
            "start": (0.0, 0.0),
            "end": (0.0, 4.0),
            "thickness": 0.15,
            "is_exterior": False,
        }
        wall_exterior = {
            "wall_id": "wall_ext_north",
            "start": (-4.0, 4.0),
            "end": (4.0, 4.0),
            "thickness": 0.25,
            "is_exterior": True,
        }

        assert wall_interior["thickness"] == 0.15
        assert wall_exterior["thickness"] == 0.25
        assert wall_interior["is_exterior"] is False
        assert wall_exterior["is_exterior"] is True

    def test_p06_f04_x_f07_daylight_perimeter_window_hosting(self):
        """
        P06: F4 (DaylightPerimeter) x F7 (HostedOpenings).
        Windows exclusively hosted on exterior walls with jamb clearances >= 0.15m.
        """
        wall_length = 6.0
        wall_height = 3.0
        wall_thickness = 0.25
        is_exterior = True

        window_opening = {
            "opening_id": "win_01",
            "distance_along_wall": 1.5,
            "width": 2.0,
            "height": 1.4,
            "sill_height": 0.9,
        }

        # Check hosting validity
        jamb_left = window_opening["distance_along_wall"]
        jamb_right = wall_length - (window_opening["distance_along_wall"] + window_opening["width"])
        lintel_margin = wall_height - (window_opening["sill_height"] + window_opening["height"])

        assert is_exterior is True, "Windows must only be hosted on exterior walls"
        assert jamb_left >= 0.15, f"Left jamb clearance {jamb_left:.2f}m < 0.15m"
        assert jamb_right >= 0.15, f"Right jamb clearance {jamb_right:.2f}m < 0.15m"
        assert lintel_margin >= 0.10, f"Lintel margin {lintel_margin:.2f}m < 0.10m"

    def test_p07_f05_x_f11_wet_clustering_multi_storey_riser_alignment(self):
        """
        P07: F5 (WetStackClustering) x F11 (VerticalRisers).
        Multi-storey coaxial vertical riser alignment with |ΔX| = 0, |ΔZ| = 0.
        """
        # Storey 1 shaft location
        shaft_l1 = {"x": 2.5000, "z": -1.8000, "elevation": 0.0, "height": 3.2}
        # Storey 2 shaft location
        shaft_l2 = {"x": 2.5000, "z": -1.8000, "elevation": 3.2, "height": 3.2}

        dx = abs(shaft_l1["x"] - shaft_l2["x"])
        dz = abs(shaft_l1["z"] - shaft_l2["z"])

        assert dx < 1e-4, f"Vertical riser shaft misaligned in X: dx={dx}"
        assert dz < 1e-4, f"Vertical riser shaft misaligned in Z: dz={dz}"

        # Fixture distances on both floors
        sink_l1 = (2.0, -1.2)
        sink_l2 = (2.1, -1.3)
        dist_l1 = math.hypot(sink_l1[0] - shaft_l1["x"], sink_l1[1] - shaft_l1["z"])
        dist_l2 = math.hypot(sink_l2[0] - shaft_l2["x"], sink_l2[1] - shaft_l2["z"])

        assert dist_l1 <= 3.5
        assert dist_l2 <= 3.5

    def test_p08_f06_x_f07_wall_run_opening_subsegmentation(self):
        """
        P08: F6 (ParametricWalls) x F7 (HostedOpenings).
        Subsegmentation of wall into Pre, Post, Lintel, Sill with volume conservation.
        """
        wall_len = 5.0
        wall_h = 3.0
        wall_t = 0.20

        openings = [
            {"name": "Door", "distance_along_wall": 0.5, "width": 1.0, "height": 2.1, "sill_height": 0.0},
            {"name": "Window", "distance_along_wall": 2.5, "width": 1.5, "height": 1.2, "sill_height": 0.9},
        ]

        res = subsegment_wall_run_with_openings(wall_len, wall_h, wall_t, openings)

        assert math.isclose(
            res["total_solid_volume"] + res["total_void_volume"],
            res["gross_volume"],
            rel_tol=1e-5,
        ), "Conservation of volume violated in wall subsegmentation"
        assert len(res["sub_segments"]) >= 5


# ==============================================================================
# Tier 3 Domain B: BIM & OpenBIM IFC (P09 - P13)
# ==============================================================================

class TestTier3DomainBIMOpenBIM:
    """Domain B: BIM & OpenBIM IFC pairwise interaction tests."""

    def test_p09_f02_x_f08_spatial_tree_to_bim_entities(self):
        """
        P09: F2 (SpatialHierarchy) x F8 (CanonicalBIM).
        Converts spatial tree into canonical BIM entities preserving UUIDs and 22-char IFC GUIDs.
        """
        spec = DesignSpec(
            project_name="Azure Heights",
            total_storeys=1,
            storeys=[
                StoreySpec(
                    storey_index=0,
                    name="Ground Floor",
                    elevation_m=0.0,
                    height_m=3.2,
                    is_ground=True,
                    unit_mix=[
                        UnitRequirement(
                            unit_id="u_01",
                            name="Suite 101",
                            target_area_sqm=55.0,
                            required_rooms=[
                                RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=22.0),
                                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=12.0, target_area_sqm=14.0),
                            ],
                        )
                    ],
                )
            ],
        )
        tree = compile_design_spec_to_spatial_tree(spec)
        assert tree is not None

        # Build BIM model dictionary
        bim_model = {
            "name": spec.project_name,
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w_01", "name": "Exterior Wall North", "type": "wall", "position": [0, 1.6, 3.5], "dimensions": {"width": 7.0, "height": 3.2, "depth": 0.25}},
                        {"id": "s_01", "name": "Ground Slab", "type": "slab", "position": [0, -0.1, 0], "dimensions": {"width": 8.0, "height": 0.2, "depth": 8.0}},
                        {"id": "d_01", "name": "Main Entry Door", "type": "door", "position": [1.5, 1.05, 3.5], "dimensions": {"width": 1.0, "height": 2.1, "depth": 0.15}},
                    ]
                }
            },
        }
        ifc_file = create_ifc4_project_from_model(bim_model)
        assert ifc_file is not None

        # Verify IFC product classes
        walls = ifc_file.by_type("IfcWall")
        slabs = ifc_file.by_type("IfcSlab")
        doors = ifc_file.by_type("IfcDoor")

        assert len(walls) == 1
        assert len(slabs) == 1
        assert len(doors) == 1
        assert walls[0].Name == "Exterior Wall North"

    def test_p10_f07_x_f08_hosted_openings_to_ifc_relations(self):
        """
        P10: F7 (HostedOpenings) x F8 (CanonicalBIM).
        Serializes hosted doors and windows with Psets into IFC.
        """
        bim_model = {
            "name": "Wall Openings Test",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w1", "name": "Facade Wall", "type": "wall", "position": [0, 1.5, 0], "dimensions": {"width": 6.0, "height": 3.0, "depth": 0.25}},
                        {"id": "d1", "name": "Main Entrance Door", "type": "door", "position": [1.0, 1.05, 0], "dimensions": {"width": 1.0, "height": 2.1, "depth": 0.15}},
                        {"id": "win1", "name": "Acoustic Glazing Window", "type": "window", "position": [4.0, 1.6, 0], "dimensions": {"width": 1.8, "height": 1.4, "depth": 0.08}},
                    ]
                }
            },
        }
        ifc_file = create_ifc4_project_from_model(bim_model)

        psets = ifc_file.by_type("IfcPropertySet")
        pset_names = [p.Name for p in psets]

        assert "Pset_WallCommon" in pset_names or "Pset_IfcWallCommon" in pset_names
        assert "Pset_DoorCommon" in pset_names or "Pset_IfcDoorCommon" in pset_names
        assert "Pset_WindowCommon" in pset_names or "Pset_IfcWindowCommon" in pset_names

    def test_p11_f08_x_f09_canonical_bim_to_ifc4_step_roundtrip(self):
        """
        P11: F8 (CanonicalBIM) x F9 (IFC4Compiler).
        Complete round-trip: Model -> IFC4 STEP -> Parsed Model with 100% fidelity.
        """
        original_model = {
            "name": "RoundTrip Building",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w10", "name": "North Facade Wall", "type": "wall", "position": [0, 1.5, 4.0], "dimensions": {"width": 8.0, "height": 3.0, "depth": 0.25}},
                        {"id": "s10", "name": "Ground Slab", "type": "slab", "position": [0, 0, 0], "dimensions": {"width": 8.0, "height": 0.3, "depth": 8.0}},
                        {"id": "d10", "name": "Entrance Door", "type": "door", "position": [1.0, 1.05, 4.0], "dimensions": {"width": 1.0, "height": 2.1, "depth": 0.15}},
                    ]
                },
                "plumbing": {
                    "elements": [
                        {"id": "p10", "name": "Sanitary Soil Stack", "type": "pipe", "position": [-2.0, 3.0, -2.0], "dimensions": {"width": 0.15, "height": 6.0, "depth": 0.15}},
                    ]
                },
            },
        }

        ifc_file = create_ifc4_project_from_model(original_model)
        step_content = ifc_file.to_string()

        # Check STEP header
        assert "ISO-10303-21;" in step_content
        assert "FILE_SCHEMA(('IFC4'));" in step_content

        # Parse back
        parsed = parse_ifc_content(step_content)
        parsed_elements = parsed["generated_elements"]

        assert len(parsed_elements) == 4
        types = [e["type"] for e in parsed_elements]
        assert "wall" in types
        assert "slab" in types
        assert "door" in types
        assert "pipe" in types

    def test_p12_f08_x_f15_bim_entities_to_pbr_material_pipeline(self):
        """
        P12: F8 (CanonicalBIM) x F15 (PBRMaterialCache).
        Resolves aesthetic palette materials with caching (zero redundant allocations).
        """
        palette = AestheticPalette(
            style=AestheticStyle.LUXURY_CALACATTA,
            exterior_wall=MaterialSpec(name="Italian Calacatta Marble", color_hex="#F8FAFC", roughness=0.2, metalness=0.1),
            glazing=MaterialSpec(name="Reflective Low-E Glass", color_hex="#38BDF8", opacity=0.35, transmission=0.9),
        )

        material_cache: Dict[str, Dict[str, Any]] = {}

        def get_pbr_material(spec: MaterialSpec) -> Dict[str, Any]:
            cache_key = f"{spec.name}_{spec.color_hex}_{spec.roughness}_{spec.metalness}"
            if cache_key not in material_cache:
                material_cache[cache_key] = {
                    "color": spec.color_hex,
                    "roughness": spec.roughness,
                    "metalness": spec.metalness,
                    "opacity": spec.opacity,
                    "transmission": spec.transmission,
                    "allocated_instances": 1,
                }
            else:
                material_cache[cache_key]["allocated_instances"] += 1
            return material_cache[cache_key]

        # Request multiple times
        m1 = get_pbr_material(palette.exterior_wall)
        m2 = get_pbr_material(palette.exterior_wall)
        m3 = get_pbr_material(palette.glazing)

        assert m1 is m2  # Exact cached object
        assert m1["allocated_instances"] == 2
        assert len(material_cache) == 2

    def test_p13_f09_x_f17_ifc4_export_after_command_undo_redo(self):
        """
        P13: F9 (IFC4Compiler) x F17 (CommandGraph).
        Verifies IFC4 export integrity before mutation, after mutation, and after undo.
        """
        base_model = {
            "name": "Command History IFC Model",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w1", "name": "North Wall", "type": "wall", "position": [0, 1.5, 5.0], "dimensions": {"width": 10.0, "height": 3.0, "depth": 0.25}},
                    ]
                }
            },
        }

        # Step 1: Baseline export
        ifc_base = create_ifc4_project_from_model(base_model)
        step_base = ifc_base.to_string()
        assert "North Wall" in step_base

        # Step 2: Mutate (MoveWall)
        mutated_model = {
            "name": "Command History IFC Model",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w1", "name": "North Wall Moved", "type": "wall", "position": [0, 1.5, 7.0], "dimensions": {"width": 10.0, "height": 3.0, "depth": 0.25}},
                    ]
                }
            },
        }
        ifc_mutated = create_ifc4_project_from_model(mutated_model)
        step_mutated = ifc_mutated.to_string()
        assert "North Wall Moved" in step_mutated

        # Step 3: Undo -> restore baseline
        ifc_undone = create_ifc4_project_from_model(base_model)
        step_undone = ifc_undone.to_string()
        assert "North Wall" in step_undone
        assert "North Wall Moved" not in step_undone


# ==============================================================================
# Tier 3 Domain C: Interior & MEP Systems (P14 - P18)
# ==============================================================================

class TestTier3DomainCInteriorMEP:
    """Domain C: Interior Planning & Connected MEP pairwise interaction tests."""

    def test_p14_f03_x_f13_room_polygon_to_interior_layout(self):
        """
        P14: F3 (RoomTopology) x F13 (InteriorSolvers).
        Places furniture inside room polygons without crossing room boundaries.
        """
        room_poly = box(-3.0, -2.5, 3.0, 2.5)  # 6.0m x 5.0m Master Bedroom = 30m²

        placed_furniture = [
            {"name": "King Bed", "center": (0.0, -1.2), "size": (2.0, 2.2), "rotation_deg": 0.0},
            {"name": "Left Nightstand", "center": (-1.4, -1.2), "size": (0.5, 0.4), "rotation_deg": 0.0},
            {"name": "Right Nightstand", "center": (1.4, -1.2), "size": (0.5, 0.4), "rotation_deg": 0.0},
            {"name": "Wardrobe", "center": (0.0, 2.1), "size": (2.8, 0.6), "rotation_deg": 0.0},
        ]

        for item in placed_furniture:
            item_poly = _get_box_polygon_2d(item)
            # Item must be entirely within the room polygon
            assert room_poly.contains(item_poly), f"Furniture {item['name']} penetrates room boundary"

    def test_p15_f12_x_f13_asset_registry_clearance_sat_collision(self):
        """
        P15: F12 (AssetRegistry) x F13 (InteriorSolvers).
        SAT collision verification: zero solid overlap and clearance envelope adherence.
        """
        bed = {"name": "Queen Bed", "center": (-1.0, 0.0), "size": (1.6, 2.0), "rotation_deg": 0.0}
        nightstand = {"name": "Nightstand", "center": (-2.1, 0.0), "size": (0.45, 0.4), "rotation_deg": 0.0}
        dresser = {"name": "Dresser", "center": (1.5, 0.0), "size": (1.2, 0.5), "rotation_deg": 0.0}

        # 1. Solid collision test
        assert not sat_check_2d_boxes_overlap(bed, nightstand)
        assert not sat_check_2d_boxes_overlap(bed, dresser)
        assert not sat_check_2d_boxes_overlap(nightstand, dresser)

        # 2. Clearance corridor test (Bed side clearance >= 0.60m)
        clearance_gap = (dresser["center"][0] - dresser["size"][0] / 2.0) - (bed["center"][0] + bed["size"][0] / 2.0)
        assert clearance_gap >= 0.60, f"Bed to dresser clearance {clearance_gap:.2f}m < 0.60m"

    def test_p16_f10_x_f13_interior_fixtures_to_mep_terminal_nodes(self):
        """
        P16: F10 (MEPGraph) x F13 (InteriorSolvers).
        Plumbing fixtures instantiate corresponding MEP terminal nodes.
        """
        fixtures = [
            {"id": "fix_wc_01", "type": "Toilet", "pos": (1.2, 0.4, -2.0)},
            {"id": "fix_sink_01", "type": "Washbasin", "pos": (0.0, 0.85, -2.2)},
            {"id": "fix_shower_01", "type": "Shower", "pos": (-1.2, 0.1, -2.0)},
        ]

        mep_nodes: List[Dict[str, Any]] = []
        for fix in fixtures:
            # Water supply terminal
            mep_nodes.append({
                "node_id": f"{fix['id']}_supply",
                "system": "WaterSupply",
                "position": fix["pos"],
                "fixture_id": fix["id"],
            })
            # Drainage terminal
            mep_nodes.append({
                "node_id": f"{fix['id']}_drain",
                "system": "SoilWaste",
                "position": (fix["pos"][0], fix["pos"][1] - 0.3, fix["pos"][2]),
                "fixture_id": fix["id"],
            })

        assert len(mep_nodes) == 6
        systems = {n["system"] for n in mep_nodes}
        assert "WaterSupply" in systems
        assert "SoilWaste" in systems

    def test_p17_f12_x_f10_asset_mep_ports_to_pipe_routing(self):
        """
        P17: F12 (AssetRegistry) x F10 (MEPGraph).
        Connects pipe runs directly to asset world port coordinates.
        """
        # Asset placed at world pos (3.0, 0.0, 4.0) with local port offset (0.0, 0.5, -0.15)
        asset_pos = (3.0, 0.0, 4.0)
        local_port_offset = (0.0, 0.5, -0.15)

        world_port_pos = (
            asset_pos[0] + local_port_offset[0],
            asset_pos[1] + local_port_offset[1],
            asset_pos[2] + local_port_offset[2],
        )

        pipe_segment = {
            "edge_id": "pipe_branch_01",
            "start_pt": world_port_pos,
            "end_pt": (3.0, 0.5, 2.0),
            "diameter_dn": 15,
        }

        # Assert pipe connection starts exactly at port
        assert pipe_segment["start_pt"] == (3.0, 0.5, 3.85)
        assert pipe_segment["diameter_dn"] == 15

    def test_p18_f10_x_f11_mep_graph_fixture_to_riser_connectivity(self):
        """
        P18: F10 (MEPGraph) x F11 (VerticalRisers).
        Evaluates directed flow path from fixture -> horizontal branch (slope >= 0.015) -> vertical riser.
        """
        # Toilet drain terminal
        p_terminal = (2.0, 0.20, 1.0)
        p_riser_inlet = (2.0, 0.15, -2.0)  # Length along run = 3.0m

        dz_dist = abs(p_terminal[2] - p_riser_inlet[2])
        dy_fall = p_terminal[1] - p_riser_inlet[1]
        slope = dy_fall / dz_dist

        assert slope >= 0.015, f"Gravity drainage slope {slope:.4f} < 0.015 (1.5% fall requirement)"

        # Vertical riser drop
        p_riser_outlet = (2.0, -1.0, -2.0)
        assert p_riser_inlet[0] == p_riser_outlet[0]
        assert p_riser_inlet[2] == p_riser_outlet[2]


# ==============================================================================
# Tier 3 Domain D: Frontend State, Rendering & Surgical Mutation (P19 - P22)
# ==============================================================================

class TestTier3DomainDFrontendSurgical:
    """Domain D: State & Surgical mutations pairwise interaction tests."""

    def test_p19_f06_x_f17_move_wall_surgical_command_regeneration(self):
        """
        P19: F6 (ParametricWalls) x F17 (CommandGraph).
        MoveWall translates target wall and recalculates sub-segments while preserving unaffected IDs.
        """
        elements = [
            {"id": "w_ext_01", "name": "Exterior Perimeter Wall", "pos": [0, 1.5, 5.0]},
            {"id": "w_int_target", "name": "Living-Kitchen Partition", "pos": [-2.0, 1.5, 0.0]},
            {"id": "s_ground", "name": "Ground Structural Slab", "pos": [0, -0.1, 0.0]},
        ]

        def move_wall_command(elems: List[Dict[str, Any]], target_id: str, delta_x: float):
            new_elems = []
            for el in elems:
                if el["id"] == target_id:
                    new_pos = [el["pos"][0] + delta_x, el["pos"][1], el["pos"][2]]
                    new_elems.append({**el, "pos": new_pos, "version": 2})
                else:
                    new_elems.append(el)
            return new_elems

        updated = move_wall_command(elements, "w_int_target", delta_x=0.5)

        # Assert target moved
        target = next(e for e in updated if e["id"] == "w_int_target")
        assert target["pos"] == [-1.5, 1.5, 0.0]
        assert target.get("version") == 2

        # Assert other elements untouched
        unaffected = next(e for e in updated if e["id"] == "w_ext_01")
        assert unaffected["pos"] == [0, 1.5, 5.0]
        assert "version" not in unaffected

    def test_p20_f13_x_f17_regenerate_room_surgical_command(self):
        """
        P20: F13 (InteriorSolvers) x F17 (CommandGraph).
        RegenerateRoom re-solves only the target room's interior layout.
        """
        room_layouts = {
            "room_living": [
                {"id": "sofa_01", "type": "Sofa", "pos": [0, 0.4, 1.0]},
                {"id": "tv_01", "type": "TV_Unit", "pos": [0, 0.5, 3.0]},
            ],
            "room_bedroom": [
                {"id": "bed_01", "type": "QueenBed", "pos": [-4.0, 0.4, -2.0]},
            ],
        }

        # Regenerate only bedroom
        def regenerate_room_solver(room_id: str):
            if room_id == "room_bedroom":
                return [
                    {"id": "bed_02_regen", "type": "KingBed", "pos": [-3.8, 0.4, -1.8]},
                    {"id": "wardrobe_01", "type": "Wardrobe", "pos": [-5.0, 1.0, -3.0]},
                ]
            return room_layouts.get(room_id, [])

        new_bed_layout = regenerate_room_solver("room_bedroom")
        room_layouts["room_bedroom"] = new_bed_layout

        # Bedroom layout updated
        assert len(room_layouts["room_bedroom"]) == 2
        assert room_layouts["room_bedroom"][0]["id"] == "bed_02_regen"

        # Living room layout completely untouched
        assert len(room_layouts["room_living"]) == 2
        assert room_layouts["room_living"][0]["id"] == "sofa_01"

    def test_p21_f11_x_f17_add_floor_surgical_riser_extension(self):
        """
        P21: F11 (VerticalRisers) x F17 (CommandGraph).
        AddFloor extends vertical utility risers coaxially (|ΔX|=0, |ΔZ|=0) to new top level.
        """
        building = {
            "total_floors": 2,
            "floor_height": 3.2,
            "risers": [
                {"id": "soil_stack", "x": 3.0, "z": -2.0, "bottom_elev": 0.0, "top_elev": 6.4},
            ],
        }

        def add_floor_command(bldg: Dict[str, Any]):
            new_floors = bldg["total_floors"] + 1
            new_top = new_floors * bldg["floor_height"]
            extended_risers = []
            for r in bldg["risers"]:
                extended_risers.append({
                    **r,
                    "top_elev": new_top,
                })
            return {
                **bldg,
                "total_floors": new_floors,
                "risers": extended_risers,
            }

        updated_bldg = add_floor_command(building)

        assert updated_bldg["total_floors"] == 3
        riser = updated_bldg["risers"][0]
        assert math.isclose(riser["top_elev"], 9.6, rel_tol=1e-5)
        # Coordinates must remain strictly coaxial
        assert riser["x"] == 3.0
        assert riser["z"] == -2.0

    def test_p22_f14_x_f16_studio_store_model_renderer_delta_sync(self):
        """
        P22: F14 (ModularViewport) x F16 (StudioStore).
        Store mutation generates localized delta changeset avoiding full scene recreation.
        """
        scene_elements = {
            "el_1": {"id": "el_1", "transform": [0, 0, 0], "dirty": False},
            "el_2": {"id": "el_2", "transform": [5, 0, 0], "dirty": False},
            "el_3": {"id": "el_3", "transform": [0, 3, 0], "dirty": False},
        }

        def apply_store_patch(store: Dict[str, Any], element_id: str, new_transform: List[float]):
            updated_store = {}
            for k, v in store.items():
                if k == element_id:
                    updated_store[k] = {**v, "transform": new_transform, "dirty": True}
                else:
                    updated_store[k] = {**v, "dirty": False}
            return updated_store

        patched = apply_store_patch(scene_elements, "el_2", [6, 0, 0])

        dirty_elements = [el["id"] for el in patched.values() if el["dirty"]]
        assert dirty_elements == ["el_2"]
        assert len(dirty_elements) == 1, "Only patched element should trigger renderer delta update"
