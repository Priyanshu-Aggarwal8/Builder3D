"""
Pure-Python 2D Computational Geometry Engine for Builder3D.

Zero external C dependencies.
Provides robust 2D representations, vector algebra, segment intersection,
bounding boxes, polygon operations (Shoelace signed area, centroid, CCW winding,
ray-casting point-in-polygon, ear-clipping triangulation, Sutherland-Hodgman clipping,
collinear shared boundary length, line slicing, and pairwise polygon overlap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Union

# Global numerical tolerances
EPSILON: float = 1e-7
AREA_EPSILON: float = 1e-6
COLLINEAR_EPSILON: float = 1e-6


# ==============================================================================
# 1. Vector2D & Point2D
# ==============================================================================

@dataclass(slots=True, frozen=True)
class Vector2D:
    """2D planar vector in (dx, dy)."""

    dx: float
    dy: float

    def __add__(self, other: Vector2D) -> Vector2D:
        if isinstance(other, Vector2D):
            return Vector2D(self.dx + other.dx, self.dy + other.dy)
        return NotImplemented

    def __sub__(self, other: Vector2D) -> Vector2D:
        if isinstance(other, Vector2D):
            return Vector2D(self.dx - other.dx, self.dy - other.dy)
        return NotImplemented

    def __mul__(self, scalar: float) -> Vector2D:
        if isinstance(scalar, (int, float)):
            return Vector2D(self.dx * float(scalar), self.dy * float(scalar))
        return NotImplemented

    def __rmul__(self, scalar: float) -> Vector2D:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2D:
        if isinstance(scalar, (int, float)):
            if abs(scalar) < EPSILON:
                raise ZeroDivisionError("Cannot divide Vector2D by zero")
            return Vector2D(self.dx / float(scalar), self.dy / float(scalar))
        return NotImplemented

    def __neg__(self) -> Vector2D:
        return Vector2D(-self.dx, -self.dy)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Vector2D):
            return False
        return abs(self.dx - other.dx) <= EPSILON and abs(self.dy - other.dy) <= EPSILON

    def length_squared(self) -> float:
        return self.dx * self.dx + self.dy * self.dy

    def length(self) -> float:
        return math.sqrt(self.length_squared())

    def normalize(self) -> Vector2D:
        L = self.length()
        if L < EPSILON:
            return Vector2D(0.0, 0.0)
        return Vector2D(self.dx / L, self.dy / L)

    def dot(self, other: Vector2D) -> float:
        return self.dx * other.dx + self.dy * other.dy

    def cross(self, other: Vector2D) -> float:
        """2D perp-dot product (signed parallelogram area): self.dx * other.dy - self.dy * other.dx."""
        return self.dx * other.dy - self.dy * other.dx

    def perpendicular_left(self) -> Vector2D:
        """Left 90-degree counter-clockwise normal: (-dy, dx)."""
        return Vector2D(-self.dy, self.dx)

    def perpendicular_right(self) -> Vector2D:
        """Right 90-degree clockwise normal: (dy, -dx)."""
        return Vector2D(self.dy, -self.dx)

    def rotate(self, angle_rad: float) -> Vector2D:
        """Rotates vector by angle in radians counter-clockwise."""
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vector2D(
            self.dx * cos_a - self.dy * sin_a,
            self.dx * sin_a + self.dy * cos_a,
        )

    def to_tuple(self) -> Tuple[float, float]:
        return (self.dx, self.dy)


@dataclass(slots=True, frozen=True)
class Point2D:
    """2D planar point in (x, y)."""

    x: float
    y: float

    def __add__(self, vec: Any) -> Point2D:
        if isinstance(vec, Vector2D):
            return Point2D(self.x + vec.dx, self.y + vec.dy)
        elif isinstance(vec, tuple) and len(vec) == 2:
            return Point2D(self.x + float(vec[0]), self.y + float(vec[1]))
        return NotImplemented

    def __sub__(self, other: Any) -> Any:
        if isinstance(other, Point2D):
            return Vector2D(self.x - other.x, self.y - other.y)
        elif isinstance(other, Vector2D):
            return Point2D(self.x - other.dx, self.y - other.dy)
        elif isinstance(other, tuple) and len(other) == 2:
            return Vector2D(self.x - float(other[0]), self.y - float(other[1]))
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Point2D):
            if isinstance(other, (tuple, list)) and len(other) == 2:
                return abs(self.x - float(other[0])) <= EPSILON and abs(self.y - float(other[1])) <= EPSILON
            return False
        return abs(self.x - other.x) <= EPSILON and abs(self.y - other.y) <= EPSILON

    def distance_to(self, other: Point2D) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def distance_squared_to(self, other: Point2D) -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def is_close_to(self, other: Point2D, eps: float = EPSILON) -> bool:
        return (abs(self.x - other.x) <= eps) and (abs(self.y - other.y) <= eps)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, t: Sequence[float]) -> Point2D:
        return cls(float(t[0]), float(t[1]))


# ==============================================================================
# 2. BoundingBox2D
# ==============================================================================

@dataclass(slots=True, frozen=True)
class BoundingBox2D:
    """Axis-Aligned Bounding Box (AABB) in 2D."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return max(0.0, self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return max(0.0, self.max_y - self.min_y)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Point2D:
        return Point2D((self.min_x + self.max_x) * 0.5, (self.min_y + self.max_y) * 0.5)

    def intersects(self, other: BoundingBox2D, eps: float = EPSILON) -> bool:
        """Fast-reject AABB intersection test."""
        if self.max_x < other.min_x - eps or self.min_x > other.max_x + eps:
            return False
        if self.max_y < other.min_y - eps or self.min_y > other.max_y + eps:
            return False
        return True

    def contains_point(self, p: Point2D, eps: float = EPSILON) -> bool:
        return (
            self.min_x - eps <= p.x <= self.max_x + eps
            and self.min_y - eps <= p.y <= self.max_y + eps
        )

    def contains_box(self, other: BoundingBox2D, eps: float = EPSILON) -> bool:
        return (
            self.min_x - eps <= other.min_x
            and self.max_x + eps >= other.max_x
            and self.min_y - eps <= other.min_y
            and self.max_y + eps >= other.max_y
        )

    def union(self, other: BoundingBox2D) -> BoundingBox2D:
        return BoundingBox2D(
            min(self.min_x, other.min_x),
            min(self.min_y, other.min_y),
            max(self.max_x, other.max_x),
            max(self.max_y, other.max_y),
        )

    def intersection(self, other: BoundingBox2D) -> Optional[BoundingBox2D]:
        if not self.intersects(other):
            return None
        return BoundingBox2D(
            max(self.min_x, other.min_x),
            max(self.min_y, other.min_y),
            min(self.max_x, other.max_x),
            min(self.max_y, other.max_y),
        )

    def expanded_by(self, margin: float) -> BoundingBox2D:
        return BoundingBox2D(
            self.min_x - margin,
            self.min_y - margin,
            self.max_x + margin,
            self.max_y + margin,
        )

    @classmethod
    def from_points(cls, points: Sequence[Point2D]) -> BoundingBox2D:
        if not points:
            return cls(0.0, 0.0, 0.0, 0.0)
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return cls(min(xs), min(ys), max(xs), max(ys))


# ==============================================================================
# 3. Segment2D & SegmentIntersection
# ==============================================================================

class IntersectionType(str, Enum):
    NONE = "NONE"
    POINT = "POINT"
    COLINEAR_OVERLAP = "COLINEAR_OVERLAP"


@dataclass(slots=True, frozen=True)
class SegmentIntersection:
    type: IntersectionType
    point: Optional[Point2D] = None
    overlap_segment: Optional[Tuple[Point2D, Point2D]] = None
    t1: Optional[float] = None
    t2: Optional[float] = None


@dataclass(slots=True, frozen=True)
class Segment2D:
    """2D directed line segment from start Point2D to end Point2D."""

    start: Point2D
    end: Point2D

    @property
    def vector(self) -> Vector2D:
        return self.end - self.start

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def length_squared(self) -> float:
        return self.start.distance_squared_to(self.end)

    @property
    def direction(self) -> Vector2D:
        return self.vector.normalize()

    @property
    def normal_left(self) -> Vector2D:
        """Unit normal to the left of the segment direction."""
        return self.direction.perpendicular_left()

    @property
    def normal_right(self) -> Vector2D:
        """Unit normal to the right of the segment direction."""
        return self.direction.perpendicular_right()

    @property
    def midpoint(self) -> Point2D:
        return Point2D((self.start.x + self.end.x) * 0.5, (self.start.y + self.end.y) * 0.5)

    @property
    def bounds(self) -> BoundingBox2D:
        return BoundingBox2D(
            min(self.start.x, self.end.x),
            min(self.start.y, self.end.y),
            max(self.start.x, self.end.x),
            max(self.start.y, self.end.y),
        )

    def point_at(self, t: float) -> Point2D:
        return self.start + (self.vector * t)

    def project_point(self, p: Point2D) -> Tuple[Point2D, float]:
        """Projects point p onto the segment, returning (clamped_projected_point, clamped_t)."""
        v = self.vector
        L2 = self.length_squared
        if L2 < EPSILON:
            return (self.start, 0.0)
        t = ((p.x - self.start.x) * v.dx + (p.y - self.start.y) * v.dy) / L2
        clamped_t = max(0.0, min(1.0, t))
        return (self.point_at(clamped_t), clamped_t)

    def distance_to_point(self, p: Point2D) -> float:
        proj_pt, _ = self.project_point(p)
        return p.distance_to(proj_pt)

    def intersect(self, other: Segment2D) -> SegmentIntersection:
        """
        Computes exact segment-segment intersection.
        Handles non-parallel intersection, collinear overlap intervals, and disjoint/parallel segments.
        """
        # Fast bounding box rejection
        if not self.bounds.intersects(other.bounds, eps=EPSILON):
            return SegmentIntersection(type=IntersectionType.NONE)

        p = self.start
        r = self.vector
        q = other.start
        s = other.vector

        r_cross_s = r.cross(s)
        q_minus_p = q - p
        q_p_cross_r = q_minus_p.cross(r)

        # Case 1: Collinear or parallel
        if abs(r_cross_s) < EPSILON:
            if abs(q_p_cross_r) < EPSILON:
                # Collinear
                L2 = self.length_squared
                if L2 < EPSILON:
                    if other.distance_to_point(p) <= EPSILON:
                        return SegmentIntersection(type=IntersectionType.POINT, point=p, t1=0.0)
                    return SegmentIntersection(type=IntersectionType.NONE)

                t0 = (q - p).dot(r) / L2
                t1 = (other.end - p).dot(r) / L2
                t_min = min(t0, t1)
                t_max = max(t0, t1)
                overlap_start = max(0.0, t_min)
                overlap_end = min(1.0, t_max)

                if overlap_start > overlap_end + EPSILON:
                    return SegmentIntersection(type=IntersectionType.NONE)
                elif abs(overlap_start - overlap_end) <= EPSILON:
                    pt = self.point_at(overlap_start)
                    return SegmentIntersection(type=IntersectionType.POINT, point=pt, t1=overlap_start)
                else:
                    return SegmentIntersection(
                        type=IntersectionType.COLINEAR_OVERLAP,
                        overlap_segment=(self.point_at(overlap_start), self.point_at(overlap_end)),
                        t1=overlap_start,
                        t2=overlap_end,
                    )
            return SegmentIntersection(type=IntersectionType.NONE)

        # Case 2: Non-parallel intersection
        t = q_minus_p.cross(s) / r_cross_s
        u = q_minus_p.cross(r) / r_cross_s

        if (-EPSILON <= t <= 1.0 + EPSILON) and (-EPSILON <= u <= 1.0 + EPSILON):
            clamped_t = max(0.0, min(1.0, t))
            return SegmentIntersection(
                type=IntersectionType.POINT,
                point=self.point_at(clamped_t),
                t1=clamped_t,
                t2=max(0.0, min(1.0, u)),
            )

        return SegmentIntersection(type=IntersectionType.NONE)


# ==============================================================================
# 4. Polygon2D Engine
# ==============================================================================

class Polygon2D:
    """
    Pure-Python 2D Polygon Engine for Builder3D.
    Supports convex and non-convex simple polygons.
    """

    __slots__ = ("_vertices", "_edges", "_bounds", "_signed_area", "_area", "_centroid", "_perimeter")

    def __init__(self, vertices: Sequence[Union[Point2D, Tuple[float, float], Sequence[float]]]) -> None:
        raw_pts: List[Point2D] = []
        for v in vertices:
            if isinstance(v, Point2D):
                raw_pts.append(v)
            elif isinstance(v, (tuple, list)) and len(v) >= 2:
                raw_pts.append(Point2D(float(v[0]), float(v[1])))
            else:
                raise TypeError(f"Invalid vertex type: {type(v)}")

        clean_pts = self._remove_collinear_and_duplicates(raw_pts)
        if len(clean_pts) < 3:
            raise ValueError(f"Polygon2D requires at least 3 non-collinear vertices, got {len(clean_pts)}")

        self._vertices: List[Point2D] = clean_pts
        self._edges: Optional[List[Segment2D]] = None
        self._bounds: Optional[BoundingBox2D] = None
        self._signed_area: Optional[float] = None
        self._area: Optional[float] = None
        self._centroid: Optional[Point2D] = None
        self._perimeter: Optional[float] = None

    @staticmethod
    def _remove_collinear_and_duplicates(pts: List[Point2D]) -> List[Point2D]:
        if not pts:
            return []

        # 1. Remove closed end duplicate if first equals last
        if len(pts) > 1 and pts[0].is_close_to(pts[-1]):
            pts = pts[:-1]

        # 2. Filter consecutive duplicate vertices
        filtered: List[Point2D] = []
        for p in pts:
            if not filtered or not p.is_close_to(filtered[-1]):
                filtered.append(p)
        if len(filtered) > 1 and filtered[0].is_close_to(filtered[-1]):
            filtered.pop()

        # 3. Filter intermediate collinear vertices along same edge
        if len(filtered) < 3:
            return filtered

        result: List[Point2D] = []
        m = len(filtered)
        for i in range(m):
            prev_p = filtered[(i - 1) % m]
            curr_p = filtered[i]
            next_p = filtered[(i + 1) % m]

            v1 = curr_p - prev_p
            v2 = next_p - curr_p
            cross_prod = v1.cross(v2)
            # If cross product is near 0 and dot product > 0, curr_p is on the segment between prev and next
            if abs(cross_prod) < COLLINEAR_EPSILON and v1.dot(v2) > 0:
                continue
            result.append(curr_p)

        return result

    @property
    def vertices(self) -> List[Point2D]:
        return self._vertices

    @property
    def vertex_tuples(self) -> List[Tuple[float, float]]:
        return [p.to_tuple() for p in self._vertices]

    @property
    def vertex_count(self) -> int:
        return len(self._vertices)

    @property
    def edges(self) -> List[Segment2D]:
        if self._edges is None:
            n = len(self._vertices)
            self._edges = [Segment2D(self._vertices[i], self._vertices[(i + 1) % n]) for i in range(n)]
        return self._edges

    @property
    def bounds(self) -> BoundingBox2D:
        if self._bounds is None:
            self._bounds = BoundingBox2D.from_points(self._vertices)
        return self._bounds

    @property
    def signed_area(self) -> float:
        if self._signed_area is None:
            n = len(self._vertices)
            sa = 0.0
            for i in range(n):
                p1 = self._vertices[i]
                p2 = self._vertices[(i + 1) % n]
                sa += (p1.x * p2.y - p2.x * p1.y)
            self._signed_area = sa * 0.5
        return self._signed_area

    @property
    def area(self) -> float:
        if self._area is None:
            self._area = abs(self.signed_area)
        return self._area

    @property
    def is_ccw(self) -> bool:
        """True if vertices are ordered Counter-Clockwise (positive signed area)."""
        return self.signed_area > 0.0

    @property
    def perimeter(self) -> float:
        if self._perimeter is None:
            self._perimeter = sum(e.length for e in self.edges)
        return self._perimeter

    @property
    def centroid(self) -> Point2D:
        if self._centroid is None:
            sa = self.signed_area
            if abs(sa) < AREA_EPSILON:
                n = len(self._vertices)
                self._centroid = Point2D(
                    sum(p.x for p in self._vertices) / n,
                    sum(p.y for p in self._vertices) / n,
                )
            else:
                n = len(self._vertices)
                cx = 0.0
                cy = 0.0
                for i in range(n):
                    p1 = self._vertices[i]
                    p2 = self._vertices[(i + 1) % n]
                    factor = (p1.x * p2.y - p2.x * p1.y)
                    cx += (p1.x + p2.x) * factor
                    cy += (p1.y + p2.y) * factor
                factor_inv = 1.0 / (6.0 * sa)
                self._centroid = Point2D(cx * factor_inv, cy * factor_inv)
        return self._centroid

    def ensure_ccw(self) -> Polygon2D:
        """Returns a copy of this polygon oriented counter-clockwise."""
        if self.is_ccw:
            return self
        return Polygon2D(list(reversed(self._vertices)))

    def outward_edge_normals(self) -> List[Vector2D]:
        """Calculates outward unit normal vector for each edge of CCW polygon."""
        ccw_poly = self.ensure_ccw()
        return [e.normal_right for e in ccw_poly.edges]

    def inward_edge_normals(self) -> List[Vector2D]:
        """Calculates inward unit normal vector for each edge of CCW polygon."""
        ccw_poly = self.ensure_ccw()
        return [e.normal_left for e in ccw_poly.edges]

    def contains_point(self, p: Point2D, include_boundary: bool = True) -> bool:
        """
        Tests whether point p is inside the polygon using Ray-Casting.
        Properly handles half-open vertical span [min_y, max_y) and vertices on ray.
        """
        # Fast bounding box rejection
        if not self.bounds.contains_point(p, eps=EPSILON):
            return False

        # Edge boundary check
        if include_boundary:
            for edge in self.edges:
                if edge.distance_to_point(p) <= EPSILON:
                    return True

        n = len(self._vertices)
        inside = False
        for i in range(n):
            p1 = self._vertices[i]
            p2 = self._vertices[(i + 1) % n]

            # Half-open vertical span
            if ((p1.y > p.y) != (p2.y > p.y)):
                # Compute X-intercept of edge with ray y = p.y
                x_int = p1.x + (p.y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y)
                if x_int > p.x:
                    inside = not inside

        return inside

    def is_simple(self) -> bool:
        """True if no non-adjacent edges intersect."""
        edges = self.edges
        n = len(edges)
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue  # Adjacent at wrap-around
                inter = edges[i].intersect(edges[j])
                if inter.type != IntersectionType.NONE:
                    return False
        return True

    def is_valid(self) -> bool:
        """True if polygon has >= 3 vertices, positive area, and simple topology."""
        return len(self._vertices) >= 3 and self.area > AREA_EPSILON and self.is_simple()

    def shared_boundary_length(self, other: Polygon2D) -> float:
        """
        Computes total shared 1D contact length along collinear boundary edges.
        Used for room adjacency and exterior wall detection.
        """
        if not self.bounds.intersects(other.bounds, eps=EPSILON):
            return 0.0

        total_length = 0.0
        for e1 in self.edges:
            for e2 in other.edges:
                inter = e1.intersect(e2)
                if inter.type == IntersectionType.COLINEAR_OVERLAP and inter.overlap_segment:
                    p1, p2 = inter.overlap_segment
                    total_length += p1.distance_to(p2)
        return total_length

    def shared_exterior_length(self, building_boundary: Polygon2D) -> float:
        """Computes shared frontage length with exterior building boundary."""
        return self.shared_boundary_length(building_boundary)

    # --------------------------------------------------------------------------
    # Triangulation (Ear-Clipping)
    # --------------------------------------------------------------------------

    def triangulate(self) -> List[Polygon2D]:
        """
        Triangulates a simple polygon into a list of triangular Polygon2Ds
        using the Ear-Clipping algorithm (O(N^2)). Works on convex and concave polygons.
        """
        poly = self.ensure_ccw()
        pts = list(poly.vertices)
        triangles: List[Polygon2D] = []

        def _is_ear(prev_idx: int, ear_idx: int, next_idx: int, current_pts: List[Point2D]) -> bool:
            a = current_pts[prev_idx]
            b = current_pts[ear_idx]
            c = current_pts[next_idx]

            # 1. Must be convex (strictly CCW turn)
            v1 = b - a
            v2 = c - b
            if v1.cross(v2) <= EPSILON:
                return False

            # 2. No other vertex in current_pts is inside or on boundary of triangle ABC
            for k in range(len(current_pts)):
                if k in (prev_idx, ear_idx, next_idx):
                    continue
                pt = current_pts[k]
                if _point_in_triangle(pt, a, b, c):
                    return False

            # 3. The chord (a -> c) midpoint must be inside the polygon
            chord_mid = Point2D((a.x + c.x) * 0.5, (a.y + c.y) * 0.5)
            if not self.contains_point(chord_mid, include_boundary=True):
                return False

            return True

        def _point_in_triangle(p: Point2D, a: Point2D, b: Point2D, c: Point2D) -> bool:
            cp1 = (b - a).cross(p - a)
            cp2 = (c - b).cross(p - b)
            cp3 = (a - c).cross(p - c)
            return (cp1 >= -EPSILON and cp2 >= -EPSILON and cp3 >= -EPSILON)

        max_iterations = len(pts) * 3
        iter_count = 0

        while len(pts) > 3 and iter_count < max_iterations:
            iter_count += 1
            n = len(pts)
            ear_found = False
            for i in range(n):
                prev_i = (i - 1) % n
                next_i = (i + 1) % n
                if _is_ear(prev_i, i, next_i, pts):
                    tri_verts = [pts[prev_i], pts[i], pts[next_i]]
                    try:
                        triangles.append(Polygon2D(tri_verts))
                    except ValueError:
                        pass
                    pts.pop(i)
                    ear_found = True
                    break

            if not ear_found:
                # Fallback: take first valid CCW triplet
                for i in range(n):
                    prev_i = (i - 1) % n
                    next_i = (i + 1) % n
                    if (pts[i] - pts[prev_i]).cross(pts[next_i] - pts[i]) > EPSILON:
                        try:
                            triangles.append(Polygon2D([pts[prev_i], pts[i], pts[next_i]]))
                        except ValueError:
                            pass
                        pts.pop(i)
                        break
                else:
                    break

        if len(pts) == 3:
            try:
                triangles.append(Polygon2D(pts))
            except ValueError:
                pass

        return triangles

    # --------------------------------------------------------------------------
    # Sutherland-Hodgman Convex Clipping & Arbitrary Intersection Area
    # --------------------------------------------------------------------------

    @staticmethod
    def _clip_polygon_to_halfplane(
        subject_vertices: List[Point2D], line_p1: Point2D, line_p2: Point2D
    ) -> List[Point2D]:
        """
        Clips subject_vertices against the half-plane to the LEFT of directed line line_p1 -> line_p2.
        Points P with (line_p2 - line_p1).cross(P - line_p1) >= -EPSILON are inside.
        """
        output_list: List[Point2D] = []
        if not subject_vertices:
            return output_list

        line_vec = line_p2 - line_p1

        def _is_inside(p: Point2D) -> bool:
            return line_vec.cross(p - line_p1) >= -EPSILON

        def _line_intersection(p_a: Point2D, p_b: Point2D) -> Point2D:
            s_vec = p_b - p_a
            denom = line_vec.cross(s_vec)
            if abs(denom) < EPSILON:
                return p_a
            t = (p_a - line_p1).cross(s_vec) / denom
            return line_p1 + (line_vec * t)

        n = len(subject_vertices)
        for i in range(n):
            curr_pt = subject_vertices[i]
            prev_pt = subject_vertices[(i - 1) % n]

            curr_in = _is_inside(curr_pt)
            prev_in = _is_inside(prev_pt)

            if curr_in:
                if not prev_in:
                    output_list.append(_line_intersection(prev_pt, curr_pt))
                output_list.append(curr_pt)
            elif prev_in:
                output_list.append(_line_intersection(prev_pt, curr_pt))

        return output_list

    def clip_convex(self, convex_clip_poly: Polygon2D) -> Optional[Polygon2D]:
        """
        Clips self against a convex polygon using the Sutherland-Hodgman algorithm.
        Returns clipped Polygon2D or None if disjoint.
        """
        clip_poly = convex_clip_poly.ensure_ccw()
        output_pts = list(self.vertices)

        for edge in clip_poly.edges:
            output_pts = self._clip_polygon_to_halfplane(output_pts, edge.start, edge.end)
            if len(output_pts) < 3:
                return None

        try:
            res = Polygon2D(output_pts)
            if res.area > AREA_EPSILON:
                return res
        except ValueError:
            pass
        return None

    def intersection_area(self, other: Polygon2D) -> float:
        """
        Computes exact intersection area between self and other.
        Works for arbitrary convex or non-convex simple polygons by decomposing
        into triangles via Ear-Clipping and clipping pairs with Sutherland-Hodgman.
        """
        if not self.bounds.intersects(other.bounds, eps=EPSILON):
            return 0.0

        triangles_self = self.triangulate()
        triangles_other = other.triangulate()

        total_intersection_area = 0.0
        for t1 in triangles_self:
            for t2 in triangles_other:
                if not t1.bounds.intersects(t2.bounds, eps=EPSILON):
                    continue
                clipped = t1.clip_convex(t2)
                if clipped is not None:
                    total_intersection_area += clipped.area

        return total_intersection_area

    # --------------------------------------------------------------------------
    # Line Slicing
    # --------------------------------------------------------------------------

    def slice_by_line(
        self, line_point: Point2D, line_dir: Vector2D
    ) -> Tuple[List[Polygon2D], List[Polygon2D]]:
        """
        Slices polygon by infinite directed line (line_point + t * line_dir).
        Returns (left_polygons, right_polygons).
        """
        dir_norm = line_dir.normalize()
        p1 = line_point
        p2 = line_point + dir_norm

        # Left half-plane (p1 -> p2)
        left_pts = self._clip_polygon_to_halfplane(self.vertices, p1, p2)
        # Right half-plane (p2 -> p1)
        right_pts = self._clip_polygon_to_halfplane(self.vertices, p2, p1)

        left_polys: List[Polygon2D] = []
        right_polys: List[Polygon2D] = []

        if len(left_pts) >= 3:
            try:
                poly_left = Polygon2D(left_pts)
                if poly_left.area > AREA_EPSILON:
                    left_polys.append(poly_left)
            except ValueError:
                pass

        if len(right_pts) >= 3:
            try:
                poly_right = Polygon2D(right_pts)
                if poly_right.area > AREA_EPSILON:
                    right_polys.append(poly_right)
            except ValueError:
                pass

        return (left_polys, right_polys)

    def __repr__(self) -> str:
        return f"Polygon2D(vertices={self.vertex_tuples}, area={self.area:.2f})"
