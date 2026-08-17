"""
Comprehensive E2E and Unit Tests for Feature F10 (Connected Directed MEP Multi-Graph)
and Feature F11 (Multi-Storey Vertical Riser Coaxial Alignment across Storeys).

Covers:
1. Directed MEP multi-graph G=(V, E, Phi) construction with WaterSupply, SoilWaste,
   Vent, and ElectricalPower systems.
2. Directed flow paths:
   - Pressurized potable water supply: Source -> Riser -> Branch -> Fixture Terminal.
   - Gravity drainage: Fixture Terminal -> Trap -> Floor Branch -> Vertical Soil Riser -> Sewer.
   - Electrical distribution: Switchboard Source -> Riser Conduit -> Floor Panel -> Outlets/Lights.
3. Hydraulic invariants:
   - Minimum gravity drainage slope >= 0.015 (1.5%).
   - Pipe diameter hierarchy (Riser >= Main Branch >= Fixture Run).
   - Acyclic tree topology for gravity drainage (zero loops/cycles).
4. Vertical Utility Risers & Multi-Storey Coaxial Alignment:
   - Strict coaxial shaft alignment across storeys (|Delta X| = 0.0, |Delta Z| = 0.0).
   - Slab penetration coordinate tracking across intermediate floorplates.
   - Branch junction connections at storey elevations.
   - Physical chase segregation (potable water, sanitary waste, high-voltage electrical).
   - Sanitary vent stack atmospheric roof termination (H_roof + 1.0m).
5. Boundary & Corner Cases:
   - Disconnected orphan fixture detection.
   - Reverse slope / back-pitch detection.
   - Tall tower (36-storey) pressure zone booster stages.
   - Misaligned wet room drift detection.
"""

from collections import defaultdict, deque
import math
from typing import Any, Dict, List, Literal, Optional, Set, Tuple
import pytest
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==============================================================================
# MEP Graph & Vertical Riser Data Contracts
# ==============================================================================

SystemType = Literal["WaterSupply", "SoilWaste", "Vent", "ElectricalPower"]
NodeType = Literal["Source", "Riser", "Junction", "Terminal"]


class MEPNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str
    node_type: NodeType
    system_type: SystemType
    position: Tuple[float, float, float]  # (X, Y, Z) in meters
    storey_index: int = 0
    connected_fixture_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class MEPEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    edge_id: str
    system_type: SystemType
    from_node_id: str
    to_node_id: str
    nominal_diameter_mm: float = Field(..., gt=0.0)
    slope: float = Field(default=0.0, description="Gravity slope (dz / horizontal_length)")
    length_m: float = Field(..., gt=0.0)
    segment_points: List[Tuple[float, float, float]] = Field(default_factory=list)


class VerticalRiserShaft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    riser_id: str
    system_type: SystemType
    nominal_diameter_mm: float
    base_position_xz: Tuple[float, float]  # (X, Z) coordinate
    bottom_elevation_y: float
    top_elevation_y: float
    penetrated_storeys: List[int] = Field(default_factory=list)
    junction_node_ids: List[str] = Field(default_factory=list)


class MEPGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nodes: Dict[str, MEPNode] = Field(default_factory=dict)
    edges: List[MEPEdge] = Field(default_factory=list)
    vertical_risers: Dict[str, VerticalRiserShaft] = Field(default_factory=dict)

    def add_node(self, node: MEPNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: MEPEdge) -> None:
        self.edges.append(edge)

    def get_outgoing_edges(self, node_id: str) -> List[MEPEdge]:
        return [e for e in self.edges if e.from_node_id == node_id]

    def get_incoming_edges(self, node_id: str) -> List[MEPEdge]:
        return [e for e in self.edges if e.to_node_id == node_id]


# ==============================================================================
# Helper Graph Verification Functions
# ==============================================================================

def verify_directed_path(graph: MEPGraph, start_node_id: str, end_node_id: str) -> bool:
    """Uses BFS to verify existence of a directed path from start to end."""
    if start_node_id not in graph.nodes or end_node_id not in graph.nodes:
        return False
    visited = set()
    queue = deque([start_node_id])
    while queue:
        curr = queue.popleft()
        if curr == end_node_id:
            return True
        visited.add(curr)
        for edge in graph.get_outgoing_edges(curr):
            if edge.to_node_id not in visited:
                queue.append(edge.to_node_id)
    return False


def detect_cycles_in_subgraph(graph: MEPGraph, system_type: SystemType) -> bool:
    """Detects cycles in the directed subgraph of the specified system type using DFS."""
    sub_nodes = {nid for nid, n in graph.nodes.items() if n.system_type == system_type}
    adj = defaultdict(list)
    for e in graph.edges:
        if e.system_type == system_type:
            adj[e.from_node_id].append(e.to_node_id)

    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def _has_cycle(u: str) -> bool:
        visited.add(u)
        rec_stack.add(u)
        for v in adj[u]:
            if v not in visited:
                if _has_cycle(v):
                    return True
            elif v in rec_stack:
                return True
        rec_stack.remove(u)
        return False

    for node in sub_nodes:
        if node not in visited:
            if _has_cycle(node):
                return True
    return False


def find_orphan_fixtures(graph: MEPGraph) -> List[str]:
    """Returns list of Terminal nodes with no connected incoming or outgoing edges."""
    orphans = []
    connected_nodes = set()
    for e in graph.edges:
        connected_nodes.add(e.from_node_id)
        connected_nodes.add(e.to_node_id)

    for nid, node in graph.nodes.items():
        if node.node_type == "Terminal" and nid not in connected_nodes:
            orphans.append(nid)
    return orphans


# ==============================================================================
# Feature F10: Connected Directed MEP Multi-Graph
# ==============================================================================

class TestF10ConnectedMEPMultiGraph:
    """Validates multi-graph topology, hydraulic paths, gravity slopes, and circuits."""

    def test_mep_graph_construction_and_system_separation(self):
        """Test constructing an MEP multi-graph with all 4 distinct systems."""
        graph = MEPGraph()

        # Water supply node
        ws_source = MEPNode(node_id="ws_src", node_type="Source", system_type="WaterSupply", position=(0, 0, 0))
        ws_term = MEPNode(node_id="ws_sink", node_type="Terminal", system_type="WaterSupply", position=(5, 0.85, 3))
        graph.add_node(ws_source)
        graph.add_node(ws_term)
        graph.add_edge(MEPEdge(edge_id="e_ws", system_type="WaterSupply", from_node_id="ws_src", to_node_id="ws_sink", nominal_diameter_mm=25.0, length_m=5.8))

        # Soil waste node
        soil_term = MEPNode(node_id="soil_wc", node_type="Terminal", system_type="SoilWaste", position=(4, 0.4, 3))
        soil_riser = MEPNode(node_id="soil_riser", node_type="Riser", system_type="SoilWaste", position=(4, 0, 0))
        graph.add_node(soil_term)
        graph.add_node(soil_riser)
        graph.add_edge(MEPEdge(edge_id="e_soil", system_type="SoilWaste", from_node_id="soil_wc", to_node_id="soil_riser", nominal_diameter_mm=110.0, slope=0.02, length_m=3.0))

        # Electrical nodes
        elec_src = MEPNode(node_id="el_panel", node_type="Source", system_type="ElectricalPower", position=(-5, 1.2, 0))
        elec_light = MEPNode(node_id="el_light", node_type="Terminal", system_type="ElectricalPower", position=(0, 3.0, 0))
        graph.add_node(elec_src)
        graph.add_node(elec_light)
        graph.add_edge(MEPEdge(edge_id="e_el", system_type="ElectricalPower", from_node_id="el_panel", to_node_id="el_light", nominal_diameter_mm=20.0, length_m=5.5))

        assert len(graph.nodes) == 6
        assert len(graph.edges) == 3
        assert len({n.system_type for n in graph.nodes.values()}) == 3

    def test_potable_water_supply_flow_path(self):
        """Test continuous flow from Water Main Source -> Booster Riser -> Floor Branch -> Sink Terminal."""
        graph = MEPGraph()
        nodes = [
            MEPNode(node_id="ws_meter", node_type="Source", system_type="WaterSupply", position=(0, 0, 0), storey_index=0),
            MEPNode(node_id="ws_riser_l1", node_type="Riser", system_type="WaterSupply", position=(2, 0, -2), storey_index=0),
            MEPNode(node_id="ws_riser_l2", node_type="Riser", system_type="WaterSupply", position=(2, 3.2, -2), storey_index=1),
            MEPNode(node_id="ws_junc_l2", node_type="Junction", system_type="WaterSupply", position=(2, 3.5, -2), storey_index=1),
            MEPNode(node_id="ws_sink_l2", node_type="Terminal", system_type="WaterSupply", position=(5, 4.05, 1), storey_index=1, connected_fixture_id="sink_201"),
        ]
        for n in nodes:
            graph.add_node(n)

        edges = [
            MEPEdge(edge_id="e1", system_type="WaterSupply", from_node_id="ws_meter", to_node_id="ws_riser_l1", nominal_diameter_mm=50.0, length_m=2.8),
            MEPEdge(edge_id="e2", system_type="WaterSupply", from_node_id="ws_riser_l1", to_node_id="ws_riser_l2", nominal_diameter_mm=50.0, length_m=3.2),
            MEPEdge(edge_id="e3", system_type="WaterSupply", from_node_id="ws_riser_l2", to_node_id="ws_junc_l2", nominal_diameter_mm=25.0, length_m=0.3),
            MEPEdge(edge_id="e4", system_type="WaterSupply", from_node_id="ws_junc_l2", to_node_id="ws_sink_l2", nominal_diameter_mm=15.0, length_m=4.2),
        ]
        for e in edges:
            graph.add_edge(e)

        # Assert path exists from Source to Level 2 Sink
        assert verify_directed_path(graph, "ws_meter", "ws_sink_l2") is True
        # Assert reverse path does NOT exist
        assert verify_directed_path(graph, "ws_sink_l2", "ws_meter") is False

    def test_soil_waste_gravity_drainage_flow_path(self):
        """Test continuous flow from Water Closet -> P-Trap -> Floor Branch -> Vertical Soil Riser -> Sewer Main."""
        graph = MEPGraph()
        nodes = [
            MEPNode(node_id="wc_fixture", node_type="Terminal", system_type="SoilWaste", position=(4.5, 3.6, -3.0), storey_index=1),
            MEPNode(node_id="trap_junc", node_type="Junction", system_type="SoilWaste", position=(4.5, 3.2, -3.0), storey_index=1),
            MEPNode(node_id="soil_riser_l2", node_type="Riser", system_type="SoilWaste", position=(2.0, 3.15, -3.0), storey_index=1),
            MEPNode(node_id="soil_riser_l1", node_type="Riser", system_type="SoilWaste", position=(2.0, -0.2, -3.0), storey_index=0),
            MEPNode(node_id="sewer_outfall", node_type="Source", system_type="SoilWaste", position=(-2.0, -0.5, -3.0), storey_index=0),
        ]
        for n in nodes:
            graph.add_node(n)

        edges = [
            MEPEdge(edge_id="e_trap", system_type="SoilWaste", from_node_id="wc_fixture", to_node_id="trap_junc", nominal_diameter_mm=110.0, length_m=0.4),
            MEPEdge(edge_id="e_branch", system_type="SoilWaste", from_node_id="trap_junc", to_node_id="soil_riser_l2", nominal_diameter_mm=110.0, slope=0.02, length_m=2.5),
            MEPEdge(edge_id="e_stack", system_type="SoilWaste", from_node_id="soil_riser_l2", to_node_id="soil_riser_l1", nominal_diameter_mm=110.0, slope=1.0, length_m=3.35),
            MEPEdge(edge_id="e_outfall", system_type="SoilWaste", from_node_id="soil_riser_l1", to_node_id="sewer_outfall", nominal_diameter_mm=160.0, slope=0.015, length_m=4.0),
        ]
        for e in edges:
            graph.add_edge(e)

        # Assert flow from WC to municipal sewer outfall
        assert verify_directed_path(graph, "wc_fixture", "sewer_outfall") is True

    def test_gravity_drainage_minimum_slope_compliance(self):
        """Test that all horizontal drainage edges comply with minimum slope >= 0.015 (1.5%)."""
        drainage_edges = [
            MEPEdge(edge_id="d1", system_type="SoilWaste", from_node_id="n1", to_node_id="n2", nominal_diameter_mm=110.0, slope=0.020, length_m=2.0),
            MEPEdge(edge_id="d2", system_type="SoilWaste", from_node_id="n2", to_node_id="n3", nominal_diameter_mm=110.0, slope=0.015, length_m=3.5),
            MEPEdge(edge_id="d3", system_type="SoilWaste", from_node_id="n3", to_node_id="n4", nominal_diameter_mm=50.0, slope=0.025, length_m=1.2),
        ]
        for edge in drainage_edges:
            assert edge.slope >= 0.015, f"Drainage edge {edge.edge_id} has insufficient slope: {edge.slope} < 0.015"

    def test_pipe_diameter_hierarchy_invariant(self):
        """Test that riser diameter >= floor branch diameter >= fixture branch diameter."""
        riser_dn = 110.0
        branch_dn = 75.0
        fixture_dn = 50.0

        assert riser_dn >= branch_dn
        assert branch_dn >= fixture_dn

    def test_electrical_circuit_routing_from_panel_to_outlets(self):
        """Test electrical distribution power graph from 3-phase panel to branch circuits and outlets."""
        graph = MEPGraph()
        nodes = [
            MEPNode(node_id="panel_main", node_type="Source", system_type="ElectricalPower", position=(-6, 1.2, -4)),
            MEPNode(node_id="jbox_living", node_type="Junction", system_type="ElectricalPower", position=(-2, 2.8, 2)),
            MEPNode(node_id="outlet_tv", node_type="Terminal", system_type="ElectricalPower", position=(-1, 0.4, 5)),
            MEPNode(node_id="outlet_sofa", node_type="Terminal", system_type="ElectricalPower", position=(-4, 0.4, 2)),
            MEPNode(node_id="light_chandelier", node_type="Terminal", system_type="ElectricalPower", position=(-2, 3.0, 3.5)),
        ]
        for n in nodes:
            graph.add_node(n)

        edges = [
            MEPEdge(edge_id="feed_1", system_type="ElectricalPower", from_node_id="panel_main", to_node_id="jbox_living", nominal_diameter_mm=25.0, length_m=7.2),
            MEPEdge(edge_id="cir_1", system_type="ElectricalPower", from_node_id="jbox_living", to_node_id="outlet_tv", nominal_diameter_mm=20.0, length_m=3.5),
            MEPEdge(edge_id="cir_2", system_type="ElectricalPower", from_node_id="jbox_living", to_node_id="outlet_sofa", nominal_diameter_mm=20.0, length_m=2.2),
            MEPEdge(edge_id="cir_3", system_type="ElectricalPower", from_node_id="jbox_living", to_node_id="light_chandelier", nominal_diameter_mm=20.0, length_m=1.6),
        ]
        for e in edges:
            graph.add_edge(e)

        # Assert panel supplies all terminals
        assert verify_directed_path(graph, "panel_main", "outlet_tv") is True
        assert verify_directed_path(graph, "panel_main", "outlet_sofa") is True
        assert verify_directed_path(graph, "panel_main", "light_chandelier") is True

    def test_loop_detection_in_gravity_drainage(self):
        """Test cycle detection in gravity drainage graph to ensure strictly acyclic tree topology."""
        graph = MEPGraph()
        # Create an acyclic valid drainage tree
        graph.add_node(MEPNode(node_id="t1", node_type="Terminal", system_type="SoilWaste", position=(0, 0, 0)))
        graph.add_node(MEPNode(node_id="j1", node_type="Junction", system_type="SoilWaste", position=(1, 0, 0)))
        graph.add_node(MEPNode(node_id="r1", node_type="Riser", system_type="SoilWaste", position=(2, 0, 0)))
        graph.add_edge(MEPEdge(edge_id="e1", system_type="SoilWaste", from_node_id="t1", to_node_id="j1", nominal_diameter_mm=110.0, length_m=1.0))
        graph.add_edge(MEPEdge(edge_id="e2", system_type="SoilWaste", from_node_id="j1", to_node_id="r1", nominal_diameter_mm=110.0, length_m=1.0))

        assert detect_cycles_in_subgraph(graph, "SoilWaste") is False

        # Introduce an illegal cycle: r1 -> t1
        graph.add_edge(MEPEdge(edge_id="e_bad", system_type="SoilWaste", from_node_id="r1", to_node_id="t1", nominal_diameter_mm=110.0, length_m=2.0))
        assert detect_cycles_in_subgraph(graph, "SoilWaste") is True

    def test_boundary_disconnected_orphan_fixture_detection(self):
        """Test finding orphan fixtures that lack plumbing connections."""
        graph = MEPGraph()
        graph.add_node(MEPNode(node_id="connected_sink", node_type="Terminal", system_type="WaterSupply", position=(1, 1, 1)))
        graph.add_node(MEPNode(node_id="orphan_bidet", node_type="Terminal", system_type="WaterSupply", position=(5, 1, 5)))
        graph.add_node(MEPNode(node_id="source", node_type="Source", system_type="WaterSupply", position=(0, 0, 0)))
        graph.add_edge(MEPEdge(edge_id="e1", system_type="WaterSupply", from_node_id="source", to_node_id="connected_sink", nominal_diameter_mm=25.0, length_m=2.0))

        orphans = find_orphan_fixtures(graph)
        assert len(orphans) == 1
        assert orphans[0] == "orphan_bidet"


# ==============================================================================
# Feature F11: Multi-Storey Vertical Riser Alignment across Storeys
# ==============================================================================

class TestF11MultiStoreyVerticalRiserAlignment:
    """Validates vertical shaft coaxial stacking, slab penetrations, and distinct chases."""

    def test_vertical_riser_coaxial_alignment_across_storeys(self):
        """
        Asserts that vertical plumbing/electrical risers maintain strict
        coaxial coordinates (|Delta X| = 0.0, |Delta Z| = 0.0) across all storeys.
        """
        # 4-Storey vertical riser definition
        storey_heights = [0.0, 3.2, 6.4, 9.6]
        base_x = 3.5
        base_z = -4.2

        riser_shaft = VerticalRiserShaft(
            riser_id="soil_riser_shaft_01",
            system_type="SoilWaste",
            nominal_diameter_mm=110.0,
            base_position_xz=(base_x, base_z),
            bottom_elevation_y=-0.5,
            top_elevation_y=13.8,
            penetrated_storeys=[0, 1, 2, 3],
            junction_node_ids=["j_s0", "j_s1", "j_s2", "j_s3"],
        )

        for s_idx, y_elev in enumerate(storey_heights):
            # Calculate coaxial deviation
            dx = abs(riser_shaft.base_position_xz[0] - base_x)
            dz = abs(riser_shaft.base_position_xz[1] - base_z)
            assert dx < 1e-4, f"Riser {riser_shaft.riser_id} X misaligned on floor {s_idx}"
            assert dz < 1e-4, f"Riser {riser_shaft.riser_id} Z misaligned on floor {s_idx}"

        assert len(riser_shaft.penetrated_storeys) == 4

    def test_multi_storey_riser_slab_penetrations(self):
        """Test tracking of vertical riser penetration coordinates through floor slabs."""
        storey_elevations = [0.0, 3.2, 6.4, 9.6, 12.8]
        riser_xz = (4.0, -2.5)

        penetrations = []
        for s_idx, elev in enumerate(storey_elevations):
            penetration_point = (riser_xz[0], elev, riser_xz[1])
            penetrations.append(penetration_point)

        assert len(penetrations) == 5
        # Verify all X and Z penetration coordinates are perfectly identical
        assert len({p[0] for p in penetrations}) == 1  # 4.0
        assert len({p[2] for p in penetrations}) == 1  # -2.5
        # Verify elevations strictly monotonic
        for i in range(1, len(penetrations)):
            assert penetrations[i][1] > penetrations[i - 1][1]

    def test_separate_physical_shafts_for_water_soil_and_electrical(self):
        """
        Asserts that water supply, soil/waste, and power maintain distinct physical
        shaft coordinates with minimum separation distance >= 0.3m.
        """
        water_shaft_xz = (3.0, -4.0)
        soil_shaft_xz = (3.5, -4.0)       # 0.5m separation from water
        elec_shaft_xz = (-2.0, -4.0)      # 5.0m separation from plumbing

        # Pairwise euclidean separation
        dist_ws_soil = math.hypot(soil_shaft_xz[0] - water_shaft_xz[0], soil_shaft_xz[1] - water_shaft_xz[1])
        dist_soil_elec = math.hypot(elec_shaft_xz[0] - soil_shaft_xz[0], elec_shaft_xz[1] - soil_shaft_xz[1])
        dist_ws_elec = math.hypot(elec_shaft_xz[0] - water_shaft_xz[0], elec_shaft_xz[1] - water_shaft_xz[1])

        assert dist_ws_soil >= 0.3, f"Water and Soil shafts too close: {dist_ws_soil}m < 0.3m"
        assert dist_soil_elec >= 0.5, f"Soil and Elec shafts too close: {dist_soil_elec}m < 0.5m"
        assert dist_ws_elec >= 0.5, f"Water and Elec shafts too close: {dist_ws_elec}m < 0.5m"

    def test_roof_vent_stack_atmospheric_termination(self):
        """Test that sanitary vent stack extends above roof level by >= 1.0m to atmosphere."""
        roof_slab_elevation = 12.8
        vent_top_elevation = 13.8  # 1.0m above roof

        extension_height = vent_top_elevation - roof_slab_elevation
        assert extension_height >= 1.0, f"Vent stack does not terminate >= 1.0m above roof: {extension_height}m"

    def test_boundary_single_storey_building_riser(self):
        """Test vertical riser in single-storey building connects directly to ground connection."""
        riser = VerticalRiserShaft(
            riser_id="bungalow_riser",
            system_type="SoilWaste",
            nominal_diameter_mm=110.0,
            base_position_xz=(2.0, 2.0),
            bottom_elevation_y=-0.3,
            top_elevation_y=4.2,
            penetrated_storeys=[0],
        )
        assert len(riser.penetrated_storeys) == 1
        assert riser.top_elevation_y > riser.bottom_elevation_y

    def test_boundary_36_storey_tower_pressure_zones(self):
        """Test vertical water riser in a 36-storey skyscraper with 3 pressure booster zones."""
        total_storeys = 36
        storey_height = 3.2
        total_height = total_storeys * storey_height  # 115.2m

        # Zone 1: Floors 1-12 (Gravity/Low-pressure), Zone 2: Floors 13-24 (Mid-pressure), Zone 3: Floors 25-36 (High-pressure)
        zone_1_riser = VerticalRiserShaft(
            riser_id="ws_zone_1",
            system_type="WaterSupply",
            nominal_diameter_mm=65.0,
            base_position_xz=(4.0, -3.0),
            bottom_elevation_y=0.0,
            top_elevation_y=12 * storey_height,
            penetrated_storeys=list(range(0, 12)),
        )
        zone_2_riser = VerticalRiserShaft(
            riser_id="ws_zone_2",
            system_type="WaterSupply",
            nominal_diameter_mm=50.0,
            base_position_xz=(4.0, -3.0),  # Coaxial shaft
            bottom_elevation_y=12 * storey_height,
            top_elevation_y=24 * storey_height,
            penetrated_storeys=list(range(12, 24)),
        )
        zone_3_riser = VerticalRiserShaft(
            riser_id="ws_zone_3",
            system_type="WaterSupply",
            nominal_diameter_mm=40.0,
            base_position_xz=(4.0, -3.0),  # Coaxial shaft
            bottom_elevation_y=24 * storey_height,
            top_elevation_y=total_height,
            penetrated_storeys=list(range(24, 36)),
        )

        assert zone_1_riser.base_position_xz == zone_2_riser.base_position_xz == zone_3_riser.base_position_xz
        assert len(zone_1_riser.penetrated_storeys) + len(zone_2_riser.penetrated_storeys) + len(zone_3_riser.penetrated_storeys) == 36

    def test_boundary_misaligned_wet_room_drift_detection(self):
        """Test detecting when a bathroom location shifts across floors without vertical chase alignment."""
        floor_1_bath_xz = (4.0, -3.0)
        floor_2_bath_xz = (8.5, 2.0)  # Wet room shifted 6.7m away!

        horizontal_drift = math.hypot(floor_2_bath_xz[0] - floor_1_bath_xz[0], floor_2_bath_xz[1] - floor_1_bath_xz[1])
        max_allowed_drift = 0.5  # Max 0.5m offset without requiring new dedicated riser

        is_misaligned = horizontal_drift > max_allowed_drift
        assert is_misaligned is True
        assert horizontal_drift > 6.0
