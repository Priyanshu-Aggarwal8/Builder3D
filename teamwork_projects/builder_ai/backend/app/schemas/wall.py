"""
Pydantic Schemas for Parametric Wall Engine and Hosted Openings (Milestone 3).

Establishes Interface Contract 4:
- OpeningType, DoorSwingDirection, WallSubSegmentType Enums
- HostedOpening (DOOR, WINDOW, PASS_THROUGH)
- WallSubSegment (SOLID, PRE, POST, LINTEL, SILL)
- ParametricWall (3D coordinates, thickness, height, openings, sub-segments)
- StoreyWalls (Collection of walls per storey)
- REST API Request/Response DTOs
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from app.schemas.spatial_solver import FloorplanLayout, RoomBoundary


# ==============================================================================
# 1. Enums
# ==============================================================================

class OpeningType(str, Enum):
    """Architectural opening classification."""
    DOOR = "DOOR"
    WINDOW = "WINDOW"
    PASS_THROUGH = "PASS_THROUGH"


class DoorSwingDirection(str, Enum):
    """Door leaf swing trajectory and hinge location."""
    INWARD_LEFT = "INWARD_LEFT"
    INWARD_RIGHT = "INWARD_RIGHT"
    OUTWARD_LEFT = "OUTWARD_LEFT"
    OUTWARD_RIGHT = "OUTWARD_RIGHT"
    SLIDING = "SLIDING"
    SLIDING_LEFT = "SLIDING_LEFT"
    SLIDING_RIGHT = "SLIDING_RIGHT"
    NONE = "NONE"


# Alias for cross-contract compatibility
SwingDirection = DoorSwingDirection


class WallSubSegmentType(str, Enum):
    """Structural classification of wall sub-volume."""
    SOLID = "SOLID"
    PRE = "PRE"
    POST = "POST"
    LINTEL = "LINTEL"
    SILL = "SILL"
    VOID = "VOID"


# Alias for cross-contract compatibility
SubSegmentType = WallSubSegmentType


# ==============================================================================
# 2. Core Domain Models (Interface Contract 4)
# ==============================================================================

class HostedOpening(BaseModel):
    """Architectural door or window hosted parametrically within a host wall run."""

    model_config = ConfigDict(extra="ignore")

    opening_id: str = Field(..., description="Unique opening identifier")
    opening_type: Union[OpeningType, str] = Field(..., description="DOOR, WINDOW, or PASS_THROUGH")
    wall_id: str = Field(..., description="ID of host ParametricWall")
    distance_along_wall: float = Field(
        ..., ge=0.0, description="Offset from wall start point along centerline in meters"
    )
    width: float = Field(..., gt=0.0, description="Physical clear width in meters")
    height: float = Field(..., gt=0.0, description="Physical clear height in meters")
    sill_height: float = Field(
        default=0.0, ge=0.0, description="Elevation of opening bottom above floor in meters (0 for doors)"
    )
    swing_direction: Optional[Union[DoorSwingDirection, str]] = Field(
        default=None, description="Door hinge & swing direction"
    )
    frame_width: float = Field(default=0.05, ge=0.0, description="Opening frame profile width in meters")
    frame_thickness: float = Field(default=0.05, ge=0.0, description="Opening frame profile thickness in meters")
    glazing_thickness: float = Field(default=0.02, ge=0.0, description="Glass pane thickness in meters")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional BIM/Pset properties")

    @model_validator(mode="after")
    def validate_opening_rules(self) -> HostedOpening:
        op_type_str = self.opening_type.value if isinstance(self.opening_type, Enum) else str(self.opening_type)
        if op_type_str.upper() == "DOOR" and self.sill_height > 1e-4:
            raise ValueError(
                f"Door opening '{self.opening_id}' must have sill_height == 0.0, got {self.sill_height}"
            )
        return self


class WallSubSegment(BaseModel):
    """Solid or void 3D sub-mesh bounding volume generated around hosted openings."""

    model_config = ConfigDict(extra="ignore")

    segment_id: str = Field(..., description="Unique segment identifier")
    wall_id: str = Field(..., description="ID of host ParametricWall")
    segment_type: Union[WallSubSegmentType, str] = Field(..., description="SOLID, PRE, POST, LINTEL, or SILL")
    start_dist: float = Field(..., ge=0.0, description="Start distance along wall centerline in meters")
    end_dist: float = Field(..., ge=0.0, description="End distance along wall centerline in meters")
    bottom_elev: float = Field(..., ge=0.0, description="Lower vertical elevation in meters")
    top_elev: float = Field(..., ge=0.0, description="Upper vertical elevation in meters")
    thickness: float = Field(..., gt=0.0, description="Wall thickness in meters")
    volume: float = Field(..., ge=0.0, description="Solid volume in cubic meters")

    @property
    def length(self) -> float:
        return max(0.0, self.end_dist - self.start_dist)

    @property
    def height(self) -> float:
        return max(0.0, self.top_elev - self.bottom_elev)

    @model_validator(mode="after")
    def validate_segment_bounds(self) -> WallSubSegment:
        if self.end_dist < self.start_dist - 1e-6:
            raise ValueError(f"Segment end_dist ({self.end_dist}) < start_dist ({self.start_dist})")
        if self.top_elev < self.bottom_elev - 1e-6:
            raise ValueError(f"Segment top_elev ({self.top_elev}) < bottom_elev ({self.bottom_elev})")
        return self


class ParametricWall(BaseModel):
    """Parametric linear wall run extracted from room boundary polygons with hosted openings."""

    model_config = ConfigDict(extra="ignore")

    wall_id: str = Field(..., description="Unique wall run identifier")
    start_pt: Tuple[float, float, float] = Field(..., description="3D start point (x, y, z)")
    end_pt: Tuple[float, float, float] = Field(..., description="3D end point (x, y, z)")
    thickness: float = Field(default=0.25, gt=0.0, description="Wall thickness in meters (0.25 ext, 0.12 int)")
    height: float = Field(default=3.0, gt=0.0, description="Clear storey wall height in meters")
    is_exterior: bool = Field(default=True, description="True if exterior building facade wall")
    storey_index: int = Field(default=0, ge=0, description="Storey index")
    adjacent_room_ids: List[str] = Field(default_factory=list, description="IDs of rooms sharing this wall run")
    openings: List[HostedOpening] = Field(default_factory=list, description="Hosted doors and windows")
    sub_segments: List[WallSubSegment] = Field(default_factory=list, description="Computed solid sub-segments")

    @property
    def length(self) -> float:
        dx = self.end_pt[0] - self.start_pt[0]
        dy = self.end_pt[1] - self.start_pt[1]
        dz = self.end_pt[2] - self.start_pt[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def direction_vector(self) -> Tuple[float, float, float]:
        L = self.length
        if L < 1e-6:
            return (1.0, 0.0, 0.0)
        return (
            (self.end_pt[0] - self.start_pt[0]) / L,
            (self.end_pt[1] - self.start_pt[1]) / L,
            (self.end_pt[2] - self.start_pt[2]) / L,
        )

    @property
    def normal_vector(self) -> Tuple[float, float, float]:
        """Horizontal left normal vector in XZ plane."""
        dx, _, dz = self.direction_vector
        return (-dz, 0.0, dx)

    @property
    def gross_volume(self) -> float:
        return self.length * self.height * self.thickness

    @property
    def total_solid_volume(self) -> float:
        return sum(s.volume for s in self.sub_segments)

    @property
    def solid_volume(self) -> float:
        return self.total_solid_volume

    @property
    def total_void_volume(self) -> float:
        return sum(op.width * op.height * self.thickness for op in self.openings)

    @property
    def void_volume(self) -> float:
        return self.total_void_volume

    def validate_volume_conservation(self, rel_tol: float = 1e-4) -> bool:
        """Verifies Invariant 4: sum(V_subsegments) + sum(V_void) == gross_volume."""
        return math.isclose(self.total_solid_volume + self.total_void_volume, self.gross_volume, rel_tol=rel_tol)


class StoreyWalls(BaseModel):
    """Collection of parametric walls for an entire building storey."""

    model_config = ConfigDict(extra="ignore")

    storey_index: int = Field(default=0, ge=0, description="Storey index")
    elevation: float = Field(default=0.0, description="Storey base elevation in meters")
    height: float = Field(default=3.0, gt=0.0, description="Storey clear height in meters")
    walls: List[ParametricWall] = Field(default_factory=list, description="Extracted parametric walls")


# ==============================================================================
# 3. REST API Request / Response DTOs
# ==============================================================================

class WallExtractionRequest(BaseModel):
    """Generic wall extraction request supporting FloorplanLayout or List[RoomBoundary]."""

    model_config = ConfigDict(extra="ignore")

    layout: Optional[FloorplanLayout] = Field(default=None, description="FloorplanLayout model")
    rooms: Optional[List[RoomBoundary]] = Field(default=None, description="List of RoomBoundary models")
    exterior_thickness: float = Field(default=0.25, gt=0.0, description="Exterior wall thickness (m)")
    interior_thickness: float = Field(default=0.12, gt=0.0, description="Interior wall thickness (m)")
    wall_height: float = Field(default=3.0, gt=0.0, description="Wall height (m)")
    base_elevation: float = Field(default=0.0, description="Storey base elevation (m)")
    storey_index: int = Field(default=0, ge=0, description="Storey index")


class WallGenerationFromFloorplanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    layout: FloorplanLayout
    exterior_thickness: float = Field(default=0.25, gt=0.0)
    interior_thickness: float = Field(default=0.12, gt=0.0)
    wall_height: float = Field(default=3.0, gt=0.0)


class WallGenerationFromRoomsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rooms: List[RoomBoundary]
    exterior_thickness: float = Field(default=0.25, gt=0.0)
    interior_thickness: float = Field(default=0.12, gt=0.0)
    wall_height: float = Field(default=3.0, gt=0.0)
    base_elevation: float = Field(default=0.0)
    storey_index: int = Field(default=0, ge=0)


class WallExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    walls: List[ParametricWall]
    total_walls: int
    exterior_walls_count: int
    interior_walls_count: int
    total_linear_length_m: float
    total_gross_volume_m3: float


class HostedOpeningRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wall: ParametricWall
    opening: HostedOpening


# Alias
HostOpeningRequest = HostedOpeningRequest


class HostedOpeningResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wall: ParametricWall
    opening: HostedOpening
    sub_segments: List[WallSubSegment]


class VolumeValidationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wall: ParametricWall


class VolumeValidationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wall_id: str
    is_valid: bool
    gross_volume_m3: float
    solid_subsegments_volume_m3: float
    void_openings_volume_m3: float
    volume_delta_m3: float
    sub_segments_count: int
    openings_count: int
    message: str


class BatchSubSegmentRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    walls: List[ParametricWall]


# Alias
BatchSubsegmentRequest = BatchSubSegmentRequest


class BatchSubSegmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    walls: List[ParametricWall]
    total_walls_processed: int
    all_volumes_conserved: bool


# Alias
BatchSubsegmentResponse = BatchSubSegmentResponse
