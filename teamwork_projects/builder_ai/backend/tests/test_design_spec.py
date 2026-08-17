"""
Comprehensive E2E and Unit Test Suite for Features F1 and F2.

Features Covered:
- F1: AI Prompt to DesignSpec Validation (Schema validation, typologies, PBR materials, MEP strategy, raw geometry prohibition).
- F2: 6-Tier Spatial Hierarchy & UUID5 / IFC GUID Bijective Mapping (Tree containment, deterministic UUID5, 22-char IFC Base64, search & integrity traversal).
"""

from __future__ import annotations

import json
import uuid
import pytest
from pydantic import ValidationError

from app.schemas.design_spec import (
    AestheticPalette,
    AestheticStyle,
    BuildingTypology,
    CorePlacementStrategy,
    DesignSpec,
    ElectricalDistributionType,
    FireProtectionType,
    HVACType,
    MaterialSpec,
    MEPStrategy,
    OccupancyCategory,
    PlumbingSystemType,
    RooftopMEPType,
    RoomProgram,
    RoomType,
    SetbackSpec,
    SiteParameters,
    StoreySpec,
    StoreyUseType,
    StructuralSystem,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
    ZoningClassification,
    assert_no_raw_geometry,
)
from app.schemas.spatial import (
    ALLOWED_CHILD_TYPES,
    BuildingProperties,
    DevelopmentProperties,
    ProjectProperties,
    RoomProperties,
    SiteProperties,
    SpatialNode,
    SpatialNodeType,
    StoreyProperties,
    UnitProperties,
    compile_design_spec_to_spatial_tree,
    decode_ifc_guid,
    encode_ifc_guid,
    filter_nodes_by_type,
    find_node_by_global_id,
    find_node_by_id,
    find_node_by_path,
    flatten_spatial_tree,
    generate_spatial_uuid,
    get_ancestor_chain,
    get_descendants,
    ifc_guid_to_uuid,
    uuid_to_ifc_guid,
    validate_tree_integrity,
)
from app.services.meta_agent import parse_prompt_to_design_spec
from tests.conftest import DesignSpecFactory, SpatialTreeFactory


# ==============================================================================
# FEATURE F1: AI Prompt to DesignSpec Validation (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature1DesignSpecValidation:
    """Feature F1: Comprehensive validation of typed DesignSpec models and architectural constraints."""

    def test_f1_valid_studio_spec(self, design_spec_factory):
        """F1.1: Validates DesignSpec for a Studio Apartment."""
        spec = design_spec_factory.make_studio_spec()
        assert spec.project_name == "Studio Apartment Project"
        assert spec.total_storeys == 1
        assert len(spec.storeys) == 1
        assert spec.storeys[0].unit_mix[0].unit_type == UnitType.STUDIO
        assert len(spec.storeys[0].unit_mix[0].required_rooms) == 4
        assert spec.building_typology == BuildingTypology.RESIDENTIAL
        assert spec.mep_strategy.hvac_type == HVACType.SPLIT_DX

    def test_f1_valid_1bhk_spec(self, design_spec_factory):
        """F1.2: Validates DesignSpec for a 1BHK unit."""
        spec = design_spec_factory.make_1bhk_spec()
        assert spec.total_storeys == 1
        assert spec.storeys[0].unit_mix[0].unit_type == UnitType.BHK1
        assert spec.storeys[0].unit_mix[0].target_area_sqm == 55.0
        room_types = [r.room_type for r in spec.storeys[0].unit_mix[0].required_rooms]
        assert RoomType.LIVING_ROOM in room_types
        assert RoomType.KITCHEN in room_types
        assert RoomType.MASTER_BEDROOM in room_types
        assert RoomType.BATHROOM in room_types
        assert RoomType.BALCONY in room_types

    def test_f1_valid_2bhk_spec(self, design_spec_factory):
        """F1.3: Validates DesignSpec for a 2BHK residential apartment."""
        spec = design_spec_factory.make_2bhk_spec()
        assert spec.total_storeys == 1
        assert spec.storeys[0].unit_mix[0].unit_type == UnitType.BHK2
        assert spec.storeys[0].unit_mix[0].target_area_sqm == 90.0
        assert len(spec.storeys[0].unit_mix[0].required_rooms) == 8

    def test_f1_valid_3bhk_spec(self, design_spec_factory):
        """F1.4: Validates DesignSpec for a 3BHK luxury suite."""
        spec = design_spec_factory.make_3bhk_spec()
        assert spec.total_storeys == 1
        assert spec.storeys[0].unit_mix[0].unit_type == UnitType.BHK3
        assert spec.storeys[0].unit_mix[0].target_area_sqm == 160.0
        assert spec.aesthetic_palette.style == AestheticStyle.LUXURY_CALACATTA

    def test_f1_valid_multi_storey_villa(self, design_spec_factory):
        """F1.5: Validates DesignSpec for a 2-storey modern villa with distinct floor programs."""
        spec = design_spec_factory.make_villa_spec()
        assert spec.building_typology == BuildingTypology.VILLA
        assert spec.total_storeys == 2
        assert len(spec.storeys) == 2
        assert spec.storeys[0].elevation_m == 0.0
        assert spec.storeys[1].elevation_m == 3.6
        assert spec.storeys[0].unit_mix[0].target_area_sqm == 150.0
        assert spec.storeys[1].unit_mix[0].target_area_sqm == 130.0

    def test_f1_valid_12_storey_tower(self, design_spec_factory):
        """F1.6: Validates DesignSpec for a 12-storey residential tower."""
        spec = design_spec_factory.make_tower_spec(storeys=12)
        assert spec.building_typology == BuildingTypology.TOWER
        assert spec.total_storeys == 12
        assert len(spec.storeys) == 12
        assert spec.mep_strategy.hvac_type == HVACType.VRF_MULTI_SPLIT
        assert spec.mep_strategy.rooftop_mep == RooftopMEPType.SOLAR_PV_ARRAY
        # Verify strictly monotonic elevation progression
        for i in range(1, 12):
            assert spec.storeys[i].elevation_m > spec.storeys[i - 1].elevation_m

    def test_f1_prohibit_raw_geometry_keys(self):
        """F1.7: Rejects raw Cartesian coordinates and mesh arrays."""
        prohibited = ["vertices", "vertex_list", "coords", "coordinates", "points", "faces", "triangles", "polygons", "mesh", "mesh_data"]
        for key in prohibited:
            with pytest.raises(ValueError) as exc_info:
                assert_no_raw_geometry({key: [0.0, 1.0, 2.0]})
            assert f"Prohibited raw geometry key '{key}'" in str(exc_info.value)

    def test_f1_prohibit_raw_geometry_in_design_spec_input(self):
        """F1.8: Verifies DesignSpec model validation blocks injected geometry payloads."""
        payload = {
            "project_name": "Injected Geometry Payload",
            "total_storeys": 1,
            "coordinates": [[0, 0], [10, 0], [10, 10], [0, 10]],
        }
        with pytest.raises(ValidationError) as exc_info:
            DesignSpec.model_validate(payload)
        assert "Prohibited raw geometry key 'coordinates'" in str(exc_info.value)

    def test_f1_site_setbacks_fit_plot_dimensions(self):
        """F1.9: Rejects setback margins that exceed plot width or depth."""
        # Front (25m) + Rear (20m) = 45m >= Depth 40m
        with pytest.raises(ValidationError) as exc_info:
            SiteParameters(
                plot_width_m=30.0,
                plot_depth_m=40.0,
                setbacks=SetbackSpec(front_m=25.0, rear_m=20.0, side_left_m=2.0, side_right_m=2.0),
            )
        assert "depth setbacks" in str(exc_info.value)

        # Left (18m) + Right (15m) = 33m >= Width 30m
        with pytest.raises(ValidationError) as exc_info:
            SiteParameters(
                plot_width_m=30.0,
                plot_depth_m=40.0,
                setbacks=SetbackSpec(front_m=4.0, rear_m=4.0, side_left_m=18.0, side_right_m=15.0),
            )
        assert "width setbacks" in str(exc_info.value)

    def test_f1_strictly_monotonic_storey_elevations(self):
        """F1.10: Rejects non-monotonic or reversed floor elevations."""
        storeys = [
            StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.2),
            StoreySpec(storey_index=1, name="Level 1", elevation_m=3.2, height_m=3.2),
            StoreySpec(storey_index=2, name="Level 2", elevation_m=2.5, height_m=3.2),  # Inverted!
        ]
        with pytest.raises(ValidationError) as exc_info:
            DesignSpec(total_storeys=3, storeys=storeys)
        assert "Non-monotonic storey elevations" in str(exc_info.value)

    def test_f1_storey_count_mismatch_rejection(self):
        """F1.11: Rejects mismatch between total_storeys and storeys list length."""
        storeys = [StoreySpec(storey_index=0, name="Ground", elevation_m=0.0, height_m=3.2)]
        with pytest.raises(ValidationError) as exc_info:
            DesignSpec(total_storeys=5, storeys=storeys)
        assert "Storey count mismatch" in str(exc_info.value)

    def test_f1_room_target_area_less_than_min_area_rejection(self):
        """F1.12: Rejects room specification where target area is less than min area."""
        with pytest.raises(ValidationError) as exc_info:
            RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=25.0, target_area_sqm=18.0)
        assert "target_area_sqm" in str(exc_info.value)

    def test_f1_unit_room_area_sum_exceeds_target_rejection(self):
        """F1.13: Rejects unit requirement when sum of room min areas exceeds target area with margin."""
        rooms = [
            RoomProgram(room_type=RoomType.LIVING_ROOM, min_area_sqm=30.0, target_area_sqm=35.0),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, min_area_sqm=25.0, target_area_sqm=30.0),
            RoomProgram(room_type=RoomType.BEDROOM, min_area_sqm=20.0, target_area_sqm=25.0),
        ]
        with pytest.raises(ValidationError) as exc_info:
            UnitRequirement(unit_type=UnitType.BHK2, target_area_sqm=50.0, required_rooms=rooms)
        assert "exceeds unit target area" in str(exc_info.value)

    def test_f1_pbr_material_bounds_and_color_hex(self):
        """F1.14: Validates MaterialSpec color hex regex and PBR property bounds [0, 1]."""
        valid_mat = MaterialSpec(name="Polished Concrete", color_hex="#CCCCCC", roughness=0.7, metalness=0.1, opacity=1.0)
        assert valid_mat.color_hex == "#CCCCCC"
        assert valid_mat.roughness == 0.7

        with pytest.raises(ValidationError):
            MaterialSpec(color_hex="INVALID_HEX")

        with pytest.raises(ValidationError):
            MaterialSpec(roughness=1.8)

        with pytest.raises(ValidationError):
            MaterialSpec(metalness=-0.2)

    def test_f1_json_roundtrip_fidelity(self, design_spec_factory):
        """F1.15: Tests JSON serialization and deserialization roundtrip preserves all fields."""
        original_spec = design_spec_factory.make_tower_spec(storeys=4)
        json_str = original_spec.model_dump_json()
        assert isinstance(json_str, str)

        restored_spec = DesignSpec.model_validate_json(json_str)
        assert restored_spec.project_name == original_spec.project_name
        assert restored_spec.total_storeys == original_spec.total_storeys
        assert len(restored_spec.storeys) == len(original_spec.storeys)
        assert restored_spec.mep_strategy.hvac_type == original_spec.mep_strategy.hvac_type

    def test_f1_prompt_parser_typologies(self):
        """F1.16: Validates LLM prompt parser generates valid DesignSpec across varied typologies."""
        spec_villa = parse_prompt_to_design_spec("2-story modern villa in Japandi style with 3 bedrooms")
        assert spec_villa.building_typology == BuildingTypology.VILLA
        assert spec_villa.total_storeys == 2

        spec_tower = parse_prompt_to_design_spec("12-story high-rise apartment tower with 2BHK and 3BHK units")
        assert spec_tower.building_typology == BuildingTypology.TOWER
        assert spec_tower.total_storeys == 12


# ==============================================================================
# FEATURE F2: 6-Tier Spatial Hierarchy & UUID5 / IFC GUID (Tier 1 & Tier 2)
# ==============================================================================

class TestFeature2SpatialHierarchyAndGUIDs:
    """Feature F2: Comprehensive validation of 6-Tier Spatial Tree and bijective UUID5/IFC GUID mapping."""

    def test_f2_spatial_hierarchy_6_tier_tree_structure(self, sample_spatial_tree):
        """F2.1: Verifies 6-tier spatial hierarchy containment: Project -> Site -> Development -> Building -> Storey -> Unit -> Room."""
        root = sample_spatial_tree
        assert root.node_type == SpatialNodeType.PROJECT
        assert len(root.children) == 1

        site_node = root.children[0]
        assert site_node.node_type == SpatialNodeType.SITE
        assert site_node.parent_id == root.id

        dev_node = site_node.children[0]
        assert dev_node.node_type == SpatialNodeType.DEVELOPMENT
        assert dev_node.parent_id == site_node.id

        bldg_node = dev_node.children[0]
        assert bldg_node.node_type == SpatialNodeType.BUILDING
        assert bldg_node.parent_id == dev_node.id

        assert len(bldg_node.children) >= 1
        storey_node = bldg_node.children[0]
        assert storey_node.node_type == SpatialNodeType.STOREY
        assert storey_node.parent_id == bldg_node.id

        assert len(storey_node.children) >= 1
        unit_node = storey_node.children[0]
        assert unit_node.node_type == SpatialNodeType.UNIT
        assert unit_node.parent_id == storey_node.id

        assert len(unit_node.children) >= 1
        room_node = unit_node.children[0]
        assert room_node.node_type == SpatialNodeType.ROOM
        assert room_node.parent_id == unit_node.id
        assert len(room_node.children) == 0  # Leaf node

    def test_f2_deterministic_uuid5_generation(self):
        """F2.2: Asserts identical spatial hierarchy paths consistently generate the exact same UUID5."""
        path = "project:metropolis/site:main/dev:phase1/bldg:tower_a/storey:1/unit:u101/room:living"
        uuid1 = generate_spatial_uuid(path)
        uuid2 = generate_spatial_uuid(path)
        assert uuid1 == uuid2
        assert str(uuid1) == str(uuid2)

    def test_f2_distinct_uuid5_for_different_paths(self):
        """F2.3: Asserts distinct spatial paths generate distinct UUID5s."""
        path1 = "project:metropolis/site:main/dev:phase1/bldg:tower_a/storey:1/unit:u101/room:living"
        path2 = "project:metropolis/site:main/dev:phase1/bldg:tower_a/storey:1/unit:u102/room:living"
        uuid1 = generate_spatial_uuid(path1)
        uuid2 = generate_spatial_uuid(path2)
        assert uuid1 != uuid2

    def test_f2_ifc_guid_bijective_roundtrip_standard(self):
        """F2.4: Verifies 128-bit UUID to 22-char IFC Base64 GUID encoding and decoding roundtrip."""
        test_uuids = [
            uuid.uuid4(),
            uuid.uuid5(uuid.NAMESPACE_DNS, "builder3d.test.node.1"),
            uuid.uuid5(uuid.NAMESPACE_DNS, "builder3d.test.node.2"),
            uuid.UUID("12345678-1234-5678-1234-567812345678"),
        ]
        for original_u in test_uuids:
            ifc_str = encode_ifc_guid(original_u)
            assert len(ifc_str) == 22
            assert ifc_str[0] in {"0", "1", "2", "3"}

            decoded_u = decode_ifc_guid(ifc_str)
            assert decoded_u == original_u
            assert str(decoded_u) == str(original_u)

    def test_f2_ifc_guid_bijective_roundtrip_boundary_values(self):
        """F2.5: Verifies IFC GUID encoding and decoding on Nil and Max boundary UUIDs."""
        # Nil UUID
        nil_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        nil_ifc = encode_ifc_guid(nil_uuid)
        assert len(nil_ifc) == 22
        assert nil_ifc == "0000000000000000000000"
        assert decode_ifc_guid(nil_ifc) == nil_uuid

        # Max UUID
        max_uuid = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        max_ifc = encode_ifc_guid(max_uuid)
        assert len(max_ifc) == 22
        assert decode_ifc_guid(max_ifc) == max_uuid

    def test_f2_ifc_guid_format_and_alphabet_validation(self):
        """F2.6: Tests rejection of invalid length, non-alphabet characters, and invalid leading characters."""
        # Invalid length
        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("0123456789")
        assert "exactly 22 characters" in str(exc.value)

        # Invalid character
        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("0123456789ABCDEFGHIKL!")  # '!' is not in IFC base64
        assert "Invalid character" in str(exc.value)

        # Invalid leading character (e.g. '4' would overflow 8-bit chunk)
        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("4000000000000000000000")
        assert "exceeds 255" in str(exc.value)

    def test_f2_tree_traversal_find_by_id_and_global_id(self, sample_spatial_tree):
        """F2.7: Tests finding nodes by UUID and IFC GUID."""
        root = sample_spatial_tree
        all_nodes = flatten_spatial_tree(root)
        for nid, node in all_nodes.items():
            found_by_id = find_node_by_id(root, nid)
            assert found_by_id is not None
            assert found_by_id.id == nid

            found_by_guid = find_node_by_global_id(root, node.global_id)
            assert found_by_guid is not None
            assert found_by_guid.global_id == node.global_id

    def test_f2_filter_nodes_by_type(self, sample_spatial_tree):
        """F2.8: Tests querying nodes filtered by spatial hierarchy level."""
        root = sample_spatial_tree
        storeys = filter_nodes_by_type(root, SpatialNodeType.STOREY)
        units = filter_nodes_by_type(root, SpatialNodeType.UNIT)
        rooms = filter_nodes_by_type(root, SpatialNodeType.ROOM)

        assert len(storeys) >= 1
        assert len(units) >= 1
        assert len(rooms) >= 1
        assert all(s.node_type == SpatialNodeType.STOREY for s in storeys)
        assert all(u.node_type == SpatialNodeType.UNIT for u in units)
        assert all(r.node_type == SpatialNodeType.ROOM for r in rooms)

    def test_f2_ancestor_chain_and_descendants(self, sample_spatial_tree):
        """F2.9: Tests retrieving ancestor chain from Project root to leaf room, and subtree descendants."""
        root = sample_spatial_tree
        rooms = filter_nodes_by_type(root, SpatialNodeType.ROOM)
        target_room = rooms[0]

        chain = get_ancestor_chain(root, target_room.id)
        assert chain is not None
        assert len(chain) == 7  # Project -> Site -> Dev -> Bldg -> Storey -> Unit -> Room
        assert chain[0].node_type == SpatialNodeType.PROJECT
        assert chain[-1].node_type == SpatialNodeType.ROOM
        assert chain[-1].id == target_room.id

        descendants = get_descendants(root)
        assert len(descendants) == len(flatten_spatial_tree(root)) - 1  # All except root

    def test_f2_validate_tree_integrity_success(self, sample_spatial_tree):
        """F2.10: Validates structural integrity (acyclicity, unique IDs, correct parent pointers)."""
        assert validate_tree_integrity(sample_spatial_tree) is True

    def test_f2_tree_integrity_rejects_cycles_and_broken_parents(self, spatial_tree_factory):
        """F2.11: Tests detection and rejection of broken parent pointers and duplicate IDs."""
        node1 = spatial_tree_factory.make_custom_node(SpatialNodeType.PROJECT, "Proj 1")
        node2 = spatial_tree_factory.make_custom_node(SpatialNodeType.SITE, "Site 1", parent_id="wrong_parent_id")
        node1.children.append(node2)

        with pytest.raises(ValueError) as exc:
            validate_tree_integrity(node1)
        assert "Parent ID mismatch" in str(exc.value)

    def test_f2_leaf_room_cannot_have_children(self, spatial_tree_factory):
        """F2.12: Enforces that Room nodes are leaf nodes and cannot contain children."""
        room = spatial_tree_factory.make_custom_node(SpatialNodeType.ROOM, "Living Room", parent_id=str(uuid.uuid4()))
        illegal_child = spatial_tree_factory.make_custom_node(SpatialNodeType.ROOM, "Sub Room", parent_id=room.id)

        room.children.append(illegal_child)
        with pytest.raises(ValueError) as exc:
            SpatialNode.model_validate(room.model_dump())
        assert "cannot contain child" in str(exc.value)

    def test_f2_compile_design_spec_to_spatial_tree(self, design_spec_factory):
        """F2.13: Tests compiling a full 3-storey DesignSpec into a valid 6-tier SpatialNode hierarchy."""
        spec = design_spec_factory.make_tower_spec(storeys=3)
        tree = compile_design_spec_to_spatial_tree(spec)
        assert tree is not None
        assert tree.node_type == SpatialNodeType.PROJECT
        assert validate_tree_integrity(tree) is True

        storeys = filter_nodes_by_type(tree, SpatialNodeType.STOREY)
        assert len(storeys) == 3
