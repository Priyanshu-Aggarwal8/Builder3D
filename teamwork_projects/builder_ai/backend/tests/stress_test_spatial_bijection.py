"""
Empirical Adversarial Stress Test Suite for Milestone 1 (M1).

Target:
- Bijective 128-bit UUID <-> 22-character IFC Base64 GUID encoding/decoding.
- Deterministic UUID5 hierarchical path generation.
- Canonical Spatial Hierarchy schema constraints and integrity validators.

Author: Challenger 1 (critic/specialist)
"""

from __future__ import annotations

import os
import random
import sys
import time
import uuid
from typing import Dict, List, Set, Tuple

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.design_spec import RoomType, UnitType
from app.schemas.spatial import (
    IFC_BASE64_CHARS,
    IFC_BASE64_DICT,
    NAMESPACE_BUILDER_AI,
    NAMESPACE_BUILDER3D,
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


class TestMetrics:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failures: List[str] = []

    def record_pass(self, test_name: str):
        self.tests_run += 1
        self.tests_passed += 1

    def record_fail(self, test_name: str, reason: str):
        self.tests_run += 1
        self.tests_failed += 1
        msg = f"[FAIL] {test_name}: {reason}"
        self.failures.append(msg)
        print(msg, file=sys.stderr)


metrics = TestMetrics()


def test_100k_random_uuid_bijectivity():
    """
    Empirically tests 100,000 randomized UUID conversions with zero bit degradation.
    Checks:
    1. Exact bitwise round-trip (decoded == original).
    2. Encoding length is strictly 22 characters.
    3. Encoding leading char is in ['0', '1', '2', '3'].
    4. All 22 characters belong to the 64-character IFC alphabet.
    5. String input overload matches UUID object input.
    """
    test_name = "100k_random_uuid_bijectivity"
    print(f"[*] Running {test_name} (100,000 iterations)...")
    count = 100_000
    valid_leading_chars = {"0", "1", "2", "3"}
    alphabet_set = set(IFC_BASE64_CHARS)

    t0 = time.perf_counter()
    bit_errors = 0
    invariant_errors = 0

    for i in range(count):
        # Mix standard uuid4 with raw high-entropy os.urandom bytes
        if i % 2 == 0:
            orig_uuid = uuid.uuid4()
        else:
            orig_uuid = uuid.UUID(bytes=os.urandom(16))

        # Test encoding
        guid = encode_ifc_guid(orig_uuid)

        # Invariant checks
        if len(guid) != 22:
            invariant_errors += 1
            metrics.record_fail(test_name, f"GUID length {len(guid)} != 22 at iter {i}")
            return

        if guid[0] not in valid_leading_chars:
            invariant_errors += 1
            metrics.record_fail(test_name, f"Invalid leading char {guid[0]!r} at iter {i}")
            return

        for c in guid:
            if c not in alphabet_set:
                invariant_errors += 1
                metrics.record_fail(test_name, f"Invalid alphabet char {c!r} at iter {i}")
                return

        # String overload check
        guid_from_str = encode_ifc_guid(str(orig_uuid))
        if guid_from_str != guid:
            bit_errors += 1
            metrics.record_fail(test_name, f"String overload mismatch at iter {i}: {guid_from_str} != {guid}")
            return

        # Decode round-trip
        decoded_uuid = decode_ifc_guid(guid)
        if decoded_uuid != orig_uuid or decoded_uuid.int != orig_uuid.int or decoded_uuid.bytes != orig_uuid.bytes:
            bit_errors += 1
            metrics.record_fail(test_name, f"Bit degradation at iter {i}: original={orig_uuid.hex}, decoded={decoded_uuid.hex}")
            return

    elapsed = time.perf_counter() - t0
    ops_per_sec = count / elapsed
    print(f"[+] {test_name} PASSED: {count:,} conversions in {elapsed:.3f}s ({ops_per_sec:,.0f} ops/sec, 0 bit degradation)")
    metrics.record_pass(test_name)


def test_boundary_and_edge_cases():
    """
    Tests edge cases: Nil UUID, Max UUID, single-bit flips, high-entropy random bytes, byte-order sensitivity.
    """
    test_name = "boundary_and_edge_cases"
    print(f"[*] Running {test_name}...")

    # 1. Nil UUID (0x0000...0000)
    nil_uuid = uuid.UUID("00000000-0000-0000-0000-000000000000")
    nil_guid = encode_ifc_guid(nil_uuid)
    if nil_guid != "0000000000000000000000":
        metrics.record_fail(test_name, f"Nil UUID encoded as {nil_guid}, expected '0000000000000000000000'")
        return
    if decode_ifc_guid(nil_guid) != nil_uuid:
        metrics.record_fail(test_name, "Nil UUID decode mismatch")
        return

    # 2. Max UUID (0xFFFF...FFFF)
    max_uuid = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    max_guid = encode_ifc_guid(max_uuid)
    if max_guid != "3$$$$$$$$$$$$$$$$$$$$$":
        metrics.record_fail(test_name, f"Max UUID encoded as {max_guid}, expected '3$$$$$$$$$$$$$$$$$$$$$'")
        return
    if decode_ifc_guid(max_guid) != max_uuid:
        metrics.record_fail(test_name, "Max UUID decode mismatch")
        return

    # 3. All 128 Single-Bit Set Vectors (1 << k for k in 0..127)
    for bit in range(128):
        u_bit = uuid.UUID(int=1 << bit)
        guid_bit = encode_ifc_guid(u_bit)
        dec_bit = decode_ifc_guid(guid_bit)
        if dec_bit != u_bit or dec_bit.int != (1 << bit):
            metrics.record_fail(test_name, f"Single-bit set roundtrip failure at bit {bit}")
            return

    # 4. All 128 Single-Bit Cleared Vectors ((2^128 - 1) ^ (1 << k))
    full_mask = (1 << 128) - 1
    for bit in range(128):
        u_cleared = uuid.UUID(int=full_mask ^ (1 << bit))
        guid_cleared = encode_ifc_guid(u_cleared)
        dec_cleared = decode_ifc_guid(guid_cleared)
        if dec_cleared != u_cleared or dec_cleared.int != (full_mask ^ (1 << bit)):
            metrics.record_fail(test_name, f"Single-bit cleared roundtrip failure at bit {bit}")
            return

    # 5. All 16 Single-Byte Active Vectors (0xFF at byte k, 0x00 elsewhere)
    for byte_idx in range(16):
        raw_b = bytearray(16)
        raw_b[byte_idx] = 0xFF
        u_byte = uuid.UUID(bytes=bytes(raw_b))
        guid_byte = encode_ifc_guid(u_byte)
        dec_byte = decode_ifc_guid(guid_byte)
        if dec_byte != u_byte or dec_byte.bytes != bytes(raw_b):
            metrics.record_fail(test_name, f"Single-byte active roundtrip failure at byte {byte_idx}")
            return

    # 6. Byte-order sensitivity: verify distinct byte orders produce distinct GUIDs and exact recovery
    seq_bytes = bytes(range(1, 17))
    rev_bytes = bytes(range(16, 0, -1))
    u_seq = uuid.UUID(bytes=seq_bytes)
    u_rev = uuid.UUID(bytes=rev_bytes)
    g_seq = encode_ifc_guid(u_seq)
    g_rev = encode_ifc_guid(u_rev)
    if g_seq == g_rev:
        metrics.record_fail(test_name, "Byte order sensitivity failure: sequential and reversed bytes produced identical GUIDs")
        return
    if decode_ifc_guid(g_seq) != u_seq or decode_ifc_guid(g_rev) != u_rev:
        metrics.record_fail(test_name, "Byte order recovery mismatch")
        return

    # 7. Alternating bit patterns (0x5555... and 0xAAAA...)
    u_55 = uuid.UUID(int=0x55555555555555555555555555555555)
    u_AA = uuid.UUID(int=0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA)
    if decode_ifc_guid(encode_ifc_guid(u_55)) != u_55:
        metrics.record_fail(test_name, "Alternating bit pattern 0x55 failed")
        return
    if decode_ifc_guid(encode_ifc_guid(u_AA)) != u_AA:
        metrics.record_fail(test_name, "Alternating bit pattern 0xAA failed")
        return

    print(f"[+] {test_name} PASSED: Nil, Max, 128 bit-flips, 128 bit-clears, 16 single-bytes, endianness & alternating patterns verified")
    metrics.record_pass(test_name)


def test_adversarial_malformed_inputs():
    """
    Tests rejection of invalid character injection, incorrect lengths (!= 22 chars),
    and out-of-range leading characters (>= 4).
    """
    test_name = "adversarial_malformed_inputs"
    print(f"[*] Running {test_name}...")

    # 1. Non-string inputs
    non_strings = [None, 12345, 3.14, [], {}, b"0000000000000000000000", True]
    for bad_input in non_strings:
        try:
            decode_ifc_guid(bad_input)  # type: ignore
            metrics.record_fail(test_name, f"Failed to reject non-string input: {type(bad_input)}")
            return
        except ValueError:
            pass
        except Exception as e:
            metrics.record_fail(test_name, f"Unexpected exception type for non-string: {type(e).__name__}")
            return

    # 2. Incorrect length strings (lengths 0..100 except 22)
    for length in range(101):
        if length == 22:
            continue
        test_str = "0" * length
        try:
            decode_ifc_guid(test_str)
            metrics.record_fail(test_name, f"Failed to reject invalid string length {length}")
            return
        except ValueError as e:
            if "22 characters" not in str(e):
                metrics.record_fail(test_name, f"Unexpected error message for length {length}: {e}")
                return

    # 3. Invalid character injection across all 22 positions
    hostile_chars = [
        "!", "@", "#", "%", "^", "&", "*", "(", ")", "-", "+", "=", "/", "\\",
        " ", "\t", "\n", "\x00", "\xff", "~", "`", "?", ":", ";", "'", "\"",
        ",", ".", "<", ">", "[", "]", "{", "}", "|",
    ]
    base_valid = "0" * 22
    for pos in range(22):
        for bad_c in hostile_chars:
            mutated = base_valid[:pos] + bad_c + base_valid[pos + 1 :]
            try:
                decode_ifc_guid(mutated)
                metrics.record_fail(test_name, f"Failed to reject invalid char {bad_c!r} at position {pos}")
                return
            except ValueError as e:
                if "Invalid character" not in str(e) and "22 characters" not in str(e):
                    metrics.record_fail(test_name, f"Unexpected error message for invalid char {bad_c!r}: {e}")
                    return

    # 4. Out-of-range leading characters (characters '4' through '$' at index 0)
    # The IFC alphabet indices 0..3 are '0','1','2','3'. Indices 4..63 are '4'..'$'.
    # All indices >= 4 will cause chunk 0 = (char0 * 64 + char1) >= 4 * 64 = 256 > 255.
    illegal_leading_chars = IFC_BASE64_CHARS[4:]  # All 60 illegal leading characters
    assert len(illegal_leading_chars) == 60

    for ill_c in illegal_leading_chars:
        # Test with second char '0' (gives value ill_c_idx * 64 >= 256)
        ill_guid = ill_c + "0" * 21
        try:
            decode_ifc_guid(ill_guid)
            metrics.record_fail(test_name, f"Failed to reject illegal leading character {ill_c!r}")
            return
        except ValueError as e:
            if "exceeds 255" not in str(e) and "first character" not in str(e):
                metrics.record_fail(test_name, f"Unexpected error message for leading char {ill_c!r}: {e}")
                return

        # Test with second char '$' (maximum 2nd char)
        ill_guid_max2 = ill_c + "$" + "0" * 20
        try:
            decode_ifc_guid(ill_guid_max2)
            metrics.record_fail(test_name, f"Failed to reject illegal leading character {ill_c!r} with 2nd char '$'")
            return
        except ValueError as e:
            if "exceeds 255" not in str(e) and "first character" not in str(e):
                metrics.record_fail(test_name, f"Unexpected error message for leading char {ill_c!r} with '$': {e}")
                return

    # 5. Chunk 0 boundary test:
    # '3$' = 3 * 64 + 63 = 255 -> VALID (decodes without error)
    # '40' = 4 * 64 + 0 = 256 -> INVALID (must raise error)
    valid_boundary_chunk0 = "3$" + "0" * 20
    decoded_b0 = decode_ifc_guid(valid_boundary_chunk0)
    if decoded_b0.bytes[0] != 255:
        metrics.record_fail(test_name, f"Expected byte 0 to be 255, got {decoded_b0.bytes[0]}")
        return

    invalid_boundary_chunk0 = "40" + "0" * 20
    try:
        decode_ifc_guid(invalid_boundary_chunk0)
        metrics.record_fail(test_name, "Failed to reject chunk 0 overflow at '40'")
        return
    except ValueError:
        pass

    print(f"[+] {test_name} PASSED: Non-strings, lengths 0..100, 770 char mutations, and all 60 illegal leading chars rejected")
    metrics.record_pass(test_name)


def test_uuid5_path_collision_resistance_10k():
    """
    Tests collision resistance across 10,000 hierarchically distinct spatial paths.
    Also verifies path determinism, namespace isolation, and whitespace handling.
    """
    test_name = "uuid5_path_collision_resistance_10k"
    print(f"[*] Running {test_name} (10,000 hierarchically distinct paths)...")
    path_count = 10_000

    generated_paths: List[str] = []
    uuids_ai: List[uuid.UUID] = []
    uuids_3d: List[uuid.UUID] = []
    seen_ai: Set[uuid.UUID] = set()

    # Generate 10,000 realistic hierarchical paths
    for i in range(path_count):
        proj = f"project:skyline_{i // 1000}"
        site = f"site:plot_{ (i // 500) % 2 }"
        dev = f"dev:phase_{ (i // 250) % 2 }"
        bldg = f"bldg:tower_{ (i // 50) % 5 }"
        storey = f"storey_{ (i // 10) % 5 }"
        unit = f"unit_{(i % 10) + 1:02d}"
        room = f"room:{random.choice(['living', 'kitchen', 'bedroom_master', 'bath_common', 'balcony', 'utility'])}_{i}"

        path = f"{proj}/{site}/{dev}/{bldg}/{storey}/{unit}/{room}"
        generated_paths.append(path)

        # Generate in NAMESPACE_BUILDER_AI
        u_ai = generate_spatial_uuid(path, NAMESPACE_BUILDER_AI)
        if u_ai in seen_ai:
            metrics.record_fail(test_name, f"Collision detected at index {i} for path: {path}")
            return
        seen_ai.add(u_ai)
        uuids_ai.append(u_ai)

        # Generate in NAMESPACE_BUILDER3D
        u_3d = generate_spatial_uuid(path, NAMESPACE_BUILDER3D)
        uuids_3d.append(u_3d)

    # 1. Collision check
    if len(seen_ai) != path_count:
        metrics.record_fail(test_name, f"Unique UUID count {len(seen_ai)} != {path_count}")
        return

    # 2. Namespace isolation check (BuilderAI vs Builder3D namespaces must produce 0 overlap)
    cross_namespace_collisions = seen_ai.intersection(set(uuids_3d))
    if len(cross_namespace_collisions) > 0:
        metrics.record_fail(test_name, f"Cross-namespace collision found: {len(cross_namespace_collisions)} matches")
        return

    # 3. Determinism check (re-run all 10,000 paths and compare)
    for i, path in enumerate(generated_paths):
        u_re = generate_spatial_uuid(path, NAMESPACE_BUILDER_AI)
        if u_re != uuids_ai[i]:
            metrics.record_fail(test_name, f"Determinism failure at path {i}: {u_re} != {uuids_ai[i]}")
            return
        if u_re.version != 5:
            metrics.record_fail(test_name, f"UUID version {u_re.version} != 5 at path {i}")
            return

    # 4. Empty and whitespace-only path rejections
    for bad_path in ["", "   ", "\t\n", "\n"]:
        try:
            generate_spatial_uuid(bad_path)
            metrics.record_fail(test_name, f"Failed to reject empty/whitespace path: {bad_path!r}")
            return
        except ValueError:
            pass

    print(f"[+] {test_name} PASSED: 10,000 distinct paths, 0 collisions, 100% deterministic, 0 cross-namespace overlap")
    metrics.record_pass(test_name)


def test_spatial_node_pydantic_validation():
    """
    Stress-tests Pydantic schema validation for SpatialNode:
    - ID format validation (RFC 4122 UUID)
    - Global ID validation (22-char IFC GUID)
    - Hierarchy containment and cycle detection
    - High-density multi-storey spatial tree construction
    """
    test_name = "spatial_node_pydantic_validation"
    print(f"[*] Running {test_name}...")

    # 1. Invalid UUID format in SpatialNode.id
    try:
        SpatialNode(
            id="not-a-valid-uuid",
            global_id="0000000000000000000000",
            name="Bad UUID Node",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
        )
        metrics.record_fail(test_name, "Failed to reject invalid UUID in SpatialNode.id")
        return
    except Exception:
        pass

    # 2. Invalid IFC GUID leading character in SpatialNode.global_id
    try:
        SpatialNode(
            id=str(uuid.uuid4()),
            global_id="4000000000000000000000",  # leading char '4' is invalid
            name="Bad GUID Node",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
        )
        metrics.record_fail(test_name, "Failed to reject illegal leading character '4' in SpatialNode.global_id")
        return
    except Exception:
        pass

    # 3. Invalid IFC GUID length in SpatialNode.global_id
    try:
        SpatialNode(
            id=str(uuid.uuid4()),
            global_id="0000000000",  # 10 chars
            name="Short GUID Node",
            node_type=SpatialNodeType.PROJECT,
            parent_id=None,
        )
        metrics.record_fail(test_name, "Failed to reject short IFC GUID in SpatialNode.global_id")
        return
    except Exception:
        pass

    # 4. Stress test: Construct massive 50-storey high-rise spatial tree
    # 1 Project + 1 Site + 1 Dev + 1 Bldg + 50 Storeys + 200 Units + 1000 Rooms = 1,254 Nodes
    proj_path = "project:megatower_50"
    proj_id = str(generate_spatial_uuid(proj_path))
    site_path = f"{proj_path}/site:main"
    site_id = str(generate_spatial_uuid(site_path))
    dev_path = f"{site_path}/dev:phase1"
    dev_id = str(generate_spatial_uuid(dev_path))
    bldg_path = f"{dev_path}/bldg:tower1"
    bldg_id = str(generate_spatial_uuid(bldg_path))

    storeys: List[SpatialNode] = []
    total_node_count = 4  # Project, Site, Dev, Bldg

    for s_idx in range(50):
        s_path = f"{bldg_path}/storey:{s_idx}"
        s_id = str(generate_spatial_uuid(s_path))
        units: List[SpatialNode] = []
        total_node_count += 1

        for u_idx in range(4):
            u_path = f"{s_path}/unit:{u_idx + 1}"
            u_id = str(generate_spatial_uuid(u_path))
            rooms: List[SpatialNode] = []
            total_node_count += 1

            for r_idx, r_name in enumerate(["Living", "Kitchen", "Master Bed", "Bed 2", "Bath"]):
                r_path = f"{u_path}/room:{r_name.lower().replace(' ', '_')}_{r_idx}"
                r_id = str(generate_spatial_uuid(r_path))
                room_node = SpatialNode(
                    id=r_id,
                    global_id=encode_ifc_guid(r_id),
                    name=r_name,
                    node_type=SpatialNodeType.ROOM,
                    parent_id=u_id,
                    canonical_path=r_path,
                    properties=RoomProperties(room_type=RoomType.LIVING_ROOM, area_sqm=20.0).model_dump(),
                )
                rooms.append(room_node)
                total_node_count += 1

            unit_node = SpatialNode(
                id=u_id,
                global_id=encode_ifc_guid(u_id),
                name=f"Unit {s_idx}{u_idx + 1:02d}",
                node_type=SpatialNodeType.UNIT,
                parent_id=s_id,
                canonical_path=u_path,
                properties=UnitProperties(unit_type=UnitType.BHK2, target_area_sqm=85.0).model_dump(),
                children=rooms,
            )
            units.append(unit_node)

        storey_node = SpatialNode(
            id=s_id,
            global_id=encode_ifc_guid(s_id),
            name=f"Level {s_idx}",
            node_type=SpatialNodeType.STOREY,
            parent_id=bldg_id,
            canonical_path=s_path,
            properties=StoreyProperties(storey_index=s_idx, elevation=s_idx * 3.2).model_dump(),
            children=units,
        )
        storeys.append(storey_node)

    bldg_node = SpatialNode(
        id=bldg_id,
        global_id=encode_ifc_guid(bldg_id),
        name="Tower 1",
        node_type=SpatialNodeType.BUILDING,
        parent_id=dev_id,
        canonical_path=bldg_path,
        properties=BuildingProperties(total_storeys=50).model_dump(),
        children=storeys,
    )
    dev_node = SpatialNode(
        id=dev_id,
        global_id=encode_ifc_guid(dev_id),
        name="Phase 1",
        node_type=SpatialNodeType.DEVELOPMENT,
        parent_id=site_id,
        canonical_path=dev_path,
        children=[bldg_node],
    )
    site_node = SpatialNode(
        id=site_id,
        global_id=encode_ifc_guid(site_id),
        name="Main Site",
        node_type=SpatialNodeType.SITE,
        parent_id=proj_id,
        canonical_path=site_path,
        children=[dev_node],
    )
    root = SpatialNode(
        id=proj_id,
        global_id=encode_ifc_guid(proj_id),
        name="Mega Tower 50",
        node_type=SpatialNodeType.PROJECT,
        parent_id=None,
        canonical_path=proj_path,
        children=[site_node],
    )

    t0 = time.perf_counter()
    assert validate_tree_integrity(root) is True
    val_time = time.perf_counter() - t0

    flattened = flatten_spatial_tree(root)
    if len(flattened) != total_node_count:
        metrics.record_fail(test_name, f"Flattened tree size {len(flattened)} != {total_node_count}")
        return

    # Verify lookups on deep node (50th storey unit 4 room 5)
    sample_room = storeys[49].children[3].children[4]
    found_node = find_node_by_id(root, sample_room.id)
    if found_node is None or found_node.name != sample_room.name:
        metrics.record_fail(test_name, f"Failed to find deep node {sample_room.id} by ID")
        return

    ancestor_chain = get_ancestor_chain(root, sample_room.id)
    if ancestor_chain is None or len(ancestor_chain) != 7:
        metrics.record_fail(test_name, f"Ancestor chain length {len(ancestor_chain) if ancestor_chain else 0} != 7")
        return

    print(f"[+] {test_name} PASSED: {total_node_count} node tree validated in {val_time*1000:.2f}ms, exact lookups & ancestor chains verified")
    metrics.record_pass(test_name)


def main() -> int:
    print("=" * 80)
    print("EMPIRICAL ADVERSARIAL STRESS TEST HARNESS — MILESTONE 1 (M1)")
    print("=" * 80)
    start_time = time.perf_counter()

    test_100k_random_uuid_bijectivity()
    test_boundary_and_edge_cases()
    test_adversarial_malformed_inputs()
    test_uuid5_path_collision_resistance_10k()
    test_spatial_node_pydantic_validation()

    total_time = time.perf_counter() - start_time
    print("=" * 80)
    print(f"SUMMARY: {metrics.tests_passed}/{metrics.tests_run} test suites PASSED in {total_time:.3f}s")
    if metrics.tests_failed > 0:
        print(f"VERDICT: REJECT ({metrics.tests_failed} test suites failed)")
        for fail in metrics.failures:
            print(f"  - {fail}")
        return 1
    else:
        print("VERDICT: APPROVE (100% empirical verification passed with 0 defects)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
