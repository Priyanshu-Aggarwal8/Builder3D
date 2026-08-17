# Project: Builder3D OpenBIM Architectural Platform

## Architecture Overview
Builder3D is an AI-driven, OpenBIM architectural generation and spatial planning platform.
The architecture enforces strict separation between AI intent (typed `DesignSpec`), deterministic spatial and BIM compilation, connected MEP graph topology, parametric geometry generation with hosted openings, typed asset registries, and a decoupled modular Three.js presentation engine.

```
+-----------------------------------------------------------------------------------+
|                                 USER / CLIENT                                     |
|  - Natural Language Prompt  - Studio UI Controls  - Surgical Mutations / Undo-Redo|
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         AI AGENT & DESIGNSPEC PARSER                              |
|  - Parses natural language into validated, typed DesignSpec (No raw coordinates)  |
|  - Schema: Site, Typology, Storey Count, Unit Mix, MEP Strategy, Palette          |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               DETERMINISTIC SPATIAL & ROOM TOPOLOGY SOLVER (R2)                   |
|  - Adjacency Graph Solver (Kitchen-Dining, Master-Ensuite, etc.)                  |
|  - Daylight Perimeter Allocation & Circulation Spine Routing (No Cut-Throughs)   |
|  - Multi-Storey Coaxial Wet Stack Clustering (Bathrooms/Kitchens aligned)         |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                 CANONICAL BIM & SPATIAL HIERARCHY MODEL (R1, R4)                  |
|  Project -> Site -> Development -> Building -> Storey -> Unit -> Room / Element   |
|  - Bijective UUID5 <-> 22-char IFC GUID Mapping                                   |
|  - ISO 10303-21 IFC4 STEP Serializer / Parser (Zero-dependency pure Python)       |
+-------------------+---------------------------------------+-----------------------+
                    |                                       |
                    v                                       v
+------------------------------------+   +------------------------------------------+
|  PARAMETRIC WALL & OPENINGS (R3)   |   |        CONNECTED MEP GRAPH (R5)          |
|  - 2D Wall Run Boundary Generator  |   |  - Directed Flow Multi-Graph G=(V,E,Phi) |
|  - Hosted Door/Window Opening Cuts |   |  - Vertical Utility Risers & Gravity Run |
|  - Pre/Post/Lintel/Sill Sub-Meshes |   |  - Supply, Waste, Soil, Vent, Power      |
+-------------------+----------------+   +------------------+-----------------------+
                    |                                       |
                    v                                       v
+-----------------------------------------------------------------------------------+
|               TYPED ASSET REGISTRY & INTERIOR LAYOUT SOLVERS (R6)                 |
|  - AssetRegistry catalog with Bounding Boxes, MEP Ports, & Clearance Envelopes   |
|  - Room Solvers: LivingRoom, Bedroom, Bathroom, Kitchen (SAT Collision-Free)     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                   CENTRALIZED MODEL STATE & COMMAND GRAPH (R8)                    |
|  - Central useStudioStore & CommandHistory (Undo / Redo)                          |
|  - Surgical Mutations (RegenerateRoom, MoveWall, ChangeMaterial, AddFloor)        |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|              MODULAR THREE.JS RENDERING ENGINE & PBR MATERIALS (R7)               |
|  - SceneRuntime (Lifecycle/Resize)  - ModelRenderer (Delta Reconciliation)        |
|  - MaterialSystem & PBR Cache       - CameraController (Orbit / FPS / Floorplan)  |
|  - SelectionSystem (Hover / Select) - LODManager (LOD0 Massing -> LOD4 Interior)  |
+-----------------------------------------------------------------------------------+
```

---

## Feature Inventory
Every feature from the architectural survey is cataloged and assigned to a specific milestone.

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Strongly Typed DesignSpec Schema | Validation schema for site, building typology, storeys, unit mix, MEP & aesthetic palette without raw coordinates | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Canonical Spatial Hierarchy Engine | 6-tier spatial tree (Project -> Site -> Development -> Building -> Storey -> Unit -> Room) with deterministic UUID5 identifiers | M1 | ORIGINAL_REQUEST §R1 |
| 3 | AI Prompt to DesignSpec Compiler | Refactor LLM prompt parsing to strictly generate valid DesignSpec schemas | M1 | ORIGINAL_REQUEST §R1, §Acceptance |
| 4 | Deterministic 2D Room Topology & Adjacency | Topological boundary polygon solver enforcing architectural adjacency constraints | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Daylight Perimeter & Circulation Spine | Room perimeter daylight allocation and dedicated circulation corridors preventing room cut-throughs | M2 | ORIGINAL_REQUEST §R2 |
| 6 | Coaxial Wet Stack Clustering | Spatial clustering of wet zones (bathrooms/kitchens) across multi-storey designs within vertical riser threshold | M2 | ORIGINAL_REQUEST §R2 |
| 7 | Parametric Wall Run Generator | Derivation of 2D/3D wall runs from topological room boundary polygons | M3 | ORIGINAL_REQUEST §R3 |
| 8 | Hosted Opening Voiding Engine | Sub-segmentation of host walls for doors and windows with lintels, sills, frames, reveals, and swing clearance | M3 | ORIGINAL_REQUEST §R3 |
| 9 | Canonical BIM Entity Model | Core BIM entities (IfcBuildingStorey, IfcSpace, IfcWall, IfcDoor, IfcWindow, IfcSlab, IfcColumn, IfcDistributionElement) with Psets | M4 | ORIGINAL_REQUEST §R4 |
| 10 | Pure-Python IFC4 STEP Serializer & Parser | Zero-dependency ISO 10303-21 STEP serializer and parser guaranteeing 100% round-trip fidelity | M4 | ORIGINAL_REQUEST §R4 |
| 11 | Connected MEP Graph Multi-Graph Engine | Directed flow multi-graph routing water supply, soil, waste, vent, and electrical circuits | M5 | ORIGINAL_REQUEST §R5 |
| 12 | Multi-Storey Vertical Riser Alignment | Vertical utility shafts and coaxial alignment across stacked storeys with slope-aware routing | M5 | ORIGINAL_REQUEST §R5 |
| 13 | Typed Furniture Asset Registry | Structured catalog with parametric dimensions, clearance envelopes (use, circulation, maintenance), and MEP connection ports | M6 | ORIGINAL_REQUEST §R6 |
| 14 | Rule-Based Interior Layout Solvers | Deterministic room layout solvers (Living, Bed, Bath, Kitchen) enforcing SAT collision avoidance | M6 | ORIGINAL_REQUEST §R6 |
| 15 | Modular Three.js Engine Subsystems | Decoupled SceneRuntime, ModelRenderer, MaterialSystem, CameraController, SelectionSystem, and LODManager | M7 | ORIGINAL_REQUEST §R7 |
| 16 | Cached PBR Material Library | PBR materials with physical textures, normal maps, roughness, metalness, and zero WebGL memory leaks | M7 | ORIGINAL_REQUEST §R7 |
| 17 | Centralized Frontend Model State | Single-source-of-truth useStudioStore decoupled from 3D rendering loops | M8 | ORIGINAL_REQUEST §R8 |
| 18 | Surgical Command Graph & Undo/Redo | Command pattern execution (RegenerateRoom, MoveWall, ChangeMaterial, AddFloor) with immutable history | M8 | ORIGINAL_REQUEST §R8 |
| 19 | E2E Automated Testing Suite | Comprehensive test runner, verification harness, and Golden Reference benchmarks (1BHK, 2BHK, 3BHK, Villa, 12-storey Tower) | E2E | ORIGINAL_REQUEST §Acceptance |
| 20 | Adversarial Coverage Hardening | White-box stress-testing, boundary validation, and zero-error production verification | M_FINAL | ORIGINAL_REQUEST §Acceptance |

---

## Milestones

| # | Milestone Name | Scope | Dependencies | Status |
|---|----------------|-------|-------------|--------|
| **E2E** | **E2E Testing Track** | Test harness, runner, and 4-tier test suites (Tiers 1-4) with Golden Reference models | None | DONE |
| **M1** | **DesignSpec & Spatial Hierarchy** | Typed DesignSpec schema, 6-tier SpatialHierarchy engine, UUID5 generator, AI parser integration | None | DONE |
| **M2** | **Deterministic Spatial Solver & Room Topology** | 2D Polygon engine, adjacency graph solver, daylight allocation, circulation corridors, wet stack clustering | M1 | PLANNED |
| **M3** | **Parametric Wall Engine & Hosted Openings** | Boundary wall extraction, wall sub-segmentation, door/window hosted cuts, lintel/sill/frame assemblies | M2 | PLANNED |
| **M4** | **Canonical BIM Model & IFC4 Round-Trip Compiler** | Canonical BIM entities, Pset properties, pure-Python ISO 10303-21 STEP serializer/parser, round-trip test | M1, M3 | PLANNED |
| **M5** | **Connected MEP Graph Engine** | Directed flow multi-graph, terminal/junction/riser nodes, coaxial multi-storey risers, drainage slopes | M2, M4 | PLANNED |
| **M6** | **Asset Registry & Interior Solvers** | Typed AssetRegistry catalog, clearance envelopes, room solvers (Living, Bed, Bath, Kitchen), SAT solver | M2, M3 | PLANNED |
| **M7** | **Modular Three.js Engine & PBR Materials** | SceneRuntime, ModelRenderer, MaterialSystem, CameraController, SelectionSystem, LODManager, PBR library | M3, M4 | PLANNED |
| **M8** | **Centralized State & Surgical Command Graph** | useStudioStore, CommandGraph (RegenerateRoom, MoveWall, ChangeMaterial, AddFloor), undo/redo, UI binding | M7, M1 | PLANNED |
| **M_FINAL** | **Final Milestone: 100% E2E Pass & Adversarial Hardening** | Pass 100% E2E tests, Tier 5 white-box adversarial stress testing, full production build verification | M1-M8, E2E | PLANNED |

---

## Interface Contracts

### 1. AI Parsing & DesignSpec Contract (`backend/app/schemas/design_spec.py`)
```python
class UnitRequirement(BaseModel):
    unit_type: Literal["1BHK", "2BHK", "3BHK", "Studio", "Penthouse", "Custom"]
    target_area_sqm: float
    required_rooms: List[RoomProgram] # room_type, min_area, requires_daylight, requires_plumbing

class StoreySpec(BaseModel):
    storey_index: int
    elevation: float
    height: float
    unit_mix: List[UnitRequirement]

class DesignSpec(BaseModel):
    spec_id: str
    project_name: str
    building_typology: Literal["Residential", "Commercial", "Villa", "Tower", "MixedUse"]
    total_storeys: int
    floor_to_floor_height: float
    mep_strategy: MEPStrategy
    aesthetic_palette: AestheticPalette
    storeys: List[StoreySpec]
```

### 2. Spatial Hierarchy Contract (`backend/app/schemas/spatial.py`)
```python
class SpatialNode(BaseModel):
    id: str # Deterministic UUID5
    global_id: str # 22-char IFC GUID
    name: str
    node_type: Literal["Project", "Site", "Development", "Building", "Storey", "Unit", "Room"]
    parent_id: Optional[str]
    children: List[SpatialNode] = []
    properties: Dict[str, Any] = {}
```

### 3. Spatial Solver & Room Geometry Contract (`backend/app/services/spatial_solver.py`)
```python
class RoomBoundary(BaseModel):
    room_id: str
    room_type: str
    polygon: List[Tuple[float, float]] # Ordered 2D vertices [x, z]
    area: float
    is_exterior: bool
    wet_zone: bool
    adjacent_room_ids: List[str]

class FloorplanLayout(BaseModel):
    storey_index: int
    elevation: float
    boundary_polygon: List[Tuple[float, float]]
    rooms: List[RoomBoundary]
    corridors: List[RoomBoundary]
    vertical_risers: List[VerticalRiserLocation]
```

### 4. Wall & Hosted Opening Contract (`backend/app/services/wall_engine.py`)
```python
class HostedOpening(BaseModel):
    opening_id: str
    opening_type: Literal["DOOR", "WINDOW"]
    wall_id: str
    distance_along_wall: float
    width: float
    height: float
    sill_height: float
    swing_direction: Optional[str]

class ParametricWall(BaseModel):
    wall_id: str
    start_pt: Tuple[float, float, float]
    end_pt: Tuple[float, float, float]
    thickness: float
    height: float
    is_exterior: bool
    openings: List[HostedOpening]
    sub_segments: List[WallSubSegment] # Pre, Post, Lintel, Sill 3D boxes/meshes
```

### 5. IFC4 Round-Trip Compiler Contract (`backend/app/services/ifc_compiler.py`)
```python
def compile_bim_to_ifc4_step(model: CanonicalBIMModel) -> str:
    """Serializes canonical BIM model into valid ISO 10303-21 STEP string."""
    ...

def parse_ifc4_step_to_bim(step_content: str) -> CanonicalBIMModel:
    """Parses ISO 10303-21 STEP content back into CanonicalBIMModel with 100% fidelity."""
    ...
```

### 6. MEP Multi-Graph Contract (`backend/app/services/mep_engine.py`)
```python
class MEPNode(BaseModel):
    node_id: str
    node_type: Literal["Terminal", "Junction", "Riser", "Source"]
    system_type: Literal["WaterSupply", "SoilWaste", "Vent", "ElectricalPower"]
    position: Tuple[float, float, float]
    connected_fixture_id: Optional[str]

class MEPEdge(BaseModel):
    edge_id: str
    from_node_id: str
    to_node_id: str
    diameter: float
    slope: float
    segment_points: List[Tuple[float, float, float]]

class MEPGraph(BaseModel):
    nodes: Dict[str, MEPNode]
    edges: List[MEPEdge]
    vertical_risers: Dict[str, VerticalRiserShaft]
```

### 7. Frontend Central Store & Command Graph Contract (`frontend_react/src/store/studioStore.ts`)
```typescript
interface Command {
  id: string;
  name: string;
  execute: () => Promise<void> | void;
  undo: () => Promise<void> | void;
}

interface StudioState {
  currentModel: CanonicalBIMModel | null;
  selectedElementId: string | null;
  activeLayer: string[];
  activeLOD: LODLevel;
  cameraMode: 'orbit' | 'firstPerson' | 'floorplan';
  commandHistory: Command[];
  historyIndex: number;
  executeCommand: (cmd: Command) => Promise<void>;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
}
```

---

## Code Layout

```
c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── bim.py              # OpenBIM IFC export, upload, spatial-tree routes
│   │   │       ├── chat.py             # LLM DesignSpec parsing and chat endpoints
│   │   │       ├── models.py           # Model retrieval, mutation, and element PATCH
│   │   │       └── projects.py         # Project CRUD and metadata management
│   │   ├── core/
│   │   │   ├── config.py           # Application settings
│   │   │   └── database.py         # SQLAlchemy SQLite database setup
│   │   ├── schemas/
│   │   │   ├── bim.py              # Canonical BIM entities and element schemas
│   │   │   ├── design_spec.py      # Typed DesignSpec schemas (R1)
│   │   │   ├── mep.py              # MEP graph, nodes, edges, riser schemas (R5)
│   │   │   └── spatial.py          # 6-tier SpatialHierarchy schemas (R1)
│   │   ├── services/
│   │   │   ├── asset_registry.py   # Typed AssetRegistry catalog and clearance envelopes (R6)
│   │   │   ├── ifc_compiler.py     # Pure-Python ISO 10303-21 STEP serializer & parser (R4)
│   │   │   ├── interior_solvers.py # Room layout solvers (Living, Bed, Bath, Kitchen) (R6)
│   │   │   ├── mep_engine.py       # Connected MEP multi-graph and riser router (R5)
│   │   │   ├── spatial_solver.py   # Deterministic 2D floorplan topology solver (R2)
│   │   │   └── wall_engine.py      # Parametric wall & hosted opening engine (R3)
│   │   └── main.py                 # FastAPI application entrypoint
│   └── tests/
│       ├── conftest.py             # Test fixtures and database teardown
│       ├── test_design_spec.py     # R1 DesignSpec & SpatialHierarchy tests
│       ├── test_spatial_solver.py  # R2 Room topology & adjacency tests
│       ├── test_wall_engine.py     # R3 Wall run & hosted opening tests
│       ├── test_ifc_compiler.py    # R4 Canonical BIM & IFC4 round-trip tests
│       ├── test_mep_engine.py      # R5 MEP graph & vertical riser tests
│       ├── test_asset_registry.py  # R6 Asset registry & room layout tests
│       └── test_golden_models.py   # Golden reference models (1BHK, 2BHK, 3BHK, Villa, 12-storey)
├── frontend_react/
│   ├── src/
│   │   ├── engine/                 # Modular Three.js Rendering Engine (R7)
│   │   │   ├── CameraController.ts # Multi-mode camera management
│   │   │   ├── LODManager.ts       # Progressive LOD streaming manager
│   │   │   ├── MaterialSystem.ts   # PBR materials and shader cache
│   │   │   ├── ModelRenderer.ts    # BIM spatial model delta renderer
│   │   │   ├── SceneRuntime.ts     # Three.js lifecycle, loop, and viewport resize
│   │   │   └── SelectionSystem.ts  # Raycasting, highlight, and element picking
│   │   ├── store/
│   │   │   ├── commandGraph.ts     # Command Pattern (RegenerateRoom, MoveWall, etc.) (R8)
│   │   │   └── studioStore.ts      # Centralized Zustand/React model state (R8)
│   │   ├── components/
│   │   │   ├── studio/
│   │   │   │   ├── ThreeViewport.tsx # Decoupled viewport wrapper for SceneRuntime
│   │   │   │   ├── LayerPanel.tsx
│   │   │   │   ├── SpatialTree.tsx
│   │   │   │   └── PropertyPanel.tsx
│   │   │   └── pages/
│   │   │       └── StudioPage.tsx  # Centralized studio workspace
│   │   └── types/
│   │       └── bim.ts              # TypeScript interfaces mirroring CanonicalBIMModel
│   └── package.json
└── TEST_INFRA.md                   # Opaque-box E2E test suite blueprint
```
