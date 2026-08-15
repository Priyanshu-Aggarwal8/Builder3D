import json
import uuid
import re
import copy
from typing import List, Dict, Any, Optional

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

class MetaArchitectAgent:
    """
    Principal Meta-Agent coordinating specialized sub-agents:
    1. Typology & Scale Agent: Classifies scale (building only vs storey vs unit).
    2. Structural & Massing Agent: Generates multi-story facades, mullions, slabs, and elevator cores.
    3. Hyper-Detailed 2BHK & 3BHK Unit Architecture: Generates complete, fully furnished suites with distinct rooms,
       curtains, area rugs, kitchen islands with faucets, dining sets with pendant lighting, master beds with headboards,
       spa bathrooms with soaking tubs, and balconies.
    4. In-Place Customizer & State Preserver: Mutates existing models incrementally without scrapping user work!
    5. MEP Systems Agent: Routes vertical utility risers, electrical switchboards, and drainage stacks.
    """

    def __init__(self):
        pass

    def parse_scale_and_typology(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower()

        floors = 12
        floor_match = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', p)
        if floor_match:
            floors = max(1, min(36, int(floor_match.group(1))))
        elif "single story" in p or "bungalow" in p or "1 story" in p:
            floors = 1
        elif "two story" in p or "2 story" in p or "duplex" in p:
            floors = 2
        elif "three story" in p or "3 story" in p:
            floors = 3
        elif "tower" in p or "high rise" in p or "high-rise" in p or "skyscraper" in p:
            floors = 12

        has_city = any(k in p for k in ["city", "urban district", "downtown", "metropolis", "cityscape", "skyline"])
        has_society = any(k in p for k in ["society", "gated community", "masterplan", "campus", "enclave", "multiple towers", "condo complex", "residential complex"])
        
        is_apartment = any(k in p for k in ["bhk", "apartment", "apartments", "flat", "flats", "houses per floor", "residential building"]) or floors >= 4
        has_2bhk = "2bhk" in p or "2 bhk" in p or "2 bedroom" in p
        has_3bhk = "3bhk" in p or "3 bhk" in p or "3 bedroom" in p
        
        if is_apartment and not (has_2bhk or has_3bhk):
            has_2bhk = True
            has_3bhk = True

        has_pool = any(k in p for k in ["pool", "swimming", "jacuzzi", "infinity pool"])
        has_fire_pit = any(k in p for k in ["fire pit", "firepit", "fireplace"])
        has_solar = any(k in p for k in ["solar", "photovoltaic", "pv array", "green energy"]) or floors >= 6
        has_balcony = "balcony" in p or "balconies" in p or is_apartment

        style = "Japandi Scandinavian"
        if any(k in p for k in ["luxury", "italian", "marble", "calacatta", "mansion", "penthouse"]):
            style = "Luxury Calacatta"
        elif any(k in p for k in ["industrial", "loft", "brick", "concrete", "steel"]):
            style = "Industrial Loft"
        elif any(k in p for k in ["biophilic", "sustainable", "green", "timber", "plant"]):
            style = "Biophilic Green"
        elif any(k in p for k in ["contemporary", "modern", "minimalist"]):
            style = "Contemporary Modern"

        return {
            "floors": floors,
            "has_city": has_city,
            "has_society": has_society,
            "is_apartment": is_apartment,
            "has_2bhk": has_2bhk,
            "has_3bhk": has_3bhk,
            "has_pool": has_pool,
            "has_fire_pit": has_fire_pit,
            "has_solar": has_solar,
            "has_balcony": has_balcony,
            "style": style,
            "available_scales": (
                ["city", "society", "building", "storey", "apartment", "mep"] if has_city else
                ["society", "building", "storey", "apartment", "mep"] if has_society else
                ["building", "storey", "apartment", "mep"]
            )
        }

    def get_style_materials(self, style: str) -> Dict[str, Any]:
        if style == "Japandi Scandinavian":
            return {
                "wall": "#E5E5E5",
                "wall_inner": "#FAF7F2",
                "floor_living": "#D4A373",
                "floor_kitchen": "#F5F5F4",
                "floor_bath": "#44403C",
                "accent": "#78350F",
                "furniture": "#D6C7B2",
                "glass": "#BAE6FD",
                "mullion": "#171717",
                "fascia": "#262626",
                "curtain": "#F8FAFC",
                "opacity": 0.45
            }
        elif style == "Luxury Calacatta":
            return {
                "wall": "#F8FAFC",
                "wall_inner": "#FFFFFF",
                "floor_living": "#EDE9FE",
                "floor_kitchen": "#FFFFFF",
                "floor_bath": "#0F172A",
                "accent": "#B45309",
                "furniture": "#0F172A",
                "glass": "#7DD3FC",
                "mullion": "#09090B",
                "fascia": "#0F172A",
                "curtain": "#FAF5FF",
                "opacity": 0.4
            }
        elif style == "Industrial Loft":
            return {
                "wall": "#334155",
                "wall_inner": "#475569",
                "floor_living": "#64748B",
                "floor_kitchen": "#334155",
                "floor_bath": "#1E293B",
                "accent": "#B45309",
                "furniture": "#0F172A",
                "glass": "#94A3B8",
                "mullion": "#0A0A0A",
                "fascia": "#1E293B",
                "curtain": "#94A3B8",
                "opacity": 0.5
            }
        else:
            return {
                "wall": "#E2E8F0",
                "wall_inner": "#F8FAFC",
                "floor_living": "#C9935E",
                "floor_kitchen": "#E2E8F0",
                "floor_bath": "#334155",
                "accent": "#0F172A",
                "furniture": "#334155",
                "glass": "#38BDF8",
                "mullion": "#18181B",
                "fascia": "#1E293B",
                "curtain": "#FFFFFF",
                "opacity": 0.4
            }

    def modify_existing_model(self, existing_model: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        model = copy.deepcopy(existing_model)
        p = prompt.lower()

        floor_match = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', p)
        if floor_match:
            new_floors = max(1, min(36, int(floor_match.group(1))))
            return self.synthesize_model(f"{new_floors}-story building with {model.get('meta', {}).get('style', 'Japandi Scandinavian')}", model.get("id", 1))

        new_style = None
        if any(k in p for k in ["luxury", "calacatta", "marble"]):
            new_style = "Luxury Calacatta"
        elif any(k in p for k in ["industrial", "loft", "concrete"]):
            new_style = "Industrial Loft"
        elif any(k in p for k in ["japandi", "scandinavian", "oak"]):
            new_style = "Japandi Scandinavian"
        elif any(k in p for k in ["biophilic", "green", "timber"]):
            new_style = "Biophilic Green"

        if new_style:
            mats = self.get_style_materials(new_style)
            model["meta"]["style"] = new_style
            if "layers" in model and "structural" in model["layers"]:
                for el in model["layers"]["structural"].get("elements", []):
                    name_lower = el.get("name", "").lower()
                    if "sofa" in name_lower or "bed" in name_lower or "lounge" in name_lower:
                        el["material"]["color"] = mats["furniture"]
                    elif "floor" in name_lower or "finish" in name_lower:
                        el["material"]["color"] = mats["floor_living"]
                    elif "wall" in name_lower:
                        el["material"]["color"] = mats["wall"]
            return model

        if "pool" in p and not any("pool" in el.get("name", "").lower() for el in model.get("layers", {}).get("structural", {}).get("elements", [])):
            pool_el = {
                "id": uid("infinity_pool"),
                "layer_id": "structural",
                "type": "slab",
                "name": "Rooftop Infinity Edge Swimming Pool",
                "position": [6.0, model.get("meta", {}).get("floors", 12) * 3.2 + 0.3, 0],
                "dimensions": {"width": 6.0, "height": 0.5, "depth": 9.0},
                "material": {"color": "#06B6D4", "opacity": 0.85}
            }
            model["layers"]["structural"]["elements"].append(pool_el)
            return model

        if "solar" in p and not any("solar" in el.get("name", "").lower() for el in model.get("layers", {}).get("electrical", {}).get("elements", [])):
            solar_el = {
                "id": uid("solar_pv"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Rooftop High-Efficiency Photovoltaic Solar Array (18kWp)",
                "position": [0, model.get("meta", {}).get("floors", 12) * 3.2 + 3.2, 0],
                "dimensions": {"width": 14.0, "height": 0.15, "depth": 7.0},
                "material": {"color": "#0284C7"}
            }
            model["layers"]["electrical"]["elements"].append(solar_el)
            return model

        return model

    def synthesize_model(self, prompt: str, project_id: int = 1) -> Dict[str, Any]:
        spec = self.parse_scale_and_typology(prompt)
        mats = self.get_style_materials(spec["style"])

        floors = spec["floors"]
        is_apartment = spec["is_apartment"]
        h_floor = 3.2
        total_height = floors * h_floor

        elements: List[Dict[str, Any]] = []

        w_bldg = 26.0 if is_apartment else 16.0
        d_bldg = 18.0 if is_apartment else 13.0

        # Ground Grade Granite Plaza Platform
        elements.append({
            "id": uid("site_podium"),
            "layer_id": "structural",
            "type": "slab",
            "name": f"Ground Entrance Granite Plaza ({w_bldg + 8}x{d_bldg + 8}m)",
            "position": [0, -0.25, 0],
            "dimensions": {"width": w_bldg + 8.0, "height": 0.5, "depth": d_bldg + 8.0},
            "material": {"color": "#0F172A", "roughness": 0.9}
        })

        # Ground Lobby Entrance Canopy
        elements.append({
            "id": uid("entry_canopy"),
            "layer_id": "structural",
            "type": "slab",
            "name": "Grand Entrance Cantilevered Canopy",
            "position": [0, 3.4, d_bldg / 2 + 2.2],
            "dimensions": {"width": 8.0, "height": 0.25, "depth": 4.5},
            "material": {"color": "#171717", "roughness": 0.2}
        })

        # Floor-by-Floor Construction
        for f in range(floors):
            y_base = f * h_floor
            f_num = f + 1

            # 1. Structural Post-Tensioned Concrete Floor Slab with Fascia Band
            elements.append({
                "id": uid(f"slab_L{f_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {f_num} Post-Tensioned Floor Slab",
                "position": [0, y_base + 0.15, 0],
                "dimensions": {"width": w_bldg, "height": 0.3, "depth": d_bldg},
                "material": {"color": mats["fascia"], "roughness": 0.7}
            })

            # 2. Hardwood / Porcelain Finished Flooring
            elements.append({
                "id": uid(f"floor_finish_L{f_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {f_num} {spec['style']} Finished Flooring",
                "position": [0, y_base + 0.31, 0],
                "dimensions": {"width": w_bldg - 0.3, "height": 0.02, "depth": d_bldg - 0.3},
                "material": {"color": mats["floor_living"], "roughness": 0.55}
            })

            # 3. Structural RC Columns
            for cx in [-w_bldg / 2 + 0.5, -w_bldg / 4, w_bldg / 4, w_bldg / 2 - 0.5]:
                for cz in [-d_bldg / 2 + 0.5, 0, d_bldg / 2 - 0.5]:
                    elements.append({
                        "id": uid(f"col_L{f_num}"),
                        "layer_id": "structural",
                        "type": "column",
                        "name": f"Level {f_num} Structural RC Column",
                        "position": [cx, y_base + h_floor / 2, cz],
                        "dimensions": {"width": 0.5, "height": h_floor, "depth": 0.5},
                        "material": {"color": "#171717"}
                    })

            # 4. Central Core: Dual Elevator Shaft & Pressurized Fire Exit Stair Core
            elements.append({
                "id": uid(f"lift_shaft_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} Dual Elevator Shaft Core",
                "position": [0, y_base + h_floor / 2, -1.5],
                "dimensions": {"width": 3.6, "height": h_floor, "depth": 3.0},
                "material": {"color": "#1E293B"}
            })
            elements.append({
                "id": uid(f"stair_core_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} Fire Escape Stair Core",
                "position": [0, y_base + h_floor / 2, 2.0],
                "dimensions": {"width": 3.6, "height": h_floor, "depth": 2.8},
                "material": {"color": "#1E293B"}
            })

            # 5. Exterior Curtain Glazing & Mullion Ribs
            elements.append({
                "id": uid(f"curtain_s_L{f_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {f_num} South Curtain Glass Facade",
                "position": [0, y_base + h_floor / 2, d_bldg / 2],
                "dimensions": {"width": w_bldg, "height": h_floor - 0.2, "depth": 0.08},
                "material": {"color": mats["glass"], "opacity": mats["opacity"], "transmission": 0.92}
            })
            elements.append({
                "id": uid(f"curtain_n_L{f_num}"),
                "layer_id": "structural",
                "type": "window",
                "name": f"Level {f_num} North Curtain Glass Facade",
                "position": [0, y_base + h_floor / 2, -d_bldg / 2],
                "dimensions": {"width": w_bldg, "height": h_floor - 0.2, "depth": 0.08},
                "material": {"color": mats["glass"], "opacity": mats["opacity"], "transmission": 0.92}
            })
            elements.append({
                "id": uid(f"facade_w_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} West Architectural Shear Wall",
                "position": [-w_bldg / 2, y_base + h_floor / 2, 0],
                "dimensions": {"width": 0.3, "height": h_floor, "depth": d_bldg},
                "material": {"color": mats["wall"]}
            })
            elements.append({
                "id": uid(f"facade_e_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} East Architectural Shear Wall",
                "position": [w_bldg / 2, y_base + h_floor / 2, 0],
                "dimensions": {"width": 0.3, "height": h_floor, "depth": d_bldg},
                "material": {"color": mats["wall"]}
            })

            # Facade Aluminum Mullion Vertical Ribs
            for mx in [-w_bldg / 2 + 3.0, -w_bldg / 6, w_bldg / 6, w_bldg / 2 - 3.0]:
                elements.append({
                    "id": uid(f"mullion_s_L{f_num}"),
                    "layer_id": "structural",
                    "type": "column",
                    "name": f"Level {f_num} South Aluminum Mullion Rib",
                    "position": [mx, y_base + h_floor / 2, d_bldg / 2 + 0.06],
                    "dimensions": {"width": 0.12, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["mullion"]}
                })
                elements.append({
                    "id": uid(f"mullion_n_L{f_num}"),
                    "layer_id": "structural",
                    "type": "column",
                    "name": f"Level {f_num} North Aluminum Mullion Rib",
                    "position": [mx, y_base + h_floor / 2, -d_bldg / 2 - 0.06],
                    "dimensions": {"width": 0.12, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["mullion"]}
                })

            # 6. Sculptural Cantilevered Balconies
            if spec["has_balcony"]:
                elements.append({
                    "id": uid(f"balc_slab_w_L{f_num}"),
                    "layer_id": "structural",
                    "type": "slab",
                    "name": f"Level {f_num} Sunset Balcony Teak Deck",
                    "position": [-w_bldg / 4 - 1.0, y_base + 0.15, d_bldg / 2 + 1.2],
                    "dimensions": {"width": w_bldg / 2 - 2.0, "height": 0.25, "depth": 2.4},
                    "material": {"color": mats["fascia"]}
                })
                elements.append({
                    "id": uid(f"balc_glass_w_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"Level {f_num} Sunset Balcony Tempered Glass Balustrade",
                    "position": [-w_bldg / 4 - 1.0, y_base + 0.75, d_bldg / 2 + 2.35],
                    "dimensions": {"width": w_bldg / 2 - 2.0, "height": 1.1, "depth": 0.05},
                    "material": {"color": mats["glass"], "opacity": 0.45}
                })

                elements.append({
                    "id": uid(f"balc_slab_e_L{f_num}"),
                    "layer_id": "structural",
                    "type": "slab",
                    "name": f"Level {f_num} Sunrise Balcony Teak Deck",
                    "position": [w_bldg / 4 + 1.0, y_base + 0.15, d_bldg / 2 + 1.2],
                    "dimensions": {"width": w_bldg / 2 - 2.0, "height": 0.25, "depth": 2.4},
                    "material": {"color": mats["fascia"]}
                })
                elements.append({
                    "id": uid(f"balc_glass_e_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"Level {f_num} Sunrise Balcony Tempered Glass Balustrade",
                    "position": [w_bldg / 4 + 1.0, y_base + 0.75, d_bldg / 2 + 2.35],
                    "dimensions": {"width": w_bldg / 2 - 2.0, "height": 1.1, "depth": 0.05},
                    "material": {"color": mats["glass"], "opacity": 0.45}
                })

            # =========================================================================
            # 7. HIGH-FIDELITY COMPOSITE HOUSE INTERIORS (2BHK & 3BHK SUITES)
            # =========================================================================
            if is_apartment and spec["has_2bhk"]:
                x_u1 = -w_bldg / 4 - 1.0

                # Corridor Entrance Wall with 0.9m Doorway Opening
                elements.append({
                    "id": uid(f"u1_wall_corridor_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 Corridor Wall",
                    "position": [x_u1 + 4.5, y_base + h_floor / 2, -2.0],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": d_bldg / 2 - 1.0},
                    "material": {"color": mats["wall_inner"]}
                })
                elements.append({
                    "id": uid(f"u1_door_entry_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Solid Timber Entrance Door",
                    "position": [x_u1 + 4.5, y_base + 1.1, 0.5],
                    "dimensions": {"width": 0.1, "height": 2.2, "depth": 0.9},
                    "material": {"color": mats["accent"]}
                })

                # Architectural Sheer Curtains along South Window
                elements.append({
                    "id": uid(f"u1_curtain_s_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"L{f_num} Unit 1 Flowing Pleated Sheer Curtains",
                    "position": [x_u1 - 1.0, y_base + h_floor / 2, d_bldg / 2 - 0.25],
                    "dimensions": {"width": 6.5, "height": h_floor - 0.2, "depth": 0.08},
                    "material": {"color": mats["curtain"], "opacity": 0.65, "transparent": True}
                })

                # Master Suite Acoustic Partition Wall
                elements.append({
                    "id": uid(f"u1_wall_master_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 Master Suite Wall",
                    "position": [x_u1 - 1.0, y_base + h_floor / 2, 1.5],
                    "dimensions": {"width": 6.8, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["wall_inner"]}
                })
                # Bedroom 2 Partition Wall
                elements.append({
                    "id": uid(f"u1_wall_bed2_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 Bedroom 2 Wall",
                    "position": [x_u1 + 1.8, y_base + h_floor / 2, 3.8],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": 4.5},
                    "material": {"color": mats["wall_inner"]}
                })
                # Bathroom Enclosure Wall
                elements.append({
                    "id": uid(f"u1_wall_bath_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 En-Suite Bath Enclosure Wall",
                    "position": [-w_bldg / 2 + 3.2, y_base + h_floor / 2, 2.5],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": 3.0},
                    "material": {"color": mats["wall_inner"]}
                })

                # LIVING ROOM & MEDIA ZONE
                elements.append({
                    "id": uid(f"u1_sofa_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 L-Sectional Bouclé Sofa & Pillows",
                    "position": [x_u1 - 1.2, y_base + 0.45, -2.5],
                    "dimensions": {"width": 3.4, "height": 0.75, "depth": 2.2},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_rug_L{f_num}"),
                    "layer_id": "structural",
                    "type": "slab",
                    "name": f"L{f_num} Unit 1 Woven Living Room Area Rug",
                    "position": [x_u1 - 1.2, y_base + 0.32, -2.5],
                    "dimensions": {"width": 3.8, "height": 0.02, "depth": 3.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_coffee_table_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Fluted Oak Coffee Table",
                    "position": [x_u1 - 1.2, y_base + 0.22, -2.5],
                    "dimensions": {"width": 1.6, "height": 0.35, "depth": 0.85},
                    "material": {"color": mats["floor_living"]}
                })
                elements.append({
                    "id": uid(f"u1_tv_console_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Low-Profile TV Media Console & 75\" OLED",
                    "position": [x_u1 - 1.2, y_base + 0.45, -0.4],
                    "dimensions": {"width": 2.6, "height": 0.85, "depth": 0.45},
                    "material": {"color": "#171717"}
                })

                # DINING SUITE
                elements.append({
                    "id": uid(f"u1_dining_set_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Solid Walnut Dining Table & 6 Chairs",
                    "position": [x_u1 + 2.2, y_base + 0.45, -1.8],
                    "dimensions": {"width": 2.6, "height": 0.75, "depth": 1.1},
                    "material": {"color": mats["accent"]}
                })

                # KITCHEN
                elements.append({
                    "id": uid(f"u1_kitchen_island_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Waterfall Island with Faucet & Barstools",
                    "position": [x_u1 + 2.2, y_base + 0.5, -4.5],
                    "dimensions": {"width": 2.8, "height": 0.95, "depth": 1.1},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"u1_kitchen_base_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Induction Hob & Base Cabinets",
                    "position": [x_u1 + 2.2, y_base + 0.5, -7.5],
                    "dimensions": {"width": 3.8, "height": 0.92, "depth": 0.65},
                    "material": {"color": "#1E293B"}
                })

                # MASTER SUITE
                elements.append({
                    "id": uid(f"u1_master_bed_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 King Platform Bed & Pillows",
                    "position": [x_u1 - 1.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 2.2, "height": 0.55, "depth": 2.4},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_master_headboard_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 Fluted Timber Acoustic Headboard",
                    "position": [x_u1 - 1.2, y_base + 1.2, 5.8],
                    "dimensions": {"width": 3.2, "height": 1.5, "depth": 0.12},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u1_master_nightstand_l_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Bedside Floating Nightstand & Lamp",
                    "position": [x_u1 - 2.8, y_base + 0.4, 5.2],
                    "dimensions": {"width": 0.6, "height": 0.5, "depth": 0.5},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u1_master_nightstand_r_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Bedside Floating Nightstand & Lamp Right",
                    "position": [x_u1 + 0.4, y_base + 0.4, 5.2],
                    "dimensions": {"width": 0.6, "height": 0.5, "depth": 0.5},
                    "material": {"color": mats["accent"]}
                })

                # BEDROOM 2
                elements.append({
                    "id": uid(f"u1_bed2_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Bedroom 2 Queen Bed",
                    "position": [x_u1 + 3.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 1.8, "height": 0.55, "depth": 2.0},
                    "material": {"color": mats["furniture"]}
                })

                # BATHROOM
                elements.append({
                    "id": uid(f"u1_bath_vanity_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Floating Double Vanity & Backlit Mirror",
                    "position": [-w_bldg / 2 + 1.8, y_base + 0.5, 2.5],
                    "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.6},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"u1_bath_tub_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Freestanding Soaking Tub & Floor Mixer",
                    "position": [-w_bldg / 2 + 1.8, y_base + 0.35, -0.8],
                    "dimensions": {"width": 1.7, "height": 0.65, "depth": 0.85},
                    "material": {"color": "#FAFAFA"}
                })
                elements.append({
                    "id": uid(f"u1_bath_shower_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "window",
                    "name": f"L{f_num} Unit 1 Frameless Glass Walk-In Shower",
                    "position": [-w_bldg / 2 + 1.8, y_base + 1.1, 1.2],
                    "dimensions": {"width": 1.2, "height": 2.2, "depth": 0.05},
                    "material": {"color": mats["glass"], "opacity": 0.4}
                })

            if is_apartment and spec["has_3bhk"]:
                x_u2 = w_bldg / 4 + 1.0

                # Corridor Entrance Wall with 0.9m Doorway Opening
                elements.append({
                    "id": uid(f"u2_wall_corridor_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 Corridor Wall",
                    "position": [x_u2 - 4.5, y_base + h_floor / 2, -2.0],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": d_bldg / 2 - 1.0},
                    "material": {"color": mats["wall_inner"]}
                })
                elements.append({
                    "id": uid(f"u2_door_entry_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Solid Timber Entrance Door",
                    "position": [x_u2 - 4.5, y_base + 1.1, 0.5],
                    "dimensions": {"width": 0.1, "height": 2.2, "depth": 0.9},
                    "material": {"color": mats["accent"]}
                })

                # Architectural Sheer Curtains along South Window
                elements.append({
                    "id": uid(f"u2_curtain_s_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"L{f_num} Unit 2 Flowing Pleated Sheer Curtains",
                    "position": [x_u2 + 1.0, y_base + h_floor / 2, d_bldg / 2 - 0.25],
                    "dimensions": {"width": 6.5, "height": h_floor - 0.2, "depth": 0.08},
                    "material": {"color": mats["curtain"], "opacity": 0.65, "transparent": True}
                })

                # Bedroom Wing Partition Wall
                elements.append({
                    "id": uid(f"u2_wall_beds_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 Bedroom Wing Wall",
                    "position": [x_u2, y_base + h_floor / 2, 1.2],
                    "dimensions": {"width": 6.8, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["wall_inner"]}
                })
                # Bedroom 2 & 3 Dividing Wall
                elements.append({
                    "id": uid(f"u2_wall_bed23_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 Bedroom 2/3 Dividing Wall",
                    "position": [x_u2 - 1.8, y_base + h_floor / 2, 3.8],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": 4.5},
                    "material": {"color": mats["wall_inner"]}
                })
                # Bathroom Enclosure Wall
                elements.append({
                    "id": uid(f"u2_wall_bath_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 En-Suite Bath Enclosure Wall",
                    "position": [w_bldg / 2 - 3.2, y_base + h_floor / 2, 2.5],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": 3.0},
                    "material": {"color": mats["wall_inner"]}
                })

                # LIVING ROOM
                elements.append({
                    "id": uid(f"u2_sofa_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 L-Sectional Bouclé Sofa & Pillows",
                    "position": [x_u2 + 1.2, y_base + 0.45, -2.5],
                    "dimensions": {"width": 3.4, "height": 0.75, "depth": 2.2},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_rug_L{f_num}"),
                    "layer_id": "structural",
                    "type": "slab",
                    "name": f"L{f_num} Unit 2 Woven Living Room Area Rug",
                    "position": [x_u2 + 1.2, y_base + 0.32, -2.5],
                    "dimensions": {"width": 3.8, "height": 0.02, "depth": 3.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_coffee_table_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Fluted Oak Coffee Table",
                    "position": [x_u2 + 1.2, y_base + 0.22, -2.5],
                    "dimensions": {"width": 1.6, "height": 0.35, "depth": 0.85},
                    "material": {"color": mats["floor_living"]}
                })
                elements.append({
                    "id": uid(f"u2_tv_console_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Low-Profile TV Media Console & 75\" OLED",
                    "position": [x_u2 + 1.2, y_base + 0.45, -0.4],
                    "dimensions": {"width": 2.6, "height": 0.85, "depth": 0.45},
                    "material": {"color": "#171717"}
                })

                # DINING SUITE
                elements.append({
                    "id": uid(f"u2_dining_set_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Solid Walnut Dining Table & 6 Chairs",
                    "position": [x_u2 - 2.2, y_base + 0.45, -1.8],
                    "dimensions": {"width": 2.6, "height": 0.75, "depth": 1.1},
                    "material": {"color": mats["accent"]}
                })

                # KITCHEN
                elements.append({
                    "id": uid(f"u2_kitchen_island_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Waterfall Island with Faucet & Barstools",
                    "position": [x_u2 - 2.2, y_base + 0.5, -4.5],
                    "dimensions": {"width": 2.8, "height": 0.95, "depth": 1.1},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"u2_kitchen_base_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Induction Hob & Base Cabinets",
                    "position": [x_u2 - 2.2, y_base + 0.5, -7.5],
                    "dimensions": {"width": 3.8, "height": 0.92, "depth": 0.65},
                    "material": {"color": "#1E293B"}
                })

                # MASTER SUITE
                elements.append({
                    "id": uid(f"u2_master_bed_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 King Platform Bed & Pillows",
                    "position": [x_u2 + 1.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 2.2, "height": 0.55, "depth": 2.4},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_master_headboard_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 Fluted Timber Acoustic Headboard",
                    "position": [x_u2 + 1.2, y_base + 1.2, 5.8],
                    "dimensions": {"width": 3.2, "height": 1.5, "depth": 0.12},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u2_master_nightstand_l_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Bedside Floating Nightstand & Lamp",
                    "position": [x_u2 - 0.4, y_base + 0.4, 5.2],
                    "dimensions": {"width": 0.6, "height": 0.5, "depth": 0.5},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u2_master_nightstand_r_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Bedside Floating Nightstand & Lamp Right",
                    "position": [x_u2 + 2.8, y_base + 0.4, 5.2],
                    "dimensions": {"width": 0.6, "height": 0.5, "depth": 0.5},
                    "material": {"color": mats["accent"]}
                })

                # BEDROOM 2 & 3
                elements.append({
                    "id": uid(f"u2_bed2_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Bedroom 2 Queen Bed",
                    "position": [x_u2 - 3.2, y_base + 0.45, 3.5],
                    "dimensions": {"width": 1.8, "height": 0.55, "depth": 2.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_bed3_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Bedroom 3 Twin Bed",
                    "position": [x_u2 - 3.2, y_base + 0.45, 6.5],
                    "dimensions": {"width": 1.2, "height": 0.55, "depth": 2.0},
                    "material": {"color": mats["furniture"]}
                })

                # BATHROOM
                elements.append({
                    "id": uid(f"u2_bath_vanity_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Floating Double Vanity & Backlit Mirror",
                    "position": [w_bldg / 2 - 1.8, y_base + 0.5, 2.5],
                    "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.6},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"u2_bath_tub_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Freestanding Soaking Tub & Floor Mixer",
                    "position": [w_bldg / 2 - 1.8, y_base + 0.35, -0.8],
                    "dimensions": {"width": 1.7, "height": 0.65, "depth": 0.85},
                    "material": {"color": "#FAFAFA"}
                })
                elements.append({
                    "id": uid(f"u2_bath_shower_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "window",
                    "name": f"L{f_num} Unit 2 Frameless Glass Walk-In Shower",
                    "position": [w_bldg / 2 - 1.8, y_base + 1.1, 1.2],
                    "dimensions": {"width": 1.2, "height": 2.2, "depth": 0.05},
                    "material": {"color": mats["glass"], "opacity": 0.4}
                })

        # =========================================================================
        # 8. ROOFTOP MECHANICAL SCREENING & SKY TERRACE
        # =========================================================================
        elements.append({
            "id": uid("roof_slab"),
            "layer_id": "structural",
            "type": "slab",
            "name": f"Overhanging Flat Roof Slab (Y={total_height:.1f}m)",
            "position": [0, total_height + 0.15, 0],
            "dimensions": {"width": w_bldg + 1.2, "height": 0.35, "depth": d_bldg + 1.2},
            "material": {"color": mats["fascia"]}
        })
        elements.append({
            "id": uid("roof_parapet"),
            "layer_id": "structural",
            "type": "window",
            "name": "Rooftop 1.4m Tempered Glass Windbreak Parapet",
            "position": [0, total_height + 0.85, 0],
            "dimensions": {"width": w_bldg + 1.0, "height": 1.4, "depth": d_bldg + 1.0},
            "material": {"color": mats["glass"], "opacity": 0.35}
        })
        elements.append({
            "id": uid("roof_penthouse"),
            "layer_id": "structural",
            "type": "wall",
            "name": "Elevator Machine Overrun & Louvered Penthouse",
            "position": [0, total_height + 1.6, 0],
            "dimensions": {"width": 5.0, "height": 3.0, "depth": 4.5},
            "material": {"color": "#171717"}
        })
        elements.append({
            "id": uid("roof_pergola"),
            "layer_id": "structural",
            "type": "slab",
            "name": "Panoramic Sky Lounge Timber Pergola Deck",
            "position": [-w_bldg / 4, total_height + 2.8, 0],
            "dimensions": {"width": 8.0, "height": 0.15, "depth": 6.0},
            "material": {"color": mats["accent"], "roughness": 0.4}
        })

        # =========================================================================
        # 9. MEP SYSTEMS AGENT
        # =========================================================================
        elements.append({
            "id": uid("elec_main_panel"),
            "layer_id": "electrical",
            "type": "fixture",
            "name": "Main 3-Phase 415V 400A Electrical Switchboard",
            "position": [-w_bldg / 2 + 0.6, 1.2, -d_bldg / 2 + 1.2],
            "dimensions": {"width": 0.3, "height": 1.6, "depth": 1.2},
            "material": {"color": "#F59E0B"}
        })
        elements.append({
            "id": uid("elec_vertical_riser"),
            "layer_id": "electrical",
            "type": "conduit",
            "name": f"Vertical {floors}-Story Electrical Busbar Conduit Chase",
            "position": [-w_bldg / 2 + 0.6, total_height / 2.0, -d_bldg / 2 + 1.2],
            "dimensions": {"width": 0.3, "height": total_height, "depth": 0.3},
            "material": {"color": "#FBBF24"}
        })
        elements.append({
            "id": uid("plumb_wet_stack"),
            "layer_id": "plumbing",
            "type": "pipe",
            "name": f"Vertical {floors}-Story DN110 PVC-U Drainage Stack",
            "position": [w_bldg / 2 - 0.6, total_height / 2.0, -d_bldg / 2 + 1.2],
            "dimensions": {"width": 0.3, "height": total_height, "depth": 0.3},
            "material": {"color": "#06B6D4"}
        })

        if spec["has_pool"]:
            elements.append({
                "id": uid("infinity_pool"),
                "layer_id": "structural",
                "type": "slab",
                "name": "Infinity Edge Swimming Pool & Spa Deck",
                "position": [w_bldg / 4, total_height + 0.3, 0],
                "dimensions": {"width": 6.0, "height": 0.5, "depth": 9.0},
                "material": {"color": "#06B6D4", "opacity": 0.85}
            })

        if spec["has_solar"]:
            elements.append({
                "id": uid("solar_pv"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Rooftop High-Efficiency Photovoltaic Solar Array (18kWp)",
                "position": [0, total_height + 3.2, 0],
                "dimensions": {"width": 14.0, "height": 0.15, "depth": 7.0},
                "material": {"color": "#0284C7"}
            })

        model_name = f"{floors}-Story High-Rise ({'2BHK + 3BHK' if is_apartment else 'Modern Residence'})"
        if spec["style"] != "Contemporary Modern":
            model_name += f" • {spec['style']}"

        building_model = {
            "id": project_id,
            "name": model_name,
            "version": int(uuid.uuid4().int % 1000000),
            "description": f"{floors}-Story Hyper-Realistic OpenBIM Model with {spec['style']} interior finishes, dedicated room partitions, curtains, and MEP risers.",
            "meta": {
                "floors": floors,
                "style": spec["style"],
                "has_city": spec["has_city"],
                "has_society": spec["has_society"],
                "available_scales": spec["available_scales"],
            },
            "layers": {
                "structural": {
                    "id": "structural",
                    "name": "Structural & Interior Architecture",
                    "visible": True,
                    "color": "#000000",
                    "elements": [el for el in elements if el["layer_id"] == "structural"]
                },
                "electrical": {
                    "id": "electrical",
                    "name": "Electrical Systems",
                    "visible": True,
                    "color": "#F59E0B",
                    "elements": [el for el in elements if el["layer_id"] == "electrical"]
                },
                "plumbing": {
                    "id": "plumbing",
                    "name": "Plumbing Systems",
                    "visible": True,
                    "color": "#06B6D4",
                    "elements": [el for el in elements if el["layer_id"] == "plumbing"]
                }
            },
            "generated_elements": elements
        }

        return building_model

meta_architect_agent = MetaArchitectAgent()
