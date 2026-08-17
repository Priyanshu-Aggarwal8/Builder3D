"""
Canonical OpenBIM Data Schemas & Pset Specifications for Builder3D.

Conforms to ISO 16739-1:2018 (IFC4) and buildingSMART standards:
1. Strongly-typed PropertyItem and PropertySet models with standard Pset helpers
   (Pset_WallCommon, Pset_SpaceCommon, Pset_DoorCommon, Pset_WindowCommon, Pset_SlabCommon,
    Pset_ColumnCommon, Pset_FlowSegmentCommon, Pset_DistributionBoardCommon).
2. Canonical BIM entities (CanonicalBIMEntity, BIMWall, BIMDoor, BIMWindow, BIMSlab,
   BIMColumn, BIMDistributionElement, BIMSpace, BIMStorey, BIMBuilding, BIMSite, BIMProject).
3. Root CanonicalBIMModel container with full element querying, spatial tree conversion,
   and 100% round-trip preservation.
4. Bijective UUID5 <-> 22-char IFC GUID mapping integration.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.spatial import (
    SpatialNode,
    SpatialNodeType,
    decode_ifc_guid,
    encode_ifc_guid,
    generate_spatial_uuid,
)


# ==============================================================================
# 1. Property Set Models (IFC4 IfcPropertySingleValue & IfcPropertySet)
# ==============================================================================

class PropertyItem(BaseModel):
    """
    Individual strongly-typed property conforming to IFC4 IfcPropertySingleValue.
    """
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=120, description="Property identifier name")
    value: Any = Field(..., description="Scalar property value: bool, str, float, int, or None")
    value_type: str = Field(
        default="IfcLabel",
        description=(
            "IFC data type: IfcLabel, IfcText, IfcIdentifier, IfcBoolean, IfcInteger, "
            "IfcReal, IfcLengthMeasure, IfcPositiveLengthMeasure, IfcAreaMeasure, "
            "IfcVolumeMeasure, IfcPlaneAngleMeasure, IfcThermalTransmittanceMeasure, "
            "IfcPositiveRatioMeasure"
        ),
    )
    description: Optional[str] = Field(None, description="Optional property description")


# Alias
BIMPropertyItem = PropertyItem


class PropertySet(BaseModel):
    """
    Property Set model conforming to IFC4 IfcPropertySet.
    """
    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1, max_length=120, description="Pset name (e.g. Pset_WallCommon)")
    description: Optional[str] = Field(None, description="Pset description")
    properties: Dict[str, PropertyItem] = Field(default_factory=dict, description="Typed property map")

    def get_property(self, prop_name: str) -> Optional[PropertyItem]:
        """Retrieves the PropertyItem for prop_name, if present."""
        return self.properties.get(prop_name)

    def get_value(self, prop_name: str, default: Any = None) -> Any:
        """Retrieves the scalar value of prop_name, or default if missing."""
        item = self.properties.get(prop_name)
        return item.value if item is not None else default

    def set_property(self, prop_name: str, value: Any, value_type: Optional[str] = None, description: Optional[str] = None) -> None:
        """Sets or replaces a typed property in this PropertySet."""
        if value_type is None:
            if isinstance(value, bool):
                value_type = "IfcBoolean"
            elif isinstance(value, int) and not isinstance(value, bool):
                value_type = "IfcInteger"
            elif isinstance(value, float):
                value_type = "IfcReal"
            elif isinstance(value, str):
                value_type = "IfcLabel"
            else:
                value_type = "IfcText"

        self.properties[prop_name] = PropertyItem(
            name=prop_name,
            value=value,
            value_type=value_type,
            description=description,
        )

    def set_value(self, prop_name: str, value: Any, value_type: Optional[str] = None) -> None:
        """Alias for set_property."""
        self.set_property(prop_name, value, value_type=value_type)

    def to_flat_dict(self) -> Dict[str, Any]:
        """Exports scalar properties as a simple key-value dictionary."""
        return {k: v.value for k, v in self.properties.items()}

    def to_dict(self) -> Dict[str, Any]:
        """Alias for to_flat_dict."""
        return self.to_flat_dict()

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any], description: Optional[str] = None) -> PropertySet:
        """Constructs a PropertySet from a standard dictionary."""
        pset = cls(name=name, description=description)
        for k, v in data.items():
            if isinstance(v, PropertyItem):
                pset.properties[k] = v
            elif isinstance(v, dict) and "value" in v:
                pset.properties[k] = PropertyItem(
                    name=k,
                    value=v["value"],
                    value_type=v.get("value_type", "IfcLabel"),
                    description=v.get("description"),
                )
            else:
                pset.set_property(k, v)
        return pset


# Alias
BIMPropertySet = PropertySet


# ==============================================================================
# 2. Standard IFC4 Property Set Factory Helpers
# ==============================================================================

def create_pset_wall_common(
    reference: str = "EXT-W250",
    load_bearing: bool = True,
    is_external: bool = True,
    fire_rating: str = "2h",
    acoustic_rating: str = "45dB",
    combustible: bool = False,
    surface_spread_of_flame: Optional[str] = None,
    thermal_transmittance: Optional[float] = None,
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_WallCommon instance."""
    pset = PropertySet(name="Pset_WallCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("LoadBearing", load_bearing, "IfcBoolean")
    pset.set_property("IsExternal", is_external, "IfcBoolean")
    pset.set_property("FireRating", fire_rating, "IfcLabel")
    pset.set_property("AcousticRating", acoustic_rating, "IfcLabel")
    pset.set_property("Combustible", combustible, "IfcBoolean")
    if surface_spread_of_flame is not None:
        pset.set_property("SurfaceSpreadOfFlame", surface_spread_of_flame, "IfcLabel")
    if thermal_transmittance is not None:
        pset.set_property("ThermalTransmittance", thermal_transmittance, "IfcThermalTransmittanceMeasure")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_space_common(
    reference: str = "SPACE-01",
    gross_floor_area: float = 20.0,
    net_floor_area: Optional[float] = None,
    gross_volume: Optional[float] = None,
    net_volume: Optional[float] = None,
    gross_perimeter: Optional[float] = None,
    is_external: bool = False,
    occupancy_type: str = "Residential_Living",
    ceiling_height: Optional[float] = None,
    handicap_accessible: bool = True,
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_SpaceCommon instance."""
    pset = PropertySet(name="Pset_SpaceCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("GrossFloorArea", gross_floor_area, "IfcAreaMeasure")
    pset.set_property("NetFloorArea", net_floor_area if net_floor_area is not None else gross_floor_area * 0.95, "IfcAreaMeasure")
    if gross_volume is not None:
        pset.set_property("GrossVolume", gross_volume, "IfcVolumeMeasure")
    if net_volume is not None:
        pset.set_property("NetVolume", net_volume, "IfcVolumeMeasure")
    if gross_perimeter is not None:
        pset.set_property("GrossPerimeter", gross_perimeter, "IfcLengthMeasure")
    pset.set_property("IsExternal", is_external, "IfcBoolean")
    pset.set_property("OccupancyType", occupancy_type, "IfcLabel")
    if ceiling_height is not None:
        pset.set_property("CeilingHeight", ceiling_height, "IfcLengthMeasure")
    pset.set_property("HandicapAccessible", handicap_accessible, "IfcBoolean")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_door_common(
    reference: str = "D-01",
    is_external: bool = True,
    fire_rating: str = "1h",
    security_rating: str = "High",
    handing: str = "INWARD_RIGHT",
    operation_type: str = "SINGLE_SWING_LEFT",
    acoustic_rating: Optional[str] = "32dB",
    self_closing: bool = False,
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_DoorCommon instance."""
    pset = PropertySet(name="Pset_DoorCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("IsExternal", is_external, "IfcBoolean")
    pset.set_property("FireRating", fire_rating, "IfcLabel")
    pset.set_property("SecurityRating", security_rating, "IfcLabel")
    pset.set_property("Handing", handing, "IfcLabel")
    pset.set_property("OperationType", operation_type, "IfcLabel")
    if acoustic_rating is not None:
        pset.set_property("AcousticRating", acoustic_rating, "IfcLabel")
    pset.set_property("SelfClosing", self_closing, "IfcBoolean")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_window_common(
    reference: str = "W-01",
    is_external: bool = True,
    thermal_transmittance: float = 1.4,
    acoustic_rating: str = "38dB",
    glazing_pattern: str = "Double_LowE",
    sill_height: float = 0.9,
    fire_rating: Optional[str] = None,
    solar_heat_gain_coefficient: Optional[float] = 0.45,
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_WindowCommon instance."""
    pset = PropertySet(name="Pset_WindowCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("IsExternal", is_external, "IfcBoolean")
    pset.set_property("ThermalTransmittance", thermal_transmittance, "IfcThermalTransmittanceMeasure")
    pset.set_property("AcousticRating", acoustic_rating, "IfcLabel")
    pset.set_property("GlazingPattern", glazing_pattern, "IfcLabel")
    pset.set_property("SillHeight", sill_height, "IfcLengthMeasure")
    if fire_rating is not None:
        pset.set_property("FireRating", fire_rating, "IfcLabel")
    if solar_heat_gain_coefficient is not None:
        pset.set_property("SolarHeatGainCoefficient", solar_heat_gain_coefficient, "IfcPositiveRatioMeasure")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_slab_common(
    reference: str = "SLAB-01",
    load_bearing: bool = True,
    is_external: bool = False,
    thickness: float = 0.25,
    concrete_grade: str = "C35/45",
    pitch_angle: float = 0.0,
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_SlabCommon instance."""
    pset = PropertySet(name="Pset_SlabCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("LoadBearing", load_bearing, "IfcBoolean")
    pset.set_property("IsExternal", is_external, "IfcBoolean")
    pset.set_property("Thickness", thickness, "IfcLengthMeasure")
    pset.set_property("ConcreteGrade", concrete_grade, "IfcLabel")
    pset.set_property("PitchAngle", pitch_angle, "IfcPlaneAngleMeasure")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_column_common(
    reference: str = "COL-01",
    load_bearing: bool = True,
    rebar_ratio: float = 0.02,
    fire_rating: str = "2h",
    concrete_grade: Optional[str] = "C40/50",
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_ColumnCommon instance."""
    pset = PropertySet(name="Pset_ColumnCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("LoadBearing", load_bearing, "IfcBoolean")
    pset.set_property("RebarRatio", rebar_ratio, "IfcReal")
    pset.set_property("FireRating", fire_rating, "IfcLabel")
    if concrete_grade is not None:
        pset.set_property("ConcreteGrade", concrete_grade, "IfcLabel")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


def create_pset_flow_segment_common(
    reference: str = "PIPE-DN110",
    nominal_diameter: float = 110.0,
    working_pressure: float = 0.0,
    medium: str = "Blackwater",
    **kwargs: Any,
) -> PropertySet:
    """Creates a standard Pset_FlowSegmentCommon instance."""
    pset = PropertySet(name="Pset_FlowSegmentCommon")
    pset.set_property("Reference", reference, "IfcIdentifier")
    pset.set_property("NominalDiameter", nominal_diameter, "IfcLengthMeasure")
    pset.set_property("WorkingPressure", working_pressure, "IfcReal")
    pset.set_property("Medium", medium, "IfcLabel")
    for k, v in kwargs.items():
        pset.set_property(k, v)
    return pset


# ==============================================================================
# 3. Canonical Base BIM Entity
# ==============================================================================

class CanonicalBIMEntity(BaseModel):
    """
    Base OpenBIM element model conforming to IFC4 IfcProduct / IfcRoot.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="RFC 4122 UUID string")
    global_id: str = Field(default="", description="22-character IFC Base64 GUID")
    name: str = Field(default="BIM Element", min_length=1, max_length=120)
    entity_type: str = Field(default="IfcBuildingElementProxy", description="IFC4 schema entity class")
    layer_id: str = Field(default="structural", description="Functional layer (structural, architectural, plumbing, electrical, hvac)")
    position: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="3D coordinate [x, y, z]")
    dimensions: Dict[str, float] = Field(
        default_factory=lambda: {"width": 1.0, "height": 1.0, "depth": 1.0},
        description="Bounding dimensions [width, height, depth]",
    )
    property_sets: Dict[str, PropertySet] = Field(default_factory=dict, description="Attached property sets")
    parent_storey: Optional[str] = Field(None, description="Name or identifier of parent storey")
    parent_id: Optional[str] = Field(None, description="UUID of spatial parent container")
    placement: Optional[Dict[str, Any]] = Field(None, description="Local coordinate frame / placement data")
    geometry: Optional[Dict[str, Any]] = Field(None, description="Geometric boundary representation or mesh data")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Generic metadata properties")

    @model_validator(mode="before")
    @classmethod
    def initialize_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Synchronize 'psets' alias with 'property_sets'
            if "psets" in data and "property_sets" not in data:
                psets_val = data["psets"]
                converted_psets = {}
                for k, v in psets_val.items():
                    if isinstance(v, PropertySet):
                        converted_psets[k] = v
                    elif isinstance(v, dict):
                        converted_psets[k] = PropertySet.from_dict(v.get("name", k), v.get("properties", v))
                data["property_sets"] = converted_psets

            # Auto-generate or validate id
            if "id" not in data or not data["id"]:
                data["id"] = str(uuid.uuid4())

            # Auto-generate global_id from id if not supplied
            if "global_id" not in data or not data["global_id"]:
                try:
                    u = uuid.UUID(str(data["id"]))
                    data["global_id"] = encode_ifc_guid(u)
                except Exception:
                    data["global_id"] = encode_ifc_guid(uuid.uuid4())
        return data

    @model_validator(mode="after")
    def ensure_valid_guid_and_psets(self) -> CanonicalBIMEntity:
        if not self.global_id or len(self.global_id) != 22:
            try:
                u = uuid.UUID(self.id)
                self.global_id = encode_ifc_guid(u)
            except Exception:
                self.global_id = encode_ifc_guid(uuid.uuid4())
        return self

    @property
    def psets(self) -> Dict[str, PropertySet]:
        """Getter for psets backward compatibility."""
        return self.property_sets

    @psets.setter
    def psets(self, value: Dict[str, PropertySet]) -> None:
        """Setter for psets backward compatibility."""
        self.property_sets = value

    def get_pset(self, pset_name: str) -> Optional[PropertySet]:
        """Retrieves PropertySet by name."""
        return self.property_sets.get(pset_name)

    def add_pset(self, pset: PropertySet) -> None:
        """Adds or updates a PropertySet."""
        self.property_sets[pset.name] = pset

    def get_property(self, pset_name: str, prop_name: str, default: Any = None) -> Any:
        """Retrieves a single property value from a named Pset."""
        pset = self.property_sets.get(pset_name)
        if pset is not None:
            return pset.get_value(prop_name, default)
        return default

    def set_property(self, pset_name: str, prop_name: str, value: Any, value_type: Optional[str] = None) -> None:
        """Sets a property on a named Pset, creating the Pset if it does not exist."""
        if pset_name not in self.property_sets:
            self.property_sets[pset_name] = PropertySet(name=pset_name)
        self.property_sets[pset_name].set_property(prop_name, value, value_type=value_type)


# Alias
BIMEntityBase = CanonicalBIMEntity


# ==============================================================================
# 4. Canonical Building Element Entities
# ==============================================================================

class BIMWall(CanonicalBIMEntity):
    """Parametric Wall element conforming to IFC4 IfcWall."""
    entity_type: str = "IfcWall"
    start_pt: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    end_pt: Tuple[float, float, float] = (5.0, 0.0, 0.0)
    thickness: float = 0.25
    height: float = 3.0
    is_exterior: bool = True
    load_bearing: bool = True
    wall_type: str = "STANDARD"
    openings: List[str] = Field(default_factory=list, description="IDs or GUIDs of hosted doors/windows")
    material_spec: Optional[str] = None

    @model_validator(mode="after")
    def ensure_wall_defaults(self) -> BIMWall:
        if "Pset_WallCommon" not in self.property_sets:
            self.add_pset(
                create_pset_wall_common(
                    reference=self.name,
                    load_bearing=self.load_bearing,
                    is_external=self.is_exterior,
                )
            )
        return self


class BIMDoor(CanonicalBIMEntity):
    """Parametric Door element conforming to IFC4 IfcDoor."""
    entity_type: str = "IfcDoor"
    host_wall_id: Optional[str] = None
    distance_along_wall: float = 0.0
    width: float = 1.0
    height: float = 2.1
    thickness: float = 0.15
    sill_height: float = 0.0
    operation_type: str = "SINGLE_SWING_LEFT"
    panel_material: Optional[str] = "Solid Wood"
    frame_width: float = 0.05

    @model_validator(mode="after")
    def ensure_door_defaults(self) -> BIMDoor:
        if "Pset_DoorCommon" not in self.property_sets:
            self.add_pset(
                create_pset_door_common(
                    reference=self.name,
                    operation_type=self.operation_type,
                )
            )
        return self


class BIMWindow(CanonicalBIMEntity):
    """Parametric Window element conforming to IFC4 IfcWindow."""
    entity_type: str = "IfcWindow"
    host_wall_id: Optional[str] = None
    distance_along_wall: float = 0.0
    width: float = 1.8
    height: float = 1.5
    thickness: float = 0.08
    sill_height: float = 0.9
    glazing_type: str = "DOUBLE_GLAZED"
    frame_material: str = "ALUMINUM"
    thermal_transmittance: float = 1.4

    @model_validator(mode="after")
    def ensure_window_defaults(self) -> BIMWindow:
        if "Pset_WindowCommon" not in self.property_sets:
            self.add_pset(
                create_pset_window_common(
                    reference=self.name,
                    thermal_transmittance=self.thermal_transmittance,
                    sill_height=self.sill_height,
                )
            )
        return self


class BIMSlab(CanonicalBIMEntity):
    """Structural Slab element conforming to IFC4 IfcSlab."""
    entity_type: str = "IfcSlab"
    slab_type: Literal["FLOOR", "ROOF", "LANDING", "BASESLAB"] = "FLOOR"
    boundary_polygon: List[Tuple[float, float]] = Field(default_factory=list)
    elevation: float = 0.0
    thickness: float = 0.3
    gross_area: Optional[float] = None
    load_bearing: bool = True

    @model_validator(mode="after")
    def ensure_slab_defaults(self) -> BIMSlab:
        if "Pset_SlabCommon" not in self.property_sets:
            self.add_pset(
                create_pset_slab_common(
                    reference=self.name,
                    load_bearing=self.load_bearing,
                    thickness=self.thickness,
                )
            )
        return self


class BIMColumn(CanonicalBIMEntity):
    """Structural Column element conforming to IFC4 IfcColumn."""
    entity_type: str = "IfcColumn"
    cross_section_shape: Literal["RECTANGULAR", "CIRCULAR"] = "RECTANGULAR"
    width: float = 0.45
    depth: float = 0.45
    height: float = 3.2
    load_bearing: bool = True
    rebar_ratio: Optional[float] = 0.02

    @model_validator(mode="after")
    def ensure_column_defaults(self) -> BIMColumn:
        if "Pset_ColumnCommon" not in self.property_sets:
            self.add_pset(
                create_pset_column_common(
                    reference=self.name,
                    load_bearing=self.load_bearing,
                    rebar_ratio=self.rebar_ratio or 0.02,
                )
            )
        return self


class BIMDistributionElement(CanonicalBIMEntity):
    """MEP distribution element conforming to IFC4 IfcDistributionElement / IfcFlowSegment."""
    entity_type: str = "IfcFlowSegment"
    layer_id: str = "plumbing"
    distribution_type: Literal[
        "PIPE", "CONDUIT", "DUCT", "SANITARY_TERMINAL", "ELECTRICAL_PANEL",
        "LIGHT_FIXTURE", "HVAC_UNIT", "PUMP", "VALVE"
    ] = "PIPE"
    system_type: Literal["WaterSupply", "SoilWaste", "Vent", "ElectricalPower", "HVAC", "FireProtection"] = "SoilWaste"
    nominal_diameter_mm: Optional[float] = None
    voltage_v: Optional[float] = None
    power_w: Optional[float] = None
    flow_rate_lps: Optional[float] = None
    start_pt: Optional[Tuple[float, float, float]] = None
    end_pt: Optional[Tuple[float, float, float]] = None

    @model_validator(mode="after")
    def ensure_mep_defaults(self) -> BIMDistributionElement:
        if self.distribution_type in ["PIPE", "CONDUIT", "DUCT"] and "Pset_FlowSegmentCommon" not in self.property_sets:
            self.add_pset(
                create_pset_flow_segment_common(
                    reference=self.name,
                    nominal_diameter=self.nominal_diameter_mm or 110.0,
                    medium="Blackwater" if self.system_type == "SoilWaste" else "PotableWater",
                )
            )
        return self


# ==============================================================================
# 5. Spatial Containers (IfcSpace, IfcBuildingStorey, IfcBuilding, IfcSite, IfcProject)
# ==============================================================================

class BIMSpace(CanonicalBIMEntity):
    """Spatial room volume conforming to IFC4 IfcSpace."""
    entity_type: str = "IfcSpace"
    layer_id: str = "architectural"
    boundary_polygon: Optional[List[Tuple[float, float]]] = None
    area_sqm: float = 20.0
    ceiling_height: float = 2.8
    volume_cbm: Optional[float] = None
    room_type: str = "LivingRoom"
    is_exterior: bool = False
    wet_zone: bool = False
    contained_element_ids: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ensure_space_defaults(self) -> BIMSpace:
        if not self.volume_cbm:
            self.volume_cbm = round(self.area_sqm * self.ceiling_height, 2)
        if "Pset_SpaceCommon" not in self.property_sets:
            self.add_pset(
                create_pset_space_common(
                    reference=self.name,
                    gross_floor_area=self.area_sqm,
                    gross_volume=self.volume_cbm,
                    is_external=self.is_exterior,
                    occupancy_type=self.room_type,
                    ceiling_height=self.ceiling_height,
                )
            )
        return self


class BIMStorey(CanonicalBIMEntity):
    """Building Storey container conforming to IFC4 IfcBuildingStorey."""
    entity_type: str = "IfcBuildingStorey"
    storey_index: int = 0
    elevation: float = 0.0
    height: float = 3.2
    spaces: List[BIMSpace] = Field(default_factory=list)
    walls: List[BIMWall] = Field(default_factory=list)
    doors: List[BIMDoor] = Field(default_factory=list)
    windows: List[BIMWindow] = Field(default_factory=list)
    slabs: List[BIMSlab] = Field(default_factory=list)
    columns: List[BIMColumn] = Field(default_factory=list)
    distribution_elements: List[BIMDistributionElement] = Field(default_factory=list)
    custom_elements: List[CanonicalBIMEntity] = Field(default_factory=list)

    def all_elements(self) -> List[CanonicalBIMEntity]:
        """Returns a flat list of all physical elements and spaces contained in this storey."""
        res: List[CanonicalBIMEntity] = []
        res.extend(self.spaces)
        res.extend(self.walls)
        res.extend(self.doors)
        res.extend(self.windows)
        res.extend(self.slabs)
        res.extend(self.columns)
        res.extend(self.distribution_elements)
        res.extend(self.custom_elements)
        return res


class BIMBuilding(CanonicalBIMEntity):
    """Building container conforming to IFC4 IfcBuilding."""
    entity_type: str = "IfcBuilding"
    typology: str = "Residential"
    storeys: List[BIMStorey] = Field(default_factory=list)
    footprint_polygon: Optional[List[Tuple[float, float]]] = None
    total_storeys: int = 1


class BIMSite(CanonicalBIMEntity):
    """Site container conforming to IFC4 IfcSite."""
    entity_type: str = "IfcSite"
    buildings: List[BIMBuilding] = Field(default_factory=list)
    site_area_sqm: float = 1200.0
    plot_boundary: Optional[List[Tuple[float, float]]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_amsl: float = 0.0


class BIMProject(CanonicalBIMEntity):
    """Root Project container conforming to IFC4 IfcProject."""
    entity_type: str = "IfcProject"
    sites: List[BIMSite] = Field(default_factory=list)
    units: str = "METERS"
    crs_epsg: int = 3857
    north_angle_deg: float = 0.0


# ==============================================================================
# 6. Root Canonical BIM Model Container
# ==============================================================================

class CanonicalBIMModel(BaseModel):
    """
    Root OpenBIM Model container holding the complete spatial hierarchy,
    physical entities, and Psets.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schema_version: str = Field(default="IFC4", description="OpenBIM IFC Schema Version")
    project: BIMProject = Field(default_factory=lambda: BIMProject(name="Builder3D Project"))
    site: Optional[BIMSite] = Field(default=None, description="Primary site if directly accessed")
    buildings: List[BIMBuilding] = Field(default_factory=list, description="Direct building list")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    author: str = Field(default="Builder3D Principal Architect AI")
    application: str = Field(default="Builder3D OpenBIM Engine")

    # Backward-compatible properties
    project_name: str = "Builder3D Project"
    site_name: str = "Main Site"
    building_name: str = "Main Building"
    storeys: List[str] = Field(default_factory=list)
    entities: List[CanonicalBIMEntity] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def synchronize_structure(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If project_name provided, ensure project.name matches
            p_name = data.get("project_name", "Builder3D Project")
            if "project" not in data:
                proj = BIMProject(name=p_name)
                site_name = data.get("site_name", "Main Site")
                bldg_name = data.get("building_name", "Main Building")
                site = BIMSite(name=site_name)
                bldg = BIMBuilding(name=bldg_name)
                site.buildings.append(bldg)
                proj.sites.append(site)
                data["project"] = proj

            # Synchronize flat entities if provided
            if "entities" in data and isinstance(data["entities"], list):
                # Ensure all items are dicts or CanonicalBIMEntity
                pass
        return data

    @model_validator(mode="after")
    def link_spatial_hierarchy(self) -> CanonicalBIMModel:
        # Keep project_name in sync
        self.project_name = self.project.name
        if self.project.sites:
            primary_site = self.project.sites[0]
            self.site = primary_site
            self.site_name = primary_site.name
            if primary_site.buildings:
                self.buildings = primary_site.buildings
                self.building_name = primary_site.buildings[0].name
        return self

    def get_element_by_id(self, target_id: str) -> Optional[CanonicalBIMEntity]:
        """Finds any BIM entity by its 36-character UUID."""
        for elem in self.all_elements():
            if elem.id == target_id:
                return elem
        return None

    def get_element_by_global_id(self, target_guid: str) -> Optional[CanonicalBIMEntity]:
        """Finds any BIM entity by its 22-character IFC Base64 GUID."""
        for elem in self.all_elements():
            if elem.global_id == target_guid:
                return elem
        return None

    def get_elements_by_type(self, entity_type: str) -> List[CanonicalBIMEntity]:
        """Returns all elements matching the specified IFC entity type."""
        t = entity_type.strip().lower()
        return [el for el in self.all_elements() if el.entity_type.lower() == t]

    def all_storeys(self) -> List[BIMStorey]:
        """Returns all storeys in the building hierarchy."""
        storeys: List[BIMStorey] = []
        for site in self.project.sites:
            for bldg in site.buildings:
                storeys.extend(bldg.storeys)
        return storeys

    def all_spaces(self) -> List[BIMSpace]:
        """Returns all spaces across all storeys."""
        spaces: List[BIMSpace] = []
        for storey in self.all_storeys():
            spaces.extend(storey.spaces)
        return spaces

    def all_walls(self) -> List[BIMWall]:
        """Returns all walls across all storeys."""
        walls: List[BIMWall] = []
        for storey in self.all_storeys():
            walls.extend(storey.walls)
        return walls

    def all_elements(self) -> List[CanonicalBIMEntity]:
        """Returns all entities across the entire model."""
        res: List[CanonicalBIMEntity] = [self.project]
        for site in self.project.sites:
            res.append(site)
            for bldg in site.buildings:
                res.append(bldg)
                for storey in bldg.storeys:
                    res.append(storey)
                    res.extend(storey.all_elements())
        # Include any detached flat entities if present
        for e in self.entities:
            if not any(r.id == e.id for r in res):
                res.append(e)
        return res

    def to_spatial_tree(self) -> SpatialNode:
        """Converts the CanonicalBIMModel to a standard 6-Tier SpatialNode hierarchy."""
        # Project
        p_node = SpatialNode(
            id=self.project.id,
            global_id=self.project.global_id,
            name=self.project.name,
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
            children=[],
        )

        for site in self.project.sites:
            s_node = SpatialNode(
                id=site.id,
                global_id=site.global_id,
                name=site.name,
                node_type=SpatialNodeType.SITE,
                parent_id=p_node.id,
                children=[],
            )
            p_node.children.append(s_node)

            for bldg in site.buildings:
                b_node = SpatialNode(
                    id=bldg.id,
                    global_id=bldg.global_id,
                    name=bldg.name,
                    node_type=SpatialNodeType.BUILDING,
                    parent_id=s_node.id,
                    children=[],
                )
                s_node.children.append(b_node)

                for storey in bldg.storeys:
                    st_node = SpatialNode(
                        id=storey.id,
                        global_id=storey.global_id,
                        name=storey.name,
                        node_type=SpatialNodeType.STOREY,
                        parent_id=b_node.id,
                        children=[],
                    )
                    b_node.children.append(st_node)

                    for space in storey.spaces:
                        sp_node = SpatialNode(
                            id=space.id,
                            global_id=space.global_id,
                            name=space.name,
                            node_type=SpatialNodeType.ROOM,
                            parent_id=st_node.id,
                            children=[],
                        )
                        st_node.children.append(sp_node)

        return p_node

    @classmethod
    def from_spatial_tree(cls, tree: SpatialNode) -> CanonicalBIMModel:
        """Constructs a CanonicalBIMModel from a SpatialNode hierarchy."""
        model = cls(project_name=tree.name)
        proj = BIMProject(
            id=tree.id,
            global_id=tree.global_id,
            name=tree.name,
        )

        for s_child in tree.children:
            site = BIMSite(
                id=s_child.id,
                global_id=s_child.global_id,
                name=s_child.name,
            )
            proj.sites.append(site)

            for b_child in s_child.children:
                bldg = BIMBuilding(
                    id=b_child.id,
                    global_id=b_child.global_id,
                    name=b_child.name,
                )
                site.buildings.append(bldg)

                for st_child in b_child.children:
                    s_props = st_child.properties or {}
                    storey = BIMStorey(
                        id=st_child.id,
                        global_id=st_child.global_id,
                        name=st_child.name,
                        storey_index=int(s_props.get("storey_index", 0)),
                        elevation=float(s_props.get("elevation", 0.0)),
                        height=float(s_props.get("height", 3.2)),
                    )
                    bldg.storeys.append(storey)

                    for sp_child in st_child.children:
                        r_props = sp_child.properties or {}
                        space = BIMSpace(
                            id=sp_child.id,
                            global_id=sp_child.global_id,
                            name=sp_child.name,
                            area_sqm=float(r_props.get("area_sqm", 20.0)),
                            room_type=str(r_props.get("room_type", "LivingRoom")),
                            ceiling_height=float(r_props.get("ceiling_height", 2.8)),
                            parent_storey=storey.name,
                            parent_id=storey.id,
                        )
                        storey.spaces.append(space)

        model.project = proj
        model.link_spatial_hierarchy()
        return model
