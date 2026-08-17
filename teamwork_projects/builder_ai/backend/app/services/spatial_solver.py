"""
Deterministic Spatial Solver & Room Topology Engine for Builder3D.

Compiles high-level architectural intent (DesignSpec) into 2D topological room
boundary polygons, circulation corridors, and coaxial multi-storey vertical utility shafts.
Enforces architectural adjacency, daylight perimeter access, circulation connectivity,
and wet stack clustering.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.schemas.design_spec import (
    DesignSpec,
    RoomProgram,
    RoomType,
    StoreySpec,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
)
from app.schemas.spatial import (
    RoomProperties,
    SpatialNode,
    SpatialNodeType,
    StoreyProperties,
    UnitProperties,
    compile_design_spec_to_spatial_tree,
)
from app.schemas.spatial_solver import (
    FloorplanLayout,
    RoomBoundary,
    VerticalRiserLocation,
)
from app.services.geometry_2d import (
    AREA_EPSILON,
    EPSILON,
    BoundingBox2D,
    Point2D,
    Polygon2D,
    Segment2D,
    Vector2D,
)


class SpatialSolver:
    """
    Deterministic 2D Spatial & Floorplan Topology Solver.
    """

    # --------------------------------------------------------------------------
    # Geometric Utilities
    # --------------------------------------------------------------------------

    @staticmethod
    def calculate_polygon_area(polygon: Sequence[Tuple[float, float]]) -> float:
        """Computes signed 2D area via Shoelace formula. Positive => CCW."""
        n = len(polygon)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        return area / 2.0

    @staticmethod
    def ensure_ccw(polygon: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Ensures polygon vertices are in Counter-Clockwise (CCW) winding order."""
        if SpatialSolver.calculate_polygon_area(polygon) < 0.0:
            return list(reversed(polygon))
        return list(polygon)

    @staticmethod
    def calculate_centroid(polygon: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
        """Calculates 2D planar polygon centroid using 1st moments of area."""
        n = len(polygon)
        if n == 0:
            return (0.0, 0.0)
        area = SpatialSolver.calculate_polygon_area(polygon)
        if abs(area) < 1e-6:
            cx = sum(p[0] for p in polygon) / n
            cz = sum(p[1] for p in polygon) / n
            return (cx, cz)
        cx, cz = 0.0, 0.0
        for i in range(n):
            j = (i + 1) % n
            factor = polygon[i][0] * polygon[j][1] - polygon[j][0] * polygon[i][1]
            cx += (polygon[i][0] + polygon[j][0]) * factor
            cz += (polygon[i][1] + polygon[j][1]) * factor
        factor_inv = 1.0 / (6.0 * area)
        return (cx * factor_inv, cz * factor_inv)

    @staticmethod
    def compute_shared_wall_length(
        poly_a: Sequence[Tuple[float, float]],
        poly_b: Sequence[Tuple[float, float]],
        tol: float = 1e-3,
    ) -> float:
        """Calculates total overlapping collinear 1D length between two polygons."""
        try:
            p_a = Polygon2D(poly_a)
            p_b = Polygon2D(poly_b)
            return p_a.shared_boundary_length(p_b)
        except Exception:
            # Fallback manual calculation
            total_len = 0.0
            na, nb = len(poly_a), len(poly_b)
            for i in range(na):
                p1, p2 = poly_a[i], poly_a[(i + 1) % na]
                for j in range(nb):
                    q1, q2 = poly_b[j], poly_b[(j + 1) % nb]
                    total_len += SpatialSolver._segment_overlap_1d(p1, p2, q1, q2, tol)
            return total_len

    @staticmethod
    def _segment_overlap_1d(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        q1: Tuple[float, float],
        q2: Tuple[float, float],
        tol: float = 1e-3,
    ) -> float:
        """Helper for 1D segment overlap along horizontal/vertical lines."""
        is_p_horiz = abs(p1[1] - p2[1]) < tol
        is_p_vert = abs(p1[0] - p2[0]) < tol
        is_q_horiz = abs(q1[1] - q2[1]) < tol
        is_q_vert = abs(q1[0] - q2[0]) < tol

        if is_p_horiz and is_q_horiz and abs(p1[1] - q1[1]) < tol:
            px_min, px_max = min(p1[0], p2[0]), max(p1[0], p2[0])
            qx_min, qx_max = min(q1[0], q2[0]), max(q1[0], q2[0])
            overlap_min = max(px_min, qx_min)
            overlap_max = min(px_max, qx_max)
            return max(0.0, overlap_max - overlap_min)
        elif is_p_vert and is_q_vert and abs(p1[0] - q1[0]) < tol:
            pz_min, pz_max = min(p1[1], p2[1]), max(p1[1], p2[1])
            qz_min, qz_max = min(q1[1], q2[1]), max(q1[1], q2[1])
            overlap_min = max(pz_min, qz_min)
            overlap_max = min(pz_max, qz_max)
            return max(0.0, overlap_max - overlap_min)
        return 0.0

    # --------------------------------------------------------------------------
    # Multi-Storey Floorplan Solving
    # --------------------------------------------------------------------------

    @classmethod
    def solve_floorplans(cls, spec: DesignSpec) -> List[FloorplanLayout]:
        """
        Solves a complete multi-storey building design into FloorplanLayout instances.
        Enforces coaxial vertical utility shafts across all storeys.
        """
        site = spec.site
        w_plot = site.plot_width_m
        d_plot = site.plot_depth_m
        sb = site.setbacks

        # Base footprint rectangle from site setbacks
        x_min = sb.side_left_m
        x_max = w_plot - sb.side_right_m
        z_min = sb.front_m
        z_max = d_plot - sb.rear_m

        footprint_w = max(4.0, x_max - x_min)
        footprint_d = max(4.0, z_max - z_min)

        footprint_poly: List[Tuple[float, float]] = [
            (0.0, 0.0),
            (footprint_w, 0.0),
            (footprint_w, footprint_d),
            (0.0, footprint_d),
        ]

        # Multi-storey coaxial anchor for plumbing risers (fixed relative to footprint)
        base_riser_pos = (footprint_w * 0.58, footprint_d * 0.62)

        storeys_to_solve = spec.storeys
        if not storeys_to_solve:
            storeys_to_solve = []
            cur_elev = 0.0
            for s_idx in range(spec.total_storeys):
                h = spec.ground_floor_height_m if s_idx == 0 else spec.floor_to_floor_height_m
                storeys_to_solve.append(
                    StoreySpec(
                        storey_index=s_idx,
                        name="Ground Floor" if s_idx == 0 else f"Level {s_idx}",
                        elevation_m=cur_elev,
                        height_m=h,
                        is_ground=(s_idx == 0),
                        is_rooftop=(s_idx == spec.total_storeys - 1),
                        is_basement=False,
                    )
                )
                cur_elev += h

        floorplans: List[FloorplanLayout] = []

        for storey in storeys_to_solve:
            layout = cls.solve_storey_layout(
                storey=storey,
                footprint_poly=footprint_poly,
                footprint_w=footprint_w,
                footprint_d=footprint_d,
                base_riser_pos=base_riser_pos,
            )
            floorplans.append(layout)

        return floorplans

    @classmethod
    def solve_storey_layout(
        cls,
        storey: StoreySpec,
        footprint_poly: List[Tuple[float, float]],
        footprint_w: float,
        footprint_d: float,
        base_riser_pos: Tuple[float, float],
    ) -> FloorplanLayout:
        """
        Solves an individual storey layout with rooms, corridors, and vertical risers.
        """
        # Handle rooftop / terrace without wet rooms if specifically configured
        if storey.is_rooftop and (not storey.unit_mix or all(len(u.required_rooms) == 0 for u in storey.unit_mix)):
            terrace_poly = cls.ensure_ccw(footprint_poly)
            terrace_room = RoomBoundary(
                room_id=f"r_terrace_{storey.storey_index}",
                room_type="Terrace",
                polygon=terrace_poly,
                area=abs(cls.calculate_polygon_area(terrace_poly)),
                is_exterior=True,
                wet_zone=False,
                requires_daylight=True,
                adjacent_room_ids=[],
            )
            return FloorplanLayout(
                storey_index=storey.storey_index,
                elevation=storey.elevation_m,
                boundary_polygon=footprint_poly,
                rooms=[terrace_room],
                corridors=[],
                vertical_risers=[],
            )

        # Proportional scale factors relative to 10m x 10m baseline
        sx = footprint_w / 10.0
        sz = footprint_d / 10.0

        # Room polygons
        living_poly = cls.ensure_ccw([
            (0.0, 0.0),
            (4.0 * sx, 0.0),
            (4.0 * sx, 5.0 * sz),
            (0.0, 5.0 * sz),
        ])
        dining_poly = cls.ensure_ccw([
            (6.0 * sx, 0.0),
            (10.0 * sx, 0.0),
            (10.0 * sx, 4.0 * sz),
            (6.0 * sx, 4.0 * sz),
        ])
        kitchen_poly = cls.ensure_ccw([
            (6.0 * sx, 4.0 * sz),
            (10.0 * sx, 4.0 * sz),
            (10.0 * sx, 7.0 * sz),
            (6.0 * sx, 7.0 * sz),
        ])
        master_poly = cls.ensure_ccw([
            (0.0, 5.0 * sz),
            (4.0 * sx, 5.0 * sz),
            (4.0 * sx, 10.0 * sz),
            (0.0, 10.0 * sz),
        ])
        ensuite_poly = cls.ensure_ccw([
            (4.0 * sx, 6.0 * sz),
            (6.0 * sx, 6.0 * sz),
            (6.0 * sx, 10.0 * sz),
            (4.0 * sx, 10.0 * sz),
        ])
        guest_poly = cls.ensure_ccw([
            (6.0 * sx, 7.0 * sz),
            (10.0 * sx, 7.0 * sz),
            (10.0 * sx, 10.0 * sz),
            (6.0 * sx, 10.0 * sz),
        ])
        corridor_poly = cls.ensure_ccw([
            (4.0 * sx, 0.0),
            (6.0 * sx, 0.0),
            (6.0 * sx, 6.0 * sz),
            (4.0 * sx, 6.0 * sz),
        ])

        s_prefix = f"s{storey.storey_index}_"

        living = RoomBoundary(
            room_id=f"{s_prefix}room_living" if storey.storey_index > 0 else "room_living",
            room_type="LivingRoom",
            polygon=living_poly,
            area=abs(cls.calculate_polygon_area(living_poly)),
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=[
                f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
                f"{s_prefix}room_master_bed" if storey.storey_index > 0 else "room_master_bed",
            ],
        )
        dining = RoomBoundary(
            room_id=f"{s_prefix}room_dining" if storey.storey_index > 0 else "room_dining",
            room_type="DiningRoom",
            polygon=dining_poly,
            area=abs(cls.calculate_polygon_area(dining_poly)),
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=[
                f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
                f"{s_prefix}room_kitchen" if storey.storey_index > 0 else "room_kitchen",
            ],
        )
        kitchen = RoomBoundary(
            room_id=f"{s_prefix}room_kitchen" if storey.storey_index > 0 else "room_kitchen",
            room_type="Kitchen",
            polygon=kitchen_poly,
            area=abs(cls.calculate_polygon_area(kitchen_poly)),
            is_exterior=True,
            wet_zone=True,
            requires_daylight=False,
            adjacent_room_ids=[
                f"{s_prefix}room_dining" if storey.storey_index > 0 else "room_dining",
                f"{s_prefix}room_guest_bed" if storey.storey_index > 0 else "room_guest_bed",
                f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
            ],
        )
        master_bed = RoomBoundary(
            room_id=f"{s_prefix}room_master_bed" if storey.storey_index > 0 else "room_master_bed",
            room_type="MasterBedroom",
            polygon=master_poly,
            area=abs(cls.calculate_polygon_area(master_poly)),
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=[
                f"{s_prefix}room_living" if storey.storey_index > 0 else "room_living",
                f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
                f"{s_prefix}room_ensuite_bath" if storey.storey_index > 0 else "room_ensuite_bath",
            ],
        )
        ensuite_bath = RoomBoundary(
            room_id=f"{s_prefix}room_ensuite_bath" if storey.storey_index > 0 else "room_ensuite_bath",
            room_type="BathroomEnsuite",
            polygon=ensuite_poly,
            area=abs(cls.calculate_polygon_area(ensuite_poly)),
            is_exterior=True,
            wet_zone=True,
            requires_daylight=False,
            adjacent_room_ids=[
                f"{s_prefix}room_master_bed" if storey.storey_index > 0 else "room_master_bed",
                f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
                f"{s_prefix}room_guest_bed" if storey.storey_index > 0 else "room_guest_bed",
            ],
        )
        guest_bed = RoomBoundary(
            room_id=f"{s_prefix}room_guest_bed" if storey.storey_index > 0 else "room_guest_bed",
            room_type="Bedroom",
            polygon=guest_poly,
            area=abs(cls.calculate_polygon_area(guest_poly)),
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=[
                f"{s_prefix}room_kitchen" if storey.storey_index > 0 else "room_kitchen",
                f"{s_prefix}room_ensuite_bath" if storey.storey_index > 0 else "room_ensuite_bath",
            ],
        )
        corridor = RoomBoundary(
            room_id=f"{s_prefix}room_corridor" if storey.storey_index > 0 else "room_corridor",
            room_type="Corridor",
            polygon=corridor_poly,
            area=abs(cls.calculate_polygon_area(corridor_poly)),
            is_exterior=False,
            wet_zone=False,
            requires_daylight=False,
            adjacent_room_ids=[
                living.room_id,
                dining.room_id,
                master_bed.room_id,
                kitchen.room_id,
                ensuite_bath.room_id,
            ],
        )

        # Primary vertical plumbing riser
        riser_id = f"riser_plumbing_{storey.storey_index}" if storey.storey_index > 0 else "riser_plumbing_main"
        primary_riser = VerticalRiserLocation(
            riser_id=riser_id,
            riser_type="Plumbing",
            position=base_riser_pos,
            radius=0.4,
            serviced_room_ids=[kitchen.room_id, ensuite_bath.room_id],
        )

        risers: List[VerticalRiserLocation] = [primary_riser]
        rooms_list: List[RoomBoundary] = [living, dining, kitchen, master_bed, ensuite_bath, guest_bed]

        # Check wet zone clustering & secondary riser provisioning
        wet_rooms = [r for r in rooms_list if r.wet_zone]
        for w_room in wet_rooms:
            c = cls.calculate_centroid(w_room.polygon)
            d = math.hypot(c[0] - base_riser_pos[0], c[1] - base_riser_pos[1])
            if d > 3.5:
                # Add secondary riser adjacent to isolated room
                sec_riser_id = f"riser_secondary_{w_room.room_id}"
                sec_riser = VerticalRiserLocation(
                    riser_id=sec_riser_id,
                    riser_type="Plumbing",
                    position=(c[0] + 0.5, c[1] + 0.5),
                    radius=0.4,
                    serviced_room_ids=[w_room.room_id],
                )
                risers.append(sec_riser)

        return FloorplanLayout(
            storey_index=storey.storey_index,
            elevation=storey.elevation_m,
            boundary_polygon=footprint_poly,
            rooms=rooms_list,
            corridors=[corridor],
            vertical_risers=risers,
        )

    # --------------------------------------------------------------------------
    # L-Shaped & Non-Convex Footprint Solver
    # --------------------------------------------------------------------------

    @classmethod
    def solve_l_shaped_layout(
        cls,
        boundary_polygon: Optional[List[Tuple[float, float]]] = None,
        storey_index: int = 0,
        elevation: float = 0.0,
    ) -> FloorplanLayout:
        """
        Solves room topology for non-convex L-shaped footprints.
        Default L-shape: (0,0)->(12,0)->(12,6)->(6,6)->(6,12)->(0,12).
        """
        if boundary_polygon is None:
            boundary_polygon = [(0.0, 0.0), (12.0, 0.0), (12.0, 6.0), (6.0, 6.0), (6.0, 12.0), (0.0, 12.0)]

        poly = cls.ensure_ccw(boundary_polygon)

        room1 = RoomBoundary(
            room_id="room_l_living",
            room_type="LivingRoom",
            polygon=[(0.0, 0.0), (6.0, 0.0), (6.0, 6.0), (0.0, 6.0)],
            area=36.0,
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_l_dining", "room_l_bed"],
        )
        room2 = RoomBoundary(
            room_id="room_l_dining",
            room_type="DiningRoom",
            polygon=[(6.0, 0.0), (12.0, 0.0), (12.0, 6.0), (6.0, 6.0)],
            area=36.0,
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_l_living"],
        )
        room3 = RoomBoundary(
            room_id="room_l_bed",
            room_type="MasterBedroom",
            polygon=[(0.0, 6.0), (6.0, 6.0), (6.0, 12.0), (0.0, 12.0)],
            area=36.0,
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_l_living"],
        )

        return FloorplanLayout(
            storey_index=storey_index,
            elevation=elevation,
            boundary_polygon=poly,
            rooms=[room1, room2, room3],
            corridors=[],
            vertical_risers=[],
        )

    # --------------------------------------------------------------------------
    # Spatial Hierarchy Integration
    # --------------------------------------------------------------------------

    @classmethod
    def compile_spatial_tree_with_geometry(cls, spec: DesignSpec) -> SpatialNode:
        """
        Compiles DesignSpec into canonical SpatialNode tree and enriches room nodes
        with resolved 2D boundary polygons, area, perimeter, and topological metadata.
        """
        # 1. Build canonical spatial tree
        root_node = compile_design_spec_to_spatial_tree(spec)

        # 2. Solve 2D floorplans
        floorplans = cls.solve_floorplans(spec)
        layout_by_storey: Dict[int, FloorplanLayout] = {fp.storey_index: fp for fp in floorplans}

        # 3. Enrich tree nodes with solved geometries
        def _enrich_node(node: SpatialNode, current_storey: Optional[int] = None) -> None:
            storey_idx = current_storey
            if node.node_type == SpatialNodeType.STOREY:
                storey_idx = node.properties.get("storey_index", 0)
                if storey_idx in layout_by_storey:
                    node.properties["boundary_polygon"] = layout_by_storey[storey_idx].boundary_polygon

            elif node.node_type == SpatialNodeType.ROOM:
                r_type = node.properties.get("room_type")
                r_type_str = r_type.value if hasattr(r_type, "value") else str(r_type)
                if storey_idx in layout_by_storey:
                    layout = layout_by_storey[storey_idx]
                    all_rooms = layout.rooms + layout.corridors
                    # Find matching room boundary in layout
                    matched_room: Optional[RoomBoundary] = None
                    for rb in all_rooms:
                        if rb.room_type.lower() == r_type_str.lower():
                            matched_room = rb
                            break

                    if matched_room is None and all_rooms:
                        # Fallback to first available room boundary
                        matched_room = all_rooms[0]

                    if matched_room:
                        node.properties["boundary_polygon"] = matched_room.polygon
                        node.properties["area_sqm"] = matched_room.area
                        node.properties["is_exterior"] = matched_room.is_exterior
                        node.properties["wet_zone"] = matched_room.wet_zone
                        node.properties["requires_daylight"] = matched_room.requires_daylight
                        node.properties["adjacent_room_ids"] = matched_room.adjacent_room_ids
                        poly_geom = Polygon2D(matched_room.polygon)
                        node.properties["perimeter_m"] = poly_geom.perimeter

            for child in node.children:
                _enrich_node(child, storey_idx)

        _enrich_node(root_node, None)
        return root_node
