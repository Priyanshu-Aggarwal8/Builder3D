"""
Comprehensive Test Suites for Canonical Spatial Hierarchy and Bijective IFC GUID Engine.

Verifies:
1. Pure-Python 100% bijective 128-bit UUID <-> 22-character IFC Base64 GUID conversions.
   - 10,000+ random UUIDs fuzzing test.
   - Nil UUID (0000...0) and Max UUID (ffff...f) boundary tests.
   - Invalid string length, illegal character set, and chunk 0 overflow rejections.
2. Deterministic UUID5 generation and path reproducibility.
3. 6-Tier Spatial Hierarchy tree creation, parent-child transitions, and integrity validation.
4. Tree traversal, lookup, filtering, ancestor chain, and flattening operations.
5. Strict containment violation rejections (illegal child types, broken parent IDs, cycles).
6. Compilation of DesignSpec into valid SpatialNode trees.
"""

import uuid
import pytest
from pydantic import ValidationError

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
from app.schemas.spatial import (
    IFC_BASE64_CHARS,
    IFC_BASE64_DICT,
    NAMESPACE_BUILDER_AI,
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


class TestIFCGUIDBijectivity:
    """Rigorous mathematical tests for the 22-char IFC Base64 GUID converter."""

    def test_known_boundary_vectors(self):
        """Test exact known boundary vectors (Nil and Max UUIDs)."""
        # Nil UUID
        nil_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
        nil_guid = encode_ifc_guid(nil_uuid)
        assert nil_guid == "0000000000000000000000"
        assert decode_ifc_guid(nil_guid) == nil_uuid

        # Max UUID
        max_uuid = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        max_guid = encode_ifc_guid(max_uuid)
        assert max_guid == "3$$$$$$$$$$$$$$$$$$$$$"
        assert decode_ifc_guid(max_guid) == max_uuid

    def test_random_uuid_bijectivity_10000_iterations(self):
        """
        Fuzz test: Generates 10,000 random RFC 4122 UUIDs and verifies
        exact 100% lossless round-trip bijection.
        """
        for _ in range(10000):
            original_uuid = uuid.uuid4()
            guid = encode_ifc_guid(original_uuid)

            # Assert invariants on encoded GUID
            assert len(guid) == 22
            assert guid[0] in {"0", "1", "2", "3"}
            for char in guid:
                assert char in IFC_BASE64_DICT

            # Assert exact inverse decode
            decoded_uuid = decode_ifc_guid(guid)
            assert decoded_uuid == original_uuid

    def test_string_and_uuid_input_overloads(self):
        """Verify encoder handles both str and uuid.UUID inputs identically."""
        sample_uuid = uuid.uuid4()
        guid1 = encode_ifc_guid(sample_uuid)
        guid2 = encode_ifc_guid(str(sample_uuid))
        assert guid1 == guid2

    def test_malformed_ifc_guid_length_rejections(self):
        """Verify decoder rejects strings not exactly 22 characters."""
        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("0123456789")  # 10 chars
        assert "22 characters" in str(exc.value)

        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("00000000000000000000000")  # 23 chars
        assert "22 characters" in str(exc.value)

        with pytest.raises(ValueError) as exc:
            decode_ifc_guid("")
        assert "22 characters" in str(exc.value)

    def test_malformed_ifc_guid_character_rejections(self):
        """Verify decoder rejects characters not in standard IFC Base64 alphabet."""
        invalid_chars = ["!", "@", "#", "%", "^", "&", "*", "(", ")", "-", "+", "=", "/"]
        for bad_c in invalid_chars:
            bad_guid = f"000000000000000000000{bad_c}"
            with pytest.raises(ValueError) as exc:
                decode_ifc_guid(bad_guid)
            assert "Invalid character" in str(exc.value)

    def test_first_char_overflow_rejections(self):
        """
        Verify decoder rejects 22-char strings whose first character is not '0', '1', '2', '3'.
        Values '4' through '$' cause chunk 0 (8-bit) overflow > 255.
        """
        overflow_chars = ["4", "5", "9", "A", "Z", "a", "z", "_", "$"]
        for c in overflow_chars:
            overflow_guid = f"{c}000000000000000000000"
            with pytest.raises(ValueError) as exc:
                decode_ifc_guid(overflow_guid)
            assert "exceeds 255" in str(exc.value) or "first character" in str(exc.value)


class TestDeterministicUUID5PathAddressing:
    """Tests deterministic UUID5 hierarchical URI addressing."""

    def test_uuid5_determinism(self):
        path = "project:skyline_tower/site:main/dev:phase1/bldg:tower_a/storey:1/unit:101/room:living"
        id1 = generate_spatial_uuid(path)
        id2 = generate_spatial_uuid(path)
        assert id1 == id2
        assert id1.version == 5

    def test_distinct_paths_generate_distinct_uuids(self):
        path1 = "project:skyline/site:main/dev:phase1/bldg:tower/storey:1/unit:101/room:living"
        path2 = "project:skyline/site:main/dev:phase1/bldg:tower/storey:1/unit:101/room:bedroom"
        id1 = generate_spatial_uuid(path1)
        id2 = generate_spatial_uuid(path2)
        assert id1 != id2

    def test_empty_path_raises_error(self):
        with pytest.raises(ValueError):
            generate_spatial_uuid("")


class TestCanonicalSpatialHierarchyTree:
    """Tests 6-tier hierarchy building, traversal, and validation."""

    def _build_sample_hierarchy(self) -> SpatialNode:
        """Helper building a valid 6-tier Project->Site->Dev->Bldg->Storey->Unit->Room tree."""
        proj_path = "project:test_project"
        proj_id = str(generate_spatial_uuid(proj_path))
        proj_guid = encode_ifc_guid(proj_id)

        site_path = f"{proj_path}/site:main"
        site_id = str(generate_spatial_uuid(site_path))
        site_guid = encode_ifc_guid(site_id)

        dev_path = f"{site_path}/dev:phase1"
        dev_id = str(generate_spatial_uuid(dev_path))
        dev_guid = encode_ifc_guid(dev_id)

        bldg_path = f"{dev_path}/bldg:main"
        bldg_id = str(generate_spatial_uuid(bldg_path))
        bldg_guid = encode_ifc_guid(bldg_id)

        storey_path = f"{bldg_path}/storey:0"
        storey_id = str(generate_spatial_uuid(storey_path))
        storey_guid = encode_ifc_guid(storey_id)

        unit_path = f"{storey_path}/unit:101"
        unit_id = str(generate_spatial_uuid(unit_path))
        unit_guid = encode_ifc_guid(unit_id)

        room_path = f"{unit_path}/room:living_0"
        room_id = str(generate_spatial_uuid(room_path))
        room_guid = encode_ifc_guid(room_id)

        room_node = SpatialNode(
            id=room_id,
            global_id=room_guid,
            name="Living Room",
            node_type=SpatialNodeType.ROOM,
            parent_id=unit_id,
            canonical_path=room_path,
            properties=RoomProperties(room_type=RoomType.LIVING_ROOM, area_sqm=24.0).model_dump(),
        )

        unit_node = SpatialNode(
            id=unit_id,
            global_id=unit_guid,
            name="Unit 101",
            node_type=SpatialNodeType.UNIT,
            parent_id=storey_id,
            canonical_path=unit_path,
            properties=UnitProperties(unit_type=UnitType.BHK2, unit_number="101", target_area_sqm=90.0).model_dump(),
            children=[room_node],
        )

        storey_node = SpatialNode(
            id=storey_id,
            global_id=storey_guid,
            name="Ground Floor",
            node_type=SpatialNodeType.STOREY,
            parent_id=bldg_id,
            canonical_path=storey_path,
            properties=StoreyProperties(storey_index=0, elevation=0.0, height=3.2).model_dump(),
            children=[unit_node],
        )

        bldg_node = SpatialNode(
            id=bldg_id,
            global_id=bldg_guid,
            name="Main Building",
            node_type=SpatialNodeType.BUILDING,
            parent_id=dev_id,
            canonical_path=bldg_path,
            properties=BuildingProperties(typology=BuildingTypology.RESIDENTIAL, total_storeys=1).model_dump(),
            children=[storey_node],
        )

        dev_node = SpatialNode(
            id=dev_id,
            global_id=dev_guid,
            name="Phase 1",
            node_type=SpatialNodeType.DEVELOPMENT,
            parent_id=site_id,
            canonical_path=dev_path,
            properties=DevelopmentProperties().model_dump(),
            children=[bldg_node],
        )

        site_node = SpatialNode(
            id=site_id,
            global_id=site_guid,
            name="Main Site",
            node_type=SpatialNodeType.SITE,
            parent_id=proj_id,
            canonical_path=site_path,
            properties=SiteProperties().model_dump(),
            children=[dev_node],
        )

        project_node = SpatialNode(
            id=proj_id,
            global_id=proj_guid,
            name="Test Project",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
            canonical_path=proj_path,
            properties=ProjectProperties().model_dump(),
            children=[site_node],
        )

        return project_node

    def test_full_spatial_tree_traversal_and_queries(self):
        root = self._build_sample_hierarchy()
        assert validate_tree_integrity(root) is True

        # Find by ID
        found_root = find_node_by_id(root, root.id)
        assert found_root is not None
        assert found_root.name == "Test Project"

        # Find by global_id
        found_by_guid = find_node_by_global_id(root, root.global_id)
        assert found_by_guid is not None
        assert found_by_guid.id == root.id

        # Find by path
        found_by_path = find_node_by_path(root, root.canonical_path)
        assert found_by_path is not None
        assert found_by_path.id == root.id

        # Filter by type
        rooms = filter_nodes_by_type(root, SpatialNodeType.ROOM)
        assert len(rooms) == 1
        assert rooms[0].name == "Living Room"

        storeys = filter_nodes_by_type(root, SpatialNodeType.STOREY)
        assert len(storeys) == 1

        # Ancestor chain
        room_node = rooms[0]
        ancestors = get_ancestor_chain(root, room_node.id)
        assert ancestors is not None
        assert len(ancestors) == 7  # Project, Site, Dev, Bldg, Storey, Unit, Room
        assert [n.node_type for n in ancestors] == [
            SpatialNodeType.PROJECT,
            SpatialNodeType.SITE,
            SpatialNodeType.DEVELOPMENT,
            SpatialNodeType.BUILDING,
            SpatialNodeType.STOREY,
            SpatialNodeType.UNIT,
            SpatialNodeType.ROOM,
        ]

        # Descendants
        descendants = get_descendants(root)
        assert len(descendants) == 6

        # Flatten tree
        flattened = flatten_spatial_tree(root)
        assert len(flattened) == 7


class TestSpatialHierarchyRejections:
    """Tests rejection of invalid hierarchy transitions, broken pointers, and cycles."""

    def test_project_with_parent_id_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SpatialNode(
                id=str(uuid.uuid4()),
                global_id="0000000000000000000000",
                name="Bad Root",
                node_type=SpatialNodeType.PROJECT,
                parent_id=str(uuid.uuid4()),  # Invalid!
            )
        assert "parent_id=None" in str(exc.value)

    def test_non_root_with_none_parent_rejected(self):
        with pytest.raises(ValidationError) as exc:
            SpatialNode(
                id=str(uuid.uuid4()),
                global_id="0000000000000000000000",
                name="Orphan Site",
                node_type=SpatialNodeType.SITE,
                parent_id=None,  # Invalid!
            )
        assert "must have a parent_id" in str(exc.value)

    def test_illegal_child_transition_rejected(self):
        """Test attaching Room directly under Project raises ValidationError."""
        proj_id = str(uuid.uuid4())
        room_id = str(uuid.uuid4())
        room_node = SpatialNode(
            id=room_id,
            global_id=encode_ifc_guid(room_id),
            name="Orphan Room",
            node_type=SpatialNodeType.ROOM,
            parent_id=proj_id,
        )
        with pytest.raises(ValidationError) as exc:
            SpatialNode(
                id=proj_id,
                global_id=encode_ifc_guid(proj_id),
                name="Project",
                node_type=SpatialNodeType.PROJECT,
                parent_id=None,
                children=[room_node],  # Invalid child type for Project!
            )
        assert "Illegal hierarchy" in str(exc.value)

    def test_broken_parent_reference_rejected(self):
        """Test child whose parent_id does not match parent's id."""
        site_id = str(uuid.uuid4())
        dev_id = str(uuid.uuid4())
        dev_node = SpatialNode(
            id=dev_id,
            global_id=encode_ifc_guid(dev_id),
            name="Dev",
            node_type=SpatialNodeType.DEVELOPMENT,
            parent_id=str(uuid.uuid4()),  # Mismatched parent ID!
        )
        with pytest.raises(ValidationError) as exc:
            SpatialNode(
                id=site_id,
                global_id=encode_ifc_guid(site_id),
                name="Site",
                node_type=SpatialNodeType.SITE,
                parent_id=str(uuid.uuid4()),
                children=[dev_node],
            )
        assert "Broken parent reference" in str(exc.value)

    def test_tree_integrity_duplicate_id_detection(self):
        """Test validate_tree_integrity raises ValueError if duplicate node IDs exist in tree."""
        root = SpatialNode(
            id="11111111-1111-1111-1111-111111111111",
            global_id="0000000000000000000001",
            name="Project",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
        )
        child1 = SpatialNode(
            id="22222222-2222-2222-2222-222222222222",
            global_id="0000000000000000000002",
            name="Site 1",
            node_type=SpatialNodeType.SITE,
            parent_id=root.id,
        )
        # Duplicate child with identical ID as child1
        child2 = SpatialNode(
            id="22222222-2222-2222-2222-222222222222",
            global_id="0000000000000000000003",
            name="Site 2",
            node_type=SpatialNodeType.SITE,
            parent_id=root.id,
        )
        root.children = [child1, child2]
        with pytest.raises(ValueError) as exc:
            validate_tree_integrity(root)
        assert "Cycle or duplicate node ID detected" in str(exc.value)



class TestDesignSpecToSpatialTreeCompilation:
    """Tests compilation of DesignSpec into a complete, verified SpatialNode tree."""

    def test_compile_1bhk_flat_to_spatial_tree(self):
        spec = parse_prompt_to_design_spec("1-storey 1BHK apartment")
        tree = compile_design_spec_to_spatial_tree(spec)
        assert tree.node_type == SpatialNodeType.PROJECT
        assert validate_tree_integrity(tree) is True

        storeys = filter_nodes_by_type(tree, SpatialNodeType.STOREY)
        assert len(storeys) == 1

        units = filter_nodes_by_type(tree, SpatialNodeType.UNIT)
        assert len(units) >= 1

        rooms = filter_nodes_by_type(tree, SpatialNodeType.ROOM)
        assert len(rooms) >= 3

    def test_compile_12_storey_tower_to_spatial_tree(self):
        spec = parse_prompt_to_design_spec("12-story high-rise tower with 2BHK and 3BHK units")
        tree = compile_design_spec_to_spatial_tree(spec)
        assert tree.node_type == SpatialNodeType.PROJECT
        assert validate_tree_integrity(tree) is True

        storeys = filter_nodes_by_type(tree, SpatialNodeType.STOREY)
        assert len(storeys) == 12

        # Verify all storeys have valid monotonic elevations in properties
        prev_elevation = -1.0
        for s in storeys:
            elev = s.properties.get("elevation", 0.0)
            assert elev > prev_elevation or (elev == 0.0 and prev_elevation == -1.0)
            prev_elevation = elev

        # Verify all nodes have unique valid IFC GUIDs
        all_nodes = flatten_spatial_tree(tree)
        guids = [n.global_id for n in all_nodes.values()]
        assert len(guids) == len(set(guids))
        for g in guids:
            assert len(g) == 22
            assert g[0] in {"0", "1", "2", "3"}
