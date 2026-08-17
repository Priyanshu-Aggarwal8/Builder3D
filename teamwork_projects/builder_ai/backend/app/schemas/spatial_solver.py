"""
Pydantic Schemas for 2D Spatial Solver & Floorplan Topology.
"""

from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoomBoundary(BaseModel):
    """2D planar polygon representation of an architectural room in (x, z) coordinates."""

    model_config = ConfigDict(extra="forbid")

    room_id: str = Field(..., description="Unique room identifier within layout")
    room_type: str = Field(..., description="Semantic room type (LivingRoom, Bedroom, etc.)")
    polygon: List[Tuple[float, float]] = Field(
        ..., min_length=3, description="Ordered 2D vertices in (x, z) planar coordinates"
    )
    area: float = Field(..., gt=0.0, description="Planar geometric area in square meters")
    is_exterior: bool = Field(default=False, description="Has exterior boundary frontage")
    wet_zone: bool = Field(default=False, description="Contains plumbing fixtures / requires wet stack")
    requires_daylight: bool = Field(default=True, description="Requires natural daylight / exterior wall")
    adjacent_room_ids: List[str] = Field(default_factory=list, description="IDs of topologically adjacent rooms")

    @field_validator("polygon")
    @classmethod
    def validate_polygon_vertices(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(v) < 3:
            raise ValueError(f"Polygon must have at least 3 vertices, got {len(v)}")
        return v


class VerticalRiserLocation(BaseModel):
    """Location of a multi-storey vertical utility riser shaft in (x, z) coordinates."""

    model_config = ConfigDict(extra="forbid")

    riser_id: str = Field(..., description="Unique identifier for utility riser shaft")
    riser_type: Literal["Plumbing", "Electrical", "HVAC", "MultiService"] = Field(
        default="Plumbing", description="Utility discipline serviced by riser"
    )
    position: Tuple[float, float] = Field(..., description="(x, z) coordinates of shaft centroid")
    radius: float = Field(default=0.4, gt=0.0, description="Service clearance radius in meters")
    serviced_room_ids: List[str] = Field(
        default_factory=list, description="Room IDs serviced within gravity drainage limit"
    )


class FloorplanLayout(BaseModel):
    """Complete 2D geometric layout of a building storey."""

    model_config = ConfigDict(extra="forbid")

    storey_index: int = Field(..., description="0-based index of the storey")
    elevation: float = Field(..., description="Vertical elevation of the floorplate in meters")
    boundary_polygon: List[Tuple[float, float]] = Field(
        ..., min_length=3, description="Outer perimeter polygon of the floorplate"
    )
    rooms: List[RoomBoundary] = Field(..., description="List of room boundary polygons")
    corridors: List[RoomBoundary] = Field(default_factory=list, description="Circulation corridors")
    vertical_risers: List[VerticalRiserLocation] = Field(
        default_factory=list, description="Vertical utility riser shafts"
    )
