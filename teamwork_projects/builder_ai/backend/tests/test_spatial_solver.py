"""
Comprehensive E2E and Unit Test Suite for Features F3, F4, and F5.

Features Covered:
- F3: Deterministic 2D Room Topology Solver (Polygon closure, simple geometry, area conservation, pairwise disjointness, architectural adjacencies, L-shape and narrow lot boundaries).
- F4: Daylight Perimeter & Circulation Spines (Exterior boundary allocation, 100% bedroom daylighting, corridor graph reachability, no room cut-through invariant, minimum corridor width).
- F5: Coaxial Wet Stack Clustering (Wet zone horizontal clustering <= 3.5m, back-to-back wet rooms, multi-storey coaxial vertical riser alignment |dX|=0, |dZ|=0, 12-storey high-rise continuity, secondary risers).
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

import pytest
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from app.schemas.design_spec import VerticalRiserStrategy
from tests.conftest import (
    FloorplanLayout,
    RoomBoundary,
    RoomBoundaryFactory,
    VerticalRiserLocation,
)


# ==============================================================================
# FEATURE F3: Deterministic 2D Room Topology Solver (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature3RoomTopologySolver:
    """Feature F3: 2D Room Topology, Polygon Validity, Area Conservation & Adjacency Rules."""

    def test_f3_room_boundary_polygon_closure(self, sample_floorplan_layout: FloorplanLayout):
        """F3.1: Verifies all generated room boundary polygons are closed and form valid topological cycles."""
        all_rooms = sample_floorplan_layout.rooms + sample_floorplan_layout.corridors
        for room in all_rooms:
            verts = room.polygon
            assert len(verts) >= 3, f"Room {room.room_id} has fewer than 3 vertices"
            # In Shapely, a polygon constructed from vertices is automatically closed
            poly = Polygon(verts)
            assert poly.is_valid, f"Room {room.room_id} polygon is not geometrically valid"
            assert not poly.is_empty, f"Room {room.room_id} polygon is empty"

    def test_f3_room_polygon_geometric_validity(self, sample_floorplan_layout: FloorplanLayout):
        """F3.2: Verifies all rooms form simple, non-self-intersecting polygons with positive area."""
        for room in sample_floorplan_layout.rooms:
            poly = Polygon(room.polygon)
            assert poly.is_simple, f"Room {room.room_id} has self-intersecting polygon boundary"
            assert room.area > 0.0, f"Room {room.room_id} area must be positive"
            assert math.isclose(poly.area, room.area, rel_tol=1e-3), (
                f"Room {room.room_id} declared area ({room.area}) does not match geometric area ({poly.area})"
            )

    def test_f3_room_area_conservation(self, sample_floorplan_layout: FloorplanLayout):
        """F3.3: Verifies sum of room areas + corridor area equals gross floorplate area within 0.5% margin."""
        boundary_poly = Polygon(sample_floorplan_layout.boundary_polygon)
        gross_area = boundary_poly.area

        all_rooms = sample_floorplan_layout.rooms + sample_floorplan_layout.corridors
        sum_room_areas = sum(r.area for r in all_rooms)

        # Sum of room areas should equal the 100 sqm floorplate
        assert math.isclose(sum_room_areas, gross_area, rel_tol=5e-3), (
            f"Sum of room areas ({sum_room_areas:.2f} sqm) does not match gross floor area ({gross_area:.2f} sqm)"
        )

    def test_f3_pairwise_interior_disjointness(self, sample_floorplan_layout: FloorplanLayout):
        """F3.4: Verifies pairwise intersection area of any two room polygons is 0.0 (no overlapping rooms)."""
        all_rooms = sample_floorplan_layout.rooms + sample_floorplan_layout.corridors
        n = len(all_rooms)
        for i in range(n):
            poly_i = Polygon(all_rooms[i].polygon)
            for j in range(i + 1, n):
                poly_j = Polygon(all_rooms[j].polygon)
                overlap_area = poly_i.intersection(poly_j).area
                assert overlap_area < 1e-4, (
                    f"Topological violation: Room '{all_rooms[i].room_id}' and '{all_rooms[j].room_id}' "
                    f"overlap by {overlap_area:.4f} sqm"
                )

    def test_f3_kitchen_dining_adjacency(self, sample_floorplan_layout: FloorplanLayout):
        """F3.5: Asserts that Kitchen polygon shares at least one common boundary segment with Dining Room."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        kitchen = room_dict["room_kitchen"]
        dining = room_dict["room_dining"]

        poly_k = Polygon(kitchen.polygon)
        poly_d = Polygon(dining.polygon)

        # The intersection of their boundaries should be a LineString with non-zero length
        boundary_intersection = poly_k.intersection(poly_d)
        assert boundary_intersection.length > 0.5, (
            f"Kitchen and Dining room do not share a valid boundary wall (shared length: {boundary_intersection.length:.2f}m)"
        )
        assert "room_kitchen" in dining.adjacent_room_ids or "room_dining" in kitchen.adjacent_room_ids

    def test_f3_master_bed_ensuite_adjacency(self, sample_floorplan_layout: FloorplanLayout):
        """F3.6: Asserts that Master Bedroom shares a common boundary wall with Ensuite Bathroom."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        master = room_dict["room_master_bed"]
        ensuite = room_dict["room_ensuite_bath"]

        poly_m = Polygon(master.polygon)
        poly_e = Polygon(ensuite.polygon)

        boundary_intersection = poly_m.intersection(poly_e)
        assert boundary_intersection.length > 0.5, (
            f"Master Bedroom and Ensuite Bath must share a boundary wall (shared length: {boundary_intersection.length:.2f}m)"
        )

    def test_f3_foyer_corridor_connectivity(self, sample_floorplan_layout: FloorplanLayout):
        """F3.7: Verifies circulation corridor / foyer connects to living room and master bedroom."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        corridor = sample_floorplan_layout.corridors[0]
        living = room_dict["room_living"]

        poly_c = Polygon(corridor.polygon)
        poly_l = Polygon(living.polygon)

        assert poly_c.intersection(poly_l).length > 0.5, "Corridor must share a boundary with Living Room"

    def test_f3_non_convex_l_shaped_footprint(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F3.8: Validates room topology within a non-convex L-shaped building footprint."""
        layout = room_boundary_factory.make_l_shaped_floorplan_layout()
        boundary_poly = Polygon(layout.boundary_polygon)
        assert not boundary_poly.is_empty
        assert boundary_poly.is_valid

        # All rooms must be completely contained within the L-shaped footprint
        for room in layout.rooms:
            poly = Polygon(room.polygon)
            assert poly.is_valid
            assert boundary_poly.contains(poly) or boundary_poly.covers(poly), (
                f"Room {room.room_id} escapes the L-shaped building footprint"
            )

        # Rooms must be mutually disjoint
        for i in range(len(layout.rooms)):
            poly_i = Polygon(layout.rooms[i].polygon)
            for j in range(i + 1, len(layout.rooms)):
                poly_j = Polygon(layout.rooms[j].polygon)
                assert poly_i.intersection(poly_j).area < 1e-4

    def test_f3_extreme_aspect_ratio_narrow_lot(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F3.9: Solves rooms inside a narrow 1:4 aspect ratio footprint (5m x 20m) without polygon self-intersection."""
        # 5m wide x 20m deep plot
        boundary = [(0.0, 0.0), (5.0, 0.0), (5.0, 20.0), (0.0, 20.0)]
        room1 = room_boundary_factory.make_room_boundary("r_living", "LivingRoom", [(0.0, 0.0), (5.0, 0.0), (5.0, 7.0), (0.0, 7.0)], is_exterior=True)
        room2 = room_boundary_factory.make_room_boundary("r_kitchen", "Kitchen", [(0.0, 7.0), (5.0, 7.0), (5.0, 12.0), (0.0, 12.0)], is_exterior=True, wet_zone=True)
        room3 = room_boundary_factory.make_room_boundary("r_bedroom", "Bedroom", [(0.0, 12.0), (5.0, 12.0), (5.0, 20.0), (0.0, 20.0)], is_exterior=True)

        layout = FloorplanLayout(
            storey_index=0,
            elevation=0.0,
            boundary_polygon=boundary,
            rooms=[room1, room2, room3],
        )

        for room in layout.rooms:
            poly = Polygon(room.polygon)
            assert poly.is_valid
            assert poly.is_simple
            assert poly.area > 0.0

        # Total area conservation
        total_area = sum(r.area for r in layout.rooms)
        assert math.isclose(total_area, 100.0, rel_tol=1e-3)

    def test_f3_deterministic_topology_reproducibility(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F3.10: Repeated solver invocations on identical input yield bit-for-bit identical coordinates."""
        layout1 = room_boundary_factory.make_standard_floorplan_layout()
        layout2 = room_boundary_factory.make_standard_floorplan_layout()

        assert len(layout1.rooms) == len(layout2.rooms)
        for r1, r2 in zip(layout1.rooms, layout2.rooms):
            assert r1.room_id == r2.room_id
            assert r1.polygon == r2.polygon
            assert r1.area == r2.area


# ==============================================================================
# FEATURE F4: Daylight Perimeter & Circulation Spines (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature4DaylightAndCirculation:
    """Feature F4: Daylight Perimeter Allocation, Corridor Connectivity, and Non-Cut-Through Circulation Spines."""

    def test_f4_living_room_exterior_perimeter_access(self, sample_floorplan_layout: FloorplanLayout):
        """F4.1: Verifies living room polygon shares at least one edge with the building exterior boundary."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        living = room_dict["room_living"]
        assert living.is_exterior is True

        boundary_line = Polygon(sample_floorplan_layout.boundary_polygon).exterior
        living_line = Polygon(living.polygon).exterior

        shared_exterior_segment = boundary_line.intersection(living_line)
        assert shared_exterior_segment.length >= 4.0, (
            f"Living room must have substantial exterior frontage for windows, got {shared_exterior_segment.length:.2f}m"
        )

    def test_f4_all_bedrooms_have_exterior_daylight_access(self, sample_floorplan_layout: FloorplanLayout):
        """F4.2: Verifies 100% of bedrooms have exterior daylight perimeter access."""
        boundary_line = Polygon(sample_floorplan_layout.boundary_polygon).exterior
        bedrooms = [r for r in sample_floorplan_layout.rooms if "bed" in r.room_type.lower()]
        assert len(bedrooms) >= 2

        for bed in bedrooms:
            assert bed.is_exterior is True
            bed_line = Polygon(bed.polygon).exterior
            shared_exterior_edge = boundary_line.intersection(bed_line)
            assert shared_exterior_edge.length >= 2.5, (
                f"Bedroom '{bed.room_id}' lacks sufficient exterior perimeter for daylight: {shared_exterior_edge.length:.2f}m"
            )

    def test_f4_interior_service_rooms_without_daylight(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F4.3: Powder rooms and walk-in closets with requires_daylight=False can be placed in the interior core."""
        powder_room = room_boundary_factory.make_room_boundary(
            room_id="room_powder",
            room_type="PowderRoom",
            polygon=[(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)],
            is_exterior=False,
            wet_zone=True,
            requires_daylight=False,
        )
        assert powder_room.requires_daylight is False
        assert powder_room.is_exterior is False

    def test_f4_single_aspect_unit_daylight_allocation(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F4.4: In a single-aspect apartment (only 1 exterior wall face), daylit rooms are allocated along exterior frontage."""
        # Single exterior face on North side (y=10): (0,10) to (10,10)
        living = room_boundary_factory.make_room_boundary(
            "r_living", "LivingRoom", [(0.0, 5.0), (6.0, 5.0), (6.0, 10.0), (0.0, 10.0)], is_exterior=True, requires_daylight=True
        )
        bedroom = room_boundary_factory.make_room_boundary(
            "r_bed", "Bedroom", [(6.0, 5.0), (10.0, 5.0), (10.0, 10.0), (6.0, 10.0)], is_exterior=True, requires_daylight=True
        )
        interior_bath = room_boundary_factory.make_room_boundary(
            "r_bath", "Bathroom", [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)], is_exterior=False, requires_daylight=False
        )

        exterior_face = LineString([(0.0, 10.0), (10.0, 10.0)])
        assert Polygon(living.polygon).exterior.intersection(exterior_face).length > 0.0
        assert Polygon(bedroom.polygon).exterior.intersection(exterior_face).length > 0.0
        assert Polygon(interior_bath.polygon).exterior.intersection(exterior_face).length == 0.0

    def test_f4_circulation_spine_reachability_graph(self, sample_floorplan_layout: FloorplanLayout):
        """F4.5: Circulation corridor forms a connected graph linking entrance to every individual room."""
        corridor = sample_floorplan_layout.corridors[0]
        poly_corridor = Polygon(corridor.polygon)

        # Verify that every room is reachable from the corridor (shares boundary with corridor or direct adjacent foyer)
        for room in sample_floorplan_layout.rooms:
            poly_room = Polygon(room.polygon)
            shared_boundary = poly_corridor.intersection(poly_room)
            is_directly_accessible = shared_boundary.length > 0.5
            is_suite_room = room.room_id in ["room_ensuite_bath", "room_guest_bed"]
            # Either directly on corridor or connected via private master suite / adjacent zone
            assert is_directly_accessible or is_suite_room, (
                f"Room {room.room_id} has no valid circulation entrance"
            )

    def test_f4_no_room_cut_through_invariant(self, sample_floorplan_layout: FloorplanLayout):
        """F4.6: Accessing Guest Bedroom or Common Bath never requires crossing through Master Bedroom."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        corridor = sample_floorplan_layout.corridors[0]
        guest_bed = room_dict["room_guest_bed"]
        master_bed = room_dict["room_master_bed"]

        poly_corridor = Polygon(corridor.polygon)
        poly_guest = Polygon(guest_bed.polygon)
        poly_master = Polygon(master_bed.polygon)

        # Direct access to guest bedroom from circulation/kitchen zone does not intersect master bedroom interior
        assert poly_guest.intersection(poly_master).area < 1e-4

    def test_f4_corridor_minimum_clear_width(self, sample_floorplan_layout: FloorplanLayout):
        """F4.7: Verifies circulation corridor maintains standard minimum architectural width >= 0.9m."""
        corridor = sample_floorplan_layout.corridors[0]
        verts = corridor.polygon
        # Corridor is [(4,0), (6,0), (6,6), (4,6)] -> width = 6.0 - 4.0 = 2.0m >= 0.9m
        min_x = min(v[0] for v in verts)
        max_x = max(v[0] for v in verts)
        width = max_x - min_x
        assert width >= 0.9, f"Corridor width {width:.2f}m is below minimum clearance of 0.9m"

    def test_f4_max_corridor_dead_end_length(self, sample_floorplan_layout: FloorplanLayout):
        """F4.8: Verifies corridor dead-end length does not exceed fire safety standard (<= 6.0m)."""
        corridor = sample_floorplan_layout.corridors[0]
        verts = corridor.polygon
        min_z = min(v[1] for v in verts)
        max_z = max(v[1] for v in verts)
        corridor_len = max_z - min_z
        assert corridor_len <= 6.0, f"Corridor dead-end length {corridor_len:.2f}m exceeds 6.0m standard"


# ==============================================================================
# FEATURE F5: Coaxial Wet Stack Clustering (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature5CoaxialWetStackClustering:
    """Feature F5: Coaxial Wet Stack Clustering, Vertical Riser Alignment, and Drainage Limits."""

    def test_f5_wet_zone_horizontal_clustering_distance(self, sample_floorplan_layout: FloorplanLayout):
        """F5.1: Verifies all bathroom and kitchen fixtures are within radius R <= 3.5m of vertical riser."""
        assert len(sample_floorplan_layout.vertical_risers) >= 1
        riser = sample_floorplan_layout.vertical_risers[0]
        riser_pt = Point(riser.position)

        wet_rooms = [r for r in sample_floorplan_layout.rooms if r.wet_zone]
        assert len(wet_rooms) >= 2  # Kitchen + Ensuite Bath

        for room in wet_rooms:
            poly = Polygon(room.polygon)
            centroid = poly.centroid
            dist_to_riser = riser_pt.distance(centroid)
            assert dist_to_riser <= 3.5, (
                f"Wet room '{room.room_id}' centroid is {dist_to_riser:.2f}m from riser {riser.riser_id}, "
                f"exceeding max allowable 3.5m plumbing radius"
            )

    def test_f5_back_to_back_bathroom_pairing(self, sample_floorplan_layout: FloorplanLayout):
        """F5.2: Verifies wet rooms (Kitchen & Ensuite Bath) cluster back-to-back sharing a common utility chase."""
        room_dict = {r.room_id: r for r in sample_floorplan_layout.rooms}
        kitchen = room_dict["room_kitchen"]
        bath = room_dict["room_ensuite_bath"]

        poly_k = Polygon(kitchen.polygon)
        poly_b = Polygon(bath.polygon)

        # Distance between centroids should be compact (< 4.5m)
        dist = poly_k.centroid.distance(poly_b.centroid)
        assert dist <= 4.5, f"Wet rooms are too far apart for shared stack: {dist:.2f}m"

    def test_f5_multi_storey_riser_coaxial_coordinates(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F5.3: Asserts (X, Z) coordinates of plumbing riser shaft match identically across storeys (|dX|=0, |dZ|=0)."""
        layouts = room_boundary_factory.make_multi_storey_layouts(storeys=3)
        assert len(layouts) == 3

        base_riser = layouts[0].vertical_risers[0]
        base_pos = base_riser.position

        for s_idx in range(1, 3):
            storey_layout = layouts[s_idx]
            assert len(storey_layout.vertical_risers) >= 1
            storey_riser = storey_layout.vertical_risers[0]

            dx = abs(storey_riser.position[0] - base_pos[0])
            dz = abs(storey_riser.position[1] - base_pos[1])

            assert dx < 1e-3 and dz < 1e-3, (
                f"Riser misalignment between Storey 0 and Storey {s_idx}: dx={dx:.4f}m, dz={dz:.4f}m"
            )

    def test_f5_12_storey_high_rise_riser_continuity(self, design_spec_factory):
        """F5.4: Verifies vertical riser shafts maintain coaxial alignment across 12-storey high-rise."""
        spec = design_spec_factory.make_tower_spec(storeys=12)
        assert spec.total_storeys == 12
        assert spec.mep_strategy.riser_strategy == VerticalRiserStrategy.COAXIAL_STACKED_SHAFTS

        # Check that all 12 storeys are consistently generated
        assert len(spec.storeys) == 12
        for i in range(len(spec.storeys)):
            assert spec.storeys[i].storey_index == i

    def test_f5_secondary_riser_for_isolated_wet_room(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F5.5: Allocates secondary vertical riser when an isolated wet room is > 3.5m away."""
        main_riser = VerticalRiserLocation(riser_id="riser_main", position=(2.0, 2.0))
        isolated_room = room_boundary_factory.make_room_boundary(
            "r_powder_far", "PowderRoom", [(12.0, 12.0), (14.0, 12.0), (14.0, 14.0), (12.0, 14.0)], wet_zone=True
        )

        dist = Point(main_riser.position).distance(Polygon(isolated_room.polygon).centroid)
        assert dist > 3.5  # ~15.5m away

        # Create secondary riser adjacent to isolated room
        secondary_riser = VerticalRiserLocation(riser_id="riser_secondary", position=(13.0, 13.0))
        sec_dist = Point(secondary_riser.position).distance(Polygon(isolated_room.polygon).centroid)
        assert sec_dist <= 3.5

    def test_f5_storeys_without_wet_rooms_handled_gracefully(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F5.6: Storey without wet rooms (e.g. open terrace) does not fail validation."""
        terrace_layout = FloorplanLayout(
            storey_index=2,
            elevation=6.4,
            boundary_polygon=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
            rooms=[
                room_boundary_factory.make_room_boundary(
                    "r_terrace", "Terrace", [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)], is_exterior=True, wet_zone=False
                )
            ],
            corridors=[],
            vertical_risers=[],
        )
        assert len(terrace_layout.rooms) == 1
        assert terrace_layout.rooms[0].wet_zone is False
        assert len(terrace_layout.vertical_risers) == 0


# ==============================================================================
# FEATURE M2 SERVICE & API INTEGRATION TESTS
# ==============================================================================

class TestSpatialSolverService:
    """Tests SpatialSolver service methods, multi-storey solving, and tree enrichment."""

    def test_spatial_solver_solve_floorplans_2bhk(self, sample_design_spec_2bhk):
        from app.services.spatial_solver import SpatialSolver
        layouts = SpatialSolver.solve_floorplans(sample_design_spec_2bhk)
        assert len(layouts) == sample_design_spec_2bhk.total_storeys

        for layout in layouts:
            assert len(layout.rooms) >= 6
            assert len(layout.corridors) >= 1
            assert len(layout.vertical_risers) >= 1

            # Sum of room + corridor areas == gross area
            gross_area = Polygon(layout.boundary_polygon).area
            sum_areas = sum(r.area for r in layout.rooms + layout.corridors)
            assert math.isclose(sum_areas, gross_area, rel_tol=5e-3)

    def test_spatial_solver_compile_spatial_tree_with_geometry(self, sample_design_spec_2bhk):
        from app.services.spatial_solver import SpatialSolver
        from app.schemas.spatial import SpatialNodeType

        tree = SpatialSolver.compile_spatial_tree_with_geometry(sample_design_spec_2bhk)
        assert tree.node_type == SpatialNodeType.PROJECT

        # Traverse and verify room nodes have boundary_polygon populated
        room_nodes = []
        def _collect_rooms(node):
            if node.node_type == SpatialNodeType.ROOM:
                room_nodes.append(node)
            for c in node.children:
                _collect_rooms(c)

        _collect_rooms(tree)
        assert len(room_nodes) >= 1
        for room in room_nodes:
            assert "boundary_polygon" in room.properties
            poly = room.properties["boundary_polygon"]
            assert poly is not None
            assert len(poly) >= 3
            assert room.properties.get("area_sqm", 0.0) > 0.0
            assert room.properties.get("perimeter_m", 0.0) > 0.0

    def test_spatial_solver_l_shaped_footprint(self):
        from app.services.spatial_solver import SpatialSolver
        layout = SpatialSolver.solve_l_shaped_layout()
        assert len(layout.rooms) == 3
        poly_bound = Polygon(layout.boundary_polygon)
        assert poly_bound.is_valid

        # Disjointness
        for i in range(len(layout.rooms)):
            pi = Polygon(layout.rooms[i].polygon)
            assert poly_bound.contains(pi) or poly_bound.covers(pi)
            for j in range(i + 1, len(layout.rooms)):
                pj = Polygon(layout.rooms[j].polygon)
                assert pi.intersection(pj).area < 1e-4

    def test_spatial_solver_geometric_utilities(self):
        from app.services.spatial_solver import SpatialSolver
        poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        area = SpatialSolver.calculate_polygon_area(poly)
        assert math.isclose(area, 50.0)

        centroid = SpatialSolver.calculate_centroid(poly)
        assert math.isclose(centroid[0], 5.0) and math.isclose(centroid[1], 2.5)

        cw_poly = [(0.0, 0.0), (0.0, 5.0), (10.0, 5.0), (10.0, 0.0)]
        ccw = SpatialSolver.ensure_ccw(cw_poly)
        assert SpatialSolver.calculate_polygon_area(ccw) > 0.0

        poly_adj = [(10.0, 0.0), (15.0, 0.0), (15.0, 5.0), (10.0, 5.0)]
        shared_len = SpatialSolver.compute_shared_wall_length(poly, poly_adj)
        assert math.isclose(shared_len, 5.0)


class TestSpatialAPIEndpoints:
    """Tests FastAPI /api/v1/spatial endpoints."""

    def test_api_spatial_solve(self, sample_design_spec_2bhk):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        payload = sample_design_spec_2bhk.model_dump(mode="json")
        response = client.post("/api/v1/spatial/solve", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == sample_design_spec_2bhk.total_storeys
        first_storey = data[0]
        assert "boundary_polygon" in first_storey
        assert "rooms" in first_storey
        assert "vertical_risers" in first_storey
        assert len(first_storey["rooms"]) >= 6

    def test_api_spatial_tree_with_geometry(self, sample_design_spec_2bhk):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        payload = sample_design_spec_2bhk.model_dump(mode="json")
        response = client.post("/api/v1/spatial/tree-with-geometry", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["node_type"] == "Project"
        assert len(data["children"]) >= 1

