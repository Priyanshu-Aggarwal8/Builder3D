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
        
        is_commercial = any(k in p for k in ["commercial", "office", "headquarters", "workplace", "workstation", "boardroom", "corporate", "grade-a", "grade a", "business"])
        is_apartment = not is_commercial and (any(k in p for k in ["bhk", "apartment", "apartments", "flat", "flats", "houses per floor", "residential building"]) or (floors >= 4 and not is_commercial))
        has_2bhk = not is_commercial and ("2bhk" in p or "2 bhk" in p or "2 bedroom" in p or is_apartment)
        has_3bhk = not is_commercial and ("3bhk" in p or "3 bhk" in p or "3 bedroom" in p or is_apartment)
        
        if is_apartment and not (has_2bhk or has_3bhk):
            has_2bhk = True
            has_3bhk = True

        has_pool = any(k in p for k in ["pool", "swimming", "jacuzzi", "infinity pool"])
        has_fire_pit = any(k in p for k in ["fire pit", "firepit", "fireplace"])
        has_solar = any(k in p for k in ["solar", "photovoltaic", "pv array", "green energy"]) or floors >= 6
        has_balcony = not is_commercial and ("balcony" in p or "balconies" in p or is_apartment)

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
            "is_commercial": is_commercial,
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
        is_commercial = spec.get("is_commercial", False)
        h_floor = 3.8 if is_commercial else 3.2
        total_height = floors * h_floor

        elements: List[Dict[str, Any]] = []

        w_bldg = 32.0 if is_commercial else 26.0 if is_apartment else 16.0
        d_bldg = 22.0 if is_commercial else 18.0 if is_apartment else 13.0

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
            # 7B. GRADE-A COMMERCIAL OFFICE FLOORPLATE (WORKSTATIONS, BOARDROOM, PANTRY, RESTROOMS)
            # =========================================================================
            if is_commercial:
                # 1. Reception & Visitor Waiting Lounge (West Front)
                elements.append({
                    "id": uid(f"com_rec_wall_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Reception Acoustic Timber Feature Wall",
                    "position": [-w_bldg / 4 - 2.0, y_base + h_floor / 2, -d_bldg / 4],
                    "dimensions": {"width": 4.5, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"com_rec_desk_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Executive Reception Desk & Granite Top",
                    "position": [-w_bldg / 4 - 2.0, y_base + 0.55, -d_bldg / 4 + 1.2],
                    "dimensions": {"width": 2.8, "height": 1.05, "depth": 0.9},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"com_lounge_sofa_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Visitor Lounge 3-Seater Sofa",
                    "position": [-w_bldg / 4 - 2.0, y_base + 0.45, -d_bldg / 4 + 3.6],
                    "dimensions": {"width": 2.6, "height": 0.8, "depth": 1.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"com_lounge_table_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Calacatta Marble Reception Coffee Table",
                    "position": [-w_bldg / 4 - 2.0, y_base + 0.22, -d_bldg / 4 + 2.5],
                    "dimensions": {"width": 1.4, "height": 0.38, "depth": 0.8},
                    "material": {"color": "#F8FAFC"}
                })

                # 2. Collaborative Open-Plan Workstation Desking (West & Center Zones)
                for pod_idx, (pos_x, pos_z) in enumerate([
                    (-w_bldg / 4 - 2.0, 2.5),
                    (-w_bldg / 4 - 2.0, 6.5),
                    (-w_bldg / 4 + 3.5, 2.5),
                    (-w_bldg / 4 + 3.5, 6.5),
                ]):
                    elements.append({
                        "id": uid(f"com_desk_pod_{pod_idx+1}_L{f_num}"),
                        "layer_id": "structural",
                        "type": "fixture",
                        "name": f"L{f_num} 6-Person Sit-Stand Workstation Cluster {pod_idx+1}",
                        "position": [pos_x, y_base + 0.4, pos_z],
                        "dimensions": {"width": 3.6, "height": 0.75, "depth": 1.4},
                        "material": {"color": "#E2E8F0"}
                    })
                    # Ergonomic Mesh Task Chairs for each desk pod
                    for chair_i, (cx_off, cz_off) in enumerate([
                        (-1.2, -0.9), (0.0, -0.9), (1.2, -0.9),
                        (-1.2, 0.9), (0.0, 0.9), (1.2, 0.9)
                    ]):
                        elements.append({
                            "id": uid(f"com_chair_{pod_idx+1}_{chair_i+1}_L{f_num}"),
                            "layer_id": "structural",
                            "type": "fixture",
                            "name": f"L{f_num} Ergonomic Mesh Task Chair",
                            "position": [pos_x + cx_off, y_base + 0.45, pos_z + cz_off],
                            "dimensions": {"width": 0.6, "height": 0.9, "depth": 0.6},
                            "material": {"color": "#0F172A"}
                        })

                # 3. 14-Person Executive Boardroom (East Wing)
                elements.append({
                    "id": uid(f"com_boardroom_glass_w_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"L{f_num} Executive Boardroom Acoustic Glass Partition West",
                    "position": [w_bldg / 4 - 3.5, y_base + h_floor / 2, 2.5],
                    "dimensions": {"width": 0.1, "height": h_floor, "depth": 8.0},
                    "material": {"color": mats["glass"], "opacity": 0.35, "transmission": 0.9}
                })
                elements.append({
                    "id": uid(f"com_boardroom_glass_s_L{f_num}"),
                    "layer_id": "structural",
                    "type": "window",
                    "name": f"L{f_num} Executive Boardroom Acoustic Glass Partition South",
                    "position": [w_bldg / 4 + 1.0, y_base + h_floor / 2, -1.5],
                    "dimensions": {"width": 9.0, "height": h_floor, "depth": 0.1},
                    "material": {"color": mats["glass"], "opacity": 0.35, "transmission": 0.9}
                })
                elements.append({
                    "id": uid(f"com_boardroom_table_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Solid Walnut 14-Person Conference Table",
                    "position": [w_bldg / 4 + 1.0, y_base + 0.42, 2.5],
                    "dimensions": {"width": 4.8, "height": 0.76, "depth": 1.4},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"com_boardroom_media_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} 85\" 4K Videoconferencing Presentation Wall",
                    "position": [w_bldg / 4 + 5.2, y_base + 1.8, 2.5],
                    "dimensions": {"width": 0.15, "height": 1.6, "depth": 3.2},
                    "material": {"color": "#0F172A"}
                })
                for b_chair_i, b_cz in enumerate([-2.0, -1.2, -0.4, 0.4, 1.2, 2.0]):
                    elements.append({
                        "id": uid(f"com_board_chair_n_{b_chair_i+1}_L{f_num}"),
                        "layer_id": "structural",
                        "type": "fixture",
                        "name": f"L{f_num} Executive Boardroom Swivel Chair",
                        "position": [w_bldg / 4 + 1.0 - 0.9, y_base + 0.48, 2.5 + b_cz],
                        "dimensions": {"width": 0.65, "height": 0.95, "depth": 0.65},
                        "material": {"color": "#1E293B"}
                    })
                    elements.append({
                        "id": uid(f"com_board_chair_s_{b_chair_i+1}_L{f_num}"),
                        "layer_id": "structural",
                        "type": "fixture",
                        "name": f"L{f_num} Executive Boardroom Swivel Chair",
                        "position": [w_bldg / 4 + 1.0 + 0.9, y_base + 0.48, 2.5 + b_cz],
                        "dimensions": {"width": 0.65, "height": 0.95, "depth": 0.65},
                        "material": {"color": "#1E293B"}
                    })

                # 4. 3x Private Focus / Acoustic Phone Pods
                for pod_i, pod_x in enumerate([w_bldg / 4 - 2.5, w_bldg / 4 - 0.5, w_bldg / 4 + 1.5]):
                    elements.append({
                        "id": uid(f"com_focus_pod_{pod_i+1}_L{f_num}"),
                        "layer_id": "structural",
                        "type": "wall",
                        "name": f"L{f_num} Private Acoustic Focus Pod {pod_i+1}",
                        "position": [pod_x, y_base + 1.2, -d_bldg / 4 - 1.5],
                        "dimensions": {"width": 1.4, "height": 2.4, "depth": 1.4},
                        "material": {"color": "#334155"}
                    })
                    elements.append({
                        "id": uid(f"com_focus_door_{pod_i+1}_L{f_num}"),
                        "layer_id": "structural",
                        "type": "window",
                        "name": f"L{f_num} Focus Pod Acoustic Glass Door",
                        "position": [pod_x, y_base + 1.1, -d_bldg / 4 - 0.8],
                        "dimensions": {"width": 0.8, "height": 2.1, "depth": 0.05},
                        "material": {"color": mats["glass"], "opacity": 0.4}
                    })

                # 5. Breakout Cafe & Pantry
                elements.append({
                    "id": uid(f"com_cafe_island_L{f_num}"),
                    "layer_id": "structural",
                    "type": "fixture",
                    "name": f"L{f_num} Breakout Cafe Waterfall Island Bar & Faucet",
                    "position": [w_bldg / 4 + 4.5, y_base + 0.5, -d_bldg / 4 - 1.5],
                    "dimensions": {"width": 3.4, "height": 0.95, "depth": 1.2},
                    "material": {"color": "#F8FAFC"}
                })
                elements.append({
                    "id": uid(f"com_cafe_faucet_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "pipe",
                    "name": f"L{f_num} Pantry Matte Black Gooseneck Faucet",
                    "position": [w_bldg / 4 + 4.5, y_base + 1.15, -d_bldg / 4 - 1.5],
                    "dimensions": {"width": 0.08, "height": 0.35, "depth": 0.15},
                    "material": {"color": "#0F172A"}
                })

                # 6. Centralized Restroom Battery (Connected to Core Wet Stacks)
                elements.append({
                    "id": uid(f"com_restroom_wall_L{f_num}"),
                    "layer_id": "structural",
                    "type": "wall",
                    "name": f"L{f_num} Core Restroom Battery Enclosure Wall",
                    "position": [0, y_base + h_floor / 2, -d_bldg / 4 - 1.0],
                    "dimensions": {"width": 5.0, "height": h_floor, "depth": 0.15},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"com_wc_m_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Commercial Wall-Hung Sensor WC (Male)",
                    "position": [-1.2, y_base + 0.45, -d_bldg / 4 - 2.2],
                    "dimensions": {"width": 0.4, "height": 0.5, "depth": 0.65},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"com_wc_f_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Commercial Wall-Hung Sensor WC (Female)",
                    "position": [1.2, y_base + 0.45, -d_bldg / 4 - 2.2],
                    "dimensions": {"width": 0.4, "height": 0.5, "depth": 0.65},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"com_vanity_L{f_num}"),
                    "layer_id": "plumbing",
                    "type": "fixture",
                    "name": f"L{f_num} Commercial Double Vanity with Sensor Faucets",
                    "position": [0, y_base + 0.5, -d_bldg / 4 - 2.2],
                    "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.55},
                    "material": {"color": "#0F172A"}
                })

                # 7. Floor Electrical & Lighting MEP
                elements.append({
                    "id": uid(f"com_elec_panel_L{f_num}"),
                    "layer_id": "electrical",
                    "type": "fixture",
                    "name": f"L{f_num} Floor 415V/230V Electrical Distribution Panel",
                    "position": [-w_bldg / 2 + 0.8, y_base + 1.2, 0],
                    "dimensions": {"width": 0.2, "height": 1.1, "depth": 0.8},
                    "material": {"color": "#F59E0B"}
                })
                elements.append({
                    "id": uid(f"com_troffer_L{f_num}"),
                    "layer_id": "electrical",
                    "type": "fixture",
                    "name": f"L{f_num} Architectural Recessed 4000K LED Troffer Grid",
                    "position": [0, y_base + h_floor - 0.1, 0],
                    "dimensions": {"width": w_bldg - 2.0, "height": 0.08, "depth": d_bldg - 2.0},
                    "material": {"color": "#FEF08A", "opacity": 0.85}
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

        if is_commercial:
            model_name = f"{floors}-Story Grade-A Commercial Office Tower"
        elif is_apartment:
            model_name = f"{floors}-Story High-Rise (2BHK + 3BHK)"
        else:
            model_name = f"{floors}-Story Architecture ({spec['style']})"
            
        if spec["style"] != "Contemporary Modern" and not is_commercial:
            model_name += f" • {spec['style']}"

        building_model = {
            "id": project_id,
            "name": model_name,
            "version": int(uuid.uuid4().int % 1000000),
            "description": f"{floors}-Story Hyper-Realistic OpenBIM Model with {spec['style']} interior finishes, dedicated room partitions, curtains, and MEP risers.",
            "meta": {
                "floors": floors,
                "style": spec["style"],
                "typology": "commercial" if is_commercial else "residential",
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


# ==============================================================================
# Pure-Intent AI Prompt to DesignSpec Parser Service (Milestone 1)
# ==============================================================================

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
    RoomProgram,
    RoomType,
    RooftopMEPType,
    SetbackSpec,
    SiteParameters,
    StoreySpec,
    StoreyUseType,
    StructuralSystem,
    UnitRequirement,
    UnitType,
    VerticalRiserStrategy,
    ZoningClassification,
)
from app.schemas.spatial import (
    SpatialNode,
    compile_design_spec_to_spatial_tree as _compile_tree,
)


def _build_default_rooms_for_unit(unit_type: UnitType) -> List[RoomProgram]:
    """Generates standard architectural room programs for common unit typologies."""
    if unit_type == UnitType.BHK1:
        return [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Living Room", min_area_sqm=18.0, target_area_sqm=20.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Kitchen", min_area_sqm=7.0, target_area_sqm=8.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, name="Master Bedroom", min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, name="Bathroom", min_area_sqm=4.0, target_area_sqm=5.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Balcony", min_area_sqm=4.0, target_area_sqm=6.0, requires_daylight=True),
        ]
    elif unit_type == UnitType.BHK2:
        return [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Living Room", min_area_sqm=20.0, target_area_sqm=24.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, name="Dining Room", min_area_sqm=8.0, target_area_sqm=10.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Kitchen", min_area_sqm=8.0, target_area_sqm=9.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, name="Master Bedroom", min_area_sqm=14.0, target_area_sqm=16.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Master Ensuite", min_area_sqm=4.0, target_area_sqm=5.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, name="Bedroom 2", min_area_sqm=11.0, target_area_sqm=12.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, name="Common Bathroom", min_area_sqm=3.5, target_area_sqm=4.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Living Balcony", min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=True),
        ]
    elif unit_type == UnitType.BHK3:
        return [
            RoomProgram(room_type=RoomType.FOYER, name="Entrance Foyer", min_area_sqm=5.0, target_area_sqm=6.0, requires_daylight=False),
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Grand Living", min_area_sqm=26.0, target_area_sqm=32.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, name="Dining Room", min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Modular Kitchen", min_area_sqm=10.0, target_area_sqm=12.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.UTILITY_ROOM, name="Utility & Wash", min_area_sqm=4.0, target_area_sqm=5.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, name="Master Suite", min_area_sqm=18.0, target_area_sqm=22.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Master Bath Ensuite", min_area_sqm=5.5, target_area_sqm=7.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, name="Bedroom 2", min_area_sqm=13.0, target_area_sqm=15.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Ensuite 2", min_area_sqm=4.0, target_area_sqm=5.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.GUEST_BEDROOM, name="Bedroom 3", min_area_sqm=12.0, target_area_sqm=14.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, name="Common Bath", min_area_sqm=3.5, target_area_sqm=4.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Main Balcony", min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Bed Balcony", min_area_sqm=6.0, target_area_sqm=8.0, requires_daylight=True),
        ]
    elif unit_type == UnitType.STUDIO:
        return [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Studio Living & Sleeping", min_area_sqm=22.0, target_area_sqm=26.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Kitchenette", min_area_sqm=5.0, target_area_sqm=6.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, name="Bathroom", min_area_sqm=4.0, target_area_sqm=4.5, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BALCONY, name="Balcony", min_area_sqm=3.0, target_area_sqm=3.5, requires_daylight=True),
        ]
    elif unit_type == UnitType.PENTHOUSE:
        return [
            RoomProgram(room_type=RoomType.FOYER, name="Private Foyer", min_area_sqm=10.0, target_area_sqm=12.0, requires_daylight=False),
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Sky Lounge & Living", min_area_sqm=45.0, target_area_sqm=55.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.DINING_ROOM, name="Formal Dining", min_area_sqm=18.0, target_area_sqm=22.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Chef's Kitchen", min_area_sqm=14.0, target_area_sqm=18.0, requires_daylight=True, requires_plumbing=True),
            RoomProgram(room_type=RoomType.MASTER_BEDROOM, name="Presidential Master Suite", min_area_sqm=28.0, target_area_sqm=35.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Master Spa Bath", min_area_sqm=8.0, target_area_sqm=12.0, requires_daylight=True, requires_plumbing=True),
            RoomProgram(room_type=RoomType.WALK_IN_CLOSET, name="Dressing Suite", min_area_sqm=10.0, target_area_sqm=12.0, requires_daylight=False),
            RoomProgram(room_type=RoomType.BEDROOM, name="Guest Suite 2", min_area_sqm=18.0, target_area_sqm=22.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Guest Bath 2", min_area_sqm=5.0, target_area_sqm=6.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BEDROOM, name="Guest Suite 3", min_area_sqm=16.0, target_area_sqm=20.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM_ENSUITE, name="Guest Bath 3", min_area_sqm=5.0, target_area_sqm=6.0, requires_daylight=False, requires_plumbing=True),
            RoomProgram(room_type=RoomType.TERRACE, name="Sky Deck Terrace", min_area_sqm=25.0, target_area_sqm=40.0, requires_daylight=True),
        ]
    elif unit_type == UnitType.COMMERCIAL_OFFICE:
        return [
            RoomProgram(room_type=RoomType.LOBBY, name="Reception Lobby", min_area_sqm=15.0, target_area_sqm=20.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.CONFERENCE_ROOM, name="Main Boardroom", min_area_sqm=25.0, target_area_sqm=35.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.HOME_OFFICE, name="Open Workstation Area", min_area_sqm=60.0, target_area_sqm=80.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.KITCHEN, name="Pantry / Breakroom", min_area_sqm=10.0, target_area_sqm=12.0, requires_plumbing=True),
            RoomProgram(room_type=RoomType.BATHROOM_COMMON, name="Executive Restrooms", min_area_sqm=10.0, target_area_sqm=12.0, requires_plumbing=True),
        ]
    else:
        # Generic Custom unit
        return [
            RoomProgram(room_type=RoomType.LIVING_ROOM, name="Main Area", min_area_sqm=20.0, target_area_sqm=25.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BEDROOM, name="Room 1", min_area_sqm=12.0, target_area_sqm=15.0, requires_daylight=True),
            RoomProgram(room_type=RoomType.BATHROOM, name="Bathroom", min_area_sqm=4.0, target_area_sqm=5.0, requires_plumbing=True),
        ]


def parse_prompt_to_design_spec(prompt: str) -> DesignSpec:
    """
    Parses unstructured natural language architectural prompts into a strictly valid,
    pure-intent DesignSpec instance with complete fallback defaults.
    """
    p = (prompt or "").strip().lower()

    # 1. Floor Count Extraction
    floors = 2
    floor_match = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', p)
    if floor_match:
        floors = max(1, min(100, int(floor_match.group(1))))
    elif "single story" in p or "single storey" in p or "bungalow" in p or "1 story" in p or "1 floor" in p:
        floors = 1
    elif "two story" in p or "two storey" in p or "2 story" in p or "duplex" in p or "2 floors" in p:
        floors = 2
    elif "three story" in p or "three storey" in p or "3 story" in p or "triplex" in p or "3 floors" in p:
        floors = 3
    elif "tower" in p or "high rise" in p or "high-rise" in p or "skyscraper" in p:
        floors = 12

    # 2. Typology Classification
    if any(k in p for k in ["villa", "mansion", "bungalow", "cottage", "estate"]):
        typology = BuildingTypology.VILLA
        occupancy = OccupancyCategory.RESIDENTIAL_SINGLE_FAMILY
        zoning = ZoningClassification.SUBURBAN_ESTATE
    elif any(k in p for k in ["tower", "skyscraper", "high rise", "high-rise"]):
        typology = BuildingTypology.TOWER
        occupancy = OccupancyCategory.RESIDENTIAL_MULTI_FAMILY
        zoning = ZoningClassification.RESIDENTIAL_HIGH_DENSITY
    elif any(k in p for k in ["commercial", "office", "headquarters", "workplace"]):
        typology = BuildingTypology.COMMERCIAL
        occupancy = OccupancyCategory.BUSINESS_OFFICE
        zoning = ZoningClassification.COMMERCIAL_URBAN
    elif any(k in p for k in ["mixed use", "mixed-use", "retail and residential"]):
        typology = BuildingTypology.MIXED_USE
        occupancy = OccupancyCategory.MERCANTILE_RETAIL
        zoning = ZoningClassification.MIXED_USE_HIGH_DENSITY
    elif any(k in p for k in ["townhouse", "row house", "rowhouse"]):
        typology = BuildingTypology.TOWNHOUSE
        occupancy = OccupancyCategory.RESIDENTIAL_SINGLE_FAMILY
        zoning = ZoningClassification.RESIDENTIAL_MEDIUM_DENSITY
    elif any(k in p for k in ["hotel", "resort", "hospitality"]):
        typology = BuildingTypology.HOSPITALITY
        occupancy = OccupancyCategory.RESIDENTIAL_MULTI_FAMILY
        zoning = ZoningClassification.COMMERCIAL_URBAN
    elif floors >= 6:
        typology = BuildingTypology.TOWER
        occupancy = OccupancyCategory.RESIDENTIAL_MULTI_FAMILY
        zoning = ZoningClassification.RESIDENTIAL_HIGH_DENSITY
    else:
        typology = BuildingTypology.RESIDENTIAL
        occupancy = OccupancyCategory.RESIDENTIAL_MULTI_FAMILY if floors > 2 else OccupancyCategory.RESIDENTIAL_SINGLE_FAMILY
        zoning = ZoningClassification.RESIDENTIAL_MEDIUM_DENSITY if floors > 2 else ZoningClassification.RESIDENTIAL_LOW_DENSITY

    # 3. Structural System
    if any(k in p for k in ["mass timber", "timber", "wood", "wooden"]):
        structural_sys = StructuralSystem.MASS_TIMBER
    elif any(k in p for k in ["steel", "steel frame"]):
        structural_sys = StructuralSystem.STEEL_FRAME
    elif any(k in p for k in ["masonry", "brick", "load bearing"]):
        structural_sys = StructuralSystem.LOAD_BEARING_MASONRY
    elif floors >= 15:
        structural_sys = StructuralSystem.HYBRID_POST_TENSIONED
    else:
        structural_sys = StructuralSystem.REINFORCED_CONCRETE_FRAME

    # 4. Aesthetic Style & Palette
    if any(k in p for k in ["luxury", "calacatta", "marble", "italian", "grand"]):
        aesthetic_style = AestheticStyle.LUXURY_CALACATTA
    elif any(k in p for k in ["industrial", "loft", "exposed concrete", "brick"]):
        aesthetic_style = AestheticStyle.INDUSTRIAL_LOFT
    elif any(k in p for k in ["biophilic", "sustainable", "green", "plants", "nature"]):
        aesthetic_style = AestheticStyle.BIOPHILIC_GREEN
    elif any(k in p for k in ["art deco", "artdeco", "glamour"]):
        aesthetic_style = AestheticStyle.ART_DECO
    elif any(k in p for k in ["brutalist", "raw concrete", "monolithic"]):
        aesthetic_style = AestheticStyle.BRUTALIST_CONCRETE
    elif any(k in p for k in ["mediterranean", "terracotta", "warm stone"]):
        aesthetic_style = AestheticStyle.MEDITERRANEAN_WARM
    elif any(k in p for k in ["contemporary", "modern", "minimalist"]):
        aesthetic_style = AestheticStyle.CONTEMPORARY_MODERN
    else:
        aesthetic_style = AestheticStyle.JAPANDI_SCANDINAVIAN

    # 5. MEP Strategy
    if any(k in p for k in ["chilled water", "central chiller"]):
        hvac = HVACType.CENTRAL_CHILLED_WATER
    elif any(k in p for k in ["split", "split ac"]):
        hvac = HVACType.SPLIT_DX
    elif any(k in p for k in ["natural ventilation", "passive"]):
        hvac = HVACType.NATURAL_VENTILATION_WITH_FANS
    else:
        hvac = HVACType.VRF_MULTI_SPLIT

    rooftop = RooftopMEPType.SOLAR_PV_ARRAY
    if any(k in p for k in ["infinity pool", "pool", "swimming"]):
        rooftop = RooftopMEPType.INFINITY_POOL_HYDRAULICS
    elif any(k in p for k in ["sky lounge", "rooftop terrace", "pergola"]):
        rooftop = RooftopMEPType.SKY_LOUNGE_WITH_PERGOLA
    elif any(k in p for k in ["cooling tower"]):
        rooftop = RooftopMEPType.COOLING_TOWERS_AND_SCREENING

    mep = MEPStrategy(
        hvac_type=hvac,
        core_placement=CorePlacementStrategy.CENTRAL_CORE,
        riser_strategy=VerticalRiserStrategy.COAXIAL_STACKED_SHAFTS,
        electrical_distribution=ElectricalDistributionType.BUSBAR_RISER_3PHASE if floors >= 4 else ElectricalDistributionType.CONDUIT_CHASES_PER_FLOOR,
        plumbing_system=PlumbingSystemType.TWO_PIPE_SOIL_WASTE,
        fire_protection=FireProtectionType.PRESSURIZED_STAIRS_WET_RISER if floors >= 4 else FireProtectionType.SPRINKLER_SYSTEM,
        rooftop_mep=rooftop,
        solar_capacity_kwp=24.0 if floors >= 4 else 10.0,
        water_storage_liters=25000.0 if floors >= 4 else 5000.0,
        has_emergency_generator=(floors >= 4),
    )

    # 6. Site Parameters & Setbacks
    # Check for dimension keywords
    dim_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|meter|meters)?\s*(?:x|by|\*)\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)?', p)
    if dim_match:
        w = float(dim_match.group(1))
        d = float(dim_match.group(2))
        plot_w = max(15.0, w)
        plot_d = max(15.0, d)
        plot_area = plot_w * plot_d
    else:
        if typology == BuildingTypology.TOWER or floors >= 6:
            plot_w, plot_d, plot_area = 40.0, 50.0, 2000.0
        elif typology == BuildingTypology.VILLA:
            plot_w, plot_d, plot_area = 25.0, 30.0, 750.0
        elif typology == BuildingTypology.COMMERCIAL:
            plot_w, plot_d, plot_area = 35.0, 45.0, 1575.0
        else:
            plot_w, plot_d, plot_area = 30.0, 40.0, 1200.0

    front_sb = min(4.5, plot_d * 0.15)
    rear_sb = min(3.0, plot_d * 0.10)
    side_sb = min(2.5, plot_w * 0.10)

    site_params = SiteParameters(
        plot_width_m=plot_w,
        plot_depth_m=plot_d,
        total_area_sqm=plot_area,
        setbacks=SetbackSpec(
            front_m=round(front_sb, 1),
            rear_m=round(rear_sb, 1),
            side_left_m=round(side_sb, 1),
            side_right_m=round(side_sb, 1),
        ),
        zoning=zoning,
        max_far=4.5 if floors >= 6 else 2.5,
        max_ground_coverage_ratio=0.55 if floors >= 6 else 0.65,
        orientation_degrees=0.0,
    )

    # 7. Unit Requirements & Storeys
    has_studio = "studio" in p
    has_1bhk = "1bhk" in p or "1 bhk" in p or "1 bedroom" in p or "one bedroom" in p
    has_2bhk = "2bhk" in p or "2 bhk" in p or "2 bedroom" in p or "two bedroom" in p
    has_3bhk = "3bhk" in p or "3 bhk" in p or "3 bedroom" in p or "three bedroom" in p
    has_4bhk = "4bhk" in p or "4 bhk" in p or "4 bedroom" in p
    has_penthouse = "penthouse" in p
    has_office = "office" in p or typology == BuildingTypology.COMMERCIAL

    # Determine default unit mix per floor
    floor_units_template: List[Tuple[UnitType, float]] = []
    if has_office:
        floor_units_template.append((UnitType.COMMERCIAL_OFFICE, 180.0))
    else:
        if has_studio:
            floor_units_template.append((UnitType.STUDIO, 40.0))
        if has_1bhk:
            floor_units_template.append((UnitType.BHK1, 55.0))
        if has_2bhk:
            floor_units_template.append((UnitType.BHK2, 90.0))
        if has_3bhk:
            floor_units_template.append((UnitType.BHK3, 160.0))
        if has_4bhk:
            floor_units_template.append((UnitType.BHK4, 210.0))
        if has_penthouse:
            floor_units_template.append((UnitType.PENTHOUSE, 280.0))

        if not floor_units_template:
            # Smart defaults based on typology
            if typology == BuildingTypology.VILLA:
                floor_units_template = [(UnitType.BHK3, 160.0)]
            elif typology == BuildingTypology.TOWER or floors >= 6:
                floor_units_template = [(UnitType.BHK2, 90.0), (UnitType.BHK3, 160.0)]
            elif floors == 1:
                floor_units_template = [(UnitType.BHK2, 90.0)]
            else:
                floor_units_template = [(UnitType.BHK2, 90.0)]

    # Floor heights
    f2f_height = 3.5 if typology == BuildingTypology.COMMERCIAL else 3.2
    ground_height = 4.0 if (typology in [BuildingTypology.TOWER, BuildingTypology.COMMERCIAL, BuildingTypology.MIXED_USE]) else 3.6

    # Build StoreySpec sequence
    storeys_list: List[StoreySpec] = []
    current_elevation = 0.0

    for s_idx in range(floors):
        is_grd = (s_idx == 0)
        is_roof = (s_idx == floors - 1)
        h = ground_height if is_grd else f2f_height

        s_name = "Ground Floor" if is_grd else f"Level {s_idx}"
        if is_roof and floors > 1:
            s_name = f"Level {s_idx} (Penthouse / Sky Deck)" if (has_penthouse or floors >= 8) else f"Level {s_idx}"

        # Target Storey Use
        if is_grd and (typology == BuildingTypology.TOWER or typology == BuildingTypology.COMMERCIAL):
            use_type = StoreyUseType.COMMERCIAL_LOBBY if typology == BuildingTypology.TOWER else StoreyUseType.RETAIL
        elif is_roof and (has_penthouse or floors >= 8):
            use_type = StoreyUseType.AMENITY_SKY_LOUNGE
        elif typology == BuildingTypology.COMMERCIAL:
            use_type = StoreyUseType.OFFICE
        else:
            use_type = StoreyUseType.RESIDENTIAL

        # Unit mix for this floor
        unit_mix_for_storey: List[UnitRequirement] = []
        if is_roof and (has_penthouse or (floors >= 8 and "penthouse" in p)):
            penthouse_rooms = _build_default_rooms_for_unit(UnitType.PENTHOUSE)
            unit_mix_for_storey.append(
                UnitRequirement(
                    unit_id=f"u_{s_idx}_ph",
                    unit_type=UnitType.PENTHOUSE,
                    name=f"Penthouse Suite {s_idx}01",
                    target_area_sqm=280.0,
                    required_rooms=penthouse_rooms,
                    balcony_count=2,
                    private_access=True,
                )
            )
        else:
            for u_sub_idx, (u_type, u_area) in enumerate(floor_units_template):
                rooms = _build_default_rooms_for_unit(u_type)
                u_name = f"Unit {s_idx}{u_sub_idx + 1:02d} ({u_type.value})"
                unit_mix_for_storey.append(
                    UnitRequirement(
                        unit_id=f"u_{s_idx}_{u_sub_idx + 1:02d}",
                        unit_type=u_type,
                        name=u_name,
                        target_area_sqm=u_area,
                        required_rooms=rooms,
                        balcony_count=2 if u_type in [UnitType.BHK3, UnitType.BHK4] else 1,
                    )
                )

        storeys_list.append(
            StoreySpec(
                storey_index=s_idx,
                name=s_name,
                elevation_m=round(current_elevation, 2),
                height_m=round(h, 2),
                is_ground=is_grd,
                is_rooftop=is_roof,
                is_basement=False,
                target_use=use_type,
                unit_mix=unit_mix_for_storey,
            )
        )
        current_elevation += h

    # Project Name
    proj_title = f"{floors}-Story {typology.value} ({aesthetic_style.value})"
    if "villa" in p:
        proj_title = f"{aesthetic_style.value} Modern Villa"
    elif "tower" in p or floors >= 8:
        proj_title = f"{floors}-Story {aesthetic_style.value} Tower"

    spec = DesignSpec(
        spec_id=str(uuid.uuid4()),
        project_name=proj_title,
        description=f"Generated architectural DesignSpec from prompt: {prompt[:200]}",
        version="1.0.0",
        site=site_params,
        building_typology=typology,
        occupancy_category=occupancy,
        structural_system=structural_sys,
        total_storeys=floors,
        floor_to_floor_height_m=round(f2f_height, 2),
        ground_floor_height_m=round(ground_height, 2),
        basement_storeys=0,
        storeys=storeys_list,
        mep_strategy=mep,
        aesthetic_palette=AestheticPalette(style=aesthetic_style),
    )

    return spec


def compile_design_spec_to_spatial_hierarchy(spec: DesignSpec) -> SpatialNode:
    """Compiles a DesignSpec into a canonical SpatialNode tree."""
    return _compile_tree(spec)
