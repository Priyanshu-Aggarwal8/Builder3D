import json
import urllib.request
import uuid
import re
from typing import List, Dict, Any

import os

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}" if GEMINI_KEY else ""

def generate_aaa_building_model(prompt: str) -> List[Dict[str, Any]]:
    """
    Generates a full-fledged OpenBIM / AAA Game-Engine architectural building model
    strictly adhering to the user's prompt specifications.
    
    Rules:
    - Accurate floor count detection (1 to 24+ stories).
    - Multi-unit floor plan synthesis (e.g. 2BHK + 3BHK per floor with elevator/stair core).
    - No pools, fire pits, or resort decks unless explicitly stated in prompt!
    """
    p_lower = prompt.lower()
    
    # 1. Floor count extraction
    floors = 2
    floor_match = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', p_lower)
    if floor_match:
        floors = max(1, min(30, int(floor_match.group(1))))
    elif "single story" in p_lower or "bungalow" in p_lower or "1 story" in p_lower or "one story" in p_lower:
        floors = 1
    elif "two story" in p_lower or "2 story" in p_lower or "duplex" in p_lower:
        floors = 2
    elif "three story" in p_lower or "3 story" in p_lower or "triplex" in p_lower:
        floors = 3
    elif "four story" in p_lower or "4 story" in p_lower:
        floors = 4
    elif "tower" in p_lower or "high rise" in p_lower or "high-rise" in p_lower or "skyscraper" in p_lower:
        floors = 12

    # 2. Amenities & features detection (Strictly prompt-driven)
    has_pool = "pool" in p_lower or "swimming" in p_lower or "jacuzzi" in p_lower
    has_fire_pit = "fire pit" in p_lower or "firepit" in p_lower or "fireplace" in p_lower
    has_solar = "solar" in p_lower or "pv" in p_lower or "photovoltaic" in p_lower or "green energy" in p_lower
    has_chiller = "chiller" in p_lower or "hvac" in p_lower or "mechanical" in p_lower or floors >= 6
    is_apartment_tower = "bhk" in p_lower or "apartment" in p_lower or "apartments" in p_lower or "flat" in p_lower or "houses" in p_lower or floors >= 5

    # 3. Aesthetics & color scheme
    is_dark = "dark" in p_lower or "black" in p_lower or "charcoal" in p_lower or "industrial" in p_lower
    is_wood = "wood" in p_lower or "cabin" in p_lower or "timber" in p_lower or "scandinavian" in p_lower
    
    wall_color = "#1E293B" if is_dark else "#78350F" if is_wood else "#E2E8F0"
    glass_color = "#38BDF8"

    elements: List[Dict[str, Any]] = []

    def uid(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:6]}"

    # =========================================================================
    # CASE A: MULTI-STORY RESIDENTIAL APARTMENT TOWER (e.g. 12-Story 2BHK + 3BHK)
    # =========================================================================
    if is_apartment_tower:
        w_tower = 26.0  # Width (West 2BHK = 11.5m, Core = 3m, East 3BHK = 11.5m)
        d_tower = 18.0  # Depth (Front to Back)
        h_floor = 3.2   # Standard residential ceiling height (meters)
        total_height = floors * h_floor

        # 1. Base Ground Podium & Foundation
        elements.append({
            "id": uid("tower_podium"),
            "layer_id": "structural",
            "type": "slab",
            "name": f"Ground Podium & Entrance Grade ({w_tower + 6}x{d_tower + 6}m)",
            "position": [0, -0.25, 0],
            "dimensions": {"width": w_tower + 6.0, "height": 0.5, "depth": d_tower + 6.0},
            "material": {"color": "#0F172A", "roughness": 0.9}
        })

        # 2. Main Building Entrance Lobby & Canopy
        elements.append({
            "id": uid("entry_canopy"),
            "layer_id": "structural",
            "type": "slab",
            "name": "Tower Main Entrance Portico & Canopy",
            "position": [0, 3.4, d_tower/2 + 2.5],
            "dimensions": {"width": 6.0, "height": 0.2, "depth": 4.0},
            "material": {"color": "#1E293B"}
        })

        # 3. Vertical Circulation Core: Dual Elevator Shafts & Fire Staircase
        elements.append({
            "id": uid("core_elevator_shaft"),
            "layer_id": "structural",
            "type": "wall",
            "name": "High-Speed Dual Elevator Core Shaft",
            "position": [-0.8, total_height / 2.0, 0],
            "dimensions": {"width": 2.4, "height": total_height + 3.0, "depth": 2.8},
            "material": {"color": "#334155"}
        })
        elements.append({
            "id": uid("core_staircase_shaft"),
            "layer_id": "structural",
            "type": "wall",
            "name": "Pressurized Emergency Fire Egress Staircase",
            "position": [1.0, total_height / 2.0, 0],
            "dimensions": {"width": 2.4, "height": total_height + 3.0, "depth": 3.6},
            "material": {"color": "#1E293B"}
        })

        # 4. Vertical MEP Risers Passing Through All Floors
        elements.append({
            "id": uid("plumb_main_soil_stack"),
            "layer_id": "plumbing",
            "type": "pipe",
            "name": "Main Building DN110 Sanitary Soil & Vent Stack",
            "position": [-2.0, total_height / 2.0, -3.0],
            "dimensions": {"width": 0.25, "height": total_height + 1.0, "depth": 0.25},
            "material": {"color": "#06B6D4"}
        })
        elements.append({
            "id": uid("plumb_water_riser"),
            "layer_id": "plumbing",
            "type": "pipe",
            "name": "Domestic Potable Water Booster Riser (DN50)",
            "position": [2.0, total_height / 2.0, -3.0],
            "dimensions": {"width": 0.18, "height": total_height + 1.0, "depth": 0.18},
            "material": {"color": "#38BDF8"}
        })
        elements.append({
            "id": uid("elec_main_busbar_riser"),
            "layer_id": "electrical",
            "type": "conduit",
            "name": "Vertical 415V 400A 3-Phase Busbar Riser Chase",
            "position": [0, total_height / 2.0, 2.5],
            "dimensions": {"width": 0.25, "height": total_height + 1.0, "depth": 0.25},
            "material": {"color": "#F59E0B"}
        })

        # 5. Floors Matrix (Levels 1 to N)
        for f in range(floors):
            y_base = f * h_floor
            floor_num = f + 1

            # A. Main Concrete Structural Floor Slab
            elements.append({
                "id": uid(f"slab_l{floor_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {floor_num} Floor Plate Slab",
                "position": [0, y_base, 0],
                "dimensions": {"width": w_tower, "height": 0.28, "depth": d_tower},
                "material": {"color": "#0F172A", "roughness": 0.8}
            })

            # B. Central Circulation Corridor
            elements.append({
                "id": uid(f"corridor_l{floor_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {floor_num} Elevator Lobby & Corridor",
                "position": [0, y_base + 0.05, 0],
                "dimensions": {"width": 2.8, "height": 0.05, "depth": d_tower - 2.0},
                "material": {"color": "#334155"}
            })

            # C. UNIT 1: 2BHK APARTMENT (WEST WING: x = -7.5m)
            # 2BHK Exterior Enclosure Walls
            elements.append({
                "id": uid(f"u1_ext_wall_l{floor_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {floor_num} Unit 1 (2BHK) Exterior Facade",
                "position": [-w_tower/2 + 0.15, y_base + h_floor/2, 0],
                "dimensions": {"width": 0.25, "height": h_floor - 0.1, "depth": d_tower},
                "material": {"color": wall_color}
            })
            # 2BHK Great Living & Dining Room
            elements.append({
                "id": uid(f"u1_living_l{floor_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {floor_num} Unit 1 (2BHK) Living Room Partition",
                "position": [-7.5, y_base + h_floor/2, 3.5],
                "dimensions": {"width": 9.5, "height": h_floor - 0.2, "depth": 0.15},
                "material": {"color": "#CBD5E1"}
            })
            # 2BHK Kitchen & Utility
            elements.append({
                "id": uid(f"u1_kitchen_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 1 (2BHK) Modular Kitchen Counter",
                "position": [-10.5, y_base + 0.5, -2.5],
                "dimensions": {"width": 3.2, "height": 0.9, "depth": 1.2},
                "material": {"color": "#475569"}
            })
            # 2BHK Master Bedroom
            elements.append({
                "id": uid(f"u1_master_bed_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 1 (2BHK) Master Bedroom Suite",
                "position": [-8.0, y_base + 0.4, -5.5],
                "dimensions": {"width": 2.2, "height": 0.8, "depth": 2.0},
                "material": {"color": "#64748B"}
            })
            # 2BHK Bedroom 2 (Guest / Kids Room)
            elements.append({
                "id": uid(f"u1_bed2_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 1 (2BHK) Second Bedroom",
                "position": [-4.0, y_base + 0.4, -5.5],
                "dimensions": {"width": 1.8, "height": 0.75, "depth": 1.9},
                "material": {"color": "#64748B"}
            })
            # 2BHK Cantilevered Balcony
            elements.append({
                "id": uid(f"u1_balcony_l{floor_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {floor_num} Unit 1 (2BHK) Sunset Balcony Deck",
                "position": [-7.5, y_base + 0.05, d_tower/2 + 0.9],
                "dimensions": {"width": 4.5, "height": 0.15, "depth": 1.8},
                "material": {"color": "#1E293B"}
            })
            elements.append({
                "id": uid(f"u1_balcony_glass_l{floor_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {floor_num} Unit 1 Balcony Glass Railing",
                "position": [-7.5, y_base + 0.55, d_tower/2 + 1.75],
                "dimensions": {"width": 4.5, "height": 1.1, "depth": 0.05},
                "material": {"color": glass_color, "opacity": 0.4}
            })

            # D. UNIT 2: 3BHK APARTMENT (EAST WING: x = +7.5m)
            # 3BHK Exterior Facade Wall
            elements.append({
                "id": uid(f"u2_ext_wall_l{floor_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {floor_num} Unit 2 (3BHK) Exterior Facade",
                "position": [w_tower/2 - 0.15, y_base + h_floor/2, 0],
                "dimensions": {"width": 0.25, "height": h_floor - 0.1, "depth": d_tower},
                "material": {"color": wall_color}
            })
            # 3BHK Grand Living & Formal Dining Hall
            elements.append({
                "id": uid(f"u2_living_l{floor_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {floor_num} Unit 2 (3BHK) Living Hall Partition",
                "position": [7.5, y_base + h_floor/2, 3.5],
                "dimensions": {"width": 9.5, "height": h_floor - 0.2, "depth": 0.15},
                "material": {"color": "#CBD5E1"}
            })
            # 3BHK Modular Kitchen & Breakfast Bar
            elements.append({
                "id": uid(f"u2_kitchen_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 2 (3BHK) Chef Kitchen & Island",
                "position": [10.5, y_base + 0.5, -2.5],
                "dimensions": {"width": 3.6, "height": 0.9, "depth": 1.4},
                "material": {"color": "#475569"}
            })
            # 3BHK Master Bedroom Suite with Ensuite
            elements.append({
                "id": uid(f"u2_master_suite_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 2 (3BHK) Master King Suite",
                "position": [9.0, y_base + 0.4, -5.5],
                "dimensions": {"width": 2.4, "height": 0.85, "depth": 2.1},
                "material": {"color": "#64748B"}
            })
            # 3BHK Bedroom 2
            elements.append({
                "id": uid(f"u2_bed2_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 2 (3BHK) Bedroom 2",
                "position": [5.0, y_base + 0.4, -5.5],
                "dimensions": {"width": 2.0, "height": 0.75, "depth": 2.0},
                "material": {"color": "#64748B"}
            })
            # 3BHK Bedroom 3 (Study / Guest Bedroom)
            elements.append({
                "id": uid(f"u2_bed3_l{floor_num}"),
                "layer_id": "structural",
                "type": "fixture",
                "name": f"Level {floor_num} Unit 2 (3BHK) Bedroom 3 / Study",
                "position": [10.0, y_base + 0.4, 0.5],
                "dimensions": {"width": 1.8, "height": 0.75, "depth": 1.9},
                "material": {"color": "#64748B"}
            })
            # 3BHK Double Balconies
            elements.append({
                "id": uid(f"u2_balcony_l{floor_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {floor_num} Unit 2 (3BHK) Sunrise Balcony",
                "position": [7.5, y_base + 0.05, d_tower/2 + 0.9],
                "dimensions": {"width": 5.0, "height": 0.15, "depth": 1.8},
                "material": {"color": "#1E293B"}
            })
            elements.append({
                "id": uid(f"u2_balcony_glass_l{floor_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {floor_num} Unit 2 Balcony Glass Railing",
                "position": [7.5, y_base + 0.55, d_tower/2 + 1.75],
                "dimensions": {"width": 5.0, "height": 1.1, "depth": 0.05},
                "material": {"color": glass_color, "opacity": 0.4}
            })

            # Facade Glass Windows (Front & Back)
            elements.append({
                "id": uid(f"facade_window_front_l{floor_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {floor_num} Front Acoustic Glazing",
                "position": [0, y_base + h_floor/2, d_tower/2 - 0.05],
                "dimensions": {"width": w_tower - 0.4, "height": 2.2, "depth": 0.1},
                "material": {"color": glass_color, "opacity": 0.35}
            })
            elements.append({
                "id": uid(f"facade_window_back_l{floor_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {floor_num} Rear Bedroom Windows",
                "position": [0, y_base + h_floor/2, -d_tower/2 + 0.05],
                "dimensions": {"width": w_tower - 0.4, "height": 1.8, "depth": 0.1},
                "material": {"color": glass_color, "opacity": 0.35}
            })

        # 6. Roof & Parapet
        y_roof = total_height
        elements.append({
            "id": uid("roof_main_slab"),
            "layer_id": "structural",
            "type": "slab",
            "name": f"Level {floors + 1} Main Roof Slab",
            "position": [0, y_roof, 0],
            "dimensions": {"width": w_tower + 0.6, "height": 0.35, "depth": d_tower + 0.6},
            "material": {"color": "#0F172A"}
        })
        # Perimeter Parapet Safety Wall (1.1m high)
        elements.append({
            "id": uid("roof_parapet_north"),
            "layer_id": "structural",
            "type": "wall",
            "name": "Rooftop Concrete Safety Parapet",
            "position": [0, y_roof + 0.55, d_tower/2 + 0.25],
            "dimensions": {"width": w_tower + 0.6, "height": 1.1, "depth": 0.2},
            "material": {"color": wall_color}
        })
        elements.append({
            "id": uid("roof_parapet_south"),
            "layer_id": "structural",
            "type": "wall",
            "name": "Rooftop Concrete Safety Parapet",
            "position": [0, y_roof + 0.55, -d_tower/2 - 0.25],
            "dimensions": {"width": w_tower + 0.6, "height": 1.1, "depth": 0.2},
            "material": {"color": wall_color}
        })

        # Rooftop Elevator Machine Room & Stair Bulkhead
        elements.append({
            "id": uid("roof_penthouse_bulkhead"),
            "layer_id": "structural",
            "type": "wall",
            "name": "Elevator Machine Room & Stair Penthouse",
            "position": [0, y_roof + 1.6, 0],
            "dimensions": {"width": 5.5, "height": 3.2, "depth": 5.5},
            "material": {"color": "#1E293B"}
        })

        # Add Chiller/HVAC or Solar ONLY IF requested or tower is tall
        if has_chiller:
            elements.append({
                "id": uid("roof_hvac_chiller_1"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Central VRF Rooftop Chiller Unit 1 (50 kW)",
                "position": [-6.0, y_roof + 1.0, 3.0],
                "dimensions": {"width": 2.2, "height": 1.6, "depth": 1.8},
                "material": {"color": "#64748B"}
            })
            elements.append({
                "id": uid("roof_hvac_chiller_2"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Central VRF Rooftop Chiller Unit 2 (50 kW)",
                "position": [6.0, y_roof + 1.0, 3.0],
                "dimensions": {"width": 2.2, "height": 1.6, "depth": 1.8},
                "material": {"color": "#64748B"}
            })

        if has_solar:
            elements.append({
                "id": uid("roof_solar_array"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Rooftop Monocrystalline Solar PV Array",
                "position": [0, y_roof + 0.5, -4.5],
                "dimensions": {"width": 14.0, "height": 0.2, "depth": 5.0},
                "material": {"color": "#0284C7"}
            })

        # Add pool ONLY IF explicitly requested in prompt
        if has_pool:
            elements.append({
                "id": uid("rooftop_pool"),
                "layer_id": "structural",
                "type": "slab",
                "name": "Rooftop Infinity Swimming Pool",
                "position": [0, y_roof + 0.4, 4.0],
                "dimensions": {"width": 8.0, "height": 0.6, "depth": 4.0},
                "material": {"color": "#06B6D4", "opacity": 0.85}
            })

        return elements

    # =========================================================================
    # CASE B: RESIDENTIAL VILLA / RESIDENCE (Prompt-Aware)
    # =========================================================================
    w = 16.0
    d = 13.0
    h_floor = 3.6

    # Ground Podium
    elements.append({
        "id": uid("villa_podium"),
        "layer_id": "structural",
        "type": "slab",
        "name": "Site Grade Platform & Driveway",
        "position": [0, -0.2, 2.0],
        "dimensions": {"width": w + 6.0, "height": 0.35, "depth": d + 6.0},
        "material": {"color": "#1E212B", "roughness": 0.9}
    })

    # Structural Floors
    for f in range(floors):
        y_slab = f * h_floor
        elements.append({
            "id": uid(f"slab_l{f+1}"),
            "layer_id": "structural",
            "type": "slab",
            "name": f"Level {f+1} Main Slab ({w}x{d}m)",
            "position": [0, y_slab - 0.15, 0],
            "dimensions": {"width": w + 0.4, "height": 0.3, "depth": d + 0.4},
            "material": {"color": "#0F172A" if is_dark else "#F1F5F9", "roughness": 0.75}
        })
        # Exterior Walls
        elements.append({
            "id": uid(f"wall_north_l{f+1}"),
            "layer_id": "structural",
            "type": "wall",
            "name": f"Level {f+1} North Facade Wall",
            "position": [0, y_slab + h_floor/2, d/2],
            "dimensions": {"width": w, "height": h_floor, "depth": 0.25},
            "material": {"color": wall_color}
        })
        elements.append({
            "id": uid(f"wall_south_l{f+1}"),
            "layer_id": "structural",
            "type": "wall",
            "name": f"Level {f+1} South Facade Wall",
            "position": [0, y_slab + h_floor/2, -d/2],
            "dimensions": {"width": w, "height": h_floor, "depth": 0.25},
            "material": {"color": wall_color}
        })
        # Glass Curtain
        elements.append({
            "id": uid(f"glass_front_l{f+1}"),
            "layer_id": "structural",
            "type": "window",
            "name": f"Level {f+1} Architectural Glass Window",
            "position": [0, y_slab + h_floor/2, d/2 + 0.05],
            "dimensions": {"width": w - 2.0, "height": h_floor - 0.4, "depth": 0.08},
            "material": {"color": glass_color, "opacity": 0.35}
        })

    # Living Room Furniture & Island
    elements.append({
        "id": uid("living_sofa"),
        "layer_id": "structural",
        "type": "fixture",
        "name": "Boucle Sectional Lounge Sofa",
        "position": [-3.5, 0.45, 2.5],
        "dimensions": {"width": 3.8, "height": 0.85, "depth": 2.6},
        "material": {"color": "#475569"}
    })
    elements.append({
        "id": uid("kitchen_island"),
        "layer_id": "structural",
        "type": "fixture",
        "name": "Calacatta Marble Waterfall Kitchen Island",
        "position": [3.8, 0.5, -2.0],
        "dimensions": {"width": 3.2, "height": 0.95, "depth": 1.4},
        "material": {"color": "#F8FAFC"}
    })

    # Master Bedroom (Level 2 if 2+ floors)
    if floors >= 2:
        elements.append({
            "id": uid("master_bed"),
            "layer_id": "structural",
            "type": "fixture",
            "name": "King Platform Bed & Acoustic Headboard",
            "position": [-3.8, h_floor + 0.5, 2.0],
            "dimensions": {"width": 2.4, "height": 0.95, "depth": 2.3},
            "material": {"color": "#334155"}
        })

    # Vertical MEP Risers
    elements.append({
        "id": uid("elec_panel"),
        "layer_id": "electrical",
        "type": "fixture",
        "name": "Main 200A Electrical Distribution Panel",
        "position": [-w/2 + 0.3, 1.2, -d/2 + 1.2],
        "dimensions": {"width": 0.2, "height": 1.1, "depth": 0.8},
        "material": {"color": "#F59E0B"}
    })
    elements.append({
        "id": uid("plumb_stack"),
        "layer_id": "plumbing",
        "type": "pipe",
        "name": "Vertical 110mm PVC-U Drainage Wet Stack",
        "position": [w/2 - 0.4, floors * h_floor / 2.0, -d/2 + 1.2],
        "dimensions": {"width": 0.2, "height": floors * h_floor, "depth": 0.2},
        "material": {"color": "#06B6D4"}
    })

    # Amenities ONLY IF requested
    if has_pool:
        elements.append({
            "id": uid("infinity_pool"),
            "layer_id": "structural",
            "type": "slab",
            "name": "Infinity Edge Swimming Pool",
            "position": [-w/2 - 4.5, 0.1, 2.0],
            "dimensions": {"width": 6.0, "height": 0.5, "depth": 10.0},
            "material": {"color": "#06B6D4", "opacity": 0.85}
        })

    if has_fire_pit:
        elements.append({
            "id": uid("fire_pit"),
            "layer_id": "structural",
            "type": "fixture",
            "name": "Sunken Basalt Stone Fire Pit",
            "position": [-w/2 - 4.5, 0.3, -4.5],
            "dimensions": {"width": 2.5, "height": 0.4, "depth": 2.5},
            "material": {"color": "#EA580C"}
        })

    if has_solar:
        elements.append({
            "id": uid("solar_panels"),
            "layer_id": "electrical",
            "type": "fixture",
            "name": "Rooftop Solar PV Array",
            "position": [0, floors * h_floor + 0.4, 0],
            "dimensions": {"width": 10.0, "height": 0.15, "depth": 6.0},
            "material": {"color": "#0284C7"}
        })

    return elements

def generate_architectural_layout(prompt: str, project_id: int) -> List[Dict[str, Any]]:
    """
    Main generator calling Gemini Flash GenAI with failover to the prompt-aware architectural engine.
    """
    p_lower = prompt.lower()
    
    # If the user specifically provided structured floor & unit instructions, synthesize directly
    if "story" in p_lower or "floor" in p_lower or "bhk" in p_lower or "apartment" in p_lower:
        return generate_aaa_building_model(prompt)

    system_prompt = """
    You are a Lead Architectural Systems Engine for OpenBIM / IFC models.
    Generate a full-fledged 3D architectural building model matching the user's prompt (stories, style, rooms, and MEP).
    DO NOT add swimming pools or outdoor fire pits unless explicitly mentioned in the prompt!
    
    OUTPUT SCHEMA:
    Return a strictly valid JSON array:
    [
      {
        "id": "string",
        "layer_id": "structural" | "electrical" | "plumbing",
        "type": "slab" | "wall" | "column" | "window" | "door" | "fixture" | "conduit" | "pipe" | "light",
        "name": "Descriptive Element Name",
        "position": [x, y, z],
        "dimensions": {"width": float, "height": float, "depth": float},
        "material": {"color": "#hex"}
      }
    ]
    Generate 40 to 80 detailed architectural elements. Respond ONLY with the JSON array starting with `[` and ending with `]`.
    """

    body = {
        "contents": [
            {
                "parts": [
                    {"text": system_prompt},
                    {"text": f"USER PROMPT: {prompt}\nGenerate the complete architectural 3D building JSON array."}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    req = urllib.request.Request(
        GEMINI_URL, 
        data=json.dumps(body).encode('utf-8'), 
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            response_data = json.loads(resp.read().decode('utf-8'))
            content = response_data['candidates'][0]['content']['parts'][0]['text'].strip()
            
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                content = match.group(0)
            
            elements = json.loads(content)
            if isinstance(elements, list) and len(elements) >= 20:
                for el in elements:
                    if 'id' not in el or not el['id']:
                        el['id'] = f"gen_{uuid.uuid4().hex[:8]}"
                return elements
            else:
                return generate_aaa_building_model(prompt)

    except Exception as e:
        print(f"GenAI fallback to prompt-aware AAA Engine: {e}")
        return generate_aaa_building_model(prompt)
