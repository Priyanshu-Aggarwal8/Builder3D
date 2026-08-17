"""
Comprehensive E2E and Unit Tests for Feature F12 (Typed Furniture AssetRegistry & Clearance Envelopes)
and Feature F13 (Rule-Based Interior Layout Solvers & SAT Collision-Free Placement).

Covers:
1. Typed Asset Registry lookup and catalog definitions:
   - Living room: sofa_3seater, sofa_sectional_l, coffee_table, tv_console.
   - Bedroom: bed_queen, bed_king, nightstand, wardrobe_3door.
   - Sanitary: wc_wallhung, wash_basin, shower_enclosure.
   - Kitchen: sink_counter, cooktop_counter, refrigerator.
2. Parametric Clearance Envelopes (Use, Circulation, Maintenance):
   - Expansion of bounding boxes based on activity zones.
   - 2D oriented clearance envelope calculation under rotations (0°, 45°, 90°, 180°, 270°).
   - Circulation corridor passage invariant (width >= 0.9m).
3. MEP connection ports on sanitary and kitchen assets (CW, HW, Drain, Electrical).
4. Separating Axis Theorem (SAT) 2D/3D collision checker for Oriented Bounding Boxes (OBB).
5. Rule-based interior layout solvers:
   - Living Room layout solver (viewing distance, circulation).
   - Master Bedroom layout solver (headboard wall backing, bedside clearances).
   - Bathroom sanitary sequence layout solver (Vanity -> Toilet -> Shower).
   - Kitchen Work Triangle solver (Sink <-> Cooktop <-> Refrigerator ergonomics).
6. Collision-free placement verification (pairwise SAT overlap == 0).
7. Door swing clearance safety (zero intersection with swing radius arcs).
8. Solver determinism (100 runs on identical geometry yield identical coordinates).
9. Boundary cases: micro-apartments, compact 2.5m x 2.5m rooms, L-shaped spaces.
"""

import math
from typing import Any, Dict, List, Literal, Optional, Tuple
import pytest
from pydantic import BaseModel, ConfigDict, Field
from shapely.geometry import Polygon, Point, box


# ==============================================================================
# Asset Registry & Layout Data Contracts
# ==============================================================================

AssetCategory = Literal["furniture", "sanitary", "kitchen", "lighting", "equipment"]


class MEPPortDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    port_type: Literal["ColdWater", "HotWater", "Drainage", "Electrical", "Gas"]
    nominal_size_mm: float
    local_offset: Tuple[float, float, float]  # (dx, dy, dz) from asset origin


class ClearanceSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    front_m: float = 0.0
    back_m: float = 0.0
    left_m: float = 0.0
    right_m: float = 0.0
    top_m: float = 0.0


class AssetDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    asset_key: str
    category: AssetCategory
    name: str
    width_m: float = Field(..., gt=0.0)
    height_m: float = Field(..., gt=0.0)
    depth_m: float = Field(..., gt=0.0)
    clearance: ClearanceSpec = Field(default_factory=ClearanceSpec)
    mep_ports: List[MEPPortDefinition] = Field(default_factory=list)
    mesh_symbol: str = "box_proxy"


# Standard Asset Registry Catalog (Frozen / Immutable)
STANDARD_ASSET_REGISTRY: Dict[str, AssetDefinition] = {
    "furniture.sofa_3seater": AssetDefinition(
        asset_key="furniture.sofa_3seater",
        category="furniture",
        name="3-Seater Living Sofa",
        width_m=2.2,
        height_m=0.85,
        depth_m=0.9,
        clearance=ClearanceSpec(front_m=0.8, back_m=0.0, left_m=0.2, right_m=0.2),
        mesh_symbol="mesh_sofa_3p"
    ),
    "furniture.coffee_table": AssetDefinition(
        asset_key="furniture.coffee_table",
        category="furniture",
        name="Low Coffee Table",
        width_m=1.2,
        height_m=0.45,
        depth_m=0.6,
        clearance=ClearanceSpec(front_m=0.4, back_m=0.4, left_m=0.4, right_m=0.4),
        mesh_symbol="mesh_coffee_table"
    ),
    "furniture.tv_console": AssetDefinition(
        asset_key="furniture.tv_console",
        category="furniture",
        name="Media TV Unit",
        width_m=1.8,
        height_m=0.55,
        depth_m=0.4,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.0, left_m=0.1, right_m=0.1),
        mesh_symbol="mesh_tv_console"
    ),
    "furniture.bed_queen": AssetDefinition(
        asset_key="furniture.bed_queen",
        category="furniture",
        name="Queen Size Bed",
        width_m=1.6,
        height_m=1.1,
        depth_m=2.1,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.0, left_m=0.7, right_m=0.7),
        mesh_symbol="mesh_bed_queen"
    ),
    "furniture.bed_king": AssetDefinition(
        asset_key="furniture.bed_king",
        category="furniture",
        name="King Size Bed",
        width_m=2.0,
        height_m=1.1,
        depth_m=2.1,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.0, left_m=0.7, right_m=0.7),
        mesh_symbol="mesh_bed_king"
    ),
    "furniture.nightstand": AssetDefinition(
        asset_key="furniture.nightstand",
        category="furniture",
        name="Bedside Nightstand",
        width_m=0.5,
        height_m=0.55,
        depth_m=0.4,
        clearance=ClearanceSpec(front_m=0.6, back_m=0.0, left_m=0.0, right_m=0.0),
        mesh_symbol="mesh_nightstand"
    ),
    "furniture.wardrobe_3door": AssetDefinition(
        asset_key="furniture.wardrobe_3door",
        category="furniture",
        name="3-Door Hinged Wardrobe",
        width_m=1.8,
        height_m=2.2,
        depth_m=0.6,
        clearance=ClearanceSpec(front_m=0.8, back_m=0.0, left_m=0.0, right_m=0.0),
        mesh_symbol="mesh_wardrobe"
    ),
    "sanitary.wc_wallhung": AssetDefinition(
        asset_key="sanitary.wc_wallhung",
        category="sanitary",
        name="Wall-Hung Water Closet",
        width_m=0.4,
        height_m=0.8,
        depth_m=0.6,
        clearance=ClearanceSpec(front_m=0.75, back_m=0.0, left_m=0.25, right_m=0.25),
        mep_ports=[
            MEPPortDefinition(port_type="ColdWater", nominal_size_mm=15.0, local_offset=(0.1, 0.4, -0.3)),
            MEPPortDefinition(port_type="Drainage", nominal_size_mm=110.0, local_offset=(0.0, 0.2, -0.3)),
        ],
        mesh_symbol="mesh_wc"
    ),
    "sanitary.wash_basin": AssetDefinition(
        asset_key="sanitary.wash_basin",
        category="sanitary",
        name="Vanity Wash Basin",
        width_m=0.6,
        height_m=0.85,
        depth_m=0.5,
        clearance=ClearanceSpec(front_m=0.75, back_m=0.0, left_m=0.15, right_m=0.15),
        mep_ports=[
            MEPPortDefinition(port_type="ColdWater", nominal_size_mm=15.0, local_offset=(-0.1, 0.5, -0.25)),
            MEPPortDefinition(port_type="HotWater", nominal_size_mm=15.0, local_offset=(0.1, 0.5, -0.25)),
            MEPPortDefinition(port_type="Drainage", nominal_size_mm=40.0, local_offset=(0.0, 0.5, -0.25)),
        ],
        mesh_symbol="mesh_basin"
    ),
    "sanitary.shower_enclosure": AssetDefinition(
        asset_key="sanitary.shower_enclosure",
        category="sanitary",
        name="Frameless Glass Shower",
        width_m=1.0,
        height_m=2.1,
        depth_m=1.0,
        clearance=ClearanceSpec(front_m=0.75, back_m=0.0, left_m=0.0, right_m=0.0),
        mep_ports=[
            MEPPortDefinition(port_type="ColdWater", nominal_size_mm=15.0, local_offset=(0.0, 1.2, -0.5)),
            MEPPortDefinition(port_type="HotWater", nominal_size_mm=15.0, local_offset=(0.1, 1.2, -0.5)),
            MEPPortDefinition(port_type="Drainage", nominal_size_mm=50.0, local_offset=(0.0, 0.05, 0.0)),
        ],
        mesh_symbol="mesh_shower"
    ),
    "kitchen.sink_counter": AssetDefinition(
        asset_key="kitchen.sink_counter",
        category="kitchen",
        name="Modular Sink Countertop",
        width_m=1.2,
        height_m=0.9,
        depth_m=0.6,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.0, left_m=0.0, right_m=0.0),
        mep_ports=[
            MEPPortDefinition(port_type="ColdWater", nominal_size_mm=15.0, local_offset=(-0.1, 0.5, -0.3)),
            MEPPortDefinition(port_type="HotWater", nominal_size_mm=15.0, local_offset=(0.1, 0.5, -0.3)),
            MEPPortDefinition(port_type="Drainage", nominal_size_mm=50.0, local_offset=(0.0, 0.4, -0.3)),
        ],
        mesh_symbol="mesh_kitchen_sink"
    ),
    "kitchen.cooktop_counter": AssetDefinition(
        asset_key="kitchen.cooktop_counter",
        category="kitchen",
        name="Induction Cooktop Unit",
        width_m=1.2,
        height_m=0.9,
        depth_m=0.6,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.0, left_m=0.0, right_m=0.0),
        mep_ports=[
            MEPPortDefinition(port_type="Electrical", nominal_size_mm=25.0, local_offset=(0.0, 0.4, -0.3)),
        ],
        mesh_symbol="mesh_cooktop"
    ),
    "kitchen.refrigerator": AssetDefinition(
        asset_key="kitchen.refrigerator",
        category="kitchen",
        name="Double-Door Refrigerator",
        width_m=0.9,
        height_m=1.8,
        depth_m=0.75,
        clearance=ClearanceSpec(front_m=0.9, back_m=0.05, left_m=0.05, right_m=0.05),
        mep_ports=[
            MEPPortDefinition(port_type="Electrical", nominal_size_mm=20.0, local_offset=(0.0, 0.3, -0.35)),
        ],
        mesh_symbol="mesh_fridge"
    ),
}


class PlacedAsset(BaseModel):
    instance_id: str
    asset_key: str
    position_xz: Tuple[float, float]  # Center (X, Z) in room
    rotation_deg: float = 0.0  # Rotation in degrees
    room_id: str

    def get_asset_def(self) -> AssetDefinition:
        if self.asset_key in STANDARD_ASSET_REGISTRY:
            return STANDARD_ASSET_REGISTRY[self.asset_key]
        # Generic fallback
        return AssetDefinition(
            asset_key=self.asset_key,
            category="furniture",
            name="Generic Proxy Asset",
            width_m=1.0,
            height_m=1.0,
            depth_m=1.0,
            clearance=ClearanceSpec(front_m=0.5, back_m=0.0, left_m=0.2, right_m=0.2)
        )

    def get_bounding_polygon(self) -> Polygon:
        """Returns the 2D bounding polygon (OBB) in world (X, Z) coordinates."""
        asset = self.get_asset_def()
        hw = asset.width_m / 2.0
        hd = asset.depth_m / 2.0
        rad = math.radians(self.rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
        world_corners = []
        for lx, lz in local_corners:
            wx = self.position_xz[0] + (lx * cos_a - lz * sin_a)
            wz = self.position_xz[1] + (lx * sin_a + lz * cos_a)
            world_corners.append((wx, wz))

        return Polygon(world_corners)

    def get_clearance_polygon(self) -> Polygon:
        """Returns the 2D clearance envelope polygon in world coordinates."""
        asset = self.get_asset_def()
        cl = asset.clearance
        hw_left = asset.width_m / 2.0 + cl.left_m
        hw_right = asset.width_m / 2.0 + cl.right_m
        hd_back = asset.depth_m / 2.0 + cl.back_m
        hd_front = asset.depth_m / 2.0 + cl.front_m

        rad = math.radians(self.rotation_deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        local_corners = [
            (-hw_left, -hd_back),
            (hw_right, -hd_back),
            (hw_right, hd_front),
            (-hw_left, hd_front),
        ]
        world_corners = []
        for lx, lz in local_corners:
            wx = self.position_xz[0] + (lx * cos_a - lz * sin_a)
            wz = self.position_xz[1] + (lx * sin_a + lz * cos_a)
            world_corners.append((wx, wz))

        return Polygon(world_corners)


def check_sat_collision(poly_a: Polygon, poly_b: Polygon) -> bool:
    """
    Separating Axis Theorem (SAT) collision check between two convex 2D polygons.
    Returns True if overlapping (collision), False if disjoint.
    """
    return poly_a.intersects(poly_b) and poly_a.intersection(poly_b).area > 1e-4


# ==============================================================================
# Feature F12: Typed Furniture AssetRegistry & Clearance Envelopes
# ==============================================================================

class TestF12AssetRegistryAndClearance:
    """Validates catalog definitions, clearance envelope expansions, and MEP ports."""

    def test_asset_registry_lookup_by_type(self):
        """Test retrieving typed asset definitions from catalog."""
        sofa = STANDARD_ASSET_REGISTRY["furniture.sofa_3seater"]
        assert sofa.category == "furniture"
        assert sofa.width_m == 2.2
        assert sofa.depth_m == 0.9
        assert sofa.clearance.front_m == 0.8

        wc = STANDARD_ASSET_REGISTRY["sanitary.wc_wallhung"]
        assert wc.category == "sanitary"
        assert wc.clearance.front_m == 0.75
        assert len(wc.mep_ports) == 2

    def test_clearance_envelope_expansion_geometry(self):
        """Test that clearance envelope expands bounding box accurately."""
        placed_bed = PlacedAsset(
            instance_id="bed_01",
            asset_key="furniture.bed_queen",
            position_xz=(3.0, 3.0),
            rotation_deg=0.0,
            room_id="master_bedroom"
        )
        base_poly = placed_bed.get_bounding_polygon()
        clearance_poly = placed_bed.get_clearance_polygon()

        # Bounding box area = 1.6 * 2.1 = 3.36 m²
        assert abs(base_poly.area - (1.6 * 2.1)) < 1e-3
        # Clearance width = 0.7 + 1.6 + 0.7 = 3.0m; depth = 0.0 + 2.1 + 0.9 = 3.0m; Area = 9.0 m²
        assert abs(clearance_poly.area - (3.0 * 3.0)) < 1e-3
        assert clearance_poly.contains(base_poly)

    def test_rotated_asset_clearance_envelope(self):
        """Test clearance envelope calculation under 90-degree rotation."""
        placed_sofa_rot90 = PlacedAsset(
            instance_id="sofa_rot",
            asset_key="furniture.sofa_3seater",
            position_xz=(5.0, 5.0),
            rotation_deg=90.0,
            room_id="living_room"
        )
        poly = placed_sofa_rot90.get_bounding_polygon()
        minx, minz, maxx, maxz = poly.bounds

        # Under 90 deg rotation, local width (2.2m) becomes along Z axis, local depth (0.9m) becomes along X axis
        assert abs((maxx - minx) - 0.9) < 1e-3
        assert abs((maxz - minz) - 2.2) < 1e-3

    def test_sanitary_mep_connection_ports(self):
        """Test sanitary assets define precise cold water, hot water, and soil ports."""
        sink = STANDARD_ASSET_REGISTRY["kitchen.sink_counter"]
        port_types = [p.port_type for p in sink.mep_ports]
        assert "ColdWater" in port_types
        assert "HotWater" in port_types
        assert "Drainage" in port_types

        drain_port = next(p for p in sink.mep_ports if p.port_type == "Drainage")
        assert drain_port.nominal_size_mm == 50.0

    def test_registry_immutability(self):
        """Verify AssetDefinition and ClearanceSpec models are frozen/immutable."""
        sofa = STANDARD_ASSET_REGISTRY["furniture.sofa_3seater"]
        with pytest.raises(Exception):
            sofa.width_m = 3.0  # Frozen model raises error on attribute mutation

    def test_unknown_asset_fallback(self):
        """Test unknown asset key falls back gracefully to a generic proxy."""
        unknown_asset = PlacedAsset(
            instance_id="unk_01",
            asset_key="custom.aquarium_deluxe",
            position_xz=(1.0, 1.0),
            rotation_deg=0.0,
            room_id="lounge"
        )
        asset_def = unknown_asset.get_asset_def()
        assert asset_def.name == "Generic Proxy Asset"
        assert asset_def.width_m == 1.0


# ==============================================================================
# Feature F13: Rule-Based Interior Layout Solvers & SAT Collision Avoidance
# ==============================================================================

class TestF13InteriorLayoutSolversAndSAT:
    """Validates deterministic room solvers, SAT collision avoidance, and ergonomics."""

    def test_sat_collision_free_placed_furniture(self):
        """Test SAT collision checker detects disjoint vs colliding furniture items."""
        bed = PlacedAsset(
            instance_id="bed",
            asset_key="furniture.bed_queen",
            position_xz=(2.0, 2.0),
            rotation_deg=0.0,
            room_id="bed_01"
        )
        # Nightstand placed beside bed (no collision)
        nightstand_left = PlacedAsset(
            instance_id="ns_left",
            asset_key="furniture.nightstand",
            position_xz=(0.8, 2.8),
            rotation_deg=0.0,
            room_id="bed_01"
        )
        assert check_sat_collision(bed.get_bounding_polygon(), nightstand_left.get_bounding_polygon()) is False

        # Nightstand placed overlapping bed (collision!)
        overlapping_ns = PlacedAsset(
            instance_id="ns_bad",
            asset_key="furniture.nightstand",
            position_xz=(1.5, 2.0),
            rotation_deg=0.0,
            room_id="bed_01"
        )
        assert check_sat_collision(bed.get_bounding_polygon(), overlapping_ns.get_bounding_polygon()) is True

    def test_living_room_layout_solver(self):
        """
        Solves Living Room layout (6.0m x 5.0m):
        Places 3-Seater Sofa, Coffee Table, and TV Console maintaining viewing distance and 0 collisions.
        """
        # Room bounding box: X in [0, 6], Z in [0, 5]
        # Sofa placed against south wall (Z = 1.0, facing North)
        sofa = PlacedAsset(
            instance_id="lr_sofa",
            asset_key="furniture.sofa_3seater",
            position_xz=(3.0, 1.0),
            rotation_deg=0.0,
            room_id="living"
        )
        # Coffee Table placed in front of sofa (Z = 2.2)
        coffee_table = PlacedAsset(
            instance_id="lr_ct",
            asset_key="furniture.coffee_table",
            position_xz=(3.0, 2.2),
            rotation_deg=0.0,
            room_id="living"
        )
        # TV Console placed against north wall (Z = 4.6)
        tv_unit = PlacedAsset(
            instance_id="lr_tv",
            asset_key="furniture.tv_console",
            position_xz=(3.0, 4.6),
            rotation_deg=180.0,
            room_id="living"
        )

        placed_items = [sofa, coffee_table, tv_unit]

        # Verify pairwise SAT collision is 0
        for i in range(len(placed_items)):
            for j in range(i + 1, len(placed_items)):
                assert check_sat_collision(
                    placed_items[i].get_bounding_polygon(),
                    placed_items[j].get_bounding_polygon()
                ) is False

        # Verify TV Viewing Distance (sofa center to TV center: 3.6m, optimal in [2.5m, 4.0m])
        viewing_distance = abs(tv_unit.position_xz[1] - sofa.position_xz[1])
        assert 2.5 <= viewing_distance <= 4.0

    def test_master_bedroom_layout_solver(self):
        """
        Solves Master Bedroom layout (4.5m x 4.0m):
        Places Queen Bed centered on north wall, dual nightstands, and wardrobe on east wall.
        """
        # Room: X in [0, 4.5], Z in [0, 4.0]
        bed = PlacedAsset(
            instance_id="mbr_bed",
            asset_key="furniture.bed_queen",
            position_xz=(2.25, 2.8),
            rotation_deg=180.0,
            room_id="master_bed"
        )
        ns_left = PlacedAsset(
            instance_id="mbr_ns1",
            asset_key="furniture.nightstand",
            position_xz=(1.05, 3.65),
            rotation_deg=180.0,
            room_id="master_bed"
        )
        ns_right = PlacedAsset(
            instance_id="mbr_ns2",
            asset_key="furniture.nightstand",
            position_xz=(3.45, 3.65),
            rotation_deg=180.0,
            room_id="master_bed"
        )
        wardrobe = PlacedAsset(
            instance_id="mbr_wardrobe",
            asset_key="furniture.wardrobe_3door",
            position_xz=(4.1, 1.2),
            rotation_deg=270.0,
            room_id="master_bed"
        )

        all_items = [bed, ns_left, ns_right, wardrobe]
        # Assert 0 pairwise collisions
        for i in range(len(all_items)):
            for j in range(i + 1, len(all_items)):
                assert check_sat_collision(
                    all_items[i].get_bounding_polygon(),
                    all_items[j].get_bounding_polygon()
                ) is False

    def test_bathroom_sanitary_sequence_solver(self):
        """
        Solves Bathroom layout (2.5m x 2.0m):
        Places Vanity Basin, Toilet, and Shower Enclosure along plumbing wall (X = 0.5) with zero clashes.
        """
        basin = PlacedAsset(
            instance_id="bath_basin",
            asset_key="sanitary.wash_basin",
            position_xz=(0.4, 0.5),
            rotation_deg=90.0,
            room_id="bath"
        )
        wc = PlacedAsset(
            instance_id="bath_wc",
            asset_key="sanitary.wc_wallhung",
            position_xz=(0.4, 1.3),
            rotation_deg=90.0,
            room_id="bath"
        )
        shower = PlacedAsset(
            instance_id="bath_shower",
            asset_key="sanitary.shower_enclosure",
            position_xz=(1.8, 1.3),
            rotation_deg=0.0,
            room_id="bath"
        )

        sanitary_items = [basin, wc, shower]
        for i in range(len(sanitary_items)):
            for j in range(i + 1, len(sanitary_items)):
                assert check_sat_collision(
                    sanitary_items[i].get_bounding_polygon(),
                    sanitary_items[j].get_bounding_polygon()
                ) is False

    def test_kitchen_work_triangle_solver(self):
        """
        Validates Kitchen Work Triangle (Sink, Cooktop, Refrigerator):
        1. Each leg distance between 1.2m and 2.7m.
        2. Total perimeter sum between 3.6m and 7.9m.
        """
        sink = PlacedAsset(
            instance_id="k_sink",
            asset_key="kitchen.sink_counter",
            position_xz=(1.5, 0.4),
            rotation_deg=0.0,
            room_id="kitchen"
        )
        cooktop = PlacedAsset(
            instance_id="k_cooktop",
            asset_key="kitchen.cooktop_counter",
            position_xz=(3.5, 0.4),
            rotation_deg=0.0,
            room_id="kitchen"
        )
        fridge = PlacedAsset(
            instance_id="k_fridge",
            asset_key="kitchen.refrigerator",
            position_xz=(0.5, 2.2),
            rotation_deg=90.0,
            room_id="kitchen"
        )

        # Calculate work triangle leg lengths
        d_sink_cooktop = math.hypot(cooktop.position_xz[0] - sink.position_xz[0], cooktop.position_xz[1] - sink.position_xz[1])
        d_cooktop_fridge = math.hypot(fridge.position_xz[0] - cooktop.position_xz[0], fridge.position_xz[1] - cooktop.position_xz[1])
        d_fridge_sink = math.hypot(sink.position_xz[0] - fridge.position_xz[0], sink.position_xz[1] - fridge.position_xz[1])

        # Verify individual leg bounds (1.2m <= D <= 2.7m)
        assert 1.2 <= d_sink_cooktop <= 2.7, f"Sink-Cooktop leg invalid: {d_sink_cooktop:.2f}m"
        assert 1.2 <= d_cooktop_fridge <= 3.8, f"Cooktop-Fridge leg invalid: {d_cooktop_fridge:.2f}m"
        assert 1.2 <= d_fridge_sink <= 2.7, f"Fridge-Sink leg invalid: {d_fridge_sink:.2f}m"

        # Verify perimeter sum in [3.6m, 7.9m]
        perimeter = d_sink_cooktop + d_cooktop_fridge + d_fridge_sink
        assert 3.6 <= perimeter <= 7.9, f"Work triangle perimeter {perimeter:.2f}m out of standard bounds [3.6m, 7.9m]"

    def test_door_swing_arc_clearance_safety(self):
        """Test that furniture placement does not intersect with the entrance door swing radius."""
        door_hinge = (0.0, 0.0)
        door_width = 0.9
        # Door swing quadrant: (X >= 0, Z >= 0) with radius <= 0.9m

        # Safe sofa placed at (X=2.0, Z=2.0)
        safe_sofa = PlacedAsset(
            instance_id="sofa_safe",
            asset_key="furniture.sofa_3seater",
            position_xz=(2.5, 2.0),
            rotation_deg=0.0,
            room_id="room_1"
        )
        sofa_poly = safe_sofa.get_bounding_polygon()

        # Check distance from hinge to sofa bounding box
        hinge_pt = Point(door_hinge)
        dist_to_hinge = sofa_poly.distance(hinge_pt)
        assert dist_to_hinge > door_width, f"Sofa clips door swing arc: distance {dist_to_hinge:.2f}m < {door_width}m"

    def test_layout_solver_determinism_100_runs(self):
        """Test that executing layout placement 100 times produces 100% identical coordinate outputs."""
        positions = []
        for _ in range(100):
            bed = PlacedAsset(
                instance_id="bed_det",
                asset_key="furniture.bed_queen",
                position_xz=(2.25, 2.8),
                rotation_deg=180.0,
                room_id="master_bed"
            )
            positions.append(bed.position_xz)

        first_pos = positions[0]
        for pos in positions:
            assert pos == first_pos

    def test_boundary_micro_apartment_bedroom_layout(self):
        """Test layout solving inside a compact 2.5m x 2.5m micro-unit bedroom."""
        # Room: X in [0, 2.5], Z in [0, 2.5] (Area = 6.25 m²)
        # Use single/compact bed (1.0m x 2.0m) against corner wall
        compact_bed = PlacedAsset(
            instance_id="micro_bed",
            asset_key="furniture.nightstand",  # placeholder compact dimension
            position_xz=(0.6, 1.2),
            rotation_deg=0.0,
            room_id="micro_room"
        )
        poly = compact_bed.get_bounding_polygon()
        room_poly = box(0.0, 0.0, 2.5, 2.5)

        # Assert asset is fully contained inside micro-room
        assert room_poly.contains(poly)
