"""
Milestone 3 Challenger 2: Parametric Wall Volume Conservation Empirical Fuzzer.

Adversarially tests and verifies Invariant 4:
|V_gross - (V_solid + V_void)| < 1e-4 m3 in 100% of test cases.

Test Matrices:
1. Deterministic Boundary Openings (s=0, s+w=L, full curtain wall, full height doors, transom windows).
2. Touching and Contiguous Openings (no intermediate solid pier, multi-opening touching chains).
3. Scale Testing (up to 50 openings on a single wall run).
4. Floating Point Precision & Micro-Gaps (irrational numbers, 1mm gaps, extreme aspect ratios).
5. Three.js Mesh Transform Verification (position, rotation, dimensions, mesh box volume conservation).
6. Massive Monte Carlo Fuzzing (10,000 randomized configurations).
7. Negative & Adversarial Boundary Rejection (proper exception handling for invalid inputs).
"""

import math
import random
import pytest
from typing import List

from app.schemas.wall import (
    DoorSwingDirection,
    HostedOpening,
    OpeningType,
    ParametricWall,
    WallSubSegment,
    WallSubSegmentType,
)
from app.services.wall_engine import WallEngine


class TestDeterministicBoundaryOpenings:
    """Tests extreme boundary edge cases for hosted openings."""

    def test_solid_wall_no_openings_volume(self):
        wall = ParametricWall(
            wall_id="w_solid",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(10.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        assert len(segs) == 1
        assert segs[0].segment_type == WallSubSegmentType.SOLID
        assert math.isclose(segs[0].volume, 10.0 * 3.0 * 0.25, rel_tol=1e-6)

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_opening_flush_at_start_boundary_s_zero(self):
        """Opening at s=0.0: No PRE segment generated."""
        wall = ParametricWall(
            wall_id="w_start_flush",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.20,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="door_at_start",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_start_flush",
                    distance_along_wall=0.0,
                    width=1.2,
                    height=2.1,
                    sill_height=0.0,
                )
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        seg_types = [s.segment_type for s in segs]

        # Should have LINTEL (0.0 to 1.2) and POST (1.2 to 6.0), NO PRE segment
        assert WallSubSegmentType.PRE not in seg_types
        assert WallSubSegmentType.LINTEL in seg_types
        assert WallSubSegmentType.POST in seg_types

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_opening_flush_at_end_boundary_s_plus_w_equals_L(self):
        """Opening at s + w = L: No trailing POST segment generated."""
        wall = ParametricWall(
            wall_id="w_end_flush",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="win_at_end",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_end_flush",
                    distance_along_wall=3.5,
                    width=1.5,
                    height=1.2,
                    sill_height=0.9,
                )
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        seg_types = [s.segment_type for s in segs]

        # Should have PRE (0.0 to 3.5), SILL (3.5 to 5.0), LINTEL (3.5 to 5.0), NO trailing POST
        assert WallSubSegmentType.PRE in seg_types
        assert WallSubSegmentType.SILL in seg_types
        assert WallSubSegmentType.LINTEL in seg_types
        assert WallSubSegmentType.POST not in seg_types

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_curtain_glazing_full_wall_opening(self):
        """Curtain wall spanning s=0 to w=L and sill=0 to h=H. Total solid volume is 0.0."""
        wall = ParametricWall(
            wall_id="w_curtain",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(8.0, 0.0, 0.0),
            thickness=0.25,
            height=3.5,
            openings=[
                HostedOpening(
                    opening_id="curtain_glass",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_curtain",
                    distance_along_wall=0.0,
                    width=8.0,
                    height=3.5,
                    sill_height=0.0,
                )
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        assert len(segs) == 0  # No solid sub-segments
        assert wall.total_solid_volume == 0.0
        assert math.isclose(wall.total_void_volume, 8.0 * 3.5 * 0.25, rel_tol=1e-6)

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_full_height_door_in_middle_of_wall(self):
        """Full height door (sill=0, height=H): SILL=0, LINTEL=0."""
        wall = ParametricWall(
            wall_id="w_full_h_door",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.15,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="tall_door",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_full_h_door",
                    distance_along_wall=2.0,
                    width=1.5,
                    height=3.0,
                    sill_height=0.0,
                )
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        assert len(segs) == 2  # PRE (0 to 2) and POST (3.5 to 6)
        assert segs[0].segment_type == WallSubSegmentType.PRE
        assert segs[1].segment_type == WallSubSegmentType.POST

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_transom_window_touching_ceiling(self):
        """Window touching ceiling: sill=2.0, height=1.0, H=3.0 -> SILL exists, LINTEL=0."""
        wall = ParametricWall(
            wall_id="w_transom",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.20,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="transom_win",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_transom",
                    distance_along_wall=1.5,
                    width=2.0,
                    height=1.0,
                    sill_height=2.0,
                )
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        seg_types = [s.segment_type for s in segs]
        assert WallSubSegmentType.LINTEL not in seg_types
        assert WallSubSegmentType.SILL in seg_types

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6


class TestTouchingAndContiguousOpenings:
    """Tests touching openings where opening[k+1].start == opening[k].start + opening[k].width."""

    def test_two_touching_doors(self):
        wall = ParametricWall(
            wall_id="w_touching_doors",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="door1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_touching_doors",
                    distance_along_wall=1.0,
                    width=1.0,
                    height=2.1,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="door2",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_touching_doors",
                    distance_along_wall=2.0,
                    width=1.2,
                    height=2.1,
                    sill_height=0.0,
                ),
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        # PRE (0 to 1), LINTEL1 (1 to 2), LINTEL2 (2 to 3.2), POST (3.2 to 6)
        assert len(segs) == 4
        assert segs[0].segment_type == WallSubSegmentType.PRE
        assert segs[1].segment_type == WallSubSegmentType.LINTEL
        assert segs[2].segment_type == WallSubSegmentType.LINTEL
        assert segs[3].segment_type == WallSubSegmentType.POST

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_touching_door_and_window(self):
        wall = ParametricWall(
            wall_id="w_door_win_touching",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(7.0, 0.0, 0.0),
            thickness=0.18,
            height=3.2,
            openings=[
                HostedOpening(
                    opening_id="d1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_door_win_touching",
                    distance_along_wall=1.5,
                    width=1.0,
                    height=2.2,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="w1",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_door_win_touching",
                    distance_along_wall=2.5,
                    width=2.0,
                    height=1.4,
                    sill_height=0.8,
                ),
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        # PRE (0 to 1.5), LINTEL1 (1.5 to 2.5), SILL2 (2.5 to 4.5), LINTEL2 (2.5 to 4.5), POST (4.5 to 7)
        assert len(segs) == 5

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_three_touching_openings_spanning_entire_wall(self):
        """Three contiguous openings from s=0 to s=L. Zero PRE and zero POST."""
        wall = ParametricWall(
            wall_id="w_touching_all",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(6.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="op1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_touching_all",
                    distance_along_wall=0.0,
                    width=2.0,
                    height=2.2,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="op2",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_touching_all",
                    distance_along_wall=2.0,
                    width=2.5,
                    height=1.2,
                    sill_height=0.9,
                ),
                HostedOpening(
                    opening_id="op3",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_touching_all",
                    distance_along_wall=4.5,
                    width=1.5,
                    height=1.5,
                    sill_height=1.5,
                ),
            ],
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        seg_types = [s.segment_type for s in segs]
        assert WallSubSegmentType.PRE not in seg_types
        assert WallSubSegmentType.POST not in seg_types

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6


class TestScaleAndPrecision:
    """Stress tests high opening count and floating-point micro tolerances."""

    def test_fifty_openings_on_long_facade(self):
        """Wall of length 200m with 50 small strip windows."""
        L = 200.0
        H = 4.0
        T = 0.30
        openings = []
        for i in range(50):
            s = i * 4.0 + 0.5  # 0.5, 4.5, 8.5, ..., 196.5
            w = 2.0
            openings.append(
                HostedOpening(
                    opening_id=f"win_{i:02d}",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_facade_50",
                    distance_along_wall=s,
                    width=w,
                    height=1.5,
                    sill_height=1.2,
                )
            )

        wall = ParametricWall(
            wall_id="w_facade_50",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(L, 0.0, 0.0),
            thickness=T,
            height=H,
            openings=openings,
        )
        segs = WallEngine.compute_wall_subsegments(wall)
        # 1 PRE + 50 SILL + 50 LINTEL + 49 intermediate POST + 1 final POST = 151 segments
        assert len(segs) == 1 + 50 + 50 + 49 + 1

        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-5

    def test_irrational_dimensions_floating_point_conservation(self):
        """Tests wall with sqrt(2), pi, e dimensions."""
        L = math.sqrt(2) * 5.0  # ~ 7.0710678
        H = math.e             # ~ 2.7182818
        T = math.pi / 20.0     # ~ 0.1570796

        wall = ParametricWall(
            wall_id="w_irrational",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(L, 0.0, 0.0),
            thickness=T,
            height=H,
            openings=[
                HostedOpening(
                    opening_id="win_irrat1",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_irrational",
                    distance_along_wall=0.738192,
                    width=1.414213,
                    height=1.0,
                    sill_height=0.812345,
                ),
                HostedOpening(
                    opening_id="win_irrat2",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_irrational",
                    distance_along_wall=3.141592,
                    width=1.732050,
                    height=1.2,
                    sill_height=0.5,
                ),
            ],
        )
        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True
        assert val["volume_delta_m3"] < 1e-6

    def test_micro_gaps_between_openings(self):
        """Tests openings separated by 1mm (0.001m) and 0.1mm (0.0001m)."""
        wall = ParametricWall(
            wall_id="w_micro_gaps",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(10.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="op_m1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_micro_gaps",
                    distance_along_wall=1.0,
                    width=1.0,
                    height=2.1,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="op_m2",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_micro_gaps",
                    distance_along_wall=2.001,  # 1mm gap
                    width=1.0,
                    height=2.1,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="op_m3",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_micro_gaps",
                    distance_along_wall=3.0011,  # 0.1mm gap
                    width=1.0,
                    height=2.1,
                    sill_height=0.0,
                ),
            ],
        )
        val = WallEngine.validate_volume_conservation(wall, tol=1e-4)
        assert val["is_valid"] is True


class TestThreeJsMeshTransforms:
    """Verifies that calculate_wall_mesh_boxes transforms conserve 100% volume and align with subsegments."""

    def test_mesh_boxes_volume_and_count_match_subsegments(self):
        wall = ParametricWall(
            wall_id="w_mesh_box",
            start_pt=(1.0, 0.0, 2.0),
            end_pt=(7.0, 0.0, 10.0),  # Diagonal wall, length = 10.0
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="d1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_mesh_box",
                    distance_along_wall=2.0,
                    width=1.0,
                    height=2.1,
                    sill_height=0.0,
                ),
                HostedOpening(
                    opening_id="w1",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_mesh_box",
                    distance_along_wall=5.0,
                    width=2.0,
                    height=1.2,
                    sill_height=0.9,
                ),
            ],
        )
        subsegs = WallEngine.compute_wall_subsegments(wall)
        boxes = WallEngine.calculate_wall_mesh_boxes(wall)

        assert len(boxes) == len(subsegs)

        total_box_vol = sum(b["volume"] for b in boxes)
        total_subseg_vol = sum(s.volume for s in subsegs)
        assert math.isclose(total_box_vol, total_subseg_vol, rel_tol=1e-4)

        # Check that individual box dimensions match subsegments
        for b, s in zip(boxes, subsegs):
            assert math.isclose(b["dimensions"]["length"], s.length, rel_tol=1e-3)
            assert math.isclose(b["dimensions"]["height"], s.height, rel_tol=1e-3)
            assert math.isclose(b["dimensions"]["thickness"], s.thickness, rel_tol=1e-3)


class TestMassiveMonteCarloFuzzing:
    """Runs 10,000 randomized configurations across diverse geometry ranges."""

    def test_10000_random_wall_opening_configurations(self):
        rng = random.Random(42)  # Deterministic seed for reproducible testing
        num_trials = 10000
        max_observed_delta = 0.0
        failures = []

        for trial in range(num_trials):
            # Random wall geometry
            L = round(rng.uniform(0.5, 50.0), 3)
            H = round(rng.uniform(1.5, 6.0), 3)
            T = round(rng.uniform(0.05, 0.60), 3)

            # Random openings count
            num_ops = rng.randint(0, 6)
            openings: List[HostedOpening] = []

            cur_pos = 0.0
            for op_i in range(num_ops):
                remaining_len = L - cur_pos
                if remaining_len < 0.3:
                    break

                # Gap before opening (can be 0 for touching/flush)
                gap = 0.0 if rng.random() < 0.3 else round(rng.uniform(0.0, remaining_len * 0.3), 3)
                start_dist = cur_pos + gap
                if start_dist >= L - 0.2:
                    break

                max_w = L - start_dist
                w = round(rng.uniform(0.2, min(max_w, 3.5)), 3)
                if w < 0.1 or start_dist + w > L:
                    break

                is_door = (rng.random() < 0.4)
                if is_door:
                    op_type = OpeningType.DOOR
                    sill = 0.0
                    h = round(rng.uniform(1.8, min(H, 2.5)), 3)
                    if h > H:
                        h = H
                else:
                    op_type = OpeningType.WINDOW
                    sill = round(rng.uniform(0.0, H * 0.5), 3)
                    max_h = H - sill
                    h = round(rng.uniform(0.4, max_h), 3)
                    if sill + h > H:
                        h = round(H - sill, 3)

                openings.append(
                    HostedOpening(
                        opening_id=f"op_{trial}_{op_i}",
                        opening_type=op_type,
                        wall_id=f"wall_{trial}",
                        distance_along_wall=start_dist,
                        width=w,
                        height=h,
                        sill_height=sill,
                    )
                )
                cur_pos = start_dist + w

            wall = ParametricWall(
                wall_id=f"wall_{trial}",
                start_pt=(0.0, 0.0, 0.0),
                end_pt=(L, 0.0, 0.0),
                thickness=T,
                height=H,
                openings=openings,
            )

            res = WallEngine.validate_volume_conservation(wall, tol=1e-4)
            delta = res["volume_delta_m3"]
            if delta > max_observed_delta:
                max_observed_delta = delta

            if not res["is_valid"]:
                failures.append({
                    "trial": trial,
                    "L": L, "H": H, "T": T,
                    "openings_count": len(openings),
                    "delta": delta,
                })

        assert len(failures) == 0, f"Volume violations detected in {len(failures)} trials: {failures[:5]}"
        assert max_observed_delta < 1e-4, f"Max delta {max_observed_delta} exceeded 1e-4"
        print(f"\n[Fuzzer] Completed {num_trials} randomized Monte Carlo tests. Max delta = {max_observed_delta:.8f} m3 (100% Invariant 4 passed).")


class TestAdversarialInvalidRejections:
    """Verifies that corrupt or violating geometry correctly triggers strict exceptions."""

    def test_overlapping_openings_raise_value_error(self):
        wall = ParametricWall(
            wall_id="w_overlap",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="d1",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_overlap",
                    distance_along_wall=1.0,
                    width=1.5,
                    height=2.1,
                ),
                HostedOpening(
                    opening_id="d2",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_overlap",
                    distance_along_wall=2.0,  # Overlaps [1.0, 2.5]
                    width=1.0,
                    height=2.1,
                ),
            ],
        )
        with pytest.raises(ValueError, match="Overlapping openings"):
            WallEngine.compute_wall_subsegments(wall)

    def test_opening_exceeding_wall_length_raises_value_error(self):
        wall = ParametricWall(
            wall_id="w_exceed_len",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(4.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="op_too_long",
                    opening_type=OpeningType.DOOR,
                    wall_id="w_exceed_len",
                    distance_along_wall=2.5,
                    width=2.0,  # 2.5 + 2.0 = 4.5 > 4.0
                    height=2.1,
                )
            ],
        )
        with pytest.raises(ValueError, match="exceeds wall length"):
            WallEngine.compute_wall_subsegments(wall)

    def test_opening_exceeding_wall_height_raises_value_error(self):
        wall = ParametricWall(
            wall_id="w_exceed_h",
            start_pt=(0.0, 0.0, 0.0),
            end_pt=(5.0, 0.0, 0.0),
            thickness=0.25,
            height=3.0,
            openings=[
                HostedOpening(
                    opening_id="win_too_high",
                    opening_type=OpeningType.WINDOW,
                    wall_id="w_exceed_h",
                    distance_along_wall=1.0,
                    width=1.0,
                    height=2.0,
                    sill_height=1.5,  # 1.5 + 2.0 = 3.5 > 3.0
                )
            ],
        )
        with pytest.raises(ValueError, match="exceeds wall height"):
            WallEngine.compute_wall_subsegments(wall)

    def test_door_with_nonzero_sill_raises_validation_error(self):
        with pytest.raises(ValueError, match="must have sill_height == 0.0"):
            HostedOpening(
                opening_id="invalid_door_sill",
                opening_type=OpeningType.DOOR,
                wall_id="w_any",
                distance_along_wall=1.0,
                width=1.0,
                height=2.1,
                sill_height=0.5,
            )
