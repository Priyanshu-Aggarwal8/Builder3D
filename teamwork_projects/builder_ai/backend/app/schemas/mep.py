"""
Pydantic Schemas and Data Transfer Objects for Connected MEP Graph Engine.
Enforces Invariant 3 (Coaxial Multi-Storey Riser Alignment) and Invariant 6 (Connected MEP Graph).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.design_spec import DesignSpec
from app.schemas.spatial_solver import FloorplanLayout


SystemType = Literal["WaterSupply", "SoilWaste", "Vent", "ElectricalPower"]
NodeType = Literal["Source", "Riser", "Junction", "Terminal"]


class MEPNode(BaseModel):
    """Represents a discrete node in the connected MEP multi-graph."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Node classification (Source, Riser, Junction, Terminal)")
    system_type: SystemType = Field(..., description="Utility discipline")
    position: Tuple[float, float, float] = Field(..., description="(X, Y, Z) 3D coordinate in meters")
    storey_index: int = Field(default=0, description="0-based storey index")
    connected_fixture_id: Optional[str] = Field(default=None, description="ID of connected fixture or appliance")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Metadata and electrical/hydraulic parameters")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        if len(v) != 3:
            raise ValueError(f"Position must be a 3D coordinate (X, Y, Z), got {len(v)} elements")
        return v


class MEPEdge(BaseModel):
    """Represents a directed pipe segment or electrical circuit run."""

    model_config = ConfigDict(extra="forbid")

    edge_id: str = Field(..., description="Unique edge identifier")
    system_type: SystemType = Field(..., description="Utility discipline")
    from_node_id: str = Field(..., description="Origin node identifier")
    to_node_id: str = Field(..., description="Destination node identifier")
    nominal_diameter_mm: float = Field(..., gt=0.0, description="Nominal diameter (pipe DN or conduit size)")
    slope: float = Field(default=0.0, description="Hydraulic drainage slope (dz / horizontal_length)")
    length_m: float = Field(..., gt=0.0, description="Total center-line segment length in meters")
    segment_points: List[Tuple[float, float, float]] = Field(
        default_factory=list, description="Ordered 3D route points (start to end)"
    )


class VerticalRiserShaft(BaseModel):
    """Represents a continuous vertical utility riser shaft spanning multiple storeys."""

    model_config = ConfigDict(extra="forbid")

    riser_id: str = Field(..., description="Unique riser shaft identifier")
    system_type: SystemType = Field(..., description="Utility discipline")
    nominal_diameter_mm: float = Field(..., gt=0.0, description="Main riser pipe or busbar dimension")
    base_position_xz: Tuple[float, float] = Field(..., description="Planar (X, Z) base coordinate")
    bottom_elevation_y: float = Field(..., description="Bottom elevation in meters")
    top_elevation_y: float = Field(..., description="Top elevation in meters")
    penetrated_storeys: List[int] = Field(default_factory=list, description="List of penetrated storey indices")
    junction_node_ids: List[str] = Field(
        default_factory=list, description="Take-off junction node IDs along this riser"
    )

    @field_validator("top_elevation_y")
    @classmethod
    def validate_elevation_span(cls, v: float, info) -> float:
        bottom = info.data.get("bottom_elevation_y")
        if bottom is not None and v <= bottom:
            raise ValueError(f"top_elevation_y ({v}) must be strictly greater than bottom_elevation_y ({bottom})")
        return v


class MEPGraph(BaseModel):
    """Complete multi-system directed flow graph."""

    model_config = ConfigDict(extra="forbid")

    nodes: Dict[str, MEPNode] = Field(default_factory=dict, description="Dictionary of nodes keyed by node_id")
    edges: List[MEPEdge] = Field(default_factory=list, description="List of directed edges")
    vertical_risers: Dict[str, VerticalRiserShaft] = Field(
        default_factory=dict, description="Dictionary of vertical risers keyed by riser_id"
    )

    def add_node(self, node: MEPNode) -> None:
        """Adds or updates a node in the graph."""
        self.nodes[node.node_id] = node

    def add_edge(self, edge: MEPEdge) -> None:
        """Appends a directed edge to the graph."""
        self.edges.append(edge)

    def get_outgoing_edges(self, node_id: str) -> List[MEPEdge]:
        """Returns all directed edges starting from node_id."""
        return [e for e in self.edges if e.from_node_id == node_id]

    def get_incoming_edges(self, node_id: str) -> List[MEPEdge]:
        """Returns all directed edges ending at node_id."""
        return [e for e in self.edges if e.to_node_id == node_id]


# ==============================================================================
# REST API DTOs (Requests & Responses)
# ==============================================================================

class SystemMetricSummary(BaseModel):
    """Summary metrics for an individual utility system."""

    model_config = ConfigDict(extra="forbid")

    node_count: int = Field(..., ge=0)
    edge_count: int = Field(..., ge=0)
    total_length_m: float = Field(..., ge=0.0)
    source_node_ids: List[str] = Field(default_factory=list)
    terminal_node_ids: List[str] = Field(default_factory=list)


class MEPGenerationRequest(BaseModel):
    """Request payload for compiling full MEP graph."""

    model_config = ConfigDict(extra="forbid")

    spec: Optional[DesignSpec] = Field(default=None, description="Architectural DesignSpec")
    layouts: Optional[List[FloorplanLayout]] = Field(
        default=None, description="Pre-computed 2D FloorplanLayout instances"
    )
    auto_route_circuits: bool = Field(default=True, description="Automatically route electrical branch circuits")
    auto_calculate_slopes: bool = Field(default=True, description="Automatically calculate gravity drainage slopes")


class MEPGenerationResponse(BaseModel):
    """Response payload containing generated MEPGraph and system metrics."""

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(default=True)
    graph: MEPGraph = Field(..., description="Compiled directed MEP multi-graph")
    total_nodes: int = Field(..., ge=0)
    total_edges: int = Field(..., ge=0)
    total_risers: int = Field(..., ge=0)
    total_pipe_length_m: float = Field(..., ge=0.0)
    total_wire_length_m: float = Field(..., ge=0.0)
    system_summary: Dict[str, SystemMetricSummary] = Field(default_factory=dict)


class MEPValidationRequest(BaseModel):
    """Request payload for validating MEPGraph continuity and physical invariants."""

    model_config = ConfigDict(extra="forbid")

    graph: MEPGraph = Field(..., description="Target MEP graph to validate")
    min_drainage_slope: float = Field(default=0.015, gt=0.0, description="Minimum allowable gravity slope (1.5%)")
    max_wet_to_riser_distance_m: float = Field(default=3.5, gt=0.0, description="Max allowable horizontal branch run")
    check_coaxial_alignment: bool = Field(default=True, description="Validate strict coaxial riser stacking")
    check_shaft_segregation: bool = Field(default=True, description="Validate shaft-to-shaft code clearances")


class MEPValidationResponse(BaseModel):
    """Response payload detailing validation outcomes and diagnostic issues."""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="True if all critical invariants pass")
    continuity_valid: bool = Field(..., description="True if all terminals connect to sources/risers/outfalls")
    slope_compliant: bool = Field(..., description="True if all gravity runs satisfy minimum slope")
    acyclic_drainage_valid: bool = Field(..., description="True if gravity drainage forms strict DAG/tree")
    risers_coaxial_aligned: bool = Field(..., description="True if vertical risers have zero horizontal drift")
    shaft_segregation_valid: bool = Field(..., description="True if physical shaft clearances are satisfied")
    vent_termination_compliant: bool = Field(..., description="True if vent stacks terminate >= 1.0m above roof")
    orphan_fixture_ids: List[str] = Field(default_factory=list, description="IDs of disconnected terminal fixtures")
    cycles_detected: List[Dict[str, Any]] = Field(default_factory=list, description="Detected loops in DAGs")
    slope_violations: List[Dict[str, Any]] = Field(default_factory=list, description="Edges with back-pitch or shallow slope")
    misaligned_riser_ids: List[str] = Field(default_factory=list, description="Risers violating coaxial tolerance")
    segregation_violations: List[Dict[str, Any]] = Field(default_factory=list, description="Shaft pairs violating clearance")
    diagnostics: List[str] = Field(default_factory=list, description="Human-readable error/warning descriptions")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Graph summary statistics")


class SlabPenetrationDetail(BaseModel):
    """Slab blockout/sleeve detail at each storey level."""

    model_config = ConfigDict(extra="forbid")

    storey_index: int = Field(..., ge=0)
    elevation_y: float = Field(...)
    coordinate_3d: Tuple[float, float, float] = Field(...)
    diameter_mm: float = Field(..., gt=0.0)


class VerticalRiserDetail(BaseModel):
    """Comprehensive geometric and penetration details of a vertical riser shaft."""

    model_config = ConfigDict(extra="forbid")

    riser_id: str = Field(...)
    system_type: SystemType = Field(...)
    nominal_diameter_mm: float = Field(..., gt=0.0)
    base_position_xz: Tuple[float, float] = Field(...)
    bottom_elevation_y: float = Field(...)
    top_elevation_y: float = Field(...)
    penetrated_storeys: List[int] = Field(default_factory=list)
    slab_penetrations: List[SlabPenetrationDetail] = Field(default_factory=list)
    is_coaxially_stacked: bool = Field(default=True)
    max_drift_m: float = Field(default=0.0)


class RisersResponse(BaseModel):
    """Response payload containing all vertical riser details across the building."""

    model_config = ConfigDict(extra="forbid")

    total_risers: int = Field(..., ge=0)
    risers: List[VerticalRiserDetail] = Field(default_factory=list)
