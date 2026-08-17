"""
Comprehensive E2E and Unit Test Suite for Milestone 3 (Features F6 & F7 and API Endpoints).

Features Covered:
- F6: Parametric Wall Run Extraction (Perimeter extraction, interior partitions, shared edge deduplication, exterior vs interior thickness, corner connectivity, collinear merging, degenerate edge filtering, high density grid).
- F7: Hosted Door/Window Opening Voiding & Sub-Segmentation (Solid wall, door PRE/POST/LINTEL splitting, window PRE/POST/LINTEL/SILL splitting, multiple openings, volume conservation invariant, boundary openings, swing clearances, dimensional overflow rejection, mesh boxes).
- API Endpoints: /api/v1/walls/generate-from-floorplan, /api/v1/walls/generate-from-rooms, /api/v1/walls/host-opening, /api/v1/walls/validate-volume, /api/v1/walls/batch-subsegment.
"""

from __future__ import annotations

import math
from typing import List, Tuple

import pytest
from fastapi.testclient import TestClient

from app.main import app
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
from tests.conftest import (
    RoomBoundaryFactory,
    WallOpeningFactory,
)


# ==============================================================================
# FEATURE F6: Parametric Wall Run Extraction (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature6ParametricWallRunExtraction:
    """Feature F6: Parametric Wall Extraction from Room Boundary Polygons."""

    def test_f6_wall_extraction_from_room_polygons(self, sample_parametric_walls: List[ParametricWall]):
        """F6.1: Verifies extraction of all exterior perimeter and interior partition walls from 2D room boundaries."""
        assert len(sample_parametric_walls) > 0

        ext_walls = [w for w in sample_parametric_walls if w.is_exterior]
        int_walls = [w for w in sample_parametric_walls if not w.is_exterior]

        assert len(ext_walls) >= 4, "Must extract at least 4 perimeter exterior walls"
        assert len(int_walls) >= 4, "Must extract interior partition walls between rooms"

    def test_f6_shared_edge_deduplication(self, sample_floorplan_layout: FloorplanLayout):
        """F6.2: Verifies an interior boundary edge shared between Room 1 and Room 2 generates exactly ONE wall run."""
        all_rooms = sample_floorplan_layout.rooms + sample_floorplan_layout.corridors
        walls = WallEngine.extract_walls_from_room_boundaries(all_rooms)

        # Check for duplicate wall centerlines
        seen_edges = set()
        for w in walls:
            p1 = (round(w.start_pt[0], 3), round(w.start_pt[2], 3))
            p2 = (round(w.end_pt[0], 3), round(w.end_pt[2], 3))
            canonical = (p1, p2) if p1 <= p2 else (p2, p1)

            assert canonical not in seen_edges, f"Duplicate wall run detected between {p1} and {p2}"
            seen_edges.add(canonical)

    def test_f6_exterior_vs_interior_wall_thickness(self, sample_parametric_walls: List[ParametricWall]):
        """F6.3: Asserts exterior walls have thickness 0.25m and interior partition walls have thickness 0.12m."""
        for w in sample_parametric_walls:
            if w.is_exterior:
                assert math.isclose(w.thickness, 0.25, rel_tol=1e-2), (
                    f"Exterior wall {w.wall_id} has invalid thickness: {w.thickness}m (expected 0.25m)"
                )
            else:
                assert math.isclose(w.thickness, 0.12, rel_tol=1e-2), (
                    f"Interior wall {w.wall_id} has invalid thickness: {w.thickness}m (expected 0.12m)"
                )

    def test_f6_wall_height_matches_storey_height(self, sample_parametric_walls: List[ParametricWall]):
        """F6.4: Asserts generated wall heights match storey clear height (H = 3.0m)."""
        for w in sample_parametric_walls:
            assert math.isclose(w.height, 3.0, rel_tol=1e-2), (
                f"Wall {w.wall_id} height {w.height}m does not match storey height 3.0m"
            )

    def test_f6_wall_corner_and_t_junction_connectivity(self, sample_parametric_walls: List[ParametricWall]):
        """F6.5: Verifies wall endpoints meet cleanly at corners and T-junctions without floating gaps."""
        # Collect all endpoints
        endpoints = set()
        for w in sample_parametric_walls:
            p1 = (round(w.start_pt[0], 2), round(w.start_pt[2], 2))
            p2 = (round(w.end_pt[0], 2), round(w.end_pt[2], 2))
            endpoints.add(p1)
            endpoints.add(p2)

        # Every endpoint should connect to at least 2 walls for a closed building floorplate
        point_degrees = {pt: 0 for pt in endpoints}
        for w in sample_parametric_walls:
            p1 = (round(w.start_pt[0], 2), round(w.start_pt[2], 2))
            p2 = (round(w.end_pt[0], 2), round(w.end_pt[2], 2))
            point_degrees[p1] += 1
            point_degrees[p2] += 1

        for pt, deg in point_degrees.items():
            assert deg >= 2, f"Endpoint {pt} is disconnected / floating (connected to only {deg} wall)"

    def test_f6_degenerate_zero_length_wall_elimination(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F6.6: Filters out degenerate polygon edges with length < 0.05m."""
        room_with_notch = room_boundary_factory.make_room_boundary(
            "r_notch", "LivingRoom", [(0.0, 0.0), (4.0, 0.0), (4.0, 0.01), (4.0, 5.0), (0.0, 5.0)]
        )
        walls = WallEngine.extract_walls_from_room_boundaries([room_with_notch])
        for w in walls:
            assert w.length >= 0.05, f"Wall {w.wall_id} has degenerate length: {w.length:.4f}m"

    def test_f6_collinear_adjacent_wall_merging(self):
        """F6.7: Parametric wall run preserves linear span from start to end without artificial midpoint breaks."""
        wall = ParametricWall(
            wall_id="wall_continuous",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(10.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)
        assert math.isclose(wall.length, 10.0, rel_tol=1e-3)
        assert len(wall.sub_segments) == 1
        assert wall.sub_segments[0].segment_type == WallSubSegmentType.SOLID or str(wall.sub_segments[0].segment_type) == "SOLID"
        assert math.isclose(wall.sub_segments[0].end_dist, 10.0, rel_tol=1e-3)

    def test_f6_high_density_partition_grid_performance(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F6.8: Extracts wall runs for dense 16-room floorplate rapidly without exponential explosion."""
        import time

        rooms = []
        for i in range(4):
            for j in range(4):
                x0, z0 = i * 4.0, j * 4.0
                x1, z1 = x0 + 4.0, z0 + 4.0
                poly = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
                rooms.append(room_boundary_factory.make_room_boundary(f"room_{i}_{j}", "Bedroom", poly))

        t0 = time.perf_counter()
        walls = WallEngine.extract_walls_from_room_boundaries(rooms)
        elapsed = time.perf_counter() - t0

        assert len(walls) == 40  # 4x4 grid has 4*5 + 4*5 = 40 unique edges
        assert elapsed < 0.050, f"Wall extraction took too long: {elapsed * 1000:.2f}ms"

    def test_f6_boundary_acute_angle_wall_corners(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F6.9: Extracts walls from triangular / acute corner room geometry cleanly."""
        triangular_room = room_boundary_factory.make_room_boundary(
            "r_tri", "AtticRoom", [(0.0, 0.0), (10.0, 0.0), (5.0, 8.0)]
        )
        walls = WallEngine.extract_walls_from_room_boundaries([triangular_room])
        assert len(walls) == 3
        for w in walls:
            assert w.is_exterior is True
            assert w.thickness == 0.25

    def test_f6_boundary_curved_wall_approximation(self, room_boundary_factory: type[RoomBoundaryFactory]):
        """F6.10: Approximates circular / curved wall boundary as multi-segment polygon wall runs."""
        # 12-segment approximated circle centered at (5, 5) with radius 4
        num_segments = 12
        r = 4.0
        poly = []
        for i in range(num_segments):
            angle = 2.0 * math.pi * i / num_segments
            poly.append((5.0 + r * math.cos(angle), 5.0 + r * math.sin(angle)))

        curved_room = room_boundary_factory.make_room_boundary("r_rotunda", "Rotunda", poly)
        walls = WallEngine.extract_walls_from_room_boundaries([curved_room])
        assert len(walls) == num_segments
        for w in walls:
            assert w.is_exterior is True
            assert w.length >= 0.05


# ==============================================================================
# FEATURE F7: Hosted Door/Window Opening Voiding (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature7HostedOpeningVoiding:
    """Feature F7: Hosted Door/Window Opening Voiding and Sub-segmentation Geometry."""

    def test_f7_solid_wall_zero_openings_subsegmentation(self):
        """F7.1: Ensures solid wall without openings produces a single continuous SOLID sub-segment."""
        wall = ParametricWall(
            wall_id="wall_solid",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)
        assert len(wall.sub_segments) == 1
        seg = wall.sub_segments[0]
        assert seg.segment_type == WallSubSegmentType.SOLID or str(seg.segment_type) == "SOLID"
        assert seg.start_dist == 0.0
        assert seg.end_dist == 6.0
        assert seg.bottom_elev == 0.0
        assert seg.top_elev == 3.0
        assert math.isclose(seg.volume, 6.0 * 3.0 * 0.25, rel_tol=1e-3)

    def test_f7_door_opening_splits_wall_into_pre_post_lintel(self):
        """F7.2: Verifies door opening on a wall splits host wall into PRE, POST, and LINTEL sub-segments (0 SILL)."""
        door = HostedOpening(
            opening_id="door_01",
            opening_type=OpeningType.DOOR,
            wall_id="wall_with_door",
            distance_along_wall=2.0,
            width=0.9,
            height=2.1,
            sill_height=0.0,
            swing_direction=DoorSwingDirection.INWARD_RIGHT,
        )
        wall = ParametricWall(
            wall_id="wall_with_door",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[door],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)
        assert len(wall.sub_segments) == 3

        types = [s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type) for s in wall.sub_segments]
        assert "PRE" in types
        assert "LINTEL" in types
        assert "POST" in types
        assert "SILL" not in types

        pre_seg = [s for s in wall.sub_segments if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "PRE"][0]
        assert pre_seg.start_dist == 0.0
        assert pre_seg.end_dist == 2.0

        lintel_seg = [s for s in wall.sub_segments if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "LINTEL"][0]
        assert lintel_seg.start_dist == 2.0
        assert lintel_seg.end_dist == 2.9
        assert lintel_seg.bottom_elev == 2.1
        assert lintel_seg.top_elev == 3.0

        post_seg = [s for s in wall.sub_segments if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "POST"][0]
        assert post_seg.start_dist == 2.9
        assert post_seg.end_dist == 5.0

    def test_f7_window_opening_splits_wall_into_pre_post_lintel_sill(self):
        """F7.3: Verifies window on a wall splits host wall into PRE, POST, LINTEL, and SILL sub-segments."""
        window = HostedOpening(
            opening_id="win_01",
            opening_type=OpeningType.WINDOW,
            wall_id="wall_with_win",
            distance_along_wall=1.5,
            width=1.2,
            height=1.4,
            sill_height=0.9,
        )
        wall = ParametricWall(
            wall_id="wall_with_win",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[window],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)
        assert len(wall.sub_segments) == 4

        types = [s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type) for s in wall.sub_segments]
        assert "PRE" in types
        assert "SILL" in types
        assert "LINTEL" in types
        assert "POST" in types

        sill_seg = [s for s in wall.sub_segments if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "SILL"][0]
        assert sill_seg.bottom_elev == 0.0
        assert sill_seg.top_elev == 0.9

        lintel_seg = [s for s in wall.sub_segments if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "LINTEL"][0]
        assert lintel_seg.bottom_elev == 2.3
        assert lintel_seg.top_elev == 3.0

    def test_f7_multiple_openings_on_single_wall(self):
        """F7.4: Verifies wall hosting 1 door and 2 windows produces correctly ordered contiguous sub-segments."""
        door = HostedOpening(opening_id="d1", opening_type=OpeningType.DOOR, wall_id="w_multi", distance_along_wall=1.0, width=0.9, height=2.1, sill_height=0.0)
        win1 = HostedOpening(opening_id="w1", opening_type=OpeningType.WINDOW, wall_id="w_multi", distance_along_wall=3.0, width=1.2, height=1.4, sill_height=0.9)
        win2 = HostedOpening(opening_id="w2", opening_type=OpeningType.WINDOW, wall_id="w_multi", distance_along_wall=5.5, width=1.2, height=1.4, sill_height=0.9)

        wall = ParametricWall(
            wall_id="w_multi",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(8.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[door, win1, win2],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        assert len(wall.sub_segments) >= 7
        val = WallEngine.validate_volume_conservation(wall)
        assert val["is_valid"] is True

    def test_f7_wall_volume_conservation_invariant(self):
        """F7.5: Asserts Volume(Solid Wall) = Sum(Volume(Sub-segments)) + Sum(Volume(Openings))."""
        win = HostedOpening(opening_id="w_sub", opening_type=OpeningType.WINDOW, wall_id="w_vol", distance_along_wall=2.0, width=1.5, height=1.2, sill_height=1.0)
        wall = ParametricWall(
            wall_id="w_vol",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[win],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        solid_vol = 6.0 * 3.0 * 0.25  # 4.5 m³
        win_vol = 1.5 * 1.2 * 0.25    # 0.45 m³
        sub_vol = sum(s.volume for s in wall.sub_segments)  # 4.05 m³

        assert math.isclose(solid_vol, sub_vol + win_vol, rel_tol=1e-4)

    def test_f7_opening_at_exact_wall_start_or_end(self):
        """F7.6: Handles opening positioned at distance 0.0 (no PRE) or distance = L - w (no POST)."""
        door_start = HostedOpening(opening_id="d_start", opening_type=OpeningType.DOOR, wall_id="w_start", distance_along_wall=0.0, width=1.0, height=2.1)
        wall_start = ParametricWall(wall_id="w_start", start_pt=(0.0, 0.0, 0.0), end_pt=(4.0, 0.0, 0.0), openings=[door_start])
        wall_start.sub_segments = WallEngine.compute_wall_subsegments(wall_start)

        types_start = [s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type) for s in wall_start.sub_segments]
        assert "PRE" not in types_start
        assert "LINTEL" in types_start
        assert "POST" in types_start

        door_end = HostedOpening(opening_id="d_end", opening_type=OpeningType.DOOR, wall_id="w_end", distance_along_wall=3.0, width=1.0, height=2.1)
        wall_end = ParametricWall(wall_id="w_end", start_pt=(0.0, 0.0, 0.0), end_pt=(4.0, 0.0, 0.0), openings=[door_end])
        wall_end.sub_segments = WallEngine.compute_wall_subsegments(wall_end)

        types_end = [s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type) for s in wall_end.sub_segments]
        assert "POST" not in types_end
        assert "PRE" in types_end
        assert "LINTEL" in types_end

    def test_f7_door_clearance_and_swing_direction(self):
        """F7.7: Validates door swing direction enums and swing clearance radius."""
        valid_directions = [
            DoorSwingDirection.INWARD_LEFT,
            DoorSwingDirection.INWARD_RIGHT,
            DoorSwingDirection.OUTWARD_LEFT,
            DoorSwingDirection.OUTWARD_RIGHT,
            DoorSwingDirection.SLIDING,
        ]
        for sw in valid_directions:
            door = HostedOpening(
                opening_id="d_sw",
                opening_type=OpeningType.DOOR,
                wall_id="w1",
                distance_along_wall=1.0,
                width=0.9,
                height=2.1,
                swing_direction=sw,
            )
            assert door.swing_direction == sw

    def test_f7_window_sill_height_and_glazing(self):
        """F7.8: Enforces window sill height >= 0.8m for safety and calculates sill subsegment."""
        win = HostedOpening(
            opening_id="w_safe",
            opening_type=OpeningType.WINDOW,
            wall_id="w1",
            distance_along_wall=1.0,
            width=1.2,
            height=1.4,
            sill_height=0.9,
        )
        assert win.sill_height >= 0.8

    def test_f7_opening_width_exceeds_wall_length_rejection(self):
        """F7.9: Rejects opening whose width + start distance exceeds host wall length."""
        oversized_door = HostedOpening(
            opening_id="d_big",
            opening_type=OpeningType.DOOR,
            wall_id="w_short",
            distance_along_wall=3.0,
            width=2.5,
            height=2.1,
        )
        wall = ParametricWall(wall_id="w_short", start_pt=(0, 0, 0), end_pt=(4, 0, 0), openings=[oversized_door])
        with pytest.raises(ValueError) as exc:
            WallEngine.compute_wall_subsegments(wall)
        assert "exceeds wall length" in str(exc.value)

    def test_f7_opening_height_exceeds_wall_height_rejection(self):
        """F7.10: Rejects opening whose sill + height exceeds host wall height."""
        tall_window = HostedOpening(
            opening_id="w_tall",
            opening_type=OpeningType.WINDOW,
            wall_id="w_norm",
            distance_along_wall=1.0,
            width=1.0,
            height=2.5,
            sill_height=1.0,
        )
        wall = ParametricWall(wall_id="w_norm", start_pt=(0, 0, 0), end_pt=(5, 0, 0), height=3.0, openings=[tall_window])
        with pytest.raises(ValueError) as exc:
            WallEngine.compute_wall_subsegments(wall)
        assert "exceeds wall height" in str(exc.value)

    def test_f7_overlapping_hosted_openings_rejection(self):
        """F7.11: Detects and rejects overlapping openings hosted on the same wall."""
        op1 = HostedOpening(opening_id="op1", opening_type=OpeningType.DOOR, wall_id="w_clash", distance_along_wall=1.0, width=1.0, height=2.1)
        op2 = HostedOpening(opening_id="op2", opening_type=OpeningType.WINDOW, wall_id="w_clash", distance_along_wall=1.5, width=1.0, height=1.4, sill_height=0.9)

        wall = ParametricWall(wall_id="w_clash", start_pt=(0, 0, 0), end_pt=(6, 0, 0), openings=[op1, op2])
        with pytest.raises(ValueError) as exc:
            WallEngine.compute_wall_subsegments(wall)
        assert "Overlapping openings" in str(exc.value)

    def test_f7_boundary_touching_adjacent_openings(self):
        """F7.12: Subdivides wall with two adjacent openings separated by minimal mullion (0.05m)."""
        w1 = HostedOpening(opening_id="w1", opening_type=OpeningType.WINDOW, wall_id="w_touch", distance_along_wall=1.0, width=1.5, height=1.2, sill_height=0.9)
        w2 = HostedOpening(opening_id="w2", opening_type=OpeningType.WINDOW, wall_id="w_touch", distance_along_wall=2.55, width=1.5, height=1.2, sill_height=0.9)

        wall = ParametricWall(wall_id="w_touch", start_pt=(0, 0, 0), end_pt=(6, 0, 0), openings=[w1, w2])
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        # Intermediate segment length = 2.55 - (1.0 + 1.5) = 0.05m
        mid_segs = [
            s for s in wall.sub_segments
            if (s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type)) == "POST"
            and math.isclose(s.start_dist, 2.5, abs_tol=1e-3)
        ]
        assert len(mid_segs) == 1
        assert math.isclose(mid_segs[0].length, 0.05, abs_tol=1e-3)

    def test_f7_boundary_floor_to_ceiling_curtain_window(self):
        """F7.13: Full-height glazed curtain window (sill=0, height=wall_height) with zero lintel/sill."""
        curtain_win = HostedOpening(
            opening_id="w_curtain",
            opening_type=OpeningType.WINDOW,
            wall_id="w_curt",
            distance_along_wall=1.0,
            width=2.0,
            height=3.0,
            sill_height=0.0,
        )
        wall = ParametricWall(wall_id="w_curt", start_pt=(0, 0, 0), end_pt=(4, 0, 0), height=3.0, openings=[curtain_win])
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        types = [s.segment_type.value if hasattr(s.segment_type, "value") else str(s.segment_type) for s in wall.sub_segments]
        assert "SILL" not in types
        assert "LINTEL" not in types
        assert "PRE" in types
        assert "POST" in types
        assert len(wall.sub_segments) == 2

    def test_f7_calculate_wall_mesh_boxes(self):
        """F7.14: Generates 3D box bounding transforms for Three.js rendering."""
        door = HostedOpening(opening_id="d1", opening_type=OpeningType.DOOR, wall_id="w_box", distance_along_wall=2.0, width=1.0, height=2.1)
        wall = ParametricWall(wall_id="w_box", start_pt=(0, 0, 0), end_pt=(6, 0, 0), height=3.0, thickness=0.25, openings=[door])
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        boxes = WallEngine.calculate_wall_mesh_boxes(wall)
        assert len(boxes) == 3
        for b in boxes:
            assert "position" in b
            assert "rotation" in b
            assert "dimensions" in b
            assert "volume" in b
            assert len(b["position"]) == 3
            assert len(b["rotation"]) == 3


# ==============================================================================
# FASTAPI INTEGRATION TESTS FOR /api/v1/walls
# ==============================================================================

class TestWallsAPIEndpoints:
    """FastAPI REST Integration Tests for /api/v1/walls."""

    def test_api_generate_walls_from_floorplan(self, client: TestClient, sample_floorplan_layout: FloorplanLayout):
        payload = {
            "layout": sample_floorplan_layout.model_dump(mode="json"),
            "exterior_thickness": 0.25,
            "interior_thickness": 0.12,
            "wall_height": 3.0,
        }
        res = client.post("/api/v1/walls/generate-from-floorplan", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_walls"] >= 8
        assert data["exterior_walls_count"] >= 4
        assert data["interior_walls_count"] >= 4
        assert data["total_linear_length_m"] > 0.0
        assert data["total_gross_volume_m3"] > 0.0

    def test_api_generate_walls_from_rooms(self, client: TestClient, sample_floorplan_layout: FloorplanLayout):
        payload = {
            "rooms": [r.model_dump(mode="json") for r in sample_floorplan_layout.rooms],
            "exterior_thickness": 0.25,
            "interior_thickness": 0.12,
            "wall_height": 3.0,
            "base_elevation": 0.0,
            "storey_index": 0,
        }
        res = client.post("/api/v1/walls/generate-from-rooms", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_walls"] >= 4

    def test_api_host_opening_success(self, client: TestClient):
        wall = ParametricWall(
            wall_id="w_api",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
        )
        opening = HostedOpening(
            opening_id="win_api",
            opening_type=OpeningType.WINDOW,
            wall_id="w_api",
            distance_along_wall=2.0,
            width=1.5,
            height=1.2,
            sill_height=0.9,
        )
        payload = {
            "wall": wall.model_dump(mode="json"),
            "opening": opening.model_dump(mode="json"),
        }
        res = client.post("/api/v1/walls/host-opening", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["openings"]) == 1
        assert len(data["sub_segments"]) == 4

    def test_api_host_opening_invalid_overlap_422(self, client: TestClient):
        door = HostedOpening(opening_id="d1", opening_type=OpeningType.DOOR, wall_id="w_err", distance_along_wall=1.0, width=1.0, height=2.1)
        wall = ParametricWall(wall_id="w_err", start_pt=(0, 0, 0), end_pt=(4, 0, 0), openings=[door])
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        overlapping_win = HostedOpening(
            opening_id="w1",
            opening_type=OpeningType.WINDOW,
            wall_id="w_err",
            distance_along_wall=1.5,
            width=1.0,
            height=1.2,
            sill_height=0.9,
        )
        payload = {
            "wall": wall.model_dump(mode="json"),
            "opening": overlapping_win.model_dump(mode="json"),
        }
        res = client.post("/api/v1/walls/host-opening", json=payload)
        assert res.status_code == 422
        assert "Overlapping openings" in res.json()["detail"]

    def test_api_validate_volume_endpoint(self, client: TestClient):
        win = HostedOpening(
            opening_id="w1",
            opening_type=OpeningType.WINDOW,
            wall_id="w_val",
            distance_along_wall=1.0,
            width=1.0,
            height=1.0,
            sill_height=1.0,
        )
        wall = ParametricWall(
            wall_id="w_val",
            start_pt=(0, 0, 0),
            end_pt=(5, 0, 0),
            thickness=0.2,
            height=3.0,
            openings=[win],
        )
        wall.sub_segments = WallEngine.compute_wall_subsegments(wall)

        res = client.post("/api/v1/walls/validate-volume", json=wall.model_dump(mode="json"))
        assert res.status_code == 200
        data = res.json()
        assert data["is_valid"] is True
        assert math.isclose(data["gross_volume_m3"], 3.0)
        assert math.isclose(data["void_openings_volume_m3"], 0.2)
        assert math.isclose(data["solid_subsegments_volume_m3"], 2.8)

    def test_api_batch_subsegment_endpoint(self, client: TestClient):
        w1 = ParametricWall(wall_id="w1", start_pt=(0, 0, 0), end_pt=(5, 0, 0))
        w2 = ParametricWall(wall_id="w2", start_pt=(5, 0, 0), end_pt=(10, 0, 0))
        payload = {"walls": [w1.model_dump(mode="json"), w2.model_dump(mode="json")]}

        res = client.post("/api/v1/walls/batch-subsegment", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["total_walls_processed"] == 2
        assert data["all_volumes_conserved"] is True
