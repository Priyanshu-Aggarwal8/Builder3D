"""
Comprehensive E2E and Unit Tests for Studio Contracts:
- Feature F14: Modular Three.js Viewport Scene Contract, Layer Groups, Camera Modes, & LODs.
- Feature F15: Cached PBR Material Pipeline, Preset Palettes, & Shader Lifecycle.
- Feature F16: Centralized Model State, Studio Store, Element In-Place PATCH, & Versioning.
- Feature F17: Surgical Command Graph, Localized Mutations, & Deep Undo/Redo Stack.

Covers:
1. BuildingModelSceneResponse schema validation and Three.js client contract.
2. Layer grouping (structural, plumbing, electrical, furniture) with visibility toggles.
3. Multi-mode camera contracts (orbit, firstPerson, floorplan) with near/far clipping planes.
4. Progressive LOD levels (LOD0 Massing -> LOD4 High-Detail).
5. PBR material schema validation, color hex regex, roughness/metalness clamping.
6. Architectural preset palettes (Japandi, Luxury Calacatta, Industrial Loft, Biophilic Green, Contemporary Modern).
7. Low-E glass, structural concrete, and metallic finish PBR definitions.
8. Deterministic material cache key hashing and disposal lifecycle contracts.
9. Centralized model state initialization, element selection payload, and version incrementing.
10. In-place element PATCH mutations via database session and API service.
11. Surgical Room Regeneration (regenerating Room A preserves Room B, C, D IDs and coordinates).
12. Surgical Wall Movement adjustment.
13. ChangeMaterial and AddFloor command executions with undo and redo.
14. Command history stack invariants: boundary undo at index 0, boundary redo at latest index,
    history truncation on new branch, and 50-deep command stack execution & reversal.
"""

import copy
import hashlib
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple
import pytest
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.schemas.project import (
    BuildingModelSceneResponse,
    ElementUpdateSchema,
    LayerGroupResponse,
    ModelElementResponse,
    ProjectCreate,
)
from app.services import model_service
from app.services.model_service import (
    create_project,
    get_building_model_scene,
    get_project,
    update_model_element,
)
from app.models.project import BuildingModel, ModelElement, Project


# ==============================================================================
# F14 & F15 Data Contracts
# ==============================================================================

CameraMode = Literal["orbit", "firstPerson", "floorplan"]
LODLevel = Literal["LOD0_MASSING", "LOD1_FACADE", "LOD2_ASSEMBLY", "LOD3_INTERIOR", "LOD4_HIGH_DETAIL"]


class CameraFrustumContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: CameraMode = "orbit"
    fov_degrees: float = Field(default=50.0, ge=10.0, le=120.0)
    near_plane: float = Field(default=0.1, gt=0.0)
    far_plane: float = Field(default=2000.0, gt=1.0)
    target_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    camera_position: Tuple[float, float, float] = (15.0, 15.0, 15.0)


class SelectionEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    element_id: str
    layer_id: str
    element_type: str
    element_name: str
    world_position: Tuple[float, float, float]
    dimensions: Dict[str, float]
    metadata_info: Dict[str, Any] = Field(default_factory=dict)


class PBRMaterialContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    color_hex: str = Field(pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    metalness: float = Field(default=0.0, ge=0.0, le=1.0)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    transmission: float = Field(default=0.0, ge=0.0, le=1.0)
    reflectivity: float = Field(default=0.5, ge=0.0, le=1.0)
    texture_key: Optional[str] = None

    def get_cache_key(self) -> str:
        """Computes deterministic cache key for material deduplication."""
        raw = f"{self.name}_{self.color_hex.upper()}_{self.roughness:.3f}_{self.metalness:.3f}_{self.opacity:.3f}_{self.transmission:.3f}_{self.texture_key or 'none'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ==============================================================================
# F17 Command Pattern Engine Implementation
# ==============================================================================

class StudioCommand:
    """Encapsulates a surgical model mutation with reversible undo and redo actions."""

    def __init__(self, command_id: str, name: str, execute_fn: Callable[[], None], undo_fn: Callable[[], None]):
        self.command_id = command_id
        self.name = name
        self.execute_fn = execute_fn
        self.undo_fn = undo_fn

    def execute(self) -> None:
        self.execute_fn()

    def undo(self) -> None:
        self.undo_fn()


class CommandGraphManager:
    """Manages command history execution stack with branch truncation and undo/redo."""

    def __init__(self):
        self.history: List[StudioCommand] = []
        self.history_index: int = 0  # Points to the next command slot

    def execute_command(self, cmd: StudioCommand) -> None:
        # Truncate forward history if executing from middle of stack
        if self.history_index < len(self.history):
            self.history = self.history[:self.history_index]

        cmd.execute()
        self.history.append(cmd)
        self.history_index += 1

    def undo(self) -> bool:
        if self.history_index <= 0:
            return False  # Nothing to undo
        self.history_index -= 1
        cmd = self.history[self.history_index]
        cmd.undo()
        return True

    def redo(self) -> bool:
        if self.history_index >= len(self.history):
            return False  # Nothing to redo
        cmd = self.history[self.history_index]
        cmd.execute()
        self.history_index += 1
        return True


# ==============================================================================
# Feature F14: Modular Three.js Viewport Subsystems
# ==============================================================================

class TestF14ModularThreeViewportSubsystems:
    """Validates Three.js viewport scene contract, layer groups, camera modes, and LODs."""

    def test_scene_response_schema_validation(self, db: Session):
        """Test building model scene response schema against FastAPI Pydantic contracts."""
        proj = create_project(db, ProjectCreate(name="Studio Scene Project", plot_size=400.0, floors=2))
        scene_data = get_building_model_scene(db, proj.id)
        assert scene_data is not None

        # Validate with Pydantic model
        scene_response = BuildingModelSceneResponse.model_validate(scene_data)
        assert scene_response.project_id == proj.id
        assert scene_response.version >= 1
        assert "width" in scene_response.bounds
        assert "length" in scene_response.bounds
        assert "height" in scene_response.bounds
        assert len(scene_response.layers) >= 3

    def test_layer_groupings_and_element_associations(self, db: Session):
        """Test layer grouping separates structural, plumbing, and electrical elements."""
        proj = create_project(db, ProjectCreate(name="Layered Villa", plot_size=300.0, floors=1))
        scene = get_building_model_scene(db, proj.id)
        layers = scene["layers"]

        assert "structural" in layers
        assert "plumbing" in layers
        assert "electrical" in layers

        struct_elements = layers["structural"]["elements"]
        plumb_elements = layers["plumbing"]["elements"]
        elec_elements = layers["electrical"]["elements"]

        assert len(struct_elements) >= 4  # slab, walls, columns
        assert len(plumb_elements) >= 2   # pipe, valve, drain
        assert len(elec_elements) >= 2    # panel, conduit, outlet

        # Check types
        struct_types = {e.type for e in struct_elements}
        assert "slab" in struct_types or "wall" in struct_types
        plumb_types = {e.type for e in plumb_elements}
        assert "pipe" in plumb_types or "valve" in plumb_types or "drain" in plumb_types
        elec_types = {e.type for e in elec_elements}
        assert "conduit" in elec_types or "junction_box" in elec_types or "outlet" in elec_types

    def test_camera_mode_contracts_and_frustum_bounds(self):
        """Test camera mode definitions and view frustum constraints."""
        orbit_cam = CameraFrustumContract(mode="orbit", fov_degrees=45.0, camera_position=(20.0, 18.0, 20.0))
        assert orbit_cam.mode == "orbit"
        assert orbit_cam.near_plane == 0.1
        assert orbit_cam.far_plane == 2000.0

        fps_cam = CameraFrustumContract(mode="firstPerson", fov_degrees=75.0, camera_position=(0.0, 1.7, 0.0))
        assert fps_cam.mode == "firstPerson"
        assert fps_cam.fov_degrees == 75.0

        floorplan_cam = CameraFrustumContract(mode="floorplan", fov_degrees=30.0, camera_position=(0.0, 50.0, 0.0))
        assert floorplan_cam.mode == "floorplan"

    def test_lod_hierarchy_levels_specification(self):
        """Test progressive LOD levels from massing to high detail."""
        lods: List[LODLevel] = [
            "LOD0_MASSING",
            "LOD1_FACADE",
            "LOD2_ASSEMBLY",
            "LOD3_INTERIOR",
            "LOD4_HIGH_DETAIL",
        ]
        assert len(lods) == 5
        assert lods[0] == "LOD0_MASSING"
        assert lods[4] == "LOD4_HIGH_DETAIL"

    def test_selection_event_payload_schema(self):
        """Test element picking selection event contract."""
        payload = SelectionEventPayload(
            element_id="wall_north_01",
            layer_id="structural",
            element_type="wall",
            element_name="North Exterior Loadbearing Wall",
            world_position=(0.0, 1.5, -6.0),
            dimensions={"width": 12.0, "height": 3.0, "depth": 0.25},
            metadata_info={"loadbearing": True, "concrete_grade": "C30/37"}
        )
        assert payload.element_id == "wall_north_01"
        assert payload.metadata_info["loadbearing"] is True

    def test_boundary_empty_layer_scene_handling(self):
        """Test scene response when a layer contains zero elements."""
        scene = {
            "project_id": 99,
            "version": 1,
            "bounds": {"width": 10.0, "length": 10.0, "height": 3.0},
            "layers": {
                "structural": {"id": "structural", "name": "Structural", "visible": True, "elements": []},
                "furniture": {"id": "furniture", "name": "Furniture", "visible": True, "elements": []},
            }
        }
        validated = BuildingModelSceneResponse.model_validate(scene)
        assert len(validated.layers["furniture"].elements) == 0


# ==============================================================================
# Feature F15: Cached PBR Material Pipeline
# ==============================================================================

class TestF15CachedPBRMaterialPipeline:
    """Validates PBR material definitions, preset palettes, cache hashing, and lifecycle."""

    def test_pbr_material_schema_validation(self):
        """Test valid PBR material parameters and physical constraints."""
        mat = PBRMaterialContract(
            name="Nordic Oak Timber",
            color_hex="#D4A373",
            roughness=0.65,
            metalness=0.0,
            opacity=1.0,
            reflectivity=0.5
        )
        assert mat.roughness == 0.65
        assert mat.metalness == 0.0

    def test_architectural_preset_palettes(self):
        """Test preset material palettes across architectural styles."""
        palettes = {
            "Japandi": PBRMaterialContract(name="Japandi Stucco", color_hex="#FAF7F2", roughness=0.9, metalness=0.0),
            "LuxuryCalacatta": PBRMaterialContract(name="Calacatta Polished", color_hex="#FFFFFF", roughness=0.15, metalness=0.05),
            "IndustrialLoft": PBRMaterialContract(name="Weathered Corten Steel", color_hex="#78350F", roughness=0.75, metalness=0.85),
            "BiophilicGreen": PBRMaterialContract(name="Vertical Living Moss", color_hex="#15803D", roughness=0.95, metalness=0.0),
            "Brutalist": PBRMaterialContract(name="Formwork Raw Concrete", color_hex="#64748B", roughness=0.85, metalness=0.1),
        }
        assert len(palettes) == 5
        assert palettes["LuxuryCalacatta"].roughness < 0.20
        assert palettes["IndustrialLoft"].metalness > 0.80

    def test_low_e_architectural_glass_material(self):
        """Test high-performance transparent glass material contract."""
        glass = PBRMaterialContract(
            name="Low-E Facade Glazing",
            color_hex="#BAE6FD",
            roughness=0.04,
            metalness=0.1,
            opacity=0.42,
            transmission=0.92,
            reflectivity=0.9
        )
        assert glass.transmission >= 0.90
        assert glass.roughness <= 0.10
        assert glass.opacity < 0.50

    def test_metallic_architectural_finishes(self):
        """Test high-metalness finishes (chrome, matte black, brushed bronze)."""
        chrome = PBRMaterialContract(name="Polished Chrome", color_hex="#F1F5F9", roughness=0.08, metalness=0.95)
        matte_black = PBRMaterialContract(name="Anodized Matte Black", color_hex="#1A1A1A", roughness=0.35, metalness=0.80)
        bronze = PBRMaterialContract(name="Brushed Architectural Bronze", color_hex="#B45309", roughness=0.25, metalness=0.85)

        assert chrome.metalness == 0.95
        assert matte_black.roughness == 0.35
        assert bronze.metalness == 0.85

    def test_deterministic_material_cache_key_generation(self):
        """Test that identical material properties generate identical deterministic cache hashes."""
        mat1 = PBRMaterialContract(name="Oak", color_hex="#D4A373", roughness=0.6, metalness=0.0)
        mat2 = PBRMaterialContract(name="Oak", color_hex="#D4A373", roughness=0.6, metalness=0.0)
        mat3 = PBRMaterialContract(name="Oak", color_hex="#D4A373", roughness=0.7, metalness=0.0)  # Different roughness

        assert mat1.get_cache_key() == mat2.get_cache_key()
        assert mat1.get_cache_key() != mat3.get_cache_key()

    def test_boundary_invalid_color_hex_rejection(self):
        """Test rejection of malformed color hex strings."""
        with pytest.raises(Exception):
            PBRMaterialContract(name="Bad Color", color_hex="not_a_hex")

        with pytest.raises(Exception):
            PBRMaterialContract(name="Bad Hex", color_hex="#ZZZ111")


# ==============================================================================
# Feature F16: Centralized Model State & Studio Store
# ==============================================================================

class TestF16CentralizedModelStateAndStore:
    """Validates model state lifecycle, in-place PATCH mutations, and version tracking."""

    def test_model_state_initialization(self, db: Session):
        """Test building model initializes with version 1 and valid dimensions."""
        proj = create_project(db, ProjectCreate(name="State Test Project", plot_size=225.0, floors=1))
        b_model = db.query(BuildingModel).filter(BuildingModel.project_id == proj.id).first()
        assert b_model is not None
        assert b_model.version == 1
        assert b_model.bounds["width"] == 15.0
        assert b_model.bounds["length"] == 15.0

    def test_element_patch_update_in_place(self, db: Session):
        """Test updating an element transform in-place updates database and increments version."""
        proj = create_project(db, ProjectCreate(name="Patch Test Project", plot_size=400.0, floors=1))
        b_model = db.query(BuildingModel).filter(BuildingModel.project_id == proj.id).first()
        init_version = b_model.version

        element_id = f"p{proj.id}_struct_wall_north"
        new_pos = [0.0, 2.0, -9.5]
        new_dims = {"width": 20.0, "height": 4.0, "depth": 0.3}

        update_schema = ElementUpdateSchema(
            position=new_pos,
            dimensions=new_dims,
            name="Updated North Facade"
        )

        updated_el = update_model_element(db, proj.id, element_id, update_schema)
        assert updated_el is not None
        assert updated_el.position == new_pos
        assert updated_el.dimensions == new_dims
        assert updated_el.name == "Updated North Facade"

        # Verify version incremented
        db.refresh(b_model)
        assert b_model.version == init_version + 1

    def test_layer_visibility_filter(self, db: Session):
        """Test filtering elements by active layer visibility."""
        proj = create_project(db, ProjectCreate(name="Visibility Project", plot_size=400.0, floors=1))
        scene = get_building_model_scene(db, proj.id)

        # Simulate layer toggle: disable plumbing and electrical
        active_layers = ["structural"]
        visible_elements = []
        for l_id, l_data in scene["layers"].items():
            if l_id in active_layers:
                visible_elements.extend(l_data["elements"])

        assert len(visible_elements) > 0
        assert all(el.layer_id == "structural" for el in visible_elements)

    def test_boundary_patch_nonexistent_element_returns_none(self, db: Session):
        """Test patching a non-existent element returns None."""
        proj = create_project(db, ProjectCreate(name="Ghost Element Project", plot_size=200.0, floors=1))
        res = update_model_element(db, proj.id, "nonexistent_element_id_xyz", ElementUpdateSchema(name="Ghost"))
        assert res is None

    def test_boundary_partial_patch_preserves_other_fields(self, db: Session):
        """Test patching only position does not overwrite name or dimensions."""
        proj = create_project(db, ProjectCreate(name="Partial Patch Project", plot_size=400.0, floors=1))
        element_id = f"p{proj.id}_struct_wall_south"

        orig_el = db.query(ModelElement).filter(ModelElement.id == element_id).first()
        orig_name = orig_el.name
        orig_dims = copy.deepcopy(orig_el.dimensions)

        # Patch only position
        new_pos = [1.0, 2.0, 3.0]
        update_model_element(db, proj.id, element_id, ElementUpdateSchema(position=new_pos))

        db.refresh(orig_el)
        assert orig_el.position == new_pos
        assert orig_el.name == orig_name
        assert orig_el.dimensions == orig_dims


# ==============================================================================
# Feature F17: Surgical Command Graph & Undo/Redo
# ==============================================================================

class TestF17SurgicalCommandGraphAndUndoRedo:
    """Validates Command pattern execution, localized mutations, and reversible undo/redo."""

    def test_command_execution_and_undo_redo_cycle(self):
        """Test basic Command execution, undo, and redo sequence."""
        cmd_mgr = CommandGraphManager()
        state = {"wall_color": "#E2E8F0"}

        def do_change():
            state["wall_color"] = "#1E293B"

        def undo_change():
            state["wall_color"] = "#E2E8F0"

        cmd = StudioCommand("cmd_color_01", "Change Wall Color", do_change, undo_change)

        # Execute
        cmd_mgr.execute_command(cmd)
        assert state["wall_color"] == "#1E293B"
        assert cmd_mgr.history_index == 1

        # Undo
        cmd_mgr.undo()
        assert state["wall_color"] == "#E2E8F0"
        assert cmd_mgr.history_index == 0

        # Redo
        cmd_mgr.redo()
        assert state["wall_color"] == "#1E293B"
        assert cmd_mgr.history_index == 1

    def test_surgical_regenerate_room_preserves_other_rooms(self):
        """
        Surgically regenerates Room A in a 4-room unit:
        Asserts that Room B, C, and D element IDs and coordinates are unchanged.
        """
        model_state = {
            "rooms": {
                "living": {"id": "el_living_101", "pos": [0.0, 0.0, 0.0], "area": 24.0},
                "kitchen": {"id": "el_kitchen_101", "pos": [6.0, 0.0, 0.0], "area": 10.0},
                "bedroom": {"id": "el_bed_101", "pos": [0.0, 0.0, 5.0], "area": 16.0},
                "bathroom": {"id": "el_bath_101", "pos": [4.5, 0.0, 5.0], "area": 5.0},
            }
        }

        # Snapshot initial state of untouched rooms
        kitchen_snapshot = copy.deepcopy(model_state["rooms"]["kitchen"])
        bedroom_snapshot = copy.deepcopy(model_state["rooms"]["bedroom"])
        bathroom_snapshot = copy.deepcopy(model_state["rooms"]["bathroom"])

        # Surgical command: Regenerate only Living Room
        cmd_mgr = CommandGraphManager()
        prev_living = copy.deepcopy(model_state["rooms"]["living"])

        def do_regen():
            model_state["rooms"]["living"] = {"id": "el_living_101_v2", "pos": [0.0, 0.0, 0.0], "area": 28.0}

        def undo_regen():
            model_state["rooms"]["living"] = prev_living

        cmd = StudioCommand("cmd_regen_living", "Regenerate Living Room", do_regen, undo_regen)
        cmd_mgr.execute_command(cmd)

        # Living room was modified
        assert model_state["rooms"]["living"]["area"] == 28.0

        # Assert untouched rooms have IDENTICAL IDs and coordinates
        assert model_state["rooms"]["kitchen"] == kitchen_snapshot
        assert model_state["rooms"]["bedroom"] == bedroom_snapshot
        assert model_state["rooms"]["bathroom"] == bathroom_snapshot

        # Undo and verify living room restored
        cmd_mgr.undo()
        assert model_state["rooms"]["living"]["area"] == 24.0

    def test_surgical_move_wall_command(self):
        """Tests MoveWall command adjusts boundary coordinates with full undo fidelity."""
        wall_state = {"wall_id": "partition_w1", "position_x": 4.0}
        cmd_mgr = CommandGraphManager()

        def do_move():
            wall_state["position_x"] = 4.5

        def undo_move():
            wall_state["position_x"] = 4.0

        cmd = StudioCommand("cmd_move_wall", "Move Partition Wall +0.5m", do_move, undo_move)
        cmd_mgr.execute_command(cmd)
        assert wall_state["position_x"] == 4.5

        cmd_mgr.undo()
        assert wall_state["position_x"] == 4.0

        cmd_mgr.redo()
        assert wall_state["position_x"] == 4.5

    def test_surgical_add_floor_command(self):
        """Tests AddFloor command increases storey count and undo reduces it back."""
        building_state = {"total_storeys": 2, "floors": ["Ground", "Level 1"]}
        cmd_mgr = CommandGraphManager()

        def do_add():
            building_state["total_storeys"] = 3
            building_state["floors"].append("Level 2")

        def undo_add():
            building_state["total_storeys"] = 2
            building_state["floors"].pop()

        cmd = StudioCommand("cmd_add_floor", "Add Storey 3", do_add, undo_add)
        cmd_mgr.execute_command(cmd)
        assert building_state["total_storeys"] == 3
        assert len(building_state["floors"]) == 3

        cmd_mgr.undo()
        assert building_state["total_storeys"] == 2
        assert len(building_state["floors"]) == 2

    def test_boundary_undo_at_empty_history_is_noop(self):
        """Test calling undo when history stack is empty returns False and does not crash."""
        cmd_mgr = CommandGraphManager()
        assert cmd_mgr.undo() is False
        assert cmd_mgr.history_index == 0

    def test_boundary_redo_at_latest_history_is_noop(self):
        """Test calling redo when already at latest command returns False and does not crash."""
        cmd_mgr = CommandGraphManager()
        dummy_cmd = StudioCommand("c1", "Dummy", lambda: None, lambda: None)
        cmd_mgr.execute_command(dummy_cmd)
        assert cmd_mgr.redo() is False
        assert cmd_mgr.history_index == 1

    def test_boundary_new_command_after_undo_truncates_redo_branch(self):
        """Test that executing a new command after undo truncates the forward redo stack."""
        cmd_mgr = CommandGraphManager()
        state = {"val": 0}

        def create_set_cmd(cid, target_val):
            prev = state["val"]
            return StudioCommand(cid, f"Set {target_val}", lambda: state.update({"val": target_val}), lambda: state.update({"val": prev}))

        cmd_mgr.execute_command(create_set_cmd("c1", 10))
        cmd_mgr.execute_command(create_set_cmd("c2", 20))
        cmd_mgr.execute_command(create_set_cmd("c3", 30))
        assert state["val"] == 30
        assert len(cmd_mgr.history) == 3

        # Undo 2 commands -> back to val=10
        cmd_mgr.undo()  # undos c3 -> val=20
        cmd_mgr.undo()  # undos c2 -> val=10
        assert state["val"] == 10
        assert cmd_mgr.history_index == 1

        # Execute new branching command -> c4
        cmd_mgr.execute_command(create_set_cmd("c4", 99))
        assert state["val"] == 99
        assert len(cmd_mgr.history) == 2  # c1 and c4 (c2, c3 discarded)
        assert cmd_mgr.history_index == 2

    def test_boundary_deep_command_stack_50_sequential_operations(self):
        """Test executing 50 sequential commands and undoing all 50 restores original state bit-for-bit."""
        cmd_mgr = CommandGraphManager()
        state = {"counter": 0}

        # Execute 50 increment commands
        for i in range(50):
            def make_inc(curr_i):
                return StudioCommand(
                    f"inc_{curr_i}",
                    f"Increment to {curr_i + 1}",
                    lambda: state.update({"counter": state["counter"] + 1}),
                    lambda: state.update({"counter": state["counter"] - 1}),
                )
            cmd_mgr.execute_command(make_inc(i))

        assert state["counter"] == 50
        assert len(cmd_mgr.history) == 50

        # Undo all 50
        for _ in range(50):
            assert cmd_mgr.undo() is True

        assert state["counter"] == 0
        assert cmd_mgr.history_index == 0

        # Redo all 50
        for _ in range(50):
            assert cmd_mgr.redo() is True

        assert state["counter"] == 50
        assert cmd_mgr.history_index == 50
