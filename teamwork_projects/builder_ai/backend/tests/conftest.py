"""
Test Configuration, Fixtures, and Mock Data Factory Suite for Builder3D OpenBIM.

Provides:
1. Isolated SQLAlchemy SQLite in-memory test database lifecycle with StaticPool.
2. FastAPI TestClient fixture with dependency override.
3. DesignSpecFactory: Generates typed DesignSpec instances for Studio, 1BHK, 2BHK, 3BHK, Villa, Tower, and boundaries.
4. SpatialTreeFactory: Generates canonical 6-tier SpatialNode hierarchies and GUID/UUID verification helpers.
5. RoomBoundaryFactory: Generates 2D planar room boundaries, floorplan layouts, adjacencies, wet stack placements, and circulation spines.
6. WallOpeningFactory: Generates parametric wall runs, hosted door/window openings, and 3D sub-segment void cutters.
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from shapely.geometry import LineString, Point, Polygon
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models.project
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.design_spec import (
    AestheticPalette,
    AestheticStyle,
    BuildingTypology,
    CorePlacementStrategy,
    DesignSpec,
    ElectricalDistributionType,
    FireProtectionType,
    HVACType,
    MaterialSpec,
    MEPStrategy,
    OccupancyCategory,
    PlumbingSystemType,
    RooftopMEPType,
    RoomProgram,
    RoomType,
    SetbackSpec,
    SiteParameters,
    StoreySpec,
    StoreyUseType,
    StructuralSystem,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
    ZoningClassification,
    assert_no_raw_geometry,
)
from app.schemas.spatial import (
    ALLOWED_CHILD_TYPES,
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
    find_node_by_global_id,
    find_node_by_id,
    find_node_by_path,
    flatten_spatial_tree,
    generate_spatial_uuid,
    get_ancestor_chain,
    get_descendants,
    ifc_guid_to_uuid,
    uuid_to_ifc_guid,
    validate_tree_integrity,
)


# ==============================================================================
# 1. Database Setup & FastAPI Test Client Fixtures
# ==============================================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Session:
    """Provides a clean, isolated SQLite in-memory database session per test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """Provides a FastAPI TestClient configured to use the test database session."""
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ==============================================================================
# 2. DesignSpec Mock Factory (`DesignSpecFactory`)
# ==============================================================================

class DesignSpecFactory:
    """Constructs validated DesignSpec instances for standard and boundary typologies."""

    @staticmethod
    def make_studio_spec(project_name: str = "Studio Apartment Project") -> DesignSpec:
        rooms = [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Studio Living/Bed", min_area_sqm=20.0, target_area_sqm=24.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Kitchenette", min_area_sqm=4.5, target_area_sqm=5.5, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BATHROOM, name="Bathroom", min_area_sqm=3.5, target_area_sqm=4.5, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Balcony", min_area_sqm=2.5, target_area_sqm=3.5, requires_daylight=True),
        ]
        unit = UnitRequirement(unit_type=UnitType.STUDIO, name="Studio Unit 101", target_area_sqm=38.0, required_rooms=rooms)
        storey = StoreySpec(storey_index=0, name="Ground Floor", elevation_m=0.0, height_m=3.2, is_ground=True, is_rooftop=True, unit_mix=[unit])
        return DesignSpec(
            project_name=project_name,
            total_storeys=1,
            storeys=[storey],
            building_typology=BuildingTypology.RESIDENTIAL,
            mep_strategy=MEPStrategy(hvac_type=HVACType.SPLIT_DX, riser_strategy=VerticalRiserStrategy.COAXIAL_STACKED_SHAFTS),
            aesthetic_palette=AestheticPalette(style=AestheticStyle.CONTEMPORARY_MODERN),
        )

    @staticmethod
    def make_1bhk_spec(project_name: str = "1BHK Urban Flat") -> DesignSpec:
        rooms = [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Living Room", min_area_sqm=18.0, target_area_sqm=20.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Kitchen", min_area_sqm=7.0, target_area_sqm=8.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, name="Bedroom", min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM, name="Bathroom", min_area_sqm=4.0, target_area_sqm=5.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Balcony", min_area_sqm=4.0, target_area_sqm=6.0, requires_daylight=True),
        ]
        unit = UnitRequirement(unit_type=UnitType.BHK1, name="1BHK Flat 101", target_area_sqm=55.0, required_rooms=rooms)
        storey = StoreySpec(storey_index=0, name="Ground Floor", elevation_m=0.0, height_m=3.2, is_ground=True, is_rooftop=True, unit_mix=[unit])
        return DesignSpec(
            project_name=project_name,
            total_storeys=1,
            storeys=[storey],
            building_typology=BuildingTypology.RESIDENTIAL,
        )

    @staticmethod
    def make_2bhk_spec(project_name: str = "2BHK Residential Apartment") -> DesignSpec:
        rooms = [
            RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=24.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, min_area_sqm=8.0, target_area_sqm=10.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=8.0, target_area_sqm=9.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=11.0, target_area_sqm=12.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=3.5, target_area_sqm=4.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=True),
        ]
        unit = UnitRequirement(unit_type=UnitType.BHK2, name="Unit 201", target_area_sqm=90.0, required_rooms=rooms)
        storey = StoreySpec(storey_index=0, name="Ground Floor", elevation_m=0.0, height_m=3.2, is_ground=True, is_rooftop=True, unit_mix=[unit])
        return DesignSpec(
            project_name=project_name,
            total_storeys=1,
            storeys=[storey],
            building_typology=BuildingTypology.RESIDENTIAL,
        )

    @staticmethod
    def make_3bhk_spec(project_name: str = "3BHK Luxury Suite") -> DesignSpec:
        rooms = [
            RoomProgram(room_type=RoomType.FOYER, min_area_sqm=5.0, target_area_sqm=6.0, requires_daylight=False),
            RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=26.0, target_area_sqm=32.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=10.0, target_area_sqm=12.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.UTILITY_ROOM, min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=18.0, target_area_sqm=22.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, min_area_sqm=5.5, target_area_sqm=7.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=13.0, target_area_sqm=15.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.GUEST_BEDROOM, min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=3.5, target_area_sqm=4.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=True),
        ]
        unit = UnitRequirement(unit_type=UnitType.BHK3, name="3BHK Master Suite", target_area_sqm=160.0, required_rooms=rooms)
        storey = StoreySpec(storey_index=0, name="Ground Floor", elevation_m=0.0, height_m=3.2, is_ground=True, is_rooftop=True, unit_mix=[unit])
        return DesignSpec(
            project_name=project_name,
            total_storeys=1,
            storeys=[storey],
            building_typology=BuildingTypology.RESIDENTIAL,
            aesthetic_palette=AestheticPalette(style=AestheticStyle.LUXURY_CALACATTA),
        )

    @staticmethod
    def make_villa_spec(project_name: str = "2-Storey Modern Villa") -> DesignSpec:
        ground_rooms = [
            RoomProgram(room_type=RoomType.FOYER, min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=False),
            RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=28.0, target_area_sqm=35.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=12.0, target_area_sqm=14.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.GUEST_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.POWDER_ROOM, min_area_sqm=3.0, target_area_sqm=4.0, requires_plumbing=True),
        ]
        upper_rooms = [
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=22.0, target_area_sqm=26.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, min_area_sqm=6.0, target_area_sqm=8.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.TERRACE, min_area_sqm=15.0, target_area_sqm=20.0, requires_daylight=True),
        ]
        ground_unit = UnitRequirement(unit_type=UnitType.CUSTOM, name="Ground Living Level", target_area_sqm=150.0, required_rooms=ground_rooms)
        upper_unit = UnitRequirement(unit_type=UnitType.CUSTOM, name="First Sleeping Level", target_area_sqm=130.0, required_rooms=upper_rooms)

        storeys = [
            StoreySpec(storey_index=0, name="Ground Floor", elevation_m=0.0, height_m=3.6, is_ground=True, unit_mix=[ground_unit]),
            StoreySpec(storey_index=1, name="First Floor", elevation_m=3.6, height_m=3.2, is_rooftop=True, unit_mix=[upper_unit]),
        ]
        return DesignSpec(
            project_name=project_name,
            total_storeys=2,
            ground_floor_height_m=3.6,
            floor_to_floor_height_m=3.2,
            storeys=storeys,
            building_typology=BuildingTypology.VILLA,
            aesthetic_palette=AestheticPalette(style=AestheticStyle.JAPANDI_SCANDINAVIAN),
        )

    @staticmethod
    def make_tower_spec(storeys: int = 12, project_name: str = "Residential High-Rise Tower") -> DesignSpec:
        storey_specs: List[StoreySpec] = []
        cur_elev = 0.0
        h_ground = 3.6
        h_typical = 3.2

        # 2BHK and 3BHK unit programs
        unit_2bhk = UnitRequirement(
            unit_type=UnitType.BHK2,
            name="2BHK Unit A",
            target_area_sqm=85.0,
            required_rooms=[
                RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=22.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=7.0, target_area_sqm=8.0, requires_plumbing=True),
                RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=11.0, target_area_sqm=12.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.BATHROOM, min_area_sqm=4.0, target_area_sqm=4.5, requires_plumbing=True),
            ]
        )
        unit_3bhk = UnitRequirement(
            unit_type=UnitType.BHK3,
            name="3BHK Unit B",
            target_area_sqm=125.0,
            required_rooms=[
                RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=25.0, target_area_sqm=28.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.DINING_ROOM, min_area_sqm=10.0, target_area_sqm=12.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=8.0, target_area_sqm=10.0, requires_plumbing=True),
                RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=16.0, target_area_sqm=18.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=11.0, target_area_sqm=12.0, requires_daylight=True),
                RoomProgram(room_type=RoomType.BATHROOM, min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
            ]
        )

        for s_idx in range(storeys):
            h = h_ground if s_idx == 0 else h_typical
            is_grd = (s_idx == 0)
            is_roof = (s_idx == storeys - 1)
            name = "Ground Floor Lobby" if is_grd else f"Level {s_idx}"
            use = StoreyUseType.COMMERCIAL_LOBBY if is_grd else StoreyUseType.RESIDENTIAL
            storey_specs.append(
                StoreySpec(
                    storey_index=s_idx,
                    name=name,
                    elevation_m=cur_elev,
                    height_m=h,
                    is_ground=is_grd,
                    is_rooftop=is_roof,
                    target_use=use,
                    unit_mix=[unit_2bhk, unit_3bhk] if not is_grd else [],
                )
            )
            cur_elev += h

        return DesignSpec(
            project_name=project_name,
            total_storeys=storeys,
            ground_floor_height_m=h_ground,
            floor_to_floor_height_m=h_typical,
            storeys=storey_specs,
            building_typology=BuildingTypology.TOWER,
            mep_strategy=MEPStrategy(
                hvac_type=HVACType.VRF_MULTI_SPLIT,
                core_placement=CorePlacementStrategy.CENTRAL_CORE,
                riser_strategy=VerticalRiserStrategy.COAXIAL_STACKED_SHAFTS,
                rooftop_mep=RooftopMEPType.SOLAR_PV_ARRAY,
                solar_capacity_kwp=45.0,
            ),
        )

    @staticmethod
    def make_micro_unit_spec(area: float = 18.0) -> DesignSpec:
        rooms = [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Micro Studio", min_area_sqm=area * 0.65, target_area_sqm=area * 0.75, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM, name="Pod Bath", min_area_sqm=2.5, target_area_sqm=3.0, requires_plumbing=True),
        ]
        unit = UnitRequirement(unit_type=UnitType.STUDIO, target_area_sqm=area, required_rooms=rooms)
        storey = StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.0, is_ground=True, is_rooftop=True, unit_mix=[unit])
        return DesignSpec(project_name="Micro Living", total_storeys=1, storeys=[storey])

    @staticmethod
    def make_extreme_tower_spec(storeys: int = 36) -> DesignSpec:
        return DesignSpecFactory.make_tower_spec(storeys=storeys, project_name="Skyline 36 Tower")

    @staticmethod
    def make_narrow_lot_spec(aspect_ratio: float = 4.0) -> DesignSpec:
        site = SiteParameters(plot_width_m=10.0, plot_depth_m=40.0, setbacks=SetbackSpec(front_m=3.0, rear_m=2.0, side_left_m=1.0, side_right_m=1.0))
        spec = DesignSpecFactory.make_1bhk_spec(project_name="Narrow Lot Rowhouse")
        spec.site = site
        return spec


# ==============================================================================
# 3. Spatial Tree Mock Factory (`SpatialTreeFactory`)
# ==============================================================================

class SpatialTreeFactory:
    """Constructs 6-tier canonical spatial trees and provides hierarchy helpers."""

    @staticmethod
    def make_canonical_tree(project_name: str = "Metropolitan OpenBIM") -> SpatialNode:
        spec = DesignSpecFactory.make_2bhk_spec(project_name=project_name)
        return compile_design_spec_to_spatial_tree(spec)

    @staticmethod
    def make_storey_tree(storey_count: int = 3) -> SpatialNode:
        spec = DesignSpecFactory.make_tower_spec(storeys=storey_count)
        return compile_design_spec_to_spatial_tree(spec)

    @staticmethod
    def make_custom_node(
        node_type: SpatialNodeType,
        name: str,
        parent_id: Optional[str] = None,
        canonical_path: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> SpatialNode:
        path = canonical_path or f"{node_type.value.lower()}:{name.lower()}"
        u = generate_spatial_uuid(path)
        return SpatialNode(
            id=str(u),
            global_id=encode_ifc_guid(u),
            name=name,
            node_type=node_type,
            parent_id=parent_id,
            canonical_path=path,
            properties=properties or {},
            children=[],
        )


# ==============================================================================
# 4. Room Boundary & Spatial Topology Factory (`RoomBoundaryFactory`)
# ==============================================================================

class RoomBoundary(BaseModel):
    """2D planar polygon representation of an architectural room in (x, z) coordinates."""

    model_config = ConfigDict(extra="forbid")

    room_id: str
    room_type: str
    polygon: List[Tuple[float, float]] = Field(..., min_length=3, description="Ordered 2D vertices (x, z)")
    area: float = Field(..., gt=0.0)
    is_exterior: bool = Field(default=False, description="Has exterior boundary edge")
    wet_zone: bool = Field(default=False, description="Contains plumbing fixtures")
    requires_daylight: bool = Field(default=True)
    adjacent_room_ids: List[str] = Field(default_factory=list)

    @field_validator("polygon")
    @classmethod
    def validate_polygon_vertices(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(v) < 3:
            raise ValueError(f"Polygon must have at least 3 vertices, got {len(v)}")
        return v


class VerticalRiserLocation(BaseModel):
    """Location of a multi-storey vertical utility riser shaft in (x, z)."""

    model_config = ConfigDict(extra="forbid")

    riser_id: str
    riser_type: Literal["Plumbing", "Electrical", "HVAC", "MultiService"] = "Plumbing"
    position: Tuple[float, float] = Field(..., description="(x, z) shaft centroid")
    radius: float = Field(default=0.4, gt=0.0)
    serviced_room_ids: List[str] = Field(default_factory=list)


class FloorplanLayout(BaseModel):
    """Complete 2D geometric layout of a building storey."""

    model_config = ConfigDict(extra="forbid")

    storey_index: int
    elevation: float
    boundary_polygon: List[Tuple[float, float]]
    rooms: List[RoomBoundary]
    corridors: List[RoomBoundary] = Field(default_factory=list)
    vertical_risers: List[VerticalRiserLocation] = Field(default_factory=list)


class RoomBoundaryFactory:
    """Generates 2D planar room boundaries, floorplan layouts, and spatial topological test beds."""

    @staticmethod
    def make_room_boundary(
        room_id: str,
        room_type: str,
        polygon: List[Tuple[float, float]],
        area: Optional[float] = None,
        is_exterior: bool = False,
        wet_zone: bool = False,
        requires_daylight: bool = True,
        adjacent_room_ids: Optional[List[str]] = None,
    ) -> RoomBoundary:
        poly_obj = Polygon(polygon)
        computed_area = area if area is not None else float(poly_obj.area)
        return RoomBoundary(
            room_id=room_id,
            room_type=room_type,
            polygon=polygon,
            area=computed_area,
            is_exterior=is_exterior,
            wet_zone=wet_zone,
            requires_daylight=requires_daylight,
            adjacent_room_ids=adjacent_room_ids or [],
        )

    @staticmethod
    def make_standard_floorplan_layout(storey_index: int = 0, elevation: float = 0.0) -> FloorplanLayout:
        """
        Standard 2BHK Layout:
        Building boundary: 10m x 10m [ (0,0), (10,0), (10,10), (0,10) ] (100 sqm)
        Corridor / Foyer: [ (4, 0), (6, 0), (6, 6), (4, 6) ] (12 sqm)
        Living Room: [ (0, 0), (4, 0), (4, 5), (0, 5) ] (20 sqm, Exterior, Daylight)
        Dining Room: [ (6, 0), (10, 0), (10, 4), (6, 4) ] (16 sqm, Exterior, Daylight)
        Kitchen: [ (6, 4), (10, 4), (10, 7), (6, 7) ] (12 sqm, Exterior, WetZone)
        Master Bedroom: [ (0, 5), (4, 5), (4, 10), (0, 10) ] (20 sqm, Exterior, Daylight)
        Ensuite Bath: [ (4, 6), (6, 6), (6, 10), (4, 10) ] (8 sqm, Interior, WetZone)
        Common Bedroom: [ (6, 7), (10, 7), (10, 10), (6, 10) ] (12 sqm, Exterior, Daylight)
        Vertical Riser: Centered at (5.5, 6.5) servicing Kitchen, Ensuite Bath.
        """
        boundary = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]

        living = RoomBoundaryFactory.make_room_boundary(
            room_id="room_living",
            room_type="LivingRoom",
            polygon=[(0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)],
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_corridor", "room_master_bed"],
        )
        dining = RoomBoundaryFactory.make_room_boundary(
            room_id="room_dining",
            room_type="DiningRoom",
            polygon=[(6.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0)],
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_corridor", "room_kitchen"],
        )
        kitchen = RoomBoundaryFactory.make_room_boundary(
            room_id="room_kitchen",
            room_type="Kitchen",
            polygon=[(6.0, 4.0), (10.0, 4.0), (10.0, 7.0), (6.0, 7.0)],
            is_exterior=True,
            wet_zone=True,
            requires_daylight=False,
            adjacent_room_ids=["room_dining", "room_guest_bed", "room_corridor"],
        )
        master_bed = RoomBoundaryFactory.make_room_boundary(
            room_id="room_master_bed",
            room_type="MasterBedroom",
            polygon=[(0.0, 5.0), (4.0, 5.0), (4.0, 10.0), (0.0, 10.0)],
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_living", "room_corridor", "room_ensuite_bath"],
        )
        ensuite_bath = RoomBoundaryFactory.make_room_boundary(
            room_id="room_ensuite_bath",
            room_type="BathroomEnsuite",
            polygon=[(4.0, 6.0), (6.0, 6.0), (6.0, 10.0), (4.0, 10.0)],
            is_exterior=True,
            wet_zone=True,
            requires_daylight=False,
            adjacent_room_ids=["room_master_bed", "room_corridor", "room_guest_bed"],
        )
        guest_bed = RoomBoundaryFactory.make_room_boundary(
            room_id="room_guest_bed",
            room_type="Bedroom",
            polygon=[(6.0, 7.0), (10.0, 7.0), (10.0, 10.0), (6.0, 10.0)],
            is_exterior=True,
            wet_zone=False,
            requires_daylight=True,
            adjacent_room_ids=["room_kitchen", "room_ensuite_bath"],
        )
        corridor = RoomBoundaryFactory.make_room_boundary(
            room_id="room_corridor",
            room_type="Corridor",
            polygon=[(4.0, 0.0), (6.0, 0.0), (6.0, 6.0), (4.0, 6.0)],
            is_exterior=False,
            wet_zone=False,
            requires_daylight=False,
            adjacent_room_ids=["room_living", "room_dining", "room_master_bed", "room_kitchen", "room_ensuite_bath"],
        )

        riser = VerticalRiserLocation(
            riser_id="riser_plumbing_main",
            riser_type="Plumbing",
            position=(5.8, 6.2),
            radius=0.4,
            serviced_room_ids=["room_kitchen", "room_ensuite_bath"],
        )

        return FloorplanLayout(
            storey_index=storey_index,
            elevation=elevation,
            boundary_polygon=boundary,
            rooms=[living, dining, kitchen, master_bed, ensuite_bath, guest_bed],
            corridors=[corridor],
            vertical_risers=[riser],
        )

    @staticmethod
    def make_l_shaped_floorplan_layout(storey_index: int = 0, elevation: float = 0.0) -> FloorplanLayout:
        """L-shaped boundary footprint: (0,0)->(12,0)->(12,6)->(6,6)->(6,12)->(0,12)."""
        boundary = [(0.0, 0.0), (12.0, 0.0), (12.0, 6.0), (6.0, 6.0), (6.0, 12.0), (0.0, 12.0)]
        room1 = RoomBoundaryFactory.make_room_boundary(
            "room_l_living", "LivingRoom", [(0.0, 0.0), (6.0, 0.0), (6.0, 6.0), (0.0, 6.0)], is_exterior=True
        )
        room2 = RoomBoundaryFactory.make_room_boundary(
            "room_l_dining", "DiningRoom", [(6.0, 0.0), (12.0, 0.0), (12.0, 6.0), (6.0, 6.0)], is_exterior=True
        )
        room3 = RoomBoundaryFactory.make_room_boundary(
            "room_l_bed", "MasterBedroom", [(0.0, 6.0), (6.0, 6.0), (6.0, 12.0), (0.0, 12.0)], is_exterior=True
        )
        return FloorplanLayout(
            storey_index=storey_index,
            elevation=elevation,
            boundary_polygon=boundary,
            rooms=[room1, room2, room3],
            corridors=[],
            vertical_risers=[],
        )

    @staticmethod
    def make_multi_storey_layouts(storeys: int = 3, floor_height: float = 3.2) -> List[FloorplanLayout]:
        layouts = []
        for s in range(storeys):
            layout = RoomBoundaryFactory.make_standard_floorplan_layout(storey_index=s, elevation=s * floor_height)
            layouts.append(layout)
        return layouts


# ==============================================================================
# 5. Parametric Wall & Hosted Opening Factory (`WallOpeningFactory`)
# ==============================================================================

class HostedOpening(BaseModel):
    """Door or window architectural opening hosted within a ParametricWall."""

    model_config = ConfigDict(extra="forbid")

    opening_id: str
    opening_type: Literal["DOOR", "WINDOW"]
    wall_id: str
    distance_along_wall: float = Field(..., ge=0.0)
    width: float = Field(..., gt=0.0)
    height: float = Field(..., gt=0.0)
    sill_height: float = Field(default=0.0, ge=0.0)
    swing_direction: Optional[Literal["INWARD_LEFT", "INWARD_RIGHT", "OUTWARD_LEFT", "OUTWARD_RIGHT"]] = None


class WallSubSegment(BaseModel):
    """Solid or void 3D sub-mesh bounding volume generated around openings."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str
    wall_id: str
    segment_type: Literal["SOLID", "PRE", "POST", "LINTEL", "SILL"]
    start_dist: float = Field(..., ge=0.0)
    end_dist: float = Field(..., ge=0.0)
    bottom_elev: float = Field(..., ge=0.0)
    top_elev: float = Field(..., ge=0.0)
    thickness: float = Field(..., gt=0.0)
    volume: float = Field(..., ge=0.0)


class ParametricWall(BaseModel):
    """Parametric linear wall run extracted from polygon room boundaries."""

    model_config = ConfigDict(extra="forbid")

    wall_id: str
    start_pt: Tuple[float, float, float]
    end_pt: Tuple[float, float, float]
    thickness: float = Field(default=0.25, gt=0.0)
    height: float = Field(default=3.0, gt=0.0)
    is_exterior: bool = Field(default=True)
    openings: List[HostedOpening] = Field(default_factory=list)
    sub_segments: List[WallSubSegment] = Field(default_factory=list)

    @property
    def length(self) -> float:
        dx = self.end_pt[0] - self.start_pt[0]
        dy = self.end_pt[1] - self.start_pt[1]
        dz = self.end_pt[2] - self.start_pt[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)


class WallOpeningFactory:
    """Generates parametric walls, hosted openings, and wall sub-segment void cuts."""

    @staticmethod
    def make_hosted_opening(
        opening_id: str,
        opening_type: Literal["DOOR", "WINDOW"],
        wall_id: str,
        distance_along_wall: float,
        width: float,
        height: float,
        sill_height: float = 0.0,
        swing_direction: Optional[Literal["INWARD_LEFT", "INWARD_RIGHT", "OUTWARD_LEFT", "OUTWARD_RIGHT"]] = None,
    ) -> HostedOpening:
        return HostedOpening(
            opening_id=opening_id,
            opening_type=opening_type,
            wall_id=wall_id,
            distance_along_wall=distance_along_wall,
            width=width,
            height=height,
            sill_height=sill_height,
            swing_direction=swing_direction,
        )

    @staticmethod
    def make_parametric_wall(
        wall_id: str,
        start_pt: Tuple[float, float, float],
        end_pt: Tuple[float, float, float],
        thickness: float = 0.25,
        height: float = 3.0,
        is_exterior: bool = True,
        openings: Optional[List[HostedOpening]] = None,
    ) -> ParametricWall:
        wall = ParametricWall(
            wall_id=wall_id,
            start_pt=start_pt,
            end_pt=end_pt,
            thickness=thickness,
            height=height,
            is_exterior=is_exterior,
            openings=openings or [],
            sub_segments=[],
        )
        wall.sub_segments = WallOpeningFactory.compute_wall_subsegments(wall)
        return wall

    @staticmethod
    def compute_wall_subsegments(wall: ParametricWall) -> List[WallSubSegment]:
        """
        Sub-segments a host wall around hosted doors and windows:
        - Solid wall with no openings: Single SOLID segment.
        - Wall with 1 opening: PRE (before opening), POST (after opening),
          LINTEL (above opening), and SILL (below opening if sill_height > 0).
        - Multi-opening wall: Ordered sequence of PRE, POST, LINTEL, SILL segments.
        """
        wall_len = wall.length
        th = wall.thickness
        h = wall.height

        if not wall.openings:
            return [
                WallSubSegment(
                    segment_id=f"{wall.wall_id}_solid",
                    wall_id=wall.wall_id,
                    segment_type="SOLID",
                    start_dist=0.0,
                    end_dist=wall_len,
                    bottom_elev=0.0,
                    top_elev=h,
                    thickness=th,
                    volume=wall_len * h * th,
                )
            ]

        # Sort openings by distance along wall
        sorted_ops = sorted(wall.openings, key=lambda op: op.distance_along_wall)

        # Validate bounds & non-overlap
        last_end = 0.0
        for op in sorted_ops:
            if op.distance_along_wall < last_end - 1e-4:
                raise ValueError(f"Overlapping openings detected on wall {wall.wall_id}: opening {op.opening_id}")
            if op.distance_along_wall + op.width > wall_len + 1e-4:
                raise ValueError(
                    f"Opening {op.opening_id} (dist={op.distance_along_wall}m, width={op.width}m) "
                    f"exceeds wall length {wall_len:.2f}m"
                )
            if op.sill_height + op.height > h + 1e-4:
                raise ValueError(
                    f"Opening {op.opening_id} (sill={op.sill_height}m, height={op.height}m) "
                    f"exceeds wall height {h:.2f}m"
                )
            last_end = op.distance_along_wall + op.width

        segments: List[WallSubSegment] = []
        cur_pos = 0.0

        for idx, op in enumerate(sorted_ops):
            op_start = op.distance_along_wall
            op_end = op_start + op.width

            # 1. Segment before this opening (PRE / intermediate solid)
            if op_start > cur_pos + 1e-4:
                seg_type = "PRE" if idx == 0 else "POST"
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
                        segment_type="SILL",
                        start_dist=op_start,
                        end_dist=op_end,
                        bottom_elev=0.0,
                        top_elev=op.sill_height,
                        thickness=th,
                        volume=op.width * op.sill_height * th,
                    )
                )

            # 3. LINTEL segment (above opening)
            lintel_bottom = op.sill_height + op.height
            if lintel_bottom < h - 1e-4:
                lintel_h = h - lintel_bottom
                segments.append(
                    WallSubSegment(
                        segment_id=f"{wall.wall_id}_lintel_{op.opening_id}",
                        wall_id=wall.wall_id,
                        segment_type="LINTEL",
                        start_dist=op_start,
                        end_dist=op_end,
                        bottom_elev=lintel_bottom,
                        top_elev=h,
                        thickness=th,
                        volume=op.width * lintel_h * th,
                    )
                )

            cur_pos = op_end

        # Final POST segment after last opening
        if cur_pos < wall_len - 1e-4:
            seg_len = wall_len - cur_pos
            segments.append(
                WallSubSegment(
                    segment_id=f"{wall.wall_id}_post_final",
                    wall_id=wall.wall_id,
                    segment_type="POST",
                    start_dist=cur_pos,
                    end_dist=wall_len,
                    bottom_elev=0.0,
                    top_elev=h,
                    thickness=th,
                    volume=seg_len * h * th,
                )
            )

        return segments

    @staticmethod
    def extract_walls_from_room_boundaries(
        rooms: List[RoomBoundary],
        exterior_thickness: float = 0.25,
        interior_thickness: float = 0.12,
        wall_height: float = 3.0,
    ) -> List[ParametricWall]:
        """
        Extracts parametric wall runs from 2D room polygons with shared edge deduplication.
        Ensures an edge shared between Room A and Room B generates exactly ONE interior wall.
        """
        edge_map: Dict[Tuple[Tuple[float, float], Tuple[float, float]], List[str]] = {}

        def _canonical_edge(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
            p1_rounded = (round(p1[0], 4), round(p1[1], 4))
            p2_rounded = (round(p2[0], 4), round(p2[1], 4))
            return (p1_rounded, p2_rounded) if p1_rounded <= p2_rounded else (p2_rounded, p1_rounded)

        for r in rooms:
            n = len(r.polygon)
            for i in range(n):
                p1 = r.polygon[i]
                p2 = r.polygon[(i + 1) % n]
                edge = _canonical_edge(p1, p2)
                if edge not in edge_map:
                    edge_map[edge] = []
                edge_map[edge].append(r.room_id)

        walls: List[ParametricWall] = []
        wall_idx = 0

        for (p1, p2), sharing_rooms in edge_map.items():
            edge_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            # Filter degenerate zero-length segments (< 0.05m)
            if edge_len < 0.05:
                continue

            is_ext = len(sharing_rooms) == 1
            th = exterior_thickness if is_ext else interior_thickness
            start_3d = (p1[0], 0.0, p1[1])
            end_3d = (p2[0], 0.0, p2[1])

            wall = WallOpeningFactory.make_parametric_wall(
                wall_id=f"wall_{wall_idx:03d}",
                start_pt=start_3d,
                end_pt=end_3d,
                thickness=th,
                height=wall_height,
                is_exterior=is_ext,
            )
            walls.append(wall)
            wall_idx += 1

        return walls


# ==============================================================================
# 6. Reusable Pytest Fixtures
# ==============================================================================

@pytest.fixture
def design_spec_factory() -> type[DesignSpecFactory]:
    return DesignSpecFactory


@pytest.fixture
def spatial_tree_factory() -> type[SpatialTreeFactory]:
    return SpatialTreeFactory


@pytest.fixture
def room_boundary_factory() -> type[RoomBoundaryFactory]:
    return RoomBoundaryFactory


@pytest.fixture
def wall_opening_factory() -> type[WallOpeningFactory]:
    return WallOpeningFactory


@pytest.fixture
def sample_design_spec_2bhk() -> DesignSpec:
    return DesignSpecFactory.make_2bhk_spec()


@pytest.fixture
def sample_spatial_tree() -> SpatialNode:
    return SpatialTreeFactory.make_canonical_tree()


@pytest.fixture
def sample_floorplan_layout() -> FloorplanLayout:
    return RoomBoundaryFactory.make_standard_floorplan_layout()


@pytest.fixture
def sample_parametric_walls(sample_floorplan_layout: FloorplanLayout) -> List[ParametricWall]:
    all_rooms = sample_floorplan_layout.rooms + sample_floorplan_layout.corridors
    return WallOpeningFactory.extract_walls_from_room_boundaries(all_rooms)
