"""
Canonical Spatial Hierarchy & IFC GUID Bijective Encoding Engine.

This module establishes:
1. Bijective 128-bit UUID <-> 22-character IFC Base64 GUID encoding/decoding
   conforming to ISO 10303-21 / buildingSMART standards.
2. Deterministic UUID5 generation based on canonical hierarchy paths.
3. Canonical 6-Tier Spatial Hierarchy (Project -> Site -> Development -> Building -> Storey -> Unit -> Room).
4. Full tree traversal, querying, integrity validation, and DesignSpec compilation helpers.
"""

from __future__ import annotations

import re
import uuid
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.design_spec import (
    AestheticStyle,
    BuildingTypology,
    DesignSpec,
    RoomProgram,
    RoomType,
    StoreySpec,
    UnitRequirement,
    UnitType,
)


# ==============================================================================
# 1. IFC Base64 GUID Bijective Encoding Engine (ISO 10303-21 / buildingSMART)
# ==============================================================================

IFC_BASE64_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"
IFC_BASE64_DICT: Dict[str, int] = {c: i for i, c in enumerate(IFC_BASE64_CHARS)}

NAMESPACE_BUILDER_AI = uuid.uuid5(uuid.NAMESPACE_DNS, "builderai.bim")
NAMESPACE_BUILDER3D = uuid.uuid5(uuid.NAMESPACE_DNS, "builder3d.openbim.org")


def encode_ifc_guid(u: Union[uuid.UUID, str]) -> str:
    """
    Encodes a 128-bit UUID into a standard 22-character IFC Base64 GUID.

    Conforms to buildingSMART standard:
    - Alphabet: 0-9, A-Z, a-z, _, $ (64 characters)
    - 16 bytes partitioned into 6 chunks: 1 x 8-bit (2 chars) + 5 x 24-bit (4 chars each).
    - Resulting string is strictly 22 characters, with first character in ['0', '1', '2', '3'].
    """
    if isinstance(u, str):
        u = uuid.UUID(u)

    raw = u.bytes
    num0 = raw[0]
    num1 = (raw[1] << 16) | (raw[2] << 8) | raw[3]
    num2 = (raw[4] << 16) | (raw[5] << 8) | raw[6]
    num3 = (raw[7] << 16) | (raw[8] << 8) | raw[9]
    num4 = (raw[10] << 16) | (raw[11] << 8) | raw[12]
    num5 = (raw[13] << 16) | (raw[14] << 8) | raw[15]

    def _cv_to_64(number: int, n_digits: int) -> str:
        res = []
        act = number
        for _ in range(n_digits):
            res.append(IFC_BASE64_CHARS[act % 64])
            act //= 64
        return "".join(reversed(res))

    return (
        _cv_to_64(num0, 2)
        + _cv_to_64(num1, 4)
        + _cv_to_64(num2, 4)
        + _cv_to_64(num3, 4)
        + _cv_to_64(num4, 4)
        + _cv_to_64(num5, 4)
    )


# Alias for backwards/forwards compatibility
uuid_to_ifc_guid = encode_ifc_guid


def decode_ifc_guid(ifc_str: str) -> uuid.UUID:
    """
    Decodes a 22-character IFC Base64 GUID back into a 128-bit UUID.

    Raises:
        ValueError: If string length != 22, contains invalid characters, or exceeds 128-bit range.
    """
    if not isinstance(ifc_str, str):
        raise ValueError(f"IFC GUID must be a string, got {type(ifc_str).__name__}")

    if len(ifc_str) != 22:
        raise ValueError(f"IFC GUID must be exactly 22 characters, got {len(ifc_str)}")

    for c in ifc_str:
        if c not in IFC_BASE64_DICT:
            raise ValueError(f"Invalid character {c!r} in IFC GUID (not in IFC Base64 alphabet)")

    def _cv_from_64(s: str) -> int:
        res = 0
        for c in s:
            res = res * 64 + IFC_BASE64_DICT[c]
        return res

    num0 = _cv_from_64(ifc_str[0:2])
    if num0 > 255:
        raise ValueError(
            f"Invalid IFC GUID: first chunk value {num0} exceeds 255 "
            f"(first character must be in ['0', '1', '2', '3'])"
        )

    num1 = _cv_from_64(ifc_str[2:6])
    num2 = _cv_from_64(ifc_str[6:10])
    num3 = _cv_from_64(ifc_str[10:14])
    num4 = _cv_from_64(ifc_str[14:18])
    num5 = _cv_from_64(ifc_str[18:22])

    raw = bytearray(16)
    raw[0] = num0 & 0xFF
    raw[1] = (num1 >> 16) & 0xFF
    raw[2] = (num1 >> 8) & 0xFF
    raw[3] = num1 & 0xFF
    raw[4] = (num2 >> 16) & 0xFF
    raw[5] = (num2 >> 8) & 0xFF
    raw[6] = num2 & 0xFF
    raw[7] = (num3 >> 16) & 0xFF
    raw[8] = (num3 >> 8) & 0xFF
    raw[9] = num3 & 0xFF
    raw[10] = (num4 >> 16) & 0xFF
    raw[11] = (num4 >> 8) & 0xFF
    raw[12] = num4 & 0xFF
    raw[13] = (num5 >> 16) & 0xFF
    raw[14] = (num5 >> 8) & 0xFF
    raw[15] = num5 & 0xFF

    return uuid.UUID(bytes=bytes(raw))


# Alias for backwards/forwards compatibility
ifc_guid_to_uuid = decode_ifc_guid


def generate_spatial_uuid(canonical_path: str, namespace: uuid.UUID = NAMESPACE_BUILDER_AI) -> uuid.UUID:
    """
    Generates a deterministic RFC 4122 UUID5 based on namespace and canonical hierarchy path.

    Example path: 'project:skyline/site:main/dev:phase1/bldg:tower_a/storey:1/unit:u101/room:living'
    """
    if not canonical_path or not canonical_path.strip():
        raise ValueError("canonical_path cannot be empty")
    return uuid.uuid5(namespace, canonical_path.strip())


# ==============================================================================
# 2. Canonical Spatial Node Types & Hierarchy Constraints
# ==============================================================================


class SpatialNodeType(str, Enum):
    PROJECT = "Project"
    SITE = "Site"
    DEVELOPMENT = "Development"
    BUILDING = "Building"
    STOREY = "Storey"
    UNIT = "Unit"
    ROOM = "Room"


ALLOWED_CHILD_TYPES: Dict[SpatialNodeType, Set[SpatialNodeType]] = {
    SpatialNodeType.PROJECT: {SpatialNodeType.SITE},
    SpatialNodeType.SITE: {SpatialNodeType.DEVELOPMENT, SpatialNodeType.BUILDING},
    SpatialNodeType.DEVELOPMENT: {SpatialNodeType.BUILDING},
    SpatialNodeType.BUILDING: {SpatialNodeType.STOREY},
    SpatialNodeType.STOREY: {SpatialNodeType.UNIT, SpatialNodeType.ROOM},
    SpatialNodeType.UNIT: {SpatialNodeType.ROOM},
    SpatialNodeType.ROOM: set(),
}


# ==============================================================================
# 3. Tier Properties Models
# ==============================================================================


class ProjectProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    client: Optional[str] = None
    author: Optional[str] = None
    crs_epsg: int = Field(default=3857, description="EPSG Coordinate System code")
    units: str = Field(default="METERS", description="Measurement units")
    north_angle_deg: float = Field(default=0.0, description="True North orientation in degrees")
    description: Optional[str] = None


class SiteProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    plot_boundary: Optional[List[Tuple[float, float]]] = Field(None, description="2D [x, y/z] coordinates")
    site_area_sqm: float = Field(default=1200.0, gt=0)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_amsl: float = Field(default=0.0, description="Elevation above mean sea level")
    zoning: Optional[str] = None
    setback_front: float = Field(default=4.5, ge=0)
    setback_rear: float = Field(default=3.0, ge=0)
    setback_side_left: float = Field(default=2.5, ge=0)
    setback_side_right: float = Field(default=2.5, ge=0)


class DevelopmentProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    phase: str = Field(default="Phase 1")
    zone_type: str = Field(default="Residential")
    target_gfa_sqm: Optional[float] = None
    parking_slots: int = Field(default=0, ge=0)


class BuildingProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    typology: BuildingTypology = Field(default=BuildingTypology.RESIDENTIAL)
    footprint_polygon: Optional[List[Tuple[float, float]]] = Field(None, description="2D footprint")
    total_storeys: int = Field(default=2, ge=1)
    baseline_elevation: float = Field(default=0.0)
    roof_height: Optional[float] = None


class StoreyProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    storey_index: int = Field(..., description="Floor index")
    elevation: float = Field(..., description="Elevation above building baseline in meters")
    height: float = Field(default=3.2, gt=0, description="Floor to floor height in meters")
    slab_thickness: float = Field(default=0.2, gt=0)
    is_ground: bool = Field(default=False)
    is_rooftop: bool = Field(default=False)
    is_basement: bool = Field(default=False)


class UnitProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    unit_type: UnitType = Field(default=UnitType.BHK2)
    unit_number: str = Field(default="101")
    target_area_sqm: float = Field(..., gt=0)
    carpet_area_sqm: Optional[float] = None


class RoomProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    room_type: RoomType = Field(default=RoomType.LIVING_ROOM)
    boundary_polygon: Optional[List[Tuple[float, float]]] = None
    area_sqm: float = Field(..., gt=0)
    perimeter_m: Optional[float] = Field(None, gt=0)
    ceiling_height: float = Field(default=2.8, gt=0)
    is_exterior: bool = Field(default=False)
    wet_zone: bool = Field(default=False)
    requires_daylight: bool = Field(default=True)
    adjacent_room_ids: List[str] = Field(default_factory=list)


# ==============================================================================
# 4. Recursive SpatialNode Model
# ==============================================================================


class SpatialNode(BaseModel):
    """
    Recursive canonical spatial hierarchy node.

    Adheres to 6-Tier containment:
    Project -> Site -> Development -> Building -> Storey -> Unit -> Room.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Canonical RFC 4122 UUID string (36 chars)")
    global_id: str = Field(..., description="Canonical 22-char IFC Base64 GUID")
    name: str = Field(..., min_length=1, max_length=120, description="Human-readable node label")
    node_type: SpatialNodeType = Field(..., description="Spatial hierarchy level")
    parent_id: Optional[str] = Field(None, description="Parent UUID (None for Project root)")
    canonical_path: Optional[str] = Field(None, description="Deterministic path string")
    children: List[SpatialNode] = Field(default_factory=list, description="Ordered child spatial nodes")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Tier-specific properties")

    @field_validator("id")
    @classmethod
    def validate_uuid_format(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except Exception:
            raise ValueError(f"Invalid RFC 4122 UUID format: {v}")
        return str(uuid.UUID(v))

    @field_validator("global_id")
    @classmethod
    def validate_ifc_guid_format(cls, v: str) -> str:
        if len(v) != 22:
            raise ValueError(f"IFC GUID must be exactly 22 characters, got {len(v)}")
        if v[0] not in {"0", "1", "2", "3"}:
            raise ValueError(f"Invalid IFC GUID leading character {v[0]!r}: must be '0', '1', '2', or '3'")
        for c in v:
            if c not in IFC_BASE64_DICT:
                raise ValueError(f"Invalid IFC Base64 character: {c!r}")
        return v

    @model_validator(mode="after")
    def validate_spatial_integrity(self) -> SpatialNode:
        # 1. Root node check
        if self.node_type == SpatialNodeType.PROJECT:
            if self.parent_id is not None:
                raise ValueError("Project root node must have parent_id=None")
        else:
            if self.parent_id is None:
                raise ValueError(f"Non-root node of type '{self.node_type}' must have a parent_id")

        # 2. Child type and parent pointer validation
        allowed = ALLOWED_CHILD_TYPES.get(self.node_type, set())
        for child in self.children:
            child_type = child.node_type if isinstance(child.node_type, SpatialNodeType) else SpatialNodeType(child.node_type)
            if child_type not in allowed:
                allowed_str = ", ".join(t.value for t in allowed) if allowed else "None (Leaf)"
                raise ValueError(
                    f"Illegal hierarchy: node '{self.node_type.value}' cannot contain child of type '{child_type.value}'. "
                    f"Allowed child types: [{allowed_str}]"
                )
            if child.parent_id != self.id:
                raise ValueError(
                    f"Broken parent reference: child '{child.name}' ({child.id}) has parent_id '{child.parent_id}', "
                    f"expected '{self.id}'"
                )

        return self


# Rebuild model for recursive typing resolution
SpatialNode.model_rebuild()


# ==============================================================================
# 5. Tree Traversal, Query, and Integrity Helpers
# ==============================================================================


def find_node_by_id(root: SpatialNode, target_id: str) -> Optional[SpatialNode]:
    """Finds a node by its 36-character UUID string in O(N) time."""
    if root.id == target_id:
        return root
    for child in root.children:
        found = find_node_by_id(child, target_id)
        if found is not None:
            return found
    return None


def find_node_by_global_id(root: SpatialNode, target_global_id: str) -> Optional[SpatialNode]:
    """Finds a node by its 22-character IFC GUID in O(N) time."""
    if root.global_id == target_global_id:
        return root
    for child in root.children:
        found = find_node_by_global_id(child, target_global_id)
        if found is not None:
            return found
    return None


def find_node_by_path(root: SpatialNode, canonical_path: str) -> Optional[SpatialNode]:
    """Finds a node by its canonical path string."""
    if root.canonical_path == canonical_path:
        return root
    for child in root.children:
        found = find_node_by_path(child, canonical_path)
        if found is not None:
            return found
    return None


def filter_nodes_by_type(root: SpatialNode, node_type: Union[SpatialNodeType, str]) -> List[SpatialNode]:
    """Returns a list of all nodes in the tree matching the specified SpatialNodeType."""
    if isinstance(node_type, str):
        node_type = SpatialNodeType(node_type)

    result: List[SpatialNode] = []
    if root.node_type == node_type:
        result.append(root)
    for child in root.children:
        result.extend(filter_nodes_by_type(child, node_type))
    return result


# Alias
find_nodes_by_type = filter_nodes_by_type


def get_ancestor_chain(root: SpatialNode, target_id: str) -> Optional[List[SpatialNode]]:
    """Returns the ancestor chain from root to target node inclusive, or None if not found."""
    if root.id == target_id:
        return [root]
    for child in root.children:
        sub = get_ancestor_chain(child, target_id)
        if sub is not None:
            return [root] + sub
    return None


# Alias
get_ancestor_path = get_ancestor_chain


def get_descendants(node: SpatialNode) -> List[SpatialNode]:
    """Returns all descendant nodes under the given subtree in pre-order traversal."""
    result: List[SpatialNode] = []
    for child in node.children:
        result.append(child)
        result.extend(get_descendants(child))
    return result


def flatten_spatial_tree(root: SpatialNode) -> Dict[str, SpatialNode]:
    """Flattens the hierarchical spatial tree into a lookup dictionary keyed by node ID."""
    nodes: Dict[str, SpatialNode] = {root.id: root}
    for child in root.children:
        nodes.update(flatten_spatial_tree(child))
    return nodes


def validate_tree_integrity(root: SpatialNode) -> bool:
    """
    Validates complete tree structural integrity:
    1. Acyclicity and depth <= 7 levels (6 tier boundaries).
    2. Global ID and UUID uniqueness across all nodes.
    3. Bidirectional parent-child pointer consistency.
    """
    visited_ids: Set[str] = set()
    visited_global_ids: Set[str] = set()

    def _traverse(node: SpatialNode, expected_parent_id: Optional[str], current_depth: int) -> None:
        if current_depth > 7:
            raise ValueError(f"Spatial tree depth exceeded maximum allowed 7 levels at node '{node.name}'")
        if node.id in visited_ids:
            raise ValueError(f"Cycle or duplicate node ID detected: '{node.id}'")
        if node.global_id in visited_global_ids:
            raise ValueError(f"Duplicate IFC GUID detected: '{node.global_id}'")
        if node.parent_id != expected_parent_id:
            raise ValueError(
                f"Parent ID mismatch for node '{node.name}' ({node.id}): "
                f"expected '{expected_parent_id}', got '{node.parent_id}'"
            )

        visited_ids.add(node.id)
        visited_global_ids.add(node.global_id)

        for child in node.children:
            _traverse(child, node.id, current_depth + 1)

    _traverse(root, None, 1)
    return True


# ==============================================================================
# 6. Compiler: DesignSpec -> Canonical Spatial Tree
# ==============================================================================


def compile_design_spec_to_spatial_tree(spec: DesignSpec) -> SpatialNode:
    """
    Compiles a validated DesignSpec instance into a canonical 6-tier SpatialNode hierarchy.

    Hierarchy constructed:
    Project -> Site -> Development -> Building -> Storeys -> Units -> Rooms
    All IDs are deterministic UUID5 derived from hierarchical paths, with valid 22-char IFC GUIDs.
    """
    project_slug = re.sub(r"[^a-zA-Z0-9_]+", "_", spec.project_name.strip().lower()) or "project"
    project_path = f"project:{project_slug}"
    project_uuid = generate_spatial_uuid(project_path)
    project_guid = encode_ifc_guid(project_uuid)

    # Level 0: Project Node
    project_node = SpatialNode(
        id=str(project_uuid),
        global_id=project_guid,
        name=spec.project_name,
        node_type=SpatialNodeType.PROJECT,
        parent_id=None,
        canonical_path=project_path,
        properties=ProjectProperties(
            description=spec.description or f"Builder3D Project {spec.project_name}",
            north_angle_deg=spec.site.orientation_degrees,
        ).model_dump(),
        children=[],
    )

    # Level 1: Site Node
    site_path = f"{project_path}/site:main"
    site_uuid = generate_spatial_uuid(site_path)
    site_node = SpatialNode(
        id=str(site_uuid),
        global_id=encode_ifc_guid(site_uuid),
        name="Main Site",
        node_type=SpatialNodeType.SITE,
        parent_id=project_node.id,
        canonical_path=site_path,
        properties=SiteProperties(
            site_area_sqm=spec.site.total_area_sqm,
            zoning=spec.site.zoning.value if hasattr(spec.site.zoning, "value") else str(spec.site.zoning),
            setback_front=spec.site.setbacks.front_m,
            setback_rear=spec.site.setbacks.rear_m,
            setback_side_left=spec.site.setbacks.side_left_m,
            setback_side_right=spec.site.setbacks.side_right_m,
        ).model_dump(),
        children=[],
    )

    # Level 2: Development Node
    dev_path = f"{site_path}/dev:phase1"
    dev_uuid = generate_spatial_uuid(dev_path)
    dev_node = SpatialNode(
        id=str(dev_uuid),
        global_id=encode_ifc_guid(dev_uuid),
        name="Phase 1",
        node_type=SpatialNodeType.DEVELOPMENT,
        parent_id=site_node.id,
        canonical_path=dev_path,
        properties=DevelopmentProperties(
            phase="Phase 1",
            zone_type=spec.building_typology.value if hasattr(spec.building_typology, "value") else str(spec.building_typology),
        ).model_dump(),
        children=[],
    )

    # Level 3: Building Node
    bldg_slug = "main_building"
    bldg_path = f"{dev_path}/bldg:{bldg_slug}"
    bldg_uuid = generate_spatial_uuid(bldg_path)
    bldg_node = SpatialNode(
        id=str(bldg_uuid),
        global_id=encode_ifc_guid(bldg_uuid),
        name=f"{spec.project_name} Structure",
        node_type=SpatialNodeType.BUILDING,
        parent_id=dev_node.id,
        canonical_path=bldg_path,
        properties=BuildingProperties(
            typology=spec.building_typology,
            total_storeys=spec.total_storeys,
            baseline_elevation=0.0,
        ).model_dump(),
        children=[],
    )

    # Level 4: Storeys
    # If spec has no storeys array, generate default storeys
    storeys_to_build: List[StoreySpec] = spec.storeys
    if not storeys_to_build:
        storeys_to_build = []
        current_elev = 0.0
        for s_idx in range(spec.total_storeys):
            s_height = spec.ground_floor_height_m if s_idx == 0 else spec.floor_to_floor_height_m
            s_name = "Ground Floor" if s_idx == 0 else f"Level {s_idx}"
            is_grd = (s_idx == 0)
            is_roof = (s_idx == spec.total_storeys - 1)
            storeys_to_build.append(
                StoreySpec(
                    storey_index=s_idx,
                    name=s_name,
                    elevation_m=current_elev,
                    height_m=s_height,
                    is_ground=is_grd,
                    is_rooftop=is_roof,
                    is_basement=False,
                )
            )
            current_elev += s_height

    for storey in storeys_to_build:
        storey_slug = f"storey_{storey.storey_index}"
        storey_path = f"{bldg_path}/storey:{storey.storey_index}"
        storey_uuid = generate_spatial_uuid(storey_path)
        storey_node = SpatialNode(
            id=str(storey_uuid),
            global_id=encode_ifc_guid(storey_uuid),
            name=storey.name,
            node_type=SpatialNodeType.STOREY,
            parent_id=bldg_node.id,
            canonical_path=storey_path,
            properties=StoreyProperties(
                storey_index=storey.storey_index,
                elevation=storey.elevation_m,
                height=storey.height_m,
                is_ground=storey.is_ground,
                is_rooftop=storey.is_rooftop,
                is_basement=storey.is_basement,
            ).model_dump(),
            children=[],
        )

        # Level 5: Units
        units_to_build = storey.unit_mix
        if not units_to_build:
            # Default unit per floor
            units_to_build = [
                UnitRequirement(
                    unit_id=f"u_{storey.storey_index}_01",
                    unit_type=UnitType.BHK2,
                    name=f"Unit {storey.storey_index}01",
                    target_area_sqm=90.0,
                    required_rooms=[
                        RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=20.0, target_area_sqm=24.0),
                        RoomProgram(room_type=RoomType.KITCHEN, min_area_sqm=8.0, target_area_sqm=9.0, requires_plumbing=True),
                        RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=14.0, target_area_sqm=16.0),
                        RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=11.0, target_area_sqm=12.0),
                        RoomProgram(room_type=RoomType.BATHROOM_COMMON, min_area_sqm=4.0, target_area_sqm=4.5, requires_plumbing=True),
                    ],
                )
            ]

        for u_idx, unit_req in enumerate(units_to_build):
            unit_slug = f"unit_{u_idx + 1}"
            unit_path = f"{storey_path}/unit:{u_idx + 1}"
            unit_uuid = generate_spatial_uuid(unit_path)
            unit_node = SpatialNode(
                id=str(unit_uuid),
                global_id=encode_ifc_guid(unit_uuid),
                name=unit_req.name,
                node_type=SpatialNodeType.UNIT,
                parent_id=storey_node.id,
                canonical_path=unit_path,
                properties=UnitProperties(
                    unit_type=unit_req.unit_type,
                    unit_number=f"{storey.storey_index}{u_idx + 1:02d}",
                    target_area_sqm=unit_req.target_area_sqm,
                ).model_dump(),
                children=[],
            )

            # Level 6: Rooms
            for r_idx, room_prog in enumerate(unit_req.required_rooms):
                r_type_val = room_prog.room_type.value if hasattr(room_prog.room_type, "value") else str(room_prog.room_type)
                room_path = f"{unit_path}/room:{r_type_val.lower()}_{r_idx}"
                room_uuid = generate_spatial_uuid(room_path)
                room_node = SpatialNode(
                    id=str(room_uuid),
                    global_id=encode_ifc_guid(room_uuid),
                    name=room_prog.name or f"{r_type_val} {r_idx + 1}",
                    node_type=SpatialNodeType.ROOM,
                    parent_id=unit_node.id,
                    canonical_path=room_path,
                    properties=RoomProperties(
                        room_type=room_prog.room_type,
                        area_sqm=room_prog.target_area_sqm,
                        ceiling_height=storey.height_m - 0.4,
                        requires_daylight=room_prog.requires_daylight,
                        wet_zone=room_prog.requires_plumbing,
                    ).model_dump(),
                    children=[],
                )
                unit_node.children.append(room_node)

            storey_node.children.append(unit_node)

        bldg_node.children.append(storey_node)

    dev_node.children.append(bldg_node)
    site_node.children.append(dev_node)
    project_node.children.append(site_node)

    validate_tree_integrity(project_node)
    return project_node


# Alias
build_spatial_tree_from_design_spec = compile_design_spec_to_spatial_tree
