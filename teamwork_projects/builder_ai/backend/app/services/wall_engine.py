"""
Parametric Wall Engine & Hosted Opening Sub-Segmentation Service (Milestone 3).

Provides:
1. extract_walls_from_room_boundaries: Extracts canonical 2D/3D wall runs from 2D room polygons with shared edge deduplication.
2. extract_walls_from_floorplan / extract_walls_from_layout: Extracts storey walls from FloorplanLayout.
3. extract_storey_walls: Returns StoreyWalls model for a floorplan layout.
4. compute_wall_subsegments / compute_subsegments: Sub-segments host walls around hosted doors and windows into PRE, POST, LINTEL, SILL.
5. host_opening_on_wall / host_opening: Validates bounds, non-overlap, and re-computes sub-segments.
6. validate_volume_conservation: Verifies exact volume conservation V_solid + V_void == V_gross.
7. merge_collinear_walls: Merges contiguous collinear wall segments sharing identical classification.
8. calculate_wall_mesh_boxes: Generates 3D center, dimension, and rotation boxes for Three.js rendering.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple

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


class WallEngine:
    """
    Parametric Wall Extraction and Hosted Opening Voiding Engine.
    """

    MIN_WALL_LENGTH: float = 0.05            # Filter degenerate edges < 5cm
    DEFAULT_EXTERIOR_THICKNESS: float = 0.25  # 25cm exterior envelope
    DEFAULT_INTERIOR_THICKNESS: float = 0.12  # 12cm interior partition
    DEFAULT_WALL_HEIGHT: float = 3.0         # 3.0m storey clear height

    # --------------------------------------------------------------------------
    # 1. Wall Extraction from Floorplan and Room Boundaries
    # --------------------------------------------------------------------------

    @classmethod
    def extract_walls_from_floorplan(
        cls,
        layout: FloorplanLayout,
        exterior_thickness: float = DEFAULT_EXTERIOR_THICKNESS,
        interior_thickness: float = DEFAULT_INTERIOR_THICKNESS,
        wall_height: float = DEFAULT_WALL_HEIGHT,
    ) -> List[ParametricWall]:
        """
        Extracts deduplicated 3D parametric walls from a FloorplanLayout.
        """
        all_rooms = layout.rooms + layout.corridors
        return cls.extract_walls_from_room_boundaries(
            rooms=all_rooms,
            elevation=layout.elevation,
            storey_index=layout.storey_index,
            exterior_thickness=exterior_thickness,
            interior_thickness=interior_thickness,
            wall_height=wall_height,
        )

    @classmethod
    def extract_walls_from_layout(
        cls,
        layout: FloorplanLayout,
        exterior_thickness: float = DEFAULT_EXTERIOR_THICKNESS,
        interior_thickness: float = DEFAULT_INTERIOR_THICKNESS,
        wall_height: float = DEFAULT_WALL_HEIGHT,
    ) -> List[ParametricWall]:
        """Alias for extract_walls_from_floorplan."""
        return cls.extract_walls_from_floorplan(
            layout=layout,
            exterior_thickness=exterior_thickness,
            interior_thickness=interior_thickness,
            wall_height=wall_height,
        )

    @classmethod
    def extract_storey_walls(
        cls,
        layout: FloorplanLayout,
        exterior_thickness: float = DEFAULT_EXTERIOR_THICKNESS,
        interior_thickness: float = DEFAULT_INTERIOR_THICKNESS,
        wall_height: float = DEFAULT_WALL_HEIGHT,
    ) -> StoreyWalls:
        """
        Extracts all parametric walls for a storey and returns a StoreyWalls collection.
        """
        walls = cls.extract_walls_from_floorplan(
            layout=layout,
            exterior_thickness=exterior_thickness,
            interior_thickness=interior_thickness,
            wall_height=wall_height,
        )
        return StoreyWalls(
            storey_index=layout.storey_index,
            elevation=layout.elevation,
            height=wall_height,
            walls=walls,
        )

    @classmethod
    def extract_walls_from_room_boundaries(
        cls,
        rooms: List[RoomBoundary],
        elevation: float = 0.0,
        storey_index: int = 0,
        exterior_thickness: float = DEFAULT_EXTERIOR_THICKNESS,
        interior_thickness: float = DEFAULT_INTERIOR_THICKNESS,
        wall_height: float = DEFAULT_WALL_HEIGHT,
        base_elevation: Optional[float] = None,
    ) -> List[ParametricWall]:
        """
        Extracts parametric walls using 1D collinear interval decomposition.
        - Eliminates degenerate zero-length / notch edges (< 0.05m).
        - Shared boundary between adjacent rooms produces exactly ONE canonical wall run.
        - Correctly classifies exterior (0.25m) vs interior (0.12m) walls.
        - Preserves corner and T-junction connectivity across all rooms.
        """
        effective_elevation = base_elevation if base_elevation is not None else elevation

        # Step 1: Collect directed 2D edges from room polygons
        raw_segments: List[Tuple[Tuple[float, float], Tuple[float, float], str]] = []
        for r in rooms:
            n = len(r.polygon)
            for i in range(n):
                p1 = r.polygon[i]
                p2 = r.polygon[(i + 1) % n]
                raw_segments.append((p1, p2, r.room_id))

        # Step 2: Group segments by collinear infinite line in Hesse Normal Form
        # Line canonical equation: nx*x + nz*z = d
        line_groups: Dict[
            Tuple[float, float, float],
            List[Tuple[float, float, str, Tuple[float, float], Tuple[float, float]]],
        ] = {}

        for p1, p2, room_id in raw_segments:
            dx = p2[0] - p1[0]
            dz = p2[1] - p1[1]
            seg_len = math.hypot(dx, dz)
            if seg_len < cls.MIN_WALL_LENGTH:
                continue

            # Unit normal
            nx = -dz / seg_len
            nz = dx / seg_len

            # Canonical normal orientation: nx > 0 or (abs(nx) <= 1e-6 and nz > 0)
            if nx < -1e-6 or (abs(nx) <= 1e-6 and nz < -1e-6):
                nx, nz = -nx, -nz

            d = nx * p1[0] + nz * p1[1]

            # Canonical direction u = (-nz, nx)
            ux, uz = -nz, nx

            # Project endpoints onto 1D scalar t
            t1 = p1[0] * ux + p1[1] * uz
            t2 = p2[0] * ux + p2[1] * uz
            t_min, t_max = min(t1, t2), max(t1, t2)

            key = (round(nx, 4), round(nz, 4), round(d, 4))
            if key not in line_groups:
                line_groups[key] = []
            line_groups[key].append((t_min, t_max, room_id, p1, p2))

        # Step 3: Slicing into atomic intervals between unique scalar breakpoints
        extracted_walls: List[ParametricWall] = []
        wall_idx = 0

        for (nx, nz, d), segs in line_groups.items():
            ux, uz = -nz, nx
            # Reference origin on line
            p0_x = nx * d
            p0_z = nz * d

            # Collect all unique scalar breakpoints
            raw_t: Set[float] = set()
            for t_min, t_max, _, _, _ in segs:
                raw_t.add(round(t_min, 4))
                raw_t.add(round(t_max, 4))

            sorted_t = sorted(raw_t)
            if not sorted_t:
                continue

            # Cluster close values within 1e-4m
            clean_t = [sorted_t[0]]
            for t_val in sorted_t[1:]:
                if t_val - clean_t[-1] > 1e-4:
                    clean_t.append(t_val)

            # Analyze atomic intervals
            for i in range(len(clean_t) - 1):
                t_a = clean_t[i]
                t_b = clean_t[i + 1]
                if t_b - t_a < cls.MIN_WALL_LENGTH:
                    continue

                t_mid = (t_a + t_b) * 0.5
                sharing_rooms = list({
                    room_id for t_min, t_max, room_id, _, _ in segs
                    if t_min <= t_mid + 1e-5 and t_max >= t_mid - 1e-5
                })

                if not sharing_rooms:
                    continue

                is_ext = (len(sharing_rooms) == 1)

                x1 = p0_x + t_a * ux
                z1 = p0_z + t_a * uz
                x2 = p0_x + t_b * ux
                z2 = p0_z + t_b * uz

                span_len = math.hypot(x2 - x1, z2 - z1)
                if span_len < cls.MIN_WALL_LENGTH:
                    continue

                th = exterior_thickness if is_ext else interior_thickness
                wall_id = f"wall_{wall_idx:03d}"

                wall = ParametricWall(
                    wall_id=wall_id,
                    start_pt=(round(x1, 4), effective_elevation, round(z1, 4)),
                    end_pt=(round(x2, 4), effective_elevation, round(z2, 4)),
                    thickness=th,
                    height=wall_height,
                    is_exterior=is_ext,
                    storey_index=storey_index,
                    adjacent_room_ids=sharing_rooms,
                    openings=[],
                    sub_segments=[],
                )
                wall.sub_segments = cls.compute_wall_subsegments(wall)
                extracted_walls.append(wall)
                wall_idx += 1

        return extracted_walls

    @classmethod
    def merge_collinear_walls(cls, walls: List[ParametricWall]) -> List[ParametricWall]:
        """
        Merges adjacent collinear wall segments that share identical classification and thickness.
        """
        if not walls:
            return []

        # Group walls by collinear line
        line_groups: Dict[Tuple[float, float, float], List[ParametricWall]] = {}
        for w in walls:
            dx = w.end_pt[0] - w.start_pt[0]
            dz = w.end_pt[2] - w.start_pt[2]
            L = math.hypot(dx, dz)
            if L < 1e-6:
                continue

            nx = -dz / L
            nz = dx / L
            if nx < -1e-6 or (abs(nx) <= 1e-6 and nz < -1e-6):
                nx, nz = -nx, -nz

            d = nx * w.start_pt[0] + nz * w.start_pt[2]
            key = (round(nx, 4), round(nz, 4), round(d, 4))
            if key not in line_groups:
                line_groups[key] = []
            line_groups[key].append(w)

        merged_walls: List[ParametricWall] = []
        for (nx, nz, d), group in line_groups.items():
            ux, uz = -nz, nx
            # Sort by start scalar projection
            def _get_scalar_range(wall: ParametricWall) -> Tuple[float, float]:
                t1 = wall.start_pt[0] * ux + wall.start_pt[2] * uz
                t2 = wall.end_pt[0] * ux + wall.end_pt[2] * uz
                return min(t1, t2), max(t1, t2)

            sorted_group = sorted(group, key=lambda w: _get_scalar_range(w)[0])

            cur_wall = sorted_group[0]
            cur_min, cur_max = _get_scalar_range(cur_wall)
            cur_rooms = set(cur_wall.adjacent_room_ids)

            for next_wall in sorted_group[1:]:
                next_min, next_max = _get_scalar_range(next_wall)
                if (
                    next_wall.is_exterior == cur_wall.is_exterior
                    and math.isclose(next_wall.thickness, cur_wall.thickness, rel_tol=1e-3)
                    and math.isclose(next_wall.height, cur_wall.height, rel_tol=1e-3)
                    and not cur_wall.openings
                    and not next_wall.openings
                    and abs(next_min - cur_max) <= 1e-4
                ):
                    cur_max = next_max
                    cur_rooms.update(next_wall.adjacent_room_ids)
                else:
                    p0_x = nx * d
                    p0_z = nz * d
                    x1 = p0_x + cur_min * ux
                    z1 = p0_z + cur_min * uz
                    x2 = p0_x + cur_max * ux
                    z2 = p0_z + cur_max * uz
                    merged_walls.append(
                        ParametricWall(
                            wall_id=cur_wall.wall_id,
                            start_pt=(round(x1, 4), cur_wall.start_pt[1], round(z1, 4)),
                            end_pt=(round(x2, 4), cur_wall.end_pt[1], round(z2, 4)),
                            thickness=cur_wall.thickness,
                            height=cur_wall.height,
                            is_exterior=cur_wall.is_exterior,
                            storey_index=cur_wall.storey_index,
                            adjacent_room_ids=list(cur_rooms),
                            openings=[],
                            sub_segments=[],
                        )
                    )
                    cur_wall = next_wall
                    cur_min, cur_max = next_min, next_max
                    cur_rooms = set(next_wall.adjacent_room_ids)

            p0_x = nx * d
            p0_z = nz * d
            x1 = p0_x + cur_min * ux
            z1 = p0_z + cur_min * uz
            x2 = p0_x + cur_max * ux
            z2 = p0_z + cur_max * uz
            merged_walls.append(
                ParametricWall(
                    wall_id=cur_wall.wall_id,
                    start_pt=(round(x1, 4), cur_wall.start_pt[1], round(z1, 4)),
                    end_pt=(round(x2, 4), cur_wall.end_pt[1], round(z2, 4)),
                    thickness=cur_wall.thickness,
                    height=cur_wall.height,
                    is_exterior=cur_wall.is_exterior,
                    storey_index=cur_wall.storey_index,
                    adjacent_room_ids=list(cur_rooms),
                    openings=[],
                    sub_segments=[],
                )
            )

        for w in merged_walls:
            w.sub_segments = cls.compute_wall_subsegments(w)

        return merged_walls

    # --------------------------------------------------------------------------
    # 2. Hosted Opening Sub-Segmentation (Voiding)
    # --------------------------------------------------------------------------

    @classmethod
    def compute_wall_subsegments(cls, wall: ParametricWall) -> List[WallSubSegment]:
        """
        Computes 3D solid sub-segments (PRE, POST, LINTEL, SILL, SOLID) for a host wall:
        - Solid wall with 0 openings: Single continuous SOLID sub-segment.
        - Wall with 1 door: PRE, POST, LINTEL sub-segments (0 SILL).
        - Wall with 1 window: PRE, POST, LINTEL, and SILL sub-segments.
        - Multi-opening wall: Strictly ordered contiguous sub-segments.
        Enforces Invariant 4: Volume(Gross) == Volume(Solid) + Volume(Void).
        """
        wall_len = wall.length
        th = wall.thickness
        h = wall.height

        if not wall.openings:
            return [
                WallSubSegment(
                    segment_id=f"{wall.wall_id}_solid",
                    wall_id=wall.wall_id,
                    segment_type=WallSubSegmentType.SOLID,
                    start_dist=0.0,
                    end_dist=wall_len,
                    bottom_elev=0.0,
                    top_elev=h,
                    thickness=th,
                    volume=wall_len * h * th,
                )
            ]

        # Sort openings strictly by distance along wall
        sorted_ops = sorted(wall.openings, key=lambda op: op.distance_along_wall)

        # Validation: Bounds, non-overlap, head height
        last_end = 0.0
        for op in sorted_ops:
            if op.distance_along_wall < -1e-4:
                raise ValueError(
                    f"Opening '{op.opening_id}' has negative start distance: {op.distance_along_wall}"
                )
            if op.distance_along_wall < last_end - 1e-4:
                raise ValueError(
                    f"Overlapping openings detected on wall '{wall.wall_id}': opening '{op.opening_id}' "
                    f"starts at {op.distance_along_wall:.2f}m before previous opening end {last_end:.2f}m"
                )
            if op.distance_along_wall + op.width > wall_len + 1e-4:
                raise ValueError(
                    f"Opening '{op.opening_id}' (dist={op.distance_along_wall}m, width={op.width}m) "
                    f"exceeds wall length {wall_len:.2f}m"
                )
            if op.sill_height + op.height > h + 1e-4:
                raise ValueError(
                    f"Opening '{op.opening_id}' (sill={op.sill_height}m, height={op.height}m) "
                    f"exceeds wall height {h:.2f}m"
                )
            last_end = op.distance_along_wall + op.width

        segments: List[WallSubSegment] = []
        cur_pos = 0.0

        for idx, op in enumerate(sorted_ops):
            op_start = op.distance_along_wall
            op_end = op_start + op.width

            # 1. Solid segment before this opening (PRE for first opening, POST for intermediate solid piers)
            if op_start > cur_pos + 1e-4:
                seg_type = WallSubSegmentType.PRE if idx == 0 else WallSubSegmentType.POST
                seg_len = op_start - cur_pos
                segments.append(
                    WallSubSegment(
                        segment_id=f"{wall.wall_id}_seg_{len(segments)}",
                        wall_id=wall.wall_id,
                        segment_type=seg_type,
                        start_dist=cur_pos,
                        end_dist=op_start,
                        bottom_elev=0.0,
                        top_elev=h,
                        thickness=th,
                        volume=seg_len * h * th,
                    )
                )

            # 2. SILL segment (below opening if sill_height > 0)
            if op.sill_height > 1e-4:
                segments.append(
                    WallSubSegment(
                        segment_id=f"{wall.wall_id}_sill_{op.opening_id}",
                        wall_id=wall.wall_id,
                        segment_type=WallSubSegmentType.SILL,
                        start_dist=op_start,
                        end_dist=op_end,
                        bottom_elev=0.0,
                        top_elev=op.sill_height,
                        thickness=th,
                        volume=op.width * op.sill_height * th,
                    )
                )

            # 3. LINTEL segment (above opening)
            head_elev = op.sill_height + op.height
            if head_elev < h - 1e-4:
                lintel_h = h - head_elev
                segments.append(
                    WallSubSegment(
                        segment_id=f"{wall.wall_id}_lintel_{op.opening_id}",
                        wall_id=wall.wall_id,
                        segment_type=WallSubSegmentType.LINTEL,
                        start_dist=op_start,
                        end_dist=op_end,
                        bottom_elev=head_elev,
                        top_elev=h,
                        thickness=th,
                        volume=op.width * lintel_h * th,
                    )
                )

            cur_pos = op_end

        # 4. Final POST segment after last opening
        if cur_pos < wall_len - 1e-4:
            seg_len = wall_len - cur_pos
            segments.append(
                WallSubSegment(
                    segment_id=f"{wall.wall_id}_post_final",
                    wall_id=wall.wall_id,
                    segment_type=WallSubSegmentType.POST,
                    start_dist=cur_pos,
                    end_dist=wall_len,
                    bottom_elev=0.0,
                    top_elev=h,
                    thickness=th,
                    volume=seg_len * h * th,
                )
            )

        return segments

    @classmethod
    def compute_subsegments(cls, wall: ParametricWall) -> List[WallSubSegment]:
        """Alias for compute_wall_subsegments."""
        return cls.compute_wall_subsegments(wall)

    # --------------------------------------------------------------------------
    # 3. Opening Hosting & Volume Invariant Validation
    # --------------------------------------------------------------------------

    @classmethod
    def host_opening_on_wall(cls, wall: ParametricWall, opening: HostedOpening) -> ParametricWall:
        """
        Hosts a door or window on a host wall run and recomputes the wall's solid sub-segments.
        Raises ValueError if bounds, overlap, or clearance constraints are violated.
        """
        new_openings = list(wall.openings) + [opening]
        updated_wall = ParametricWall(
            wall_id=wall.wall_id,
            start_pt=wall.start_pt,
            end_pt=wall.end_pt,
            thickness=wall.thickness,
            height=wall.height,
            is_exterior=wall.is_exterior,
            storey_index=wall.storey_index,
            adjacent_room_ids=wall.adjacent_room_ids,
            openings=new_openings,
            sub_segments=[],
        )
        updated_wall.sub_segments = cls.compute_wall_subsegments(updated_wall)
        return updated_wall

    @classmethod
    def host_opening(cls, wall: ParametricWall, opening: HostedOpening) -> ParametricWall:
        """Alias for host_opening_on_wall."""
        return cls.host_opening_on_wall(wall, opening)

    @classmethod
    def validate_volume_conservation(cls, wall: ParametricWall, tol: float = 1e-4) -> Dict[str, Any]:
        """
        Verifies Invariant 4: Volume(Gross) == Sum(Volume(SubSegments)) + Sum(Volume(Openings)).
        """
        sub_segs = wall.sub_segments or cls.compute_wall_subsegments(wall)
        gross_vol = wall.gross_volume
        solid_vol = sum(s.volume for s in sub_segs)
        void_vol = sum(op.width * op.height * wall.thickness for op in wall.openings)
        delta = abs(gross_vol - (solid_vol + void_vol))

        is_valid = delta <= tol
        return {
            "wall_id": wall.wall_id,
            "is_valid": is_valid,
            "gross_volume_m3": round(gross_vol, 6),
            "solid_subsegments_volume_m3": round(solid_vol, 6),
            "void_openings_volume_m3": round(void_vol, 6),
            "volume_delta_m3": round(delta, 8),
            "sub_segments_count": len(sub_segs),
            "openings_count": len(wall.openings),
            "message": "Volume conserved strictly" if is_valid else f"Volume violation: delta={delta:.6f} m3",
        }

    # --------------------------------------------------------------------------
    # 4. Three.js / OpenBIM Mesh Bounding Boxes
    # --------------------------------------------------------------------------

    @classmethod
    def calculate_wall_mesh_boxes(cls, wall: ParametricWall) -> List[Dict[str, Any]]:
        """
        Calculates 3D world transforms (position, rotation, dimensions) for each solid sub-segment
        to enable direct Three.js BoxGeometry / Mesh instancing.
        """
        p_start = wall.start_pt
        p_end = wall.end_pt
        L = wall.length
        if L < 1e-6:
            return []

        # Unit direction in horizontal XZ plane
        dx = (p_end[0] - p_start[0]) / L
        dz = (p_end[2] - p_start[2]) / L
        angle_y = math.atan2(dz, dx)

        sub_segs = wall.sub_segments or cls.compute_wall_subsegments(wall)
        boxes = []
        for seg in sub_segs:
            seg_len = seg.length
            seg_h = seg.height
            mid_dist = (seg.start_dist + seg.end_dist) * 0.5
            mid_y = p_start[1] + (seg.bottom_elev + seg.top_elev) * 0.5

            world_x = p_start[0] + dx * mid_dist
            world_z = p_start[2] + dz * mid_dist

            seg_type_str = seg.segment_type.value if hasattr(seg.segment_type, "value") else str(seg.segment_type)

            boxes.append({
                "segment_id": seg.segment_id,
                "segment_type": seg_type_str,
                "position": [round(world_x, 4), round(mid_y, 4), round(world_z, 4)],
                "rotation": [0.0, round(angle_y, 4), 0.0],
                "dimensions": {
                    "length": round(seg_len, 4),
                    "height": round(seg_h, 4),
                    "thickness": round(seg.thickness, 4),
                },
                "volume": round(seg.volume, 6),
            })

        return boxes
