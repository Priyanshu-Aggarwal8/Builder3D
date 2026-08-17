"""
DesignSpec Schema - Pure Semantic Architectural Intent Data Contract.

This module defines the strongly-typed, pure-intent DesignSpec schema for the
Builder3D OpenBIM platform. In accordance with architectural principles,
DesignSpec contains ZERO raw Cartesian coordinates, vertex lists, or polygon meshes.
It captures purely architectural, structural, MEP, and aesthetic intent.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


# ==============================================================================
# Prohibited Raw Geometry Keys Set & Recursive Scanner
# ==============================================================================

PROHIBITED_GEOMETRY_KEYS = {
    "vertices",
    "vertex_list",
    "coords",
    "coordinates",
    "points",
    "faces",
    "triangles",
    "polygons",
    "mesh",
    "geometry",
    "mesh_data",
    "bounding_box_min",
    "bounding_box_max",
}


def assert_no_raw_geometry(data: Any, path: str = "") -> None:
    """Recursively validates that no dictionary, list, or object contains raw geometry keys."""
    if isinstance(data, dict):
        for k, v in data.items():
            current_path = f"{path}.{k}" if path else str(k)
            if str(k).lower() in PROHIBITED_GEOMETRY_KEYS:
                raise ValueError(
                    f"DesignSpec architectural violation: Prohibited raw geometry key '{k}' "
                    f"found at '{current_path}'. DesignSpec must specify pure semantic intent, "
                    f"not derived geometry coordinates."
                )
            assert_no_raw_geometry(v, current_path)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            assert_no_raw_geometry(item, f"{path}[{idx}]")
    elif isinstance(data, BaseModel):
        assert_no_raw_geometry(data.model_dump(exclude_unset=False), path)


# ==============================================================================
# Architectural Enums
# ==============================================================================


class BuildingTypology(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    MIXED_USE = "MixedUse"
    VILLA = "Villa"
    TOWER = "Tower"
    TOWNHOUSE = "Townhouse"
    EDUCATIONAL = "Educational"
    HOSPITALITY = "Hospitality"
    HEALTHCARE = "Healthcare"


class OccupancyCategory(str, Enum):
    RESIDENTIAL_SINGLE_FAMILY = "Residential_SingleFamily"
    RESIDENTIAL_MULTI_FAMILY = "Residential_MultiFamily"
    BUSINESS_OFFICE = "Business_Office"
    MERCANTILE_RETAIL = "Mercantile_Retail"
    ASSEMBLY_AMENITY = "Assembly_Amenity"
    STORAGE_PARKING = "Storage_Parking"


class StructuralSystem(str, Enum):
    REINFORCED_CONCRETE_FRAME = "ReinforcedConcrete_Frame"
    STEEL_FRAME = "Steel_Frame"
    MASS_TIMBER = "Mass_Timber"
    LOAD_BEARING_MASONRY = "LoadBearing_Masonry"
    HYBRID_POST_TENSIONED = "Hybrid_PostTensioned"


class ZoningClassification(str, Enum):
    RESIDENTIAL_LOW_DENSITY = "ResidentialLowDensity"
    RESIDENTIAL_MEDIUM_DENSITY = "ResidentialMediumDensity"
    RESIDENTIAL_HIGH_DENSITY = "ResidentialHighDensity"
    COMMERCIAL_URBAN = "CommercialUrban"
    MIXED_USE_HIGH_DENSITY = "MixedUseHighDensity"
    SUBURBAN_ESTATE = "SuburbanEstate"
    SPECIAL_DISTRICT = "SpecialDistrict"


class StoreyUseType(str, Enum):
    RESIDENTIAL = "Residential"
    COMMERCIAL_LOBBY = "CommercialLobby"
    RETAIL = "Retail"
    OFFICE = "Office"
    PARKING = "Parking"
    AMENITY_SKY_LOUNGE = "AmenitySkyLounge"
    MECHANICAL_PENTHOUSE = "MechanicalPenthouse"


class UnitType(str, Enum):
    STUDIO = "Studio"
    BHK1 = "1BHK"
    BHK2 = "2BHK"
    BHK3 = "3BHK"
    BHK4 = "4BHK"
    PENTHOUSE = "Penthouse"
    COMMERCIAL_OFFICE = "CommercialOffice"
    RETAIL_SHOP = "RetailShop"
    AMENITY_SPACE = "AmenitySpace"
    CIRCULATION_CORE = "CirculationCore"
    MECHANICAL_SPACE = "MechanicalSpace"
    CUSTOM = "Custom"


class RoomType(str, Enum):
    LIVING_ROOM = "LivingRoom"
    DINING_ROOM = "DiningRoom"
    KITCHEN = "Kitchen"
    MASTER_BEDROOM = "MasterBedroom"
    BEDROOM = "Bedroom"
    GUEST_BEDROOM = "GuestBedroom"
    BATHROOM_ENSUITE = "BathroomEnsuite"
    BATHROOM_COMMON = "BathroomCommon"
    BATHROOM = "Bathroom"
    POWDER_ROOM = "PowderRoom"
    BALCONY = "Balcony"
    CORRIDOR = "Corridor"
    FOYER = "Foyer"
    UTILITY_ROOM = "UtilityRoom"
    WALK_IN_CLOSET = "WalkInCloset"
    HOME_OFFICE = "HomeOffice"
    CONFERENCE_ROOM = "ConferenceRoom"
    LOBBY = "Lobby"
    STAIR_CORE = "StairCore"
    ELEVATOR_CORE = "ElevatorCore"
    MECHANICAL_CHAMBER = "MechanicalChamber"
    TERRACE = "Terrace"


class HVACType(str, Enum):
    VRF_MULTI_SPLIT = "VRF_MultiSplit"
    CENTRAL_CHILLED_WATER = "CentralChilledWater"
    PACKAGED_ROOFTOP_UNIT = "PackagedRooftopUnit"
    SPLIT_DX = "SplitDX"
    NATURAL_VENTILATION_WITH_FANS = "NaturalVentilationWithFans"
    HYDRONIC_HEAT_PUMP = "HydronicHeatPump"


class CorePlacementStrategy(str, Enum):
    CENTRAL_CORE = "CentralCore"
    OFFSET_NORTH = "OffsetNorth"
    OFFSET_SOUTH = "OffsetSouth"
    OFFSET_EAST = "OffsetEast"
    OFFSET_WEST = "OffsetWest"
    DUAL_END_CORES = "DualEndCores"
    PERIMETER_CORE = "PerimeterCore"
    SPLIT_CORES = "SplitCores"


class VerticalRiserStrategy(str, Enum):
    COAXIAL_STACKED_SHAFTS = "CoaxialStackedShafts"
    WET_COLUMN_CHASES = "WetColumnChases"
    DISTRIBUTED_CORRIDOR_CHASES = "DistributedCorridorChases"
    DEDICATED_MECHANICAL_SHAFT = "DedicatedMechanicalShaft"


class ElectricalDistributionType(str, Enum):
    BUSBAR_RISER_3PHASE = "BusbarRiser3Phase"
    CONDUIT_CHASES_PER_FLOOR = "ConduitChasesPerFloor"
    SUBSTATION_BASEMENT_DIRECT = "SubstationBasementDirect"


class PlumbingSystemType(str, Enum):
    TWO_PIPE_SOIL_WASTE = "TwoPipeSoilWaste"
    SINGLE_STACK_SOVENT = "SingleStackSovent"
    GRAVITY_DRAINAGE_WITH_VENTS = "GravityDrainageWithVents"


class FireProtectionType(str, Enum):
    PRESSURIZED_STAIRS_WET_RISER = "PressurizedStairsWetRiser"
    SPRINKLER_SYSTEM = "SprinklerSystem"
    DRY_RISER_STANDPIPE = "DryRiserStandpipe"


class RooftopMEPType(str, Enum):
    SOLAR_PV_ARRAY = "SolarPVArray"
    COOLING_TOWERS_AND_SCREENING = "CoolingTowersAndScreening"
    SKY_LOUNGE_WITH_PERGOLA = "SkyLoungeWithPergola"
    INFINITY_POOL_HYDRAULICS = "InfinityPoolHydraulics"
    STANDARD_ELEVATOR_PENTHOUSE = "StandardElevatorPenthouse"


class AestheticStyle(str, Enum):
    JAPANDI_SCANDINAVIAN = "JapandiScandinavian"
    LUXURY_CALACATTA = "LuxuryCalacatta"
    INDUSTRIAL_LOFT = "IndustrialLoft"
    BIOPHILIC_GREEN = "BiophilicGreen"
    CONTEMPORARY_MODERN = "ContemporaryModern"
    ART_DECO = "ArtDeco"
    BRUTALIST_CONCRETE = "BrutalistConcrete"
    MEDITERRANEAN_WARM = "MediterraneanWarm"


# ==============================================================================
# Sub-Models
# ==============================================================================


class SetbackSpec(BaseModel):
    """Legal building setback margins from parcel boundaries in meters."""

    model_config = ConfigDict(extra="forbid")

    front_m: float = Field(default=4.5, ge=0.0, le=100.0, description="Front setback in meters")
    rear_m: float = Field(default=3.0, ge=0.0, le=100.0, description="Rear setback in meters")
    side_left_m: float = Field(default=2.5, ge=0.0, le=100.0, description="Left side setback in meters")
    side_right_m: float = Field(default=2.5, ge=0.0, le=100.0, description="Right side setback in meters")


class SiteParameters(BaseModel):
    """Site parcel boundaries, setbacks, and zoning envelope parameters."""

    model_config = ConfigDict(extra="forbid")

    plot_width_m: float = Field(default=30.0, gt=0.0, le=2000.0, description="Plot width frontage in meters")
    plot_depth_m: float = Field(default=40.0, gt=0.0, le=2000.0, description="Plot depth in meters")
    total_area_sqm: float = Field(default=1200.0, gt=0.0, description="Total parcel area in square meters")
    setbacks: SetbackSpec = Field(default_factory=SetbackSpec)
    zoning: ZoningClassification = Field(default=ZoningClassification.RESIDENTIAL_HIGH_DENSITY)
    max_far: float = Field(default=3.5, gt=0.1, le=50.0, description="Maximum Floor Area Ratio")
    max_ground_coverage_ratio: float = Field(default=0.60, gt=0.05, le=1.0, description="Max Ground Coverage Ratio")
    max_height_m: Optional[float] = Field(default=None, gt=0.0, description="Zoning height cap in meters")
    orientation_degrees: float = Field(default=0.0, ge=0.0, lt=360.0, description="0=North, 90=East, 180=South, 270=West")
    solar_north_angle: float = Field(default=0.0, ge=0.0, lt=360.0, description="Solar azimuth north angle")

    @model_validator(mode="after")
    def validate_setbacks_fit_plot(self) -> SiteParameters:
        depth_setbacks = self.setbacks.front_m + self.setbacks.rear_m
        if depth_setbacks >= self.plot_depth_m:
            raise ValueError(
                f"Total depth setbacks ({depth_setbacks:.1f}m) exceed or equal "
                f"plot depth ({self.plot_depth_m:.1f}m)"
            )

        width_setbacks = self.setbacks.side_left_m + self.setbacks.side_right_m
        if width_setbacks >= self.plot_width_m:
            raise ValueError(
                f"Total width setbacks ({width_setbacks:.1f}m) exceed or equal "
                f"plot width ({self.plot_width_m:.1f}m)"
            )
        return self


# SiteSpec alias for compatibility
SiteSpec = SiteParameters


class MaterialSpec(BaseModel):
    """PBR material definition with color hex and optical properties."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Standard Material", min_length=1, max_length=120)
    color_hex: str = Field(default="#FFFFFF", pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    metalness: float = Field(default=0.0, ge=0.0, le=1.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    transmission: float = Field(default=0.0, ge=0.0, le=1.0)
    reflectivity: float = Field(default=0.5, ge=0.0, le=1.0)
    texture_name: Optional[str] = None


class AestheticPalette(BaseModel):
    """Comprehensive architectural aesthetic style and material finish mapping."""

    model_config = ConfigDict(extra="forbid")

    style: AestheticStyle = Field(default=AestheticStyle.JAPANDI_SCANDINAVIAN)
    exterior_wall: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Exterior Wall", color_hex="#E5E5E5", roughness=0.85)
    )
    interior_wall: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Interior Wall", color_hex="#FAF7F2", roughness=0.9)
    )
    flooring_living: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Living Flooring", color_hex="#D4A373", roughness=0.55)
    )
    flooring_wet_zones: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Wet Zone Tiles", color_hex="#44403C", roughness=0.4)
    )
    glazing: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(
            name="Facade Glass", color_hex="#BAE6FD", opacity=0.45, transmission=0.92, roughness=0.05
        )
    )
    mullions: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Aluminum Mullions", color_hex="#171717", metalness=0.8, roughness=0.3)
    )
    accent: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Wood/Metal Accent", color_hex="#78350F", roughness=0.6)
    )
    fascia: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Fascia Slab Band", color_hex="#262626", roughness=0.7)
    )
    doors: MaterialSpec = Field(
        default_factory=lambda: MaterialSpec(name="Solid Timber Door", color_hex="#78350F", roughness=0.5)
    )


class MEPStrategy(BaseModel):
    """High-level engineering strategy for building systems, shafts, and distribution."""

    model_config = ConfigDict(extra="forbid")

    hvac_type: HVACType = Field(default=HVACType.VRF_MULTI_SPLIT)
    core_placement: CorePlacementStrategy = Field(default=CorePlacementStrategy.CENTRAL_CORE)
    riser_strategy: VerticalRiserStrategy = Field(default=VerticalRiserStrategy.COAXIAL_STACKED_SHAFTS)
    electrical_distribution: ElectricalDistributionType = Field(default=ElectricalDistributionType.BUSBAR_RISER_3PHASE)
    plumbing_system: PlumbingSystemType = Field(default=PlumbingSystemType.TWO_PIPE_SOIL_WASTE)
    fire_protection: FireProtectionType = Field(default=FireProtectionType.PRESSURIZED_STAIRS_WET_RISER)
    rooftop_mep: RooftopMEPType = Field(default=RooftopMEPType.SOLAR_PV_ARRAY)
    solar_capacity_kwp: float = Field(default=18.0, ge=0.0, le=10000.0)
    water_storage_liters: float = Field(default=10000.0, ge=0.0, le=10000000.0)
    has_emergency_generator: bool = Field(default=True)


class RoomProgram(BaseModel):
    """Specific functional room intent and environmental criteria."""

    model_config = ConfigDict(extra="forbid")

    room_type: RoomType
    name: Optional[str] = None
    min_area_sqm: float = Field(..., gt=0.0, le=5000.0, description="Minimum allowable area in m²")
    target_area_sqm: float = Field(..., gt=0.0, le=5000.0, description="Target optimal area in m²")
    requires_daylight: bool = Field(default=True, description="Must be placed on exterior boundary for windows")
    requires_plumbing: bool = Field(default=False, description="Requires water supply and sanitary soil drainage")
    requires_ventilation: bool = Field(default=True, description="Natural or mechanical exhaust required")
    preferred_orientation: Optional[Literal["North", "South", "East", "West"]] = None
    adjacency_preferences: List[str] = Field(default_factory=list, description="Preferred neighbor room types")

    @field_validator("target_area_sqm")
    @classmethod
    def validate_target_ge_min(cls, v: float, info: ValidationInfo) -> float:
        min_a = info.data.get("min_area_sqm")
        if min_a is not None and v < min_a:
            raise ValueError(f"target_area_sqm ({v:.1f}) cannot be less than min_area_sqm ({min_a:.1f})")
        return v


class UnitRequirement(BaseModel):
    """Dwelling or commercial unit program specification."""

    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(default_factory=lambda: f"unit_{uuid.uuid4().hex[:6]}")
    unit_type: UnitType = Field(default=UnitType.BHK2)
    name: str = Field(default="Residential Unit", min_length=1, max_length=120)
    target_area_sqm: float = Field(..., gt=0.0, le=50000.0, description="Target gross area of the unit in m²")
    aspect_ratio_target: Optional[float] = Field(default=1.33, ge=0.2, le=5.0)
    required_rooms: List[RoomProgram] = Field(default_factory=list)
    balcony_count: int = Field(default=1, ge=0, le=20)
    private_access: bool = Field(default=False)

    @field_validator("required_rooms")
    @classmethod
    def validate_rooms_fit_target(cls, rooms: List[RoomProgram], info: ValidationInfo) -> List[RoomProgram]:
        target = info.data.get("target_area_sqm")
        if target is not None and rooms:
            total_min_room_area = sum(r.min_area_sqm for r in rooms)
            # Allow 5% margin for circulation / walls
            if total_min_room_area > target * 1.05:
                raise ValueError(
                    f"Sum of minimum room areas ({total_min_room_area:.1f} m²) "
                    f"exceeds unit target area ({target:.1f} m²)"
                )
        return rooms


class StoreySpec(BaseModel):
    """Specification of an individual floor level."""

    model_config = ConfigDict(extra="forbid")

    storey_index: int = Field(..., description="0 for Ground, 1 for Level 1, -1 for Basement 1")
    name: str = Field(..., min_length=1, max_length=120, description="E.g. 'Ground Floor', 'Level 1'")
    elevation_m: float = Field(..., description="Z elevation from site grade in meters")
    height_m: float = Field(default=3.2, ge=2.2, le=12.0, description="Floor-to-floor height in meters")
    is_ground: bool = Field(default=False)
    is_rooftop: bool = Field(default=False)
    is_basement: bool = Field(default=False)
    target_use: StoreyUseType = Field(default=StoreyUseType.RESIDENTIAL)
    unit_mix: List[UnitRequirement] = Field(default_factory=list)
    setback_override: Optional[SetbackSpec] = Field(None, description="Optional setback step-back for higher floors")


# ==============================================================================
# Root DesignSpec Container
# ==============================================================================


class DesignSpec(BaseModel):
    """
    Root pure-intent architectural specification.

    Enforces strict architectural constraints:
    - Pure intent: Zero raw coordinate or polygon mesh data permitted.
    - Elevation monotonicity: Storey elevations must strictly increase.
    - Storey count consistency: Storey list length must match total storeys when provided.
    - Site setback validity: Setback margins must fit within parcel boundary.
    """

    model_config = ConfigDict(extra="forbid")

    spec_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique DesignSpec UUID")
    project_name: str = Field(default="Architectural Project", min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # 1. Site & Context
    site: SiteParameters = Field(default_factory=SiteParameters)

    # 2. Building Typology & Structural Category
    building_typology: BuildingTypology = Field(default=BuildingTypology.RESIDENTIAL)
    occupancy_category: OccupancyCategory = Field(default=OccupancyCategory.RESIDENTIAL_MULTI_FAMILY)
    structural_system: StructuralSystem = Field(default=StructuralSystem.REINFORCED_CONCRETE_FRAME)

    # 3. Floor Count & Height Parameters
    total_storeys: int = Field(default=2, ge=1, le=100)
    floor_to_floor_height_m: float = Field(default=3.2, ge=2.2, le=12.0)
    ground_floor_height_m: float = Field(default=3.6, ge=2.2, le=15.0)
    basement_storeys: int = Field(default=0, ge=0, le=10)
    storeys: List[StoreySpec] = Field(default_factory=list)

    # 4. MEP & Systems
    mep_strategy: MEPStrategy = Field(default_factory=MEPStrategy)

    # 5. Aesthetic Palette
    aesthetic_palette: AestheticPalette = Field(default_factory=AestheticPalette)

    @model_validator(mode="before")
    @classmethod
    def check_no_raw_geometry_before(cls, data: Any) -> Any:
        """Pre-validation check against raw geometry keys."""
        assert_no_raw_geometry(data)
        return data

    @model_validator(mode="after")
    def validate_design_spec_invariants(self) -> DesignSpec:
        """Post-validation check on elevation monotonicity and storey counts."""
        # 1. Recursive check on dump
        assert_no_raw_geometry(self.model_dump())

        # 2. Storey validations if storeys are provided
        if self.storeys:
            expected_count = self.total_storeys + self.basement_storeys
            if len(self.storeys) != expected_count:
                raise ValueError(
                    f"Storey count mismatch: expected {expected_count} storeys "
                    f"({self.total_storeys} above-ground + {self.basement_storeys} basements), "
                    f"got {len(self.storeys)}"
                )

            # Check strictly monotonic elevations
            for i in range(1, len(self.storeys)):
                prev = self.storeys[i - 1]
                curr = self.storeys[i]
                if curr.elevation_m <= prev.elevation_m:
                    raise ValueError(
                        f"Non-monotonic storey elevations: storey '{curr.name}' (index {curr.storey_index}) "
                        f"has elevation {curr.elevation_m:.2f}m which is not greater than "
                        f"previous storey '{prev.name}' elevation {prev.elevation_m:.2f}m"
                    )

        return self
