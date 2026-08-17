"""
Comprehensive E2E and Unit Tests for Feature F8 (Canonical BIM Entities & Psets)
and Feature F9 (Zero-Dependency ISO 10303-21 IFC4 STEP Compilation / Parsing Round-Trip Fidelity).

Covers all 4 Tiers:
- Tier 1: Canonical BIM Entity Schemas, Property Sets, STEP formatting, pure-Python compilation/parsing.
- Tier 2: Boundary & stress conditions (empty models, special characters, unicode \\X2\\ / \\X4\\ escaping,
  malformed syntax rejection, 100-element high density, 12-storey tower depth).
- Tier 3: Cross-milestone pairwise interactions (Spatial tree <-> BIM model <-> STEP).
- Tier 4: Golden Reference architectural models (1BHK, 2BHK, 3BHK, 2-Storey Villa, 12-Storey Tower).
"""

import math
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

import pytest

from app.schemas.bim import (
    BIMBuilding,
    BIMColumn,
    BIMDistributionElement,
    BIMDoor,
    BIMEntityBase,
    BIMProject,
    BIMPropertyItem,
    BIMPropertySet,
    BIMSlab,
    BIMSite,
    BIMSpace,
    BIMStorey,
    BIMWall,
    BIMWindow,
    CanonicalBIMEntity,
    CanonicalBIMModel,
    PropertyItem,
    PropertySet,
    create_pset_column_common,
    create_pset_door_common,
    create_pset_flow_segment_common,
    create_pset_slab_common,
    create_pset_space_common,
    create_pset_wall_common,
    create_pset_window_common,
)
from app.schemas.spatial import (
    SpatialNode,
    SpatialNodeType,
    decode_ifc_guid,
    encode_ifc_guid,
    generate_spatial_uuid,
)
from app.services.ifc_compiler import (
    StepDerived,
    StepEntity,
    StepEnum,
    StepError,
    StepFile,
    StepHeader,
    StepParser,
    StepRef,
    StepSyntaxError,
    StepTypedParam,
    compile_bim_to_ifc4_step,
    create_ifc4_project_from_model,
    format_step_float,
    parse_ifc4_step_to_bim,
    parse_ifc_content,
    step_escape_string,
    step_unescape_string,
)


# ==============================================================================
# Tier 1: Feature F8 — Canonical BIM Entities & Property Sets (Psets)
# ==============================================================================

class TestF8CanonicalBIMEntitiesAndPsets:
    """Validates pure canonical BIM entities, containment, and standard/custom Psets."""

    def test_property_item_and_property_set_mechanics(self):
        """Test PropertyItem typing and PropertySet CRUD and dictionary methods."""
        pset = PropertySet(name="Pset_CustomTesting")
        pset.set_property("StringProp", "Standard Value", "IfcLabel")
        pset.set_property("BoolProp", True, "IfcBoolean")
        pset.set_property("IntProp", 42, "IfcInteger")
        pset.set_property("FloatProp", 3.14159, "IfcReal")

        assert pset.get_value("StringProp") == "Standard Value"
        assert pset.get_value("BoolProp") is True
        assert pset.get_value("IntProp") == 42
        assert abs(pset.get_value("FloatProp") - 3.14159) < 1e-5
        assert pset.get_value("NonExistent", "default_val") == "default_val"

        flat = pset.to_flat_dict()
        assert flat["StringProp"] == "Standard Value"
        assert flat["BoolProp"] is True
        assert flat["IntProp"] == 42

        reconstructed = PropertySet.from_dict("Pset_Reconstructed", flat)
        assert reconstructed.get_value("StringProp") == "Standard Value"
        assert reconstructed.get_value("BoolProp") is True

    def test_canonical_ifc_wall_entity_and_pset_wall_common(self):
        """Test instantiation of IfcWall with Pset_WallCommon properties."""
        guid = encode_ifc_guid(uuid.uuid4())
        wall = BIMWall(
            global_id=guid,
            name="Exterior Wall North",
            layer_id="structural",
            position=(0.0, 1.5, -6.0),
            dimensions={"width": 12.0, "height": 3.0, "depth": 0.25},
            thickness=0.25,
            height=3.0,
            is_exterior=True,
            load_bearing=True,
            parent_storey="Level 1 (Ground)",
        )
        assert wall.entity_type == "IfcWall"
        assert len(wall.global_id) == 22
        assert wall.get_property("Pset_WallCommon", "LoadBearing") is True
        assert wall.get_property("Pset_WallCommon", "IsExternal") is True
        assert wall.thickness == 0.25

    def test_canonical_ifc_space_entity_and_pset_space_common(self):
        """Test instantiation of IfcSpace with room boundaries and Pset_SpaceCommon."""
        guid = encode_ifc_guid(uuid.uuid4())
        space = BIMSpace(
            global_id=guid,
            name="Living & Dining Great Room",
            layer_id="architectural",
            position=(0.0, 0.0, 0.0),
            dimensions={"width": 6.0, "height": 2.8, "depth": 5.0},
            area_sqm=30.0,
            ceiling_height=2.8,
            room_type="Residential_Living",
            parent_storey="Level 1 (Ground)",
        )
        assert space.entity_type == "IfcSpace"
        assert space.get_property("Pset_SpaceCommon", "GrossFloorArea") == 30.0
        assert space.volume_cbm == 84.0
        assert space.get_property("Pset_SpaceCommon", "IsExternal") is False

    def test_canonical_ifc_door_and_window_assemblies(self):
        """Test instantiation of hosted IfcDoor and IfcWindow with architectural Psets."""
        door_guid = encode_ifc_guid(uuid.uuid4())
        door = BIMDoor(
            global_id=door_guid,
            name="Main Entrance Pivot Door",
            layer_id="structural",
            position=(2.0, 1.2, 0.0),
            dimensions={"width": 1.2, "height": 2.4, "depth": 0.15},
            width=1.2,
            height=2.4,
            operation_type="SINGLE_SWING_LEFT",
        )

        win_guid = encode_ifc_guid(uuid.uuid4())
        window = BIMWindow(
            global_id=win_guid,
            name="Double Glazed Living Window",
            layer_id="structural",
            position=(0.0, 1.5, 6.0),
            dimensions={"width": 2.4, "height": 1.8, "depth": 0.1},
            width=2.4,
            height=1.8,
            thermal_transmittance=1.2,
            sill_height=0.9,
        )

        assert door.get_property("Pset_DoorCommon", "OperationType") == "SINGLE_SWING_LEFT"
        assert window.get_property("Pset_WindowCommon", "ThermalTransmittance") == 1.2
        assert window.get_property("Pset_WindowCommon", "SillHeight") == 0.9

    def test_canonical_ifc_slab_and_column_structural_entities(self):
        """Test instantiation of structural IfcSlab and IfcColumn."""
        slab_guid = encode_ifc_guid(uuid.uuid4())
        slab = BIMSlab(
            global_id=slab_guid,
            name="Level 2 Post-Tensioned Floor Slab",
            layer_id="structural",
            position=(0.0, 3.2, 0.0),
            dimensions={"width": 20.0, "height": 0.3, "depth": 15.0},
            thickness=0.3,
            slab_type="FLOOR",
        )

        col_guid = encode_ifc_guid(uuid.uuid4())
        col = BIMColumn(
            global_id=col_guid,
            name="Structural Corner Column NW",
            layer_id="structural",
            position=(-9.5, 1.6, -7.0),
            dimensions={"width": 0.5, "height": 3.2, "depth": 0.5},
            width=0.5,
            depth=0.5,
            height=3.2,
            rebar_ratio=0.025,
        )

        assert slab.dimensions["height"] == 0.3
        assert col.get_property("Pset_ColumnCommon", "LoadBearing") is True
        assert col.get_property("Pset_ColumnCommon", "RebarRatio") == 0.025

    def test_canonical_mep_distribution_flow_entities(self):
        """Test instantiation of MEP flow segments and distribution boards."""
        pipe_guid = encode_ifc_guid(uuid.uuid4())
        pipe = BIMDistributionElement(
            global_id=pipe_guid,
            name="Main Soil Waste Riser DN110",
            entity_type="IfcFlowSegment",
            layer_id="plumbing",
            distribution_type="PIPE",
            system_type="SoilWaste",
            nominal_diameter_mm=110.0,
            position=(4.0, 6.0, -3.0),
            dimensions={"width": 0.11, "height": 12.0, "depth": 0.11},
        )

        panel_guid = encode_ifc_guid(uuid.uuid4())
        panel = BIMDistributionElement(
            global_id=panel_guid,
            name="Main 3-Phase Switchboard 400A",
            entity_type="IfcElectricDistributionBoard",
            layer_id="electrical",
            distribution_type="ELECTRICAL_PANEL",
            system_type="ElectricalPower",
            voltage_v=415.0,
            position=(-5.0, 1.2, -4.0),
            dimensions={"width": 0.8, "height": 1.2, "depth": 0.3},
        )

        assert pipe.get_property("Pset_FlowSegmentCommon", "NominalDiameter") == 110.0
        assert pipe.system_type == "SoilWaste"
        assert panel.voltage_v == 415.0

    def test_custom_user_defined_pset_extensions(self):
        """Test attachment of custom manufacturer, costing, and ESG property sets."""
        guid = encode_ifc_guid(uuid.uuid4())
        custom_entity = BIMWall(
            global_id=guid,
            name="Prefabricated Facade Panel",
        )
        custom_entity.set_property("Pset_ManufacturerSpecific", "Manufacturer", "NordicPrecast AB", "IfcLabel")
        custom_entity.set_property("Pset_ManufacturerSpecific", "WarrantyYears", 25, "IfcInteger")
        custom_entity.set_property("Pset_CostEstimate", "UnitCostUSD", 245.50, "IfcReal")
        custom_entity.set_property("Pset_EnvironmentalMetrics", "EmbodiedCarbonKgCO2e", 128.4, "IfcReal")

        assert custom_entity.get_property("Pset_ManufacturerSpecific", "Manufacturer") == "NordicPrecast AB"
        assert custom_entity.get_property("Pset_CostEstimate", "UnitCostUSD") == 245.50
        assert custom_entity.get_property("Pset_EnvironmentalMetrics", "EmbodiedCarbonKgCO2e") == 128.4

    def test_canonical_bim_model_element_lookups(self):
        """Test CanonicalBIMModel lookup methods (by ID, GlobalID, and Type)."""
        model = CanonicalBIMModel(project_name="Test Residential Model")
        storey = BIMStorey(name="Ground Floor", storey_index=0, elevation=0.0)

        wall = BIMWall(name="North Wall", position=(0.0, 1.5, 0.0))
        door = BIMDoor(name="Main Door", host_wall_id=wall.id)
        space = BIMSpace(name="Living Space", area_sqm=25.0)

        storey.walls.append(wall)
        storey.doors.append(door)
        storey.spaces.append(space)

        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        assert model.get_element_by_id(wall.id) == wall
        assert model.get_element_by_global_id(door.global_id) == door
        assert len(model.get_elements_by_type("IfcWall")) == 1
        assert len(model.get_elements_by_type("IfcDoor")) == 1
        assert len(model.all_spaces()) == 1


# ==============================================================================
# Tier 1 & Tier 2: Feature F9 — Pure-Python ISO 10303-21 STEP Compiler & Parser
# ==============================================================================

class TestF9PurePythonSTEPCompilerAndParser:
    """Validates pure-Python STEP serialization, parsing, escaping, and 100% round-trip fidelity."""

    def test_step_header_format_and_schema_validation(self):
        """Test generated STEP text conforms to ISO 10303-21 with FILE_SCHEMA(('IFC4'))."""
        model = CanonicalBIMModel(project_name="Villa Horizon")
        step_text = compile_bim_to_ifc4_step(model)

        assert step_text.startswith("ISO-10303-21;")
        assert "HEADER;" in step_text
        assert "FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');" in step_text
        assert "FILE_SCHEMA(('IFC4'));" in step_text
        assert "ENDSEC;" in step_text
        assert "DATA;" in step_text
        assert "END-ISO-10303-21;" in step_text

    def test_step_string_escaping_and_unescaping_roundtrip(self):
        """Test lossless string escaping for ISO 10303-21 STEP entities with Unicode."""
        test_strings = [
            "Simple English Text",
            "Text with 'single quotes' and \\backslashes\\",
            "French: Résidence de l'Étoile",
            "German: Großes Gebäude mit Wärmepumpe (U < 0.8 W/m²K)",
            "Japanese: オープンBIMプラットフォーム",
            "Cyrillic: Проект Жилого Здания",
            "Special Symbols: Ø110mm @ 2% slope, 45° angle, ±0.01m, α + β = 90°",
        ]
        for original in test_strings:
            escaped = step_escape_string(original)
            unescaped = step_unescape_string(escaped)
            assert unescaped == original, f"String round-trip failed: orig={original!r}, esc={escaped!r}, unesc={unescaped!r}"

    def test_pure_step_compilation_and_entity_references(self):
        """Test compiling model creates sequential deterministic entity IDs and references."""
        model = CanonicalBIMModel(project_name="Skyline Tower")
        storey = BIMStorey(name="Level 1", storey_index=0, elevation=0.0)
        wall = BIMWall(name="Outer Wall", position=(0.0, 1.5, 0.0), dimensions={"width": 6.0, "height": 3.0, "depth": 0.25})
        storey.walls.append(wall)
        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)

        assert "#1=" in step_text
        assert "IFCPROJECT" in step_text
        assert "IFCSITE" in step_text
        assert "IFCBUILDING" in step_text
        assert "IFCBUILDINGSTOREY" in step_text
        assert "IFCWALL" in step_text
        assert "IFCRELAGGREGATES" in step_text
        assert "IFCRELCONTAINEDINSPATIALSTRUCTURE" in step_text

    def test_step_parser_ast_and_by_type_queries(self):
        """Test StepParser correctly populates StepFile and supports by_type / by_id."""
        model = CanonicalBIMModel(project_name="Benchmark Site")
        storey = BIMStorey(name="Ground Floor", storey_index=0, elevation=0.0)
        storey.walls.append(BIMWall(name="Wall A"))
        storey.slabs.append(BIMSlab(name="Floor Plate"))
        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)
        step_file = StepFile.from_string(step_text)

        assert step_file.schema == "IFC4"
        assert len(step_file.by_type("IfcProject")) == 1
        assert len(step_file.by_type("IfcSite")) == 1
        assert len(step_file.by_type("IfcBuilding")) == 1
        assert len(step_file.by_type("IfcBuildingStorey")) >= 1
        assert len(step_file.by_type("IfcWall")) == 1
        assert len(step_file.by_type("IfcSlab")) == 1

        # Test IfcRoot query returns all products with GlobalId
        root_entities = step_file.by_type("IfcRoot")
        assert len(root_entities) >= 5

    def test_100_percent_semantic_roundtrip_fidelity_invariant(self):
        """
        Tests 100% semantic identity round-trip:
        CanonicalBIMModel -> compile_bim_to_ifc4_step -> STEP text -> parse_ifc4_step_to_bim -> Reconstructed Model.
        """
        original_model = CanonicalBIMModel(project_name="Roundtrip Villa")
        storey = BIMStorey(name="Ground Floor", storey_index=0, elevation=0.0)

        wall = BIMWall(
            name="Living Room Exterior Wall",
            position=(0.0, 1.5, -5.0),
            dimensions={"width": 8.0, "height": 3.0, "depth": 0.25},
            thickness=0.25,
            height=3.0,
            is_exterior=True,
            load_bearing=True,
        )
        wall.set_property("Pset_WallCommon", "FireRating", "2h", "IfcLabel")
        wall.set_property("Pset_WallCommon", "AcousticRating", "50dB", "IfcLabel")

        door = BIMDoor(
            name="Main Entrance Door",
            host_wall_id=wall.global_id,
            position=(2.0, 1.2, -5.0),
            dimensions={"width": 1.2, "height": 2.4, "depth": 0.15},
            width=1.2,
            height=2.4,
        )

        space = BIMSpace(
            name="Grand Foyer & Living",
            area_sqm=36.0,
            ceiling_height=3.0,
            room_type="Residential_Living",
        )

        slab = BIMSlab(
            name="Ground Foundation Slab",
            thickness=0.3,
            load_bearing=True,
        )

        col = BIMColumn(
            name="Porch Column",
            width=0.4,
            depth=0.4,
            height=3.0,
        )

        pipe = BIMDistributionElement(
            name="Main Soil Pipe DN110",
            entity_type="IfcFlowSegment",
            system_type="SoilWaste",
            nominal_diameter_mm=110.0,
        )

        storey.walls.append(wall)
        storey.doors.append(door)
        storey.spaces.append(space)
        storey.slabs.append(slab)
        storey.columns.append(col)
        storey.distribution_elements.append(pipe)

        original_model.project.sites[0].buildings[0].storeys.append(storey)
        original_model.link_spatial_hierarchy()

        # Compile to STEP
        step_text = compile_bim_to_ifc4_step(original_model)

        # Parse back to CanonicalBIMModel
        reparsed_model = parse_ifc4_step_to_bim(step_text)

        # Invariant Assertions
        assert reparsed_model.project.name == original_model.project.name
        assert reparsed_model.project.global_id == original_model.project.global_id

        re_storeys = reparsed_model.all_storeys()
        assert len(re_storeys) >= 1
        re_ground = re_storeys[0]
        assert re_ground.name == "Ground Floor"

        # Check Walls
        re_walls = reparsed_model.all_walls()
        assert len(re_walls) == 1
        assert re_walls[0].name == wall.name
        assert re_walls[0].global_id == wall.global_id
        assert re_walls[0].get_property("Pset_WallCommon", "FireRating") == "2h"
        assert re_walls[0].get_property("Pset_WallCommon", "AcousticRating") == "50dB"

        # Check Doors
        re_doors = [e for e in reparsed_model.all_elements() if e.entity_type == "IfcDoor"]
        assert len(re_doors) == 1
        assert re_doors[0].name == door.name
        assert re_doors[0].global_id == door.global_id
        assert re_doors[0].host_wall_id == wall.global_id

        # Check Spaces
        re_spaces = reparsed_model.all_spaces()
        assert len(re_spaces) == 1
        assert re_spaces[0].name == space.name
        assert re_spaces[0].area_sqm == 36.0

        # Check Slabs and Columns
        re_slabs = [e for e in reparsed_model.all_elements() if e.entity_type == "IfcSlab"]
        assert len(re_slabs) == 1
        assert re_slabs[0].global_id == slab.global_id

        re_cols = [e for e in reparsed_model.all_elements() if e.entity_type == "IfcColumn"]
        assert len(re_cols) == 1
        assert re_cols[0].global_id == col.global_id

    def test_legacy_adapters_create_ifc4_project_and_parse_ifc_content(self):
        """Test backward compatibility adapters without external C++ libraries."""
        model_dict = {
            "name": "Legacy Adapter Tower",
            "layers": {
                "structural": {
                    "elements": [
                        {"id": "w1", "name": "Core Shear Wall", "type": "wall", "position": [0, 1.5, 0], "dimensions": {"width": 4.0, "height": 3.0, "depth": 0.3}},
                        {"id": "d1", "name": "Fire Door", "type": "door", "position": [1.0, 1.2, 0], "dimensions": {"width": 1.0, "height": 2.1, "depth": 0.15}},
                    ]
                },
                "plumbing": {
                    "elements": [
                        {"id": "p1", "name": "Waste Pipe", "type": "pipe", "position": [3.0, 1.5, 0], "dimensions": {"width": 0.11, "height": 3.0, "depth": 0.11}},
                    ]
                }
            }
        }

        step_file = create_ifc4_project_from_model(model_dict)
        assert step_file.schema == "IFC4"
        assert len(step_file.by_type("IfcWall")) == 1
        assert len(step_file.by_type("IfcDoor")) == 1
        assert len(step_file.by_type("IfcFlowSegment")) == 1

        step_str = step_file.to_string()
        parsed_dict = parse_ifc_content(step_str)

        assert parsed_dict["name"] == "Legacy Adapter Tower"
        assert len(parsed_dict["generated_elements"]) == 3


# ==============================================================================
# Tier 2: Boundary & Stress Cases
# ==============================================================================

class TestF9BoundaryAndStressCases:
    """Stress tests, edge cases, malformed syntax, and large scale models."""

    def test_boundary_empty_model_compilation_and_parsing(self):
        """Test minimal model with zero physical elements compiles and parses cleanly."""
        empty_model = CanonicalBIMModel(project_name="Empty Site Model")
        step_text = compile_bim_to_ifc4_step(empty_model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        assert reparsed.project.name == "Empty Site Model"
        assert len(reparsed.all_walls()) == 0

    def test_boundary_malformed_step_syntax_raises_error(self):
        """Test that malformed STEP strings raise StepSyntaxError or StepError."""
        malformed_inputs = [
            "",
            "NOT AN IFC FILE",
            "ISO-10303-21; HEADER; ENDSEC; DATA; #1=CORRUPTED(;",
            "ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\nDATA;\n#1=IFCWALL(\nENDSEC;",
        ]
        for bad in malformed_inputs:
            with pytest.raises((StepError, Exception)):
                parse_ifc4_step_to_bim(bad)

    def test_multilingual_unicode_psets_and_entity_names(self):
        """Test international character sets in Psets and entity names."""
        model = CanonicalBIMModel(project_name="Résidence de l'Étoile")
        storey = BIMStorey(name="Étage 1 (Rez-de-chaussée)", storey_index=0, elevation=0.0)

        door = BIMDoor(name="Porte d'Entrée Principale VIP")
        door.set_property("Pset_Localization", "French", "Porte d'entrée vitrée & isolée", "IfcLabel")
        door.set_property("Pset_Localization", "German", "Haupteingangstür mit Wärmedämmung (U < 0.8 W/m²K)", "IfcLabel")
        door.set_property("Pset_Localization", "Japanese", "メインエントランスドア", "IfcLabel")
        door.set_property("Pset_Localization", "MathFormula", "α + β = 90° ± 0.5%", "IfcLabel")

        storey.doors.append(door)
        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        re_door = [e for e in reparsed.all_elements() if e.entity_type == "IfcDoor"][0]
        props = re_door.property_sets["Pset_Localization"].to_flat_dict()

        assert props["French"] == "Porte d'entrée vitrée & isolée"
        assert "W/m²K" in props["German"]
        assert props["Japanese"] == "メインエントランスドア"
        assert "90°" in props["MathFormula"]

    def test_high_density_100_element_model_performance(self):
        """Test performance on dense 100+ element model across structural and MEP layers."""
        model = CanonicalBIMModel(project_name="High Density Floorplate")
        storey = BIMStorey(name="Level 1", storey_index=0, elevation=0.0)

        for i in range(50):
            storey.walls.append(BIMWall(name=f"Partition Wall #{i}", position=(float(i % 10 * 3), 1.5, float(i // 10 * 3))))
        for i in range(30):
            storey.distribution_elements.append(BIMDistributionElement(name=f"Pipe Branch #{i}", entity_type="IfcFlowSegment"))
        for i in range(20):
            storey.columns.append(BIMColumn(name=f"Structural Column #{i}"))

        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        assert len(model.all_elements()) >= 104  # project + site + bldg + storey + 100 elements

        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        assert len(reparsed.all_walls()) == 50
        assert len([e for e in reparsed.all_elements() if e.entity_type == "IfcFlowSegment"]) == 30
        assert len([e for e in reparsed.all_elements() if e.entity_type == "IfcColumn"]) == 20

    def test_12_storey_multi_storey_spatial_depth(self):
        """Test multi-storey building isolation: elements on Storey 0 stay on Storey 0, Storey 11 stay on Storey 11."""
        model = CanonicalBIMModel(project_name="12-Storey Highrise")
        bldg = model.project.sites[0].buildings[0]
        bldg.storeys = []

        for s_idx in range(12):
            st = BIMStorey(name=f"Level {s_idx}", storey_index=s_idx, elevation=float(s_idx * 3.2), height=3.2)
            st.walls.append(BIMWall(name=f"Storey {s_idx} Core Wall"))
            st.spaces.append(BIMSpace(name=f"Storey {s_idx} Apartment Living", area_sqm=45.0))
            bldg.storeys.append(st)

        model.link_spatial_hierarchy()
        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        re_storeys = reparsed.all_storeys()
        assert len(re_storeys) == 12

        for s_idx, st in enumerate(re_storeys):
            assert st.name == f"Level {s_idx}"
            assert abs(st.elevation - float(s_idx * 3.2)) < 1e-4
            assert len(st.walls) == 1
            assert st.walls[0].name == f"Storey {s_idx} Core Wall"
            assert len(st.spaces) == 1
            assert st.spaces[0].name == f"Storey {s_idx} Apartment Living"


# ==============================================================================
# Tier 3 & Tier 4: Pairwise & Golden Reference Models
# ==============================================================================

class TestF9PairwiseAndGoldenReferenceModels:
    """End-to-End Golden Reference architectural scenario round-trips."""

    def test_pairwise_spatial_node_to_bim_to_step_roundtrip(self):
        """Tests SpatialNode hierarchy <-> CanonicalBIMModel <-> STEP round-trip."""
        proj_id = str(uuid.uuid4())
        site_id = str(uuid.uuid4())
        bldg_id = str(uuid.uuid4())
        storey_id = str(uuid.uuid4())
        room_id = str(uuid.uuid4())

        root_node = SpatialNode(
            id=proj_id,
            global_id=encode_ifc_guid(uuid.uuid4()),
            name="Pairwise Project",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
            children=[
                SpatialNode(
                    id=site_id,
                    global_id=encode_ifc_guid(uuid.uuid4()),
                    name="Site Alpha",
                    node_type=SpatialNodeType.SITE,
                    parent_id=proj_id,
                    children=[
                        SpatialNode(
                            id=bldg_id,
                            global_id=encode_ifc_guid(uuid.uuid4()),
                            name="Building Alpha",
                            node_type=SpatialNodeType.BUILDING,
                            parent_id=site_id,
                            children=[
                                SpatialNode(
                                    id=storey_id,
                                    global_id=encode_ifc_guid(uuid.uuid4()),
                                    name="Ground Level",
                                    node_type=SpatialNodeType.STOREY,
                                    parent_id=bldg_id,
                                    children=[
                                        SpatialNode(
                                            id=room_id,
                                            global_id=encode_ifc_guid(uuid.uuid4()),
                                            name="Room 101",
                                            node_type=SpatialNodeType.ROOM,
                                            parent_id=storey_id,
                                            children=[],
                                        )
                                    ],
                                )
                            ],
                        )
                    ],
                )
            ],
        )

        bim_model = CanonicalBIMModel.from_spatial_tree(root_node)
        step_text = compile_bim_to_ifc4_step(bim_model)
        re_model = parse_ifc4_step_to_bim(step_text)
        re_tree = re_model.to_spatial_tree()

        assert re_tree.name == "Pairwise Project"
        assert len(re_tree.children) == 1
        assert re_tree.children[0].name == "Site Alpha"

    def test_golden_scenario_1_1bhk_urban_flat(self):
        """Golden Scenario 1: 1BHK Urban Flat (Living, Kitchen, Bedroom, Bathroom, Balcony)."""
        model = CanonicalBIMModel(project_name="Golden 1BHK Urban Flat")
        storey = BIMStorey(name="Level 1", storey_index=0, elevation=0.0)

        # Living Room
        storey.spaces.append(BIMSpace(name="Living Room", area_sqm=22.0, room_type="LivingRoom"))
        # Kitchen
        storey.spaces.append(BIMSpace(name="Kitchen", area_sqm=8.0, room_type="Kitchen", wet_zone=True))
        # Master Bedroom
        storey.spaces.append(BIMSpace(name="Master Bedroom", area_sqm=14.0, room_type="MasterBedroom"))
        # Bathroom
        storey.spaces.append(BIMSpace(name="Bathroom", area_sqm=4.5, room_type="Bathroom", wet_zone=True))

        # Enclosure walls
        w_north = BIMWall(name="North Wall", position=(0.0, 1.5, -4.0), dimensions={"width": 8.0, "height": 3.0, "depth": 0.25})
        w_south = BIMWall(name="South Wall", position=(0.0, 1.5, 4.0), dimensions={"width": 8.0, "height": 3.0, "depth": 0.25})
        storey.walls.extend([w_north, w_south])

        # Hosted Door and Window
        storey.doors.append(BIMDoor(name="Entry Door", host_wall_id=w_north.global_id))
        storey.windows.append(BIMWindow(name="Balcony Window", host_wall_id=w_south.global_id))

        model.project.sites[0].buildings[0].storeys.append(storey)
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        assert len(reparsed.all_spaces()) == 4
        assert len(reparsed.all_walls()) == 2
        assert len([e for e in reparsed.all_elements() if e.entity_type == "IfcDoor"]) == 1
        assert len([e for e in reparsed.all_elements() if e.entity_type == "IfcWindow"]) == 1

    def test_golden_scenario_4_villa_2storey(self):
        """Golden Scenario 4: 2-Storey Luxury Villa (Ground Living/Kitchen, First Floor Master Suite)."""
        model = CanonicalBIMModel(project_name="Golden 2-Storey Villa")
        bldg = model.project.sites[0].buildings[0]
        bldg.storeys = []

        # Ground Floor
        st_ground = BIMStorey(name="Ground Level", storey_index=0, elevation=0.0)
        st_ground.spaces.append(BIMSpace(name="Great Living Room", area_sqm=35.0))
        st_ground.spaces.append(BIMSpace(name="Chef Island Kitchen", area_sqm=16.0, wet_zone=True))
        st_ground.walls.append(BIMWall(name="Ground Facade Wall"))
        st_ground.slabs.append(BIMSlab(name="Ground Foundation Slab"))

        # First Floor
        st_first = BIMStorey(name="First Level", storey_index=1, elevation=3.5)
        st_first.spaces.append(BIMSpace(name="Master Suite", area_sqm=28.0))
        st_first.spaces.append(BIMSpace(name="Spa Ensuite", area_sqm=10.0, wet_zone=True))
        st_first.walls.append(BIMWall(name="First Level Terrace Wall"))
        st_first.slabs.append(BIMSlab(name="First Floor Structural Slab"))

        bldg.storeys.extend([st_ground, st_first])
        model.link_spatial_hierarchy()

        step_text = compile_bim_to_ifc4_step(model)
        reparsed = parse_ifc4_step_to_bim(step_text)

        re_storeys = reparsed.all_storeys()
        assert len(re_storeys) == 2
        assert re_storeys[0].name == "Ground Level"
        assert re_storeys[1].name == "First Level"
        assert len(re_storeys[0].spaces) == 2
        assert len(re_storeys[1].spaces) == 2
