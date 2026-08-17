# E2E Test Infra: Builder3D OpenBIM Platform

## Test Philosophy
- **Requirement-Driven & Opaque-Box**: Derived strictly from `ORIGINAL_REQUEST.md` and user-facing architectural OpenBIM specifications without relying on internal implementation quirks.
- **Methodology**: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Interaction Testing + Real-World Architectural Workload Testing.
- **Progressive Testability**: Verification mechanisms utilize deterministic geometric and semantic invariant assertions.

---

## Feature Inventory & Test Matrix

| # | Feature | Source (Requirement) | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) | Tier 4 (Scenario) |
|---|---------|---------------------|:-----------------:|:-----------------:|:-----------------:|:-----------------:|
| F1 | AI Prompt to DesignSpec Validation | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F2 | 6-Tier Spatial Hierarchy (UUID5/IFC GUID) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| F3 | Deterministic 2D Room Topology Solver | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F4 | Daylight Perimeter & Circulation Spines | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F5 | Coaxial Wet Stack Clustering | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ | ✓ |
| F6 | Parametric Wall Run Extraction | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F7 | Hosted Door/Window Opening Voiding | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ | ✓ |
| F8 | Canonical BIM Entities & Psets | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| F9 | ISO 10303-21 IFC4 STEP Round-Trip | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ | ✓ |
| F10 | Connected MEP Directed Multi-Graph | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| F11 | Multi-Storey Vertical Riser Alignment | ORIGINAL_REQUEST §R5 | 5 | 5 | ✓ | ✓ |
| F12 | Typed Furniture AssetRegistry & Clearance | ORIGINAL_REQUEST §R6 | 5 | 5 | ✓ | ✓ |
| F13 | Rule-Based Interior Layout Solvers | ORIGINAL_REQUEST §R6 | 5 | 5 | ✓ | ✓ |
| F14 | Modular Three.js Viewport Subsystems | ORIGINAL_REQUEST §R7 | 5 | 5 | ✓ | ✓ |
| F15 | Cached PBR Material Pipeline | ORIGINAL_REQUEST §R7 | 5 | 5 | ✓ | ✓ |
| F16 | Centralized Model State & Studio Store | ORIGINAL_REQUEST §R8 | 5 | 5 | ✓ | ✓ |
| F17 | Surgical Command Graph & Undo/Redo | ORIGINAL_REQUEST §R8 | 5 | 5 | ✓ | ✓ |

---

## Test Architecture

### 1. Test Runner & Invocation
- **Backend Test Suite**:
  ```powershell
  cd c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai/backend
  pytest tests/ -v
  ```
- **Frontend Production Build & Static Validation**:
  ```powershell
  cd c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai/frontend_react
  npm run build
  ```

### 2. Tier Breakdown

#### Tier 1 — Feature Coverage (>=5 test cases per feature)
- Happy-path isolated feature validations:
  - F1: Valid DesignSpec parsing for studio, 1BHK, 2BHK, 3BHK, Villa, Tower.
  - F2: Spatial tree construction, parent-child integrity, GUID generation.
  - F3: Room boundary closure, correct area calculation, non-overlapping interior polygons.
  - F4: Exterior wall assignment for living/bedrooms, corridor connectivity from entry.
  - F5: Bathroom-kitchen wet zone clustering distance ($R \le 3.5m$).
  - F6: Wall run extraction from shared room edges (interior vs exterior thickness).
  - F7: Wall sub-segmentation with door and window openings (sill, lintel, jambs).
  - F8: BIM entity instantiations with `Pset_WallCommon`, `Pset_SpaceCommon`.
  - F9: IFC4 STEP header formatting, entity serialization, and parsing.
  - F10: MEP graph construction, source-to-terminal path validation.
  - F11: Multi-storey vertical shaft alignment across storeys ($|\Delta X| = 0, |\Delta Z| = 0$).
  - F12: Asset registry lookups, clearance envelope boundary creation.
  - F13: Living, bedroom, bathroom, kitchen layout placement rules.
  - F14: SceneRuntime, ModelRenderer, CameraController module instantiation.
  - F15: PBR material cache hit/miss behavior, texture disposal.
  - F16: Studio store state mutations and element selection.
  - F17: Execute and undo/redo for RegenerateRoom, MoveWall, ChangeMaterial, AddFloor.

#### Tier 2 — Boundary & Corner Cases (>=5 test cases per feature)
- Edge cases and error conditions:
  - Zero-area rooms, non-convex room polygons, extreme aspect ratios.
  - Wall runs with zero openings, max openings, touching openings.
  - Single-storey vs 36-storey buildings; high-density residential towers.
  - Deep interior rooms with zero exterior perimeter access (mechanical ventilation required).
  - High-density MEP graphs with 50+ fixtures per floor.
  - IFC STEP escaping with special characters and Unicode in project/room names.
  - Extreme undo/redo stack depths (50+ commands) without memory leaks.

#### Tier 3 — Cross-Feature Combinations (Pairwise Coverage)
- Integrated interactions:
  - DesignSpec -> Spatial Solver -> Wall Engine -> IFC4 Export -> IFC4 Import.
  - Spatial Solver -> Interior Layout Solver -> MEP Graph Fixture Connections.
  - Wall Engine Opening Edits -> RegenerateRoom Command -> BIM Model Delta Update -> Three.js Mesh Reconciliation.
  - Multi-storey Riser Changes -> Vertical MEP Routing -> Storey Regeneration.

#### Tier 4 — Real-World Application Scenarios (Golden Reference Benchmarks)
1. **Scenario 1: 1BHK Urban Flat** (Single storey, 55 sqm, Living, Open Kitchen, 1 Bed, 1 Bath, Balcony).
2. **Scenario 2: 2BHK Residential Apartment** (Single storey, 90 sqm, Living, Dining, Kitchen, Master Bed + Ensuite, Guest Bed, Common Bath).
3. **Scenario 3: 3BHK Luxury Suite** (Single storey, 160 sqm, Foyer, Living, Dining, Kitchen, Utility, Master Bed + Ensuite + Dressing, 2 Bedrooms + Baths, 2 Balconies).
4. **Scenario 4: 2-Storey Modern Villa** (Multi-storey, 280 sqm, Ground Floor: Living, Kitchen, Dining, Guest Suite, Powder Room, Internal Staircase; First Floor: Master Suite, 2 Bedrooms, Family Lounge, Terrace).
5. **Scenario 5: 12-Storey Residential Tower** (Multi-storey, Ground Commercial + 11 Typical Floors with 4 units per floor, Coaxial Wet Stacks, Central Circulation Core with Elevators/Stairs, Full Vertical MEP Risers).

---

## Coverage Thresholds
- Tier 1: $\ge 85$ unit test cases across all features
- Tier 2: $\ge 85$ boundary/edge test cases
- Tier 3: $\ge 20$ pairwise interaction test cases
- Tier 4: 5 realistic golden reference benchmark models with 7 architectural invariant checks
- **Total test cases**: $\ge 195$ test cases
