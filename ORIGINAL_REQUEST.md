# Original User Request

## 2026-08-09T16:18:01Z

# Teamwork Project Prompt — Draft

Build a production-ready first phase of the Builder AI app based on the provided architecture docs. The core feature is a real-time editable 3D building model where structural, electrical, and plumbing layers can be visualized and modified interactively.

Working directory: c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai
Integrity mode: development

## Requirements

### R1. Full-Stack Application
Build a backend to serve and manage 3D model data, and a frontend web application to render the interactive UI. The agent team is free to choose the most efficient web frameworks (e.g. FastAPI/Angular, Node/React, Python/Vanilla JS) to achieve the real-time 3D editing goal quickly.

### R2. Interactive 3D Viewer with Layers
Implement a 3D canvas that displays a building model containing distinct, toggleable functional layers (e.g., structural, electrical wiring, water pipelines).

### R3. Real-Time Editing
Implement interactive controls allowing the user to modify the 3D model in real-time (e.g., moving an object, wall, or pipeline) and have the system update the state accordingly.

## Acceptance Criteria

### API & Rendering
- [ ] The backend API exposes an endpoint that successfully serves structured 3D model data (e.g., JSON, GLTF, or OBJ).
- [ ] The frontend successfully loads the 3D data and renders it in a 3D canvas (e.g., using Three.js) without browser console errors.

### Interaction
- [ ] The UI provides visible toggle controls to independently show or hide at least two distinct building layers (e.g., "Electrical", "Plumbing").
- [ ] The UI allows the user to interactively modify at least one element in the 3D space, and the visual change is reflected in real-time.

## 2026-08-16T08:27:47Z

# Teamwork Project Prompt — Draft

Systematically transform Builder3D from a procedural primitive box visualizer into a credible, production-grade AI-driven architectural OpenBIM generation and spatial planning platform.

Working directory: c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai
Integrity mode: development

---

## Non-Negotiable Engineering Principles

1. **Single Source of Truth**: One canonical building model (`CanonicalBIMModel` / `SpatialHierarchy`).
2. **AI Separation**: LLM produces a typed structured `DesignSpec`; deterministic spatial & BIM compilers create geometry.
3. **Derived Geometry**: Room geometry is derived from topological boundary polygons; walls support true hosted openings (no overlapping boxes).
4. **Semantic Assemblies**: Doors, windows, facades, and MEP are structured assemblies with physical clearances and connectivity.
5. **Asset Registry**: Furniture and fixtures consume typed registry definitions (`assetType = "furniture.sofa"`) rather than name-based heuristic matching.
6. **IFC & BIM Rigor**: IFC4 export/import is compiled from canonical BIM entities with stable GlobalIds, hierarchy, and round-trip fidelity.
7. **Modular Presentation**: Three.js rendering engine is decoupled into focused subsystems (`SceneRuntime`, `ModelRenderer`, `MaterialSystem`, `LODManager`, `CameraController`).
8. **Surgical Regeneration & Command Graph**: Localized mutations (e.g. modify room, change facade, add floor) preserve unaffected element identities.

---

## Requirements

### R1. Structured DesignSpec & Spatial Model Hierarchy
Implement a typed `DesignSpec` schema (Site, Building typology, Floor count, Unit program, Spatial mix, MEP strategy, Aesthetic palette) and a canonical spatial hierarchy:
`Project` → `Site` → `Development` → `Building` → `Storey` → `Unit` → `Room` with stable, deterministic UUIDs.

### R2. Deterministic Spatial / Floorplan Solver & Room Topology
Implement a deterministic floorplan solver that arranges room boundary polygons based on architectural adjacency (e.g. Kitchen adjacent to Dining, Master Bed to en-suite bath, daylight perimeter access, plumbing wet stack clustering, circulation corridors without room cut-throughs).

### R3. Wall & Hosted Opening Generation System
Replace box extrusion with a parametric wall engine generating segmented wall runs with hosted architectural openings for doors (hinge, leaf, frame, swing direction) and windows (glazing, frame, mullions, sill, reveal).

### R4. Canonical BIM Model & IFC4 Round-Trip Compiler
Implement canonical BIM entities (`IfcBuildingStorey`, `IfcSpace`, `IfcWall`, `IfcDoor`, `IfcWindow`, `IfcSlab`, `IfcColumn`, `IfcDistributionElement`, etc.). Ensure IFC4 export and import maintain 100% semantic identity and spatial hierarchy round-trip.

### R5. Connected MEP Graph Engine
Implement a graph-connected MEP system where plumbing (supply, waste, soil, vent) and electrical circuits route logically between fixtures and vertical service risers across stacked storeys.

### R6. Furniture Asset Registry & Rule-Based Interior Layout
Create a typed `AssetRegistry` for furniture, sanitary ware, and appliances with defined bounding boxes and clearance envelopes. Furniture placement is driven by rule-based room layout solvers.

### R7. Modular Three.js Rendering Architecture & PBR Material Library
Refactor `ThreeViewport` into modular subsystems (`SceneRuntime`, `ModelRenderer`, `MaterialSystem`, `CameraController`, `SelectionSystem`, `LODManager`). Implement progressive LOD streaming (Massing → Facade → Assembly → Interior → High-Detail) and a cached PBR material library.

### R8. Centralized Frontend Model State & Surgical Editing
Refactor `StudioPage` to centralize model state, decouple UI controls from 3D rendering, and support surgical commands (`RegenerateRoom`, `MoveWall`, `ChangeMaterial`, `AddFloor`) with undo/redo capability.

---

## Acceptance Criteria

### Architectural Integrity & Geometry
- [ ] AI prompt parsing strictly outputs a validated `DesignSpec` without direct geometry coordinates.
- [ ] Rooms are represented as boundary polygons; walls, floors, and ceilings are generated from boundary geometry.
- [ ] Doors and windows cut physical openings into host walls without visual collision or overlapping geometry.
- [ ] Wet zones (kitchens, bathrooms) spatially cluster and vertically align risers across multi-storey designs.
- [ ] Furniture and fixtures are resolved via `AssetRegistry` and respect circulation clearance corridors.

### BIM, IFC & MEP
- [ ] Exporting to IFC4 generates valid ISO 10303-21 files with complete spatial tree (`IfcProject` down to `IfcSpace`/`IfcElement`).
- [ ] Round-trip IFC test (`Builder3D BIM` → `IFC4 Export` → `IFC Import` → `Builder3D BIM`) passes with zero semantic data loss.
- [ ] Connected MEP graph validates continuity from terminal fixtures to vertical utility shafts.

### Rendering & Studio Performance
- [ ] Three.js viewport is decoupled from React UI state and operates via dedicated engine subsystems.
- [ ] LOD switching progressively streams geometry without GPU memory leaks or WebGL context recreation.
- [ ] Frame rate maintains 60+ FPS on medium/high density 12-storey residential building models.
- [ ] Surgical regeneration updates only target sub-trees (e.g. single room or single floor) while preserving unaffected element IDs.

### Automated Testing & Quality
- [ ] Automated test suite verifies DesignSpec parsing, spatial solver constraints, wall openings, MEP routing, and IFC export/import.
- [ ] Golden reference test models (1BHK, 2BHK, 3BHK, Villa, 12-storey Tower) compile and pass architectural validation.
- [ ] Production build (`npm run build` & Python tests) passes with zero errors.
