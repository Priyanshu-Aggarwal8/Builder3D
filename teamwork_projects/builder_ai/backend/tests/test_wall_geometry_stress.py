"""
Adversarial Stress Test Suite for Wall Geometry and Boundary Resilience (Milestone 3).

Tested by: Challenger 1 (Wall Geometry & Boundary Stress Challenger)
Targets:
- WallEngine.extract_walls_from_room_boundaries
- WallEngine.extract_walls_from_floorplan
- WallEngine.merge_collinear_walls
- WallEngine.calculate_wall_mesh_boxes
- ParametricWall schema & invariants

Test Dimensions:
1. High-density layouts (10x10, 20x20 grid of rooms, honeycomb/hexagonal rooms).
2. Complex topological rooms (L-shaped, U-shaped, Donut/courtyard, T-junctions, offset junctions).
3. Extreme boundary cases (zero-length segments, micro-notches < 0.05m, collinear subdivisions, reversed orientations).
4. Graph connectivity, degree distribution, absence of floating unconnected partitions.
5. Invariant verification (volume conservation, thickness assignment, non-overlapping segments).
"""

from __future__ import annotations

import math
import time
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import pytest

from app.schemas.spatial_solver import FloorplanLayout, RoomBoundary
from app.schemas.wall import (
    DoorSwingDirection,
    HostedOpening,
    OpeningType,
    ParametricWall,
    StoreyWalls,
    WallSubSegment,
    WallSubSegmentType,
)
from app.services.wall_engine import WallEngine


# ==============================================================================
# HELPER FUNCTIONS FOR TOPOLOGICAL & GEOMETRIC VERIFICATION
# ==============================================================================

def round_pt(pt: Tuple[float, float, float] | Tuple[float, float], decimals: int = 3) -> Tuple[float, float]:
    """Helper to get rounded (x, z) 2D point."""
    if len(pt) == 3:
        return (round(pt[0], decimals), round(pt[2], decimals))
    return (round(pt[0], decimals), round(pt[1], decimals))


def build_wall_endpoint_graph(walls: List[ParametricWall], tol: float = 1e-3) -> Dict[Tuple[float, float], List[str]]:
    """Builds graph mapping rounded (x, z) vertex -> list of wall_ids connected to it."""
    graph = defaultdict(list)
    for w in walls:
        p1 = round_pt(w.start_pt)
        p2 = round_pt(w.end_pt)
        graph[p1].append(w.wall_id)
        graph[p2].append(w.wall_id)
    return graph


def verify_no_overlapping_collinear_walls(walls: List[ParametricWall], tol: float = 1e-3):
    """
    Asserts that no two extracted walls overlap along the same collinear line.
    Any collinear walls must be strictly disjoint or touching only at endpoints.
    """
    for i in range(len(walls)):
        w1 = walls[i]
        p1_a = (w1.start_pt[0], w1.start_pt[2])
        p1_b = (w1.end_pt[0], w1.end_pt[2])
        dx1, dz1 = p1_b[0] - p1_a[0], p1_b[1] - p1_a[1]
        L1 = math.hypot(dx1, dz1)
        if L1 < 1e-4:
            continue
        u1 = (dx1 / L1, dz1 / L1)

        for j in range(i + 1, len(walls)):
            w2 = walls[j]
            p2_a = (w2.start_pt[0], w2.start_pt[2])
            p2_b = (w2.end_pt[0], w2.end_pt[2])
            dx2, dz2 = p2_b[0] - p2_a[0], p2_b[1] - p2_a[1]
            L2 = math.hypot(dx2, dz2)
            if L2 < 1e-4:
                continue

            # Check if lines are collinear
            # Vector cross product of direction
            cross = u1[0] * (dz2 / L2) - u1[1] * (dx2 / L2)
            if abs(cross) > 1e-3:
                continue

            # Check perpendicular distance from p2_a to line 1
            v_perp = (p2_a[0] - p1_a[0], p2_a[1] - p1_a[1])
            dist_perp = abs(v_perp[0] * (-u1[1]) + v_perp[1] * u1[0])
            if dist_perp > 1e-3:
                continue

            # Project both segments onto line 1
            t1_a = 0.0
            t1_b = L1
            t2_a = (p2_a[0] - p1_a[0]) * u1[0] + (p2_a[1] - p1_a[1]) * u1[1]
            t2_b = (p2_b[0] - p1_a[0]) * u1[0] + (p2_b[1] - p1_a[1]) * u1[1]

            t2_min, t2_max = min(t2_a, t2_b), max(t2_a, t2_b)
            t1_min, t1_max = min(t1_a, t1_b), max(t1_a, t1_b)

            # Check overlap interval length
            overlap_min = max(t1_min, t2_min)
            overlap_max = min(t1_max, t2_max)
            overlap_len = overlap_max - overlap_min

            assert overlap_len <= tol, (
                f"Collinear overlapping walls detected: {w1.wall_id} and {w2.wall_id} "
                f"overlap by {overlap_len:.4f}m along direction ({u1[0]:.3f}, {u1[1]:.3f})"
            )


# ==============================================================================
# 1. HIGH-DENSITY GRID & SCALABILITY STRESS TESTS
# ==============================================================================

class TestHighDensityLayouts:
    """Stress tests on large multi-room grid arrangements."""

    def test_10x10_grid_room_layout(self):
        """
        Stress test: 10x10 grid of square rooms (100 rooms total).
        Expected:
        - 10 * 11 horizontal edges + 11 * 10 vertical edges = 220 unique wall runs.
        - Exterior boundary walls: 4 * 10 = 40 walls with thickness 0.25m.
        - Interior partition walls: 220 - 40 = 180 walls with thickness 0.12m.
        - Corner node degrees: exactly 4 corners with degree 2.
        - Exterior perimeter node degrees: 36 nodes with degree 3.
        - Interior grid node degrees: 81 nodes with degree 4.
        """
        grid_size = 10
        room_w = 4.0
        rooms = []
        for i in range(grid_size):
            for j in range(grid_size):
                x0, z0 = i * room_w, j * room_w
                x1, z1 = x0 + room_w, z0 + room_w
                poly = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                rooms.append(
                    RoomBoundary(
                        room_id=f"room_{i}_{j}",
                        room_type="Bedroom",
                        polygon=poly,
                        area=room_w * room_w,
                        is_exterior=(i == 0 or i == grid_size - 1 or j == 0 or j == grid_size - 1),
                        wet_zone=False,
                        adjacent_room_ids=[],
                    )
                )

        t0 = time.perf_counter()
        walls = WallEngine.extract_walls_from_room_boundaries(rooms)
        elapsed = time.perf_counter() - t0

        # Assert correct count
        assert len(walls) == 220, f"Expected 220 walls for 10x10 grid, got {len(walls)}"
        assert elapsed < 0.250, f"Extraction of 100 rooms took {elapsed:.3f}s, expected < 250ms"

        # Assert exterior vs interior
        ext_walls = [w for w in walls if w.is_exterior]
        int_walls = [w for w in walls if not w.is_exterior]

        assert len(ext_walls) == 40, f"Expected 40 exterior walls, got {len(ext_walls)}"
        assert len(int_walls) == 180, f"Expected 180 interior walls, got {len(int_walls)}"

        for w in ext_walls:
            assert math.isclose(w.thickness, 0.25, abs_tol=1e-3)
            assert len(w.adjacent_room_ids) == 1
        for w in int_walls:
            assert math.isclose(w.thickness, 0.12, abs_tol=1e-3)
            assert len(w.adjacent_room_ids) == 2

        # Verify no overlapping walls
        verify_no_overlapping_collinear_walls(walls)

        # Verify topological degree distribution
        endpoint_graph = build_wall_endpoint_graph(walls)
        deg_counts = defaultdict(int)
        for pt, connected_walls in endpoint_graph.items():
            deg_counts[len(connected_walls)] += 1

        assert deg_counts[2] == 4, f"Expected 4 corner nodes of degree 2, got {deg_counts[2]}"
        assert deg_counts[3] == 4 * (grid_size - 1), f"Expected {4*(grid_size-1)} perimeter nodes of degree 3, got {deg_counts[3]}"
        assert deg_counts[4] == (grid_size - 1) ** 2, f"Expected {(grid_size-1)**2} interior nodes of degree 4, got {deg_counts[4]}"
        assert sum(deg_counts.values()) == (grid_size + 1) ** 2

    def test_20x20_grid_scaling_benchmark(self):
        """
        Stress test: 20x20 grid of rooms (400 rooms, 840 walls).
        Validates linear/polynomial performance scaling without memory blowup.
        """
        grid_size = 20
        room_w = 3.5
        rooms = []
        for i in range(grid_size):
            for j in range(grid_size):
                x0, z0 = i * room_w, j * room_w
                x1, z1 = x0 + room_w, z0 + room_w
                poly = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                rooms.append(
                    RoomBoundary(
                        room_id=f"room_{i}_{j}",
                        room_type="Office",
                        polygon=poly,
                        area=room_w * room_w,
                        is_exterior=False,
                        wet_zone=False,
                        adjacent_room_ids=[],
                    )
                )

        t0 = time.perf_counter()
        walls = WallEngine.extract_walls_from_room_boundaries(rooms)
        elapsed = time.perf_counter() - t0

        expected_walls = 2 * grid_size * (grid_size + 1)
        assert len(walls) == expected_walls, f"Expected {expected_walls} walls, got {len(walls)}"
        assert elapsed < 1.0, f"Extraction of 400 rooms took {elapsed:.3f}s, expected < 1.0s"

        for w in walls:
            assert w.length >= 0.05
            assert len(w.sub_segments) == 1
            assert w.validate_volume_conservation()

    def test_honeycomb_hexagonal_rooms_layout(self):
        """
        Stress test: Honeycomb / Hexagonal room tiling.
        Tests 60°/120° angled edge deduplication, Hesse normal canonical form,
        and Y-junction vertex degree counts (degree 3).
        """
        # Create a cluster of 7 regular hexagons (1 center + 6 surrounding)
        r = 3.0  # circumradius
        h_dist = r * math.sqrt(3)  # center-to-center horizontal distance

        def make_hexagon(cx: float, cz: float) -> List[Tuple[float, float]]:
            pts = []
            for k in range(6):
                angle = math.radians(60 * k + 30)
                pts.append((round(cx + r * math.cos(angle), 4), round(cz + r * math.sin(angle), 4)))
            return pts

        centers = [(0.0, 0.0)]
        for angle_deg in [0, 60, 120, 180, 240, 300]:
            rad = math.radians(angle_deg)
            centers.append((h_dist * math.cos(rad), h_dist * math.sin(rad)))

        rooms = []
        for idx, (cx, cz) in enumerate(centers):
            poly = make_hexagon(cx, cz)
            rooms.append(
                RoomBoundary(
                    room_id=f"hex_{idx}",
                    room_type="Lab",
                    polygon=poly,
                    area=3 * math.sqrt(3) / 2 * r * r,
                    is_exterior=(idx != 0),
                    wet_zone=False,
                    adjacent_room_ids=[],
                )
            )

        walls = WallEngine.extract_walls_from_room_boundaries(rooms)

        # 7 separate hexagons = 42 edges.
        # The center hexagon shares all 6 edges with 6 neighbors -> 6 shared interior walls.
        # Each pair of adjacent outer hexagons share 1 edge (6 shared pairs) -> 6 shared interior walls.
        # Total interior shared walls = 6 + 6 = 12 interior walls.
        # Outer perimeter edges = 6 outer hexagons * 3 exposed edges = 18 exterior walls.
        # Total unique walls = 12 interior + 18 exterior = 30 walls.
        assert len(walls) == 30, f"Expected 30 unique walls for 7-hex rosette, got {len(walls)}"

        ext_walls = [w for w in walls if w.is_exterior]
        int_walls = [w for w in walls if not w.is_exterior]
        assert len(ext_walls) == 18
        assert len(int_walls) == 12

        # Check interior walls connect 2 rooms
        for w in int_walls:
            assert len(w.adjacent_room_ids) == 2
            assert math.isclose(w.thickness, 0.12, abs_tol=1e-3)
        for w in ext_walls:
            assert len(w.adjacent_room_ids) == 1
            assert math.isclose(w.thickness, 0.25, abs_tol=1e-3)

        verify_no_overlapping_collinear_walls(walls)


# ==============================================================================
# 2. COMPLEX TOPOLOGIES, L-SHAPED, COURTYARD & T-JUNCTIONS
# ==============================================================================

class TestComplexTopologicalRooms:
    """Stress tests on non-convex polygons, courtyards, and offset T-junctions."""

    def test_l_shaped_room_with_two_rectangular_sub_rooms(self):
        """
        Layout:
        - Room A (L-shaped): (0,0) -> (10,0) -> (10,5) -> (5,5) -> (5,10) -> (0,10)
        - Room B (Rectangular): (5,5) -> (10,5) -> (10,10) -> (5,10)
        - Room C (Rectangular): (10,0) -> (15,0) -> (15,5) -> (10,5)
        Validates T-junctions, shared boundary segments, and internal reflex corners.
        """
        poly_a = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0), (5.0, 10.0), (0.0, 10.0)]
        poly_b = [(5.0, 5.0), (10.0, 5.0), (10.0, 10.0), (5.0, 10.0)]
        poly_c = [(10.0, 0.0), (15.0, 0.0), (15.0, 5.0), (10.0, 5.0)]

        r_a = RoomBoundary(room_id="r_l_shape", room_type="LivingRoom", polygon=poly_a, area=75.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        r_b = RoomBoundary(room_id="r_rect_b", room_type="Bedroom", polygon=poly_b, area=25.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        r_c = RoomBoundary(room_id="r_rect_c", room_type="Kitchen", polygon=poly_c, area=25.0, is_exterior=True, wet_zone=True, adjacent_room_ids=[])

        walls = WallEngine.extract_walls_from_room_boundaries([r_a, r_b, r_c])

        # Verify no overlapping segments
        verify_no_overlapping_collinear_walls(walls)

        # Check endpoint connectivity: every endpoint must connect to at least 2 walls
        endpoint_graph = build_wall_endpoint_graph(walls)
        for pt, connected in endpoint_graph.items():
            assert len(connected) >= 2, f"Endpoint {pt} is disconnected (degree {len(connected)})"

        # Shared walls between r_l_shape and r_rect_b should be 2 segments: (5,5)-(10,5) and (5,5)-(5,10)
        shared_ab = [w for w in walls if set(w.adjacent_room_ids) == {"r_l_shape", "r_rect_b"}]
        assert len(shared_ab) == 2
        for w in shared_ab:
            assert w.is_exterior is False
            assert math.isclose(w.thickness, 0.12, abs_tol=1e-3)

        # Shared wall between r_l_shape and r_rect_c is (10,0)-(10,5)
        shared_ac = [w for w in walls if set(w.adjacent_room_ids) == {"r_l_shape", "r_rect_c"}]
        assert len(shared_ac) == 1
        assert shared_ac[0].is_exterior is False

    def test_donut_courtyard_room_layout(self):
        """
        Layout: 4 rooms arranged around a central open-air courtyard / atrium.
        - Room North: (0, 6) -> (10, 6) -> (10, 10) -> (0, 10)
        - Room South: (0, 0) -> (10, 0) -> (10, 4) -> (0, 4)
        - Room West:  (0, 4) -> (4, 4) -> (4, 6) -> (0, 6)
        - Room East:  (6, 4) -> (10, 4) -> (10, 6) -> (6, 6)
        Courtyard hole at (4,4) to (6,6).
        The courtyard boundary walls are exposed to exterior (atrium) -> should be marked exterior.
        """
        poly_n = [(0.0, 6.0), (10.0, 6.0), (10.0, 10.0), (0.0, 10.0)]
        poly_s = [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (0.0, 4.0)]
        poly_w = [(0.0, 4.0), (4.0, 4.0), (4.0, 6.0), (0.0, 6.0)]
        poly_e = [(6.0, 4.0), (10.0, 4.0), (10.0, 6.0), (6.0, 6.0)]

        rooms = [
            RoomBoundary(room_id="r_n", room_type="Corridor", polygon=poly_n, area=40.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[]),
            RoomBoundary(room_id="r_s", room_type="Corridor", polygon=poly_s, area=40.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[]),
            RoomBoundary(room_id="r_w", room_type="Corridor", polygon=poly_w, area=8.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[]),
            RoomBoundary(room_id="r_e", room_type="Corridor", polygon=poly_e, area=8.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[]),
        ]

        walls = WallEngine.extract_walls_from_room_boundaries(rooms)
        verify_no_overlapping_collinear_walls(walls)

        # Internal shared walls:
        # r_w and r_s share (0,4)-(4,4)
        # r_w and r_n share (0,6)-(4,6)
        # r_e and r_s share (6,4)-(10,4)
        # r_e and r_n share (6,6)-(10,6)
        int_walls = [w for w in walls if not w.is_exterior]
        assert len(int_walls) == 4

        # Courtyard walls:
        # (4,4)-(6,4) on r_s (exterior courtyard facade)
        # (4,6)-(6,6) on r_n (exterior courtyard facade)
        # (4,4)-(4,6) on r_w (exterior courtyard facade)
        # (6,4)-(6,6) on r_e (exterior courtyard facade)
        def is_courtyard_wall(w: ParametricWall) -> bool:
            if not w.is_exterior:
                return False
            x_min, x_max = min(w.start_pt[0], w.end_pt[0]), max(w.start_pt[0], w.end_pt[0])
            z_min, z_max = min(w.start_pt[2], w.end_pt[2]), max(w.start_pt[2], w.end_pt[2])
            return (
                (math.isclose(x_min, 4.0) and math.isclose(x_max, 6.0) and (math.isclose(z_min, 4.0) or math.isclose(z_min, 6.0))) or
                (math.isclose(z_min, 4.0) and math.isclose(z_max, 6.0) and (math.isclose(x_min, 4.0) or math.isclose(x_min, 6.0)))
            )

        courtyard_walls = [w for w in walls if is_courtyard_wall(w)]
        assert len(courtyard_walls) == 4
        for cw in courtyard_walls:
            assert cw.is_exterior is True
            assert math.isclose(cw.thickness, 0.25, abs_tol=1e-3)


    def test_staggered_t_junction_offset_alignment(self):
        """
        Layout: One continuous 12m wall on south.
        North side is divided into 3 rooms of different widths (3m, 5m, 4m).
        Validates interval decomposition breaking the 12m span into 3 contiguous sub-walls.
        """
        r_south = RoomBoundary(
            room_id="r_south",
            room_type="Hall",
            polygon=[(0.0, 0.0), (12.0, 0.0), (12.0, 5.0), (0.0, 5.0)],
            area=60.0,
            is_exterior=True,
            wet_zone=False,
            adjacent_room_ids=[],
        )
        r_n1 = RoomBoundary(
            room_id="r_n1",
            room_type="Room1",
            polygon=[(0.0, 5.0), (3.0, 5.0), (3.0, 10.0), (0.0, 10.0)],
            area=15.0,
            is_exterior=True,
            wet_zone=False,
            adjacent_room_ids=[],
        )
        r_n2 = RoomBoundary(
            room_id="r_n2",
            room_type="Room2",
            polygon=[(3.0, 5.0), (8.0, 5.0), (8.0, 10.0), (3.0, 10.0)],
            area=25.0,
            is_exterior=True,
            wet_zone=False,
            adjacent_room_ids=[],
        )
        r_n3 = RoomBoundary(
            room_id="r_n3",
            room_type="Room3",
            polygon=[(8.0, 5.0), (12.0, 5.0), (12.0, 10.0), (8.0, 10.0)],
            area=20.0,
            is_exterior=True,
            wet_zone=False,
            adjacent_room_ids=[],
        )

        walls = WallEngine.extract_walls_from_room_boundaries([r_south, r_n1, r_n2, r_n3])
        verify_no_overlapping_collinear_walls(walls)

        # The dividing line z=5.0 should be sliced into exactly 3 walls:
        # (0, 5) -> (3, 5) sharing (r_south, r_n1)
        # (3, 5) -> (8, 5) sharing (r_south, r_n2)
        # (8, 5) -> (12, 5) sharing (r_south, r_n3)
        mid_walls = [w for w in walls if math.isclose(w.start_pt[2], 5.0, abs_tol=1e-3) and math.isclose(w.end_pt[2], 5.0, abs_tol=1e-3)]
        assert len(mid_walls) == 3

        lengths = sorted([w.length for w in mid_walls])
        assert math.isclose(lengths[0], 3.0, abs_tol=1e-3)
        assert math.isclose(lengths[1], 4.0, abs_tol=1e-3)
        assert math.isclose(lengths[2], 5.0, abs_tol=1e-3)

        for w in mid_walls:
            assert w.is_exterior is False
            assert len(w.adjacent_room_ids) == 2


# ==============================================================================
# 3. EXTREME BOUNDARY CASES & MICRO-NOTCH RESILIENCE
# ==============================================================================

class TestExtremeBoundaryAndMicroNotches:
    """Stress tests on zero-length, micro-notches, collinear reversals, and numerical tolerances."""

    def test_zero_length_and_duplicate_vertex_elimination(self):
        """
        Polygon contains degenerate consecutive identical vertices (zero-length edges).
        Engine must discard zero-length segments without crashing or creating 0-volume walls.
        """
        poly_with_zero = [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0, 0.0),  # Duplicate
            (5.0, 5.0),
            (5.0, 5.0),  # Duplicate
            (0.0, 5.0),
            (0.0, 0.0),  # Duplicate closing point
        ]
        room = RoomBoundary(room_id="r_dup", room_type="Storage", polygon=poly_with_zero, area=25.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        walls = WallEngine.extract_walls_from_room_boundaries([room])

        assert len(walls) == 4
        for w in walls:
            assert w.length >= 0.05
            assert w.length == 5.0

    def test_micro_notches_under_threshold_are_filtered(self):
        """
        Polygon contains tiny architectural architectural notches:
        e.g., 1cm, 2cm, 4.9cm micro-steps (< 0.05m MIN_WALL_LENGTH).
        Must be cleanly filtered without throwing exceptions.
        """
        poly_notches = [
            (0.0, 0.0),
            (5.0, 0.0),
            (5.0, 0.01),      # 1cm notch
            (5.04, 0.01),     # 4cm notch
            (5.04, 5.0),
            (0.0, 5.0),
        ]
        room = RoomBoundary(room_id="r_micro", room_type="Pantry", polygon=poly_notches, area=25.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        walls = WallEngine.extract_walls_from_room_boundaries([room])

        for w in walls:
            assert w.length >= 0.05, f"Wall {w.wall_id} length {w.length} is less than 0.05m threshold"

    def test_collinear_opposite_direction_reversals(self):
        """
        Two rooms sharing a wall where Room 1 is defined CCW and Room 2 is defined CW.
        Engine must match canonical Hesse line orientation and scalar projection
        to deduplicate into a single interior wall.
        """
        # Room 1: CCW
        poly1 = [(0.0, 0.0), (6.0, 0.0), (6.0, 4.0), (0.0, 4.0)]
        # Room 2: CW
        poly2 = [(0.0, 4.0), (0.0, 8.0), (6.0, 8.0), (6.0, 4.0)]

        r1 = RoomBoundary(room_id="r1_ccw", room_type="Bed1", polygon=poly1, area=24.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        r2 = RoomBoundary(room_id="r2_cw", room_type="Bed2", polygon=poly2, area=24.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])

        walls = WallEngine.extract_walls_from_room_boundaries([r1, r2])
        verify_no_overlapping_collinear_walls(walls)

        # Total walls: 7 (3 ext for r1, 3 ext for r2, 1 shared interior at z=4.0)
        assert len(walls) == 7

        shared_wall = [w for w in walls if not w.is_exterior]
        assert len(shared_wall) == 1
        assert math.isclose(shared_wall[0].length, 6.0, abs_tol=1e-3)
        assert set(shared_wall[0].adjacent_room_ids) == {"r1_ccw", "r2_cw"}

    def test_floating_point_imprecision_resilience(self):
        """
        Points with tiny floating-point drift (e.g. 4.0000001 vs 3.9999999).
        Engine's 1e-4 scalar clustering should merge them without splitting into micro-intervals.
        """
        poly1 = [(0.0, 0.0), (4.0000002, 0.0), (4.0000001, 5.0), (0.0, 5.0)]
        poly2 = [(3.9999998, 0.0), (8.0, 0.0), (8.0, 5.0), (3.9999999, 5.0)]

        r1 = RoomBoundary(room_id="r1_drift", room_type="Bed1", polygon=poly1, area=20.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])
        r2 = RoomBoundary(room_id="r2_drift", room_type="Bed2", polygon=poly2, area=20.0, is_exterior=True, wet_zone=False, adjacent_room_ids=[])

        walls = WallEngine.extract_walls_from_room_boundaries([r1, r2])
        assert len(walls) == 7
        for w in walls:
            assert w.length >= 0.05


# ==============================================================================
# 4. COLLINEAR WALL MERGING & SUBDIVISION HARDENING
# ==============================================================================

class TestCollinearMergingAndSubdivision:
    """Stress tests on WallEngine.merge_collinear_walls and sub-division."""

    def test_merge_multiple_collinear_interior_segments(self):
        """
        Merges 3 adjacent collinear wall segments sharing identical properties.
        """
        w1 = ParametricWall(
            wall_id="w_seg1",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(3.0, 0.0, 0.0),
            thickness=0.12,
            height=3.0,
            is_exterior=False,
            adjacent_room_ids=["r1", "r2"],
        )
        w2 = ParametricWall(
            wall_id="w_seg2",
            start_pt=(3.0, 0.0, 0.0),
            end_pt=(7.0, 0.0, 0.0),
            thickness=0.12,
            height=3.0,
            is_exterior=False,
            adjacent_room_ids=["r1", "r3"],
        )
        w3 = ParametricWall(
            wall_id="w_seg3",
            start_pt=(7.0, 0.0, 0.0),
            end_pt=(10.0, 0.0, 0.0),
            thickness=0.12,
            height=3.0,
            is_exterior=False,
            adjacent_room_ids=["r1", "r4"],
        )

        merged = WallEngine.merge_collinear_walls([w1, w2, w3])
        assert len(merged) == 1
        assert math.isclose(merged[0].length, 10.0, abs_tol=1e-3)
        assert merged[0].is_exterior is False
        assert set(merged[0].adjacent_room_ids) == {"r1", "r2", "r3", "r4"}
        assert len(merged[0].sub_segments) == 1
        assert merged[0].sub_segments[0].segment_type == WallSubSegmentType.SOLID or str(merged[0].sub_segments[0].segment_type) == "SOLID"

    def test_collinear_merge_does_not_merge_different_exterior_classifications(self):
        """
        Collinear walls where one segment is exterior (0.25m) and the next is interior (0.12m)
        must NOT be merged together.
        """
        w_ext = ParametricWall(
            wall_id="w_ext",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(4.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            is_exterior=True,
        )
        w_int = ParametricWall(
            wall_id="w_int",
            start_pt=(4.0, 0.0, 0.0),
            end_pt=(8.0, 0.0, 0.0),
            thickness=0.12,
            height=3.0,
            is_exterior=False,
        )

        merged = WallEngine.merge_collinear_walls([w_ext, w_int])
        assert len(merged) == 2


# ==============================================================================
# 5. THREE.JS MESH BOX TRANSFORMS ADVERSARIAL STRESS
# ==============================================================================

class TestThreeJsMeshBoxTransforms:
    """Stress tests on calculate_wall_mesh_boxes for 3D rendering."""

    def test_mesh_box_transforms_diagonal_and_negative_slopes(self):
        """
        Verifies correct center positions, rotation angle (atan2), and dimensions
        for walls pointing in all 4 quadrants (positive X, negative X, positive Z, negative Z).
        """
        # Diagonal wall in 4th quadrant (dx > 0, dz < 0)
        wall_diag = ParametricWall(
            wall_id="w_diag",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(4.0, 0.0, -3.0),
            thickness=0.2,
            height=3.0,
        )
        wall_diag.sub_segments = WallEngine.compute_wall_subsegments(wall_diag)
        boxes = WallEngine.calculate_wall_mesh_boxes(wall_diag)

        assert len(boxes) == 1
        b = boxes[0]
        # Length = 5.0
        assert math.isclose(b["dimensions"]["length"], 5.0, abs_tol=1e-3)
        assert math.isclose(b["dimensions"]["height"], 3.0, abs_tol=1e-3)
        assert math.isclose(b["dimensions"]["thickness"], 0.2, abs_tol=1e-3)

        # Center should be (2.0, 1.5, -1.5)
        assert math.isclose(b["position"][0], 2.0, abs_tol=1e-3)
        assert math.isclose(b["position"][1], 1.5, abs_tol=1e-3)
        assert math.isclose(b["position"][2], -1.5, abs_tol=1e-3)

        # Rotation angle_y = atan2(-3, 4)
        expected_angle = math.atan2(-3.0, 4.0)
        assert math.isclose(b["rotation"][1], expected_angle, abs_tol=1e-3)

    def test_mesh_box_transforms_with_door_and_window(self):
        """
        Verifies bounding boxes for a wall with both a door and a window.
        Asserts non-overlapping 3D bounding boxes.
        """
        door = HostedOpening(opening_id="d1", opening_type=OpeningType.DOOR, wall_id="w_box2", distance_along_wall=1.0, width=1.0, height=2.1)
        win = HostedOpening(opening_id="w1", opening_type=OpeningType.WINDOW, wall_id="w_box2", distance_along_wall=3.0, width=1.5, height=1.2, sill_height=0.9)

        wall = ParametricWall(
            wall_id="w_box2",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[door, win],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)
        boxes = WallEngine.calculate_wall_mesh_boxes(wall)

        # Subsegments:
        # 1. PRE (0 to 1.0)
        # 2. LINTEL d1 (1.0 to 2.0, y=2.1 to 3.0)
        # 3. POST / MID (2.0 to 3.0, y=0 to 3.0)
        # 4. SILL w1 (3.0 to 4.5, y=0 to 0.9)
        # 5. LINTEL w1 (3.0 to 4.5, y=2.1 to 3.0)
        # 6. POST final (4.5 to 6.0, y=0 to 3.0)
        assert len(boxes) == 6

        total_box_volume = sum(b["volume"] for b in boxes)
        gross_vol = 6.0 * 3.0 * 0.25
        door_vol = 1.0 * 2.1 * 0.25
        win_vol = 1.5 * 1.2 * 0.25
        expected_solid_vol = gross_vol - (door_vol + win_vol)

        assert math.isclose(total_box_volume, expected_solid_vol, rel_tol=1e-4)
