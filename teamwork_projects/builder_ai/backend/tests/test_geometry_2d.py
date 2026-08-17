"""
Comprehensive Unit Tests for Pure-Python 2D Geometry Engine (geometry_2d.py).

Verifies Vector2D, Point2D, BoundingBox2D, Segment2D, SegmentIntersection,
and Polygon2D mathematical operations, Ear-Clipping triangulation,
Sutherland-Hodgman clipping, line slicing, and point-in-polygon routines.
"""

from __future__ import annotations

import math
import pytest

from app.services.geometry_2d import (
    AREA_EPSILON,
    EPSILON,
    BoundingBox2D,
    IntersectionType,
    Point2D,
    Polygon2D,
    Segment2D,
    SegmentIntersection,
    Vector2D,
)


# ==============================================================================
# 1. Vector2D Tests
# ==============================================================================

class TestVector2D:
    def test_vector_arithmetic(self):
        v1 = Vector2D(3.0, 4.0)
        v2 = Vector2D(1.0, 2.0)

        # Addition & Subtraction
        v_add = v1 + v2
        assert math.isclose(v_add.dx, 4.0) and math.isclose(v_add.dy, 6.0)
        v_sub = v1 - v2
        assert math.isclose(v_sub.dx, 2.0) and math.isclose(v_sub.dy, 2.0)

        # Scalar multiplication & Division
        v_mul = v1 * 2.5
        assert math.isclose(v_mul.dx, 7.5) and math.isclose(v_mul.dy, 10.0)
        v_rmul = 2.0 * v1
        assert math.isclose(v_rmul.dx, 6.0) and math.isclose(v_rmul.dy, 8.0)
        v_div = v1 / 2.0
        assert math.isclose(v_div.dx, 1.5) and math.isclose(v_div.dy, 2.0)

        # Negation
        v_neg = -v1
        assert math.isclose(v_neg.dx, -3.0) and math.isclose(v_neg.dy, -4.0)

    def test_vector_zero_division_raises(self):
        v = Vector2D(3.0, 4.0)
        with pytest.raises(ZeroDivisionError):
            _ = v / 0.0

    def test_vector_length_and_normalize(self):
        v = Vector2D(3.0, 4.0)
        assert math.isclose(v.length_squared(), 25.0)
        assert math.isclose(v.length(), 5.0)

        v_norm = v.normalize()
        assert math.isclose(v_norm.dx, 0.6)
        assert math.isclose(v_norm.dy, 0.8)
        assert math.isclose(v_norm.length(), 1.0)

        # Zero vector normalization
        v_zero = Vector2D(0.0, 0.0)
        assert v_zero.normalize() == Vector2D(0.0, 0.0)

    def test_vector_dot_and_cross_product(self):
        u = Vector2D(1.0, 0.0)
        v = Vector2D(0.0, 1.0)

        # Dot product
        assert math.isclose(u.dot(v), 0.0)  # Orthogonal
        assert math.isclose(u.dot(u), 1.0)

        # Cross product (perp-dot)
        assert math.isclose(u.cross(v), 1.0)  # CCW 90 deg turn
        assert math.isclose(v.cross(u), -1.0) # CW 90 deg turn
        assert math.isclose(u.cross(u), 0.0)  # Collinear

    def test_vector_perpendiculars_and_rotation(self):
        v = Vector2D(2.0, 3.0)
        left_normal = v.perpendicular_left()
        right_normal = v.perpendicular_right()

        assert math.isclose(left_normal.dx, -3.0) and math.isclose(left_normal.dy, 2.0)
        assert math.isclose(right_normal.dx, 3.0) and math.isclose(right_normal.dy, -2.0)
        assert math.isclose(v.dot(left_normal), 0.0)
        assert math.isclose(v.dot(right_normal), 0.0)

        # Rotation
        v_x = Vector2D(1.0, 0.0)
        v_rot_90 = v_x.rotate(math.pi / 2.0)
        assert math.isclose(v_rot_90.dx, 0.0, abs_tol=1e-7)
        assert math.isclose(v_rot_90.dy, 1.0, abs_tol=1e-7)


# ==============================================================================
# 2. Point2D Tests
# ==============================================================================

class TestPoint2D:
    def test_point_arithmetic_and_distance(self):
        p1 = Point2D(1.0, 2.0)
        p2 = Point2D(4.0, 6.0)

        # Point subtraction yields Vector2D
        vec = p2 - p1
        assert isinstance(vec, Vector2D)
        assert math.isclose(vec.dx, 3.0) and math.isclose(vec.dy, 4.0)

        # Point + Vector yields Point2D
        p3 = p1 + Vector2D(3.0, 4.0)
        assert isinstance(p3, Point2D)
        assert math.isclose(p3.x, 4.0) and math.isclose(p3.y, 6.0)

        # Distance
        assert math.isclose(p1.distance_to(p2), 5.0)
        assert math.isclose(p1.distance_squared_to(p2), 25.0)
        assert p1.is_close_to(Point2D(1.00000001, 2.00000001))

    def test_point_tuple_conversion(self):
        p = Point2D(3.5, 7.2)
        assert p.to_tuple() == (3.5, 7.2)
        p_from = Point2D.from_tuple([3.5, 7.2])
        assert p_from == p


# ==============================================================================
# 3. BoundingBox2D Tests
# ==============================================================================

class TestBoundingBox2D:
    def test_bounding_box_properties_and_intersections(self):
        bb1 = BoundingBox2D(0.0, 0.0, 10.0, 8.0)
        assert math.isclose(bb1.width, 10.0)
        assert math.isclose(bb1.height, 8.0)
        assert math.isclose(bb1.area, 80.0)
        assert bb1.center == Point2D(5.0, 4.0)

        # Point containment
        assert bb1.contains_point(Point2D(5.0, 4.0))
        assert bb1.contains_point(Point2D(0.0, 0.0))
        assert not bb1.contains_point(Point2D(11.0, 4.0))

        # Box intersection
        bb2 = BoundingBox2D(5.0, 4.0, 15.0, 12.0)
        assert bb1.intersects(bb2)
        inter = bb1.intersection(bb2)
        assert inter is not None
        assert math.isclose(inter.min_x, 5.0) and math.isclose(inter.max_x, 10.0)
        assert math.isclose(inter.min_y, 4.0) and math.isclose(inter.max_y, 8.0)

        # Disjoint boxes
        bb3 = BoundingBox2D(20.0, 20.0, 30.0, 30.0)
        assert not bb1.intersects(bb3)
        assert bb1.intersection(bb3) is None

        # Union & Expansion
        union_bb = bb1.union(bb2)
        assert math.isclose(union_bb.min_x, 0.0) and math.isclose(union_bb.max_x, 15.0)
        expanded = bb1.expanded_by(1.0)
        assert math.isclose(expanded.min_x, -1.0) and math.isclose(expanded.max_x, 11.0)

    def test_bounding_box_from_points(self):
        pts = [Point2D(2.0, 3.0), Point2D(-1.0, 8.0), Point2D(5.0, 1.0)]
        bb = BoundingBox2D.from_points(pts)
        assert math.isclose(bb.min_x, -1.0) and math.isclose(bb.max_x, 5.0)
        assert math.isclose(bb.min_y, 1.0) and math.isclose(bb.max_y, 8.0)


# ==============================================================================
# 4. Segment2D & SegmentIntersection Tests
# ==============================================================================

class TestSegment2D:
    def test_segment_properties_and_projections(self):
        seg = Segment2D(Point2D(0.0, 0.0), Point2D(10.0, 0.0))
        assert math.isclose(seg.length, 10.0)
        assert seg.midpoint == Point2D(5.0, 0.0)
        assert seg.direction == Vector2D(1.0, 0.0)
        assert seg.normal_left == Vector2D(0.0, 1.0)
        assert seg.normal_right == Vector2D(0.0, -1.0)

        # Point projection
        proj_pt, t = seg.project_point(Point2D(3.0, 5.0))
        assert proj_pt == Point2D(3.0, 0.0)
        assert math.isclose(t, 0.3)
        assert math.isclose(seg.distance_to_point(Point2D(3.0, 5.0)), 5.0)

        # Clamped projection outside endpoints
        proj_outside, t_outside = seg.project_point(Point2D(15.0, 2.0))
        assert proj_outside == Point2D(10.0, 0.0)
        assert math.isclose(t_outside, 1.0)

    def test_segment_intersections(self):
        # 1. Non-parallel crossing (X shape)
        s1 = Segment2D(Point2D(0.0, 0.0), Point2D(10.0, 10.0))
        s2 = Segment2D(Point2D(0.0, 10.0), Point2D(10.0, 0.0))
        inter1 = s1.intersect(s2)
        assert inter1.type == IntersectionType.POINT
        assert inter1.point == Point2D(5.0, 5.0)

        # 2. Parallel disjoint
        s3 = Segment2D(Point2D(0.0, 0.0), Point2D(10.0, 0.0))
        s4 = Segment2D(Point2D(0.0, 2.0), Point2D(10.0, 2.0))
        inter2 = s3.intersect(s4)
        assert inter2.type == IntersectionType.NONE

        # 3. Collinear overlapping
        s5 = Segment2D(Point2D(0.0, 0.0), Point2D(10.0, 0.0))
        s6 = Segment2D(Point2D(5.0, 0.0), Point2D(15.0, 0.0))
        inter3 = s5.intersect(s6)
        assert inter3.type == IntersectionType.COLINEAR_OVERLAP
        assert inter3.overlap_segment is not None
        p_start, p_end = inter3.overlap_segment
        assert p_start == Point2D(5.0, 0.0) and p_end == Point2D(10.0, 0.0)

        # 4. Collinear touching at single endpoint
        s7 = Segment2D(Point2D(0.0, 0.0), Point2D(5.0, 0.0))
        s8 = Segment2D(Point2D(5.0, 0.0), Point2D(10.0, 0.0))
        inter4 = s7.intersect(s8)
        assert inter4.type == IntersectionType.POINT
        assert inter4.point == Point2D(5.0, 0.0)


# ==============================================================================
# 5. Polygon2D Tests
# ==============================================================================

class TestPolygon2D:
    def test_polygon_area_centroid_and_ccw(self):
        # 10m x 8m rectangle
        verts = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]
        poly = Polygon2D(verts)

        assert poly.is_ccw
        assert math.isclose(poly.area, 80.0)
        assert math.isclose(poly.signed_area, 80.0)
        assert poly.centroid == Point2D(5.0, 4.0)
        assert math.isclose(poly.perimeter, 36.0)

        # Clockwise polygon normalized to CCW
        cw_verts = [(0.0, 0.0), (0.0, 8.0), (10.0, 8.0), (10.0, 0.0)]
        poly_cw = Polygon2D(cw_verts)
        assert not poly_cw.is_ccw
        assert math.isclose(poly_cw.area, 80.0)
        poly_ccw = poly_cw.ensure_ccw()
        assert poly_ccw.is_ccw

    def test_polygon_sanitization(self):
        # Polygon with closing duplicate and collinear intermediate point
        raw_verts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
        poly = Polygon2D(raw_verts)
        # Should filter the closing (0,0) and the intermediate (5,0)
        assert poly.vertex_count == 4
        assert math.isclose(poly.area, 50.0)

    def test_polygon_point_in_polygon(self):
        verts = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        poly = Polygon2D(verts)

        # Interior
        assert poly.contains_point(Point2D(5.0, 5.0))
        assert poly.contains_point(Point2D(1.0, 1.0))

        # Exterior
        assert not poly.contains_point(Point2D(-1.0, 5.0))
        assert not poly.contains_point(Point2D(5.0, 15.0))

        # Boundary & Vertices
        assert poly.contains_point(Point2D(0.0, 5.0), include_boundary=True)
        assert poly.contains_point(Point2D(10.0, 10.0), include_boundary=True)

    def test_polygon_shared_boundary_length(self):
        # Room A: [0, 5] x [0, 5]
        room_a = Polygon2D([(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)])
        # Room B: [5, 10] x [0, 5] (shares edge along x=5 from y=0 to y=5)
        room_b = Polygon2D([(5.0, 0.0), (10.0, 0.0), (10.0, 5.0), (5.0, 5.0)])

        shared_len = room_a.shared_boundary_length(room_b)
        assert math.isclose(shared_len, 5.0)

        # Building boundary
        building = Polygon2D([(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)])
        assert math.isclose(room_a.shared_exterior_length(building), 15.0)

    def test_ear_clipping_triangulation(self):
        # 1. Convex Pentagon
        pentagon = Polygon2D([(0.0, 0.0), (4.0, 0.0), (5.0, 3.0), (2.0, 5.0), (0.0, 3.0)])
        triangles = pentagon.triangulate()
        assert len(triangles) == 3  # N - 2 triangles
        sum_tri_area = sum(t.area for t in triangles)
        assert math.isclose(sum_tri_area, pentagon.area, rel_tol=1e-5)

        # 2. Non-Convex L-Shape
        l_shape = Polygon2D([(0.0, 0.0), (6.0, 0.0), (6.0, 3.0), (3.0, 3.0), (3.0, 6.0), (0.0, 6.0)])
        l_triangles = l_shape.triangulate()
        assert len(l_triangles) == 4  # 6 - 2 = 4 triangles
        sum_l_area = sum(t.area for t in l_triangles)
        assert math.isclose(sum_l_area, l_shape.area, rel_tol=1e-5)

    def test_sutherland_hodgman_and_intersection_area(self):
        # Room A: [0, 6] x [0, 6] (36 sqm)
        poly_a = Polygon2D([(0.0, 0.0), (6.0, 0.0), (6.0, 6.0), (0.0, 6.0)])
        # Room B: [4, 10] x [2, 8] (overlap is [4, 6] x [2, 6] = 2 x 4 = 8 sqm)
        poly_b = Polygon2D([(4.0, 2.0), (10.0, 2.0), (10.0, 8.0), (4.0, 8.0)])

        overlap = poly_a.intersection_area(poly_b)
        assert math.isclose(overlap, 8.0, rel_tol=1e-4)

        # Non-overlapping adjacent rooms -> intersection area == 0.0
        poly_c = Polygon2D([(6.0, 0.0), (12.0, 0.0), (12.0, 6.0), (6.0, 6.0)])
        assert poly_a.intersection_area(poly_c) < 1e-6

    def test_polygon_edge_normals(self):
        # 10m x 8m rectangle in CCW: (0,0) -> (10,0) -> (10,8) -> (0,8)
        rect = Polygon2D([(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)])
        outward = rect.outward_edge_normals()
        inward = rect.inward_edge_normals()

        assert len(outward) == 4
        assert len(inward) == 4

        # Edge 0: (0,0) -> (10,0) (bottom edge). Outward normal points South (0, -1)
        assert outward[0] == Vector2D(0.0, -1.0)
        assert inward[0] == Vector2D(0.0, 1.0)

        # Edge 1: (10,0) -> (10,8) (right edge). Outward normal points East (1, 0)
        assert outward[1] == Vector2D(1.0, 0.0)
        assert inward[1] == Vector2D(-1.0, 0.0)

        # Edge 2: (10,8) -> (0,8) (top edge). Outward normal points North (0, 1)
        assert outward[2] == Vector2D(0.0, 1.0)
        assert inward[2] == Vector2D(0.0, -1.0)

        # Edge 3: (0,8) -> (0,0) (left edge). Outward normal points West (-1, 0)
        assert outward[3] == Vector2D(-1.0, 0.0)
        assert inward[3] == Vector2D(1.0, 0.0)

    def test_u_shaped_polygon_triangulation(self):
        # 8-vertex U-shaped polygon
        # (0,0)->(6,0)->(6,6)->(4,6)->(4,2)->(2,2)->(2,6)->(0,6)
        u_verts = [
            (0.0, 0.0), (6.0, 0.0), (6.0, 6.0), (4.0, 6.0),
            (4.0, 2.0), (2.0, 2.0), (2.0, 6.0), (0.0, 6.0)
        ]
        u_poly = Polygon2D(u_verts)
        assert math.isclose(u_poly.area, 28.0)

        triangles = u_poly.triangulate()
        assert len(triangles) == 6  # 8 - 2 = 6 triangles
        sum_area = sum(t.area for t in triangles)
        assert math.isclose(sum_area, 28.0, rel_tol=1e-5)

        # Ensure all triangles are strictly inside or valid
        for t in triangles:
            assert t.is_valid
            assert t.area > 0.0

    def test_line_slicing_non_intersecting_lines(self):
        poly = Polygon2D([(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)])
        # Line completely outside polygon at x = -5.0
        left_polys, right_polys = poly.slice_by_line(Point2D(-5.0, 0.0), Vector2D(0.0, 1.0))
        assert len(left_polys) == 0 or len(right_polys) == 0
        total_spliced_area = sum(p.area for p in left_polys + right_polys)
        assert math.isclose(total_spliced_area, 100.0, rel_tol=1e-3)

