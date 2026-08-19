import json
import uuid
import re
import copy
from typing import List, Dict, Any, Optional, Tuple

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

COLOR_PALETTES: Dict[str, str] = {
    "white": "#FFFFFF",
    "pure white": "#FFFFFF",
    "off white": "#F8FAFC",
    "ivory": "#FAF7F2",
    "cream": "#FEF3C7",
    "black": "#0F172A",
    "jet black": "#000000",
    "matte black": "#171717",
    "charcoal": "#1E293B",
    "dark grey": "#334155",
    "dark gray": "#334155",
    "grey": "#64748B",
    "gray": "#64748B",
    "light grey": "#E2E8F0",
    "light gray": "#E2E8F0",
    "blue": "#2563EB",
    "dark blue": "#1E3A8A",
    "navy": "#0F172A",
    "cyan": "#06B6D4",
    "sky blue": "#38BDF8",
    "teal": "#0D9488",
    "green": "#16A34A",
    "emerald": "#059669",
    "olive": "#65A30D",
    "sage": "#84A98C",
    "gold": "#D97706",
    "bronze": "#B45309",
    "brass": "#CA8A04",
    "yellow": "#EAB308",
    "amber": "#F59E0B",
    "orange": "#EA580C",
    "terracotta": "#C2410C",
    "red": "#DC2626",
    "burgundy": "#881337",
    "crimson": "#991B1B",
    "brown": "#78350F",
    "walnut": "#451A03",
    "oak": "#D4A373",
    "timber": "#B45309",
    "wood": "#C9935E",
    "marble": "#F8FAFC",
    "calacatta": "#F8FAFC",
    "concrete": "#475569",
    "terrazzo": "#E2E8F0",
    "purple": "#9333EA",
    "violet": "#7C3AED",
    "pink": "#EC4899",
    "rose": "#F43F5E",
}

class MetaArchitectAgent:
    """
    Principal Meta-Agent coordinating specialized sub-agents:
    1. Typology & Scale Agent: Classifies scale and strict commercial vs residential programs.
    2. Structural & Massing Agent: Slabs, columns, shear walls, and cores.
    3. Interior Program Agent: Pure office layouts (workstations, boardrooms, focus booths) OR pure residential suites (2BHK, 3BHK).
    4. In-Place Natural Color & Material Customizer.
    5. Connected MEP Systems Agent: Vertical risers, switchboards, drainage wet stacks.
    """

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

        if is_commercial:
            style = "Corporate Modern"
        else:
            style = "Contemporary Modern"

        if any(k in p for k in ["luxury", "italian", "marble", "calacatta", "mansion", "penthouse"]):
            style = "Luxury Calacatta"
        elif any(k in p for k in ["industrial", "loft", "brick", "concrete", "steel"]):
            style = "Industrial Loft"
        elif any(k in p for k in ["japandi", "scandinavian", "oak", "light timber"]):
            style = "Japandi Scandinavian"
        elif any(k in p for k in ["biophilic", "sustainable", "green", "timber", "plant"]):
            style = "Biophilic Green"
        elif any(k in p for k in ["contemporary", "modern", "minimalist"]):
            style = "Corporate Modern" if is_commercial else "Contemporary Modern"

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
        if style == "Corporate Modern" or style == "Corporate High-Tech":
            return {
                "wall": "#F1F5F9",
                "wall_inner": "#FFFFFF",
                "floor_living": "#E2E8F0",
                "floor_kitchen": "#F8FAFC",
                "floor_bath": "#1E293B",
                "accent": "#78350F",
                "furniture": "#0F172A",
                "glass": "#38BDF8",
                "mullion": "#18181B",
                "fascia": "#0F172A",
                "curtain": "#E2E8F0",
                "opacity": 0.35
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
        elif style == "Japandi Scandinavian":
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
        elif style == "Biophilic Green":
            return {
                "wall": "#F1F5F9",
                "wall_inner": "#FAFDF7",
                "floor_living": "#D4A373",
                "floor_kitchen": "#E2E8F0",
                "floor_bath": "#1E293B",
                "accent": "#15803D",
                "furniture": "#334155",
                "glass": "#6EE7B7",
                "mullion": "#1E293B",
                "fascia": "#14532D",
                "curtain": "#ECFDF5",
                "opacity": 0.4
            }
        else:
            # Contemporary Modern default
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

    def _extract_active_meta(self, model: Dict[str, Any]) -> Tuple[int, str, str]:
        meta = model.get("meta", {})
        name_l = model.get("name", "").lower()

        # 1. Actual Floor Count
        floors = meta.get("floors")
        if not floors:
            m_floor = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', name_l)
            if m_floor:
                floors = int(m_floor.group(1))
            else:
                all_els = []
                for layer in model.get("layers", {}).values():
                    all_els.extend(layer.get("elements", []))
                all_els.extend(model.get("generated_elements", []))
                elevations = [el.get("position", [0, 0, 0])[1] for el in all_els if el.get("type") in ["slab", "wall"]]
                max_y = max(elevations, default=3.2)
                floors = max(1, round(max_y / 3.2))

        # 2. Typology
        typology = meta.get("typology")
        if not typology:
            if any(k in name_l for k in ["commercial", "office", "headquarters", "tower"]):
                typology = "commercial"
            elif any(k in name_l for k in ["villa", "mansion", "house", "residence", "bungalow"]):
                typology = "villa"
            elif any(k in name_l for k in ["penthouse", "apartment"]):
                typology = "apartment"
            else:
                typology = "residential"

        # 3. Style
        style = meta.get("style")
        if not style:
            if "japandi" in name_l:
                style = "Japandi Scandinavian"
            elif "biophilic" in name_l:
                style = "Biophilic Green"
            elif typology == "commercial":
                style = "Corporate Modern"
            else:
                style = "Contemporary Modern"

        return floors, typology, style

    def modify_existing_model(self, existing_model: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        model = copy.deepcopy(existing_model)
        p = prompt.lower()
        current_floors, current_typology, current_style = self._extract_active_meta(model)
        model.setdefault("meta", {})["floors"] = current_floors
        model.setdefault("meta", {})["typology"] = current_typology
        model.setdefault("meta", {})["style"] = current_style

        is_explicit_change = any(k in p for k in [
            "change to", "make it", "convert to", "set to", "expand to", "add floors",
            "reduce to", "increase to", "switch to", "upgrade to", "rebuild as", "make the building"
        ])

        # 1. Floor Count Changes (ONLY when explicitly commanded, never on questions or descriptions)
        floor_match = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', p)
        if floor_match and is_explicit_change and not p.endswith("?"):
            new_floors = max(1, min(36, int(floor_match.group(1))))
            if new_floors != current_floors:
                combined_prompt = f"{new_floors}-story {current_typology} building with {current_style} style. {prompt}"
                return self.synthesize_model(combined_prompt, model.get("id", 1))

        # 2. Typology Conversions (ONLY when explicitly commanded)
        if is_explicit_change and not p.endswith("?"):
            if any(k in p for k in ["commercial", "office", "workstation", "boardroom"]) and current_typology != "commercial":
                return self.synthesize_model(f"{current_floors}-story commercial office tower with {current_style} style. {prompt}", model.get("id", 1))
            elif any(k in p for k in ["residential", "apartment", "villa", "2bhk", "3bhk"]) and current_typology == "commercial":
                return self.synthesize_model(f"{current_floors}-story residential building with 2BHK and 3BHK suites. {prompt}", model.get("id", 1))

        # 3. Multi-Clause Natural Color & Material Target Matching
        all_layers = model.get("layers", {})
        clauses = re.split(r'[,;]|\band\b|\bwith\b', p)
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            clause_color = None
            for cname in sorted(COLOR_PALETTES.keys(), key=lambda x: -len(x)):
                if re.search(r'\b' + re.escape(cname) + r'\b', clause):
                    clause_color = COLOR_PALETTES[cname]
                    break

            hex_m = re.search(r'#(?:[0-9a-fA-F]{3}){1,2}\b', clause)
            if hex_m:
                clause_color = hex_m.group(0)

            if not clause_color:
                continue

            target_walls = any(k in clause for k in ["wall", "partition", "shear", "plaster"])
            target_floors = any(k in clause for k in ["floor", "flooring", "slab", "carpet", "deck"])
            target_glass = any(k in clause for k in ["glass", "facade", "window", "glazing", "curtain", "balustrade"])
            target_mullions = any(k in clause for k in ["mullion", "trim", "fascia", "frame"])
            target_chairs = any(k in clause for k in ["chair", "seat", "swivel", "mesh", "stool"])
            target_desks = any(k in clause for k in ["desk", "workstation", "table", "boardroom"])
            target_sofas = any(k in clause for k in ["sofa", "couch", "lounge", "bench"])
            target_furniture = any(k in clause for k in ["furniture", "bed"]) or (target_chairs or target_desks or target_sofas)
            target_fixtures = any(k in clause for k in ["fixture", "counter", "island", "vanity", "tub", "sink", "wc", "toilet"])

            if not any([target_walls, target_floors, target_glass, target_mullions, target_chairs, target_desks, target_sofas, target_fixtures]):
                target_walls = True
                target_furniture = True

            for l_id, layer in all_layers.items():
                for el in layer.get("elements", []):
                    name_l = el.get("name", "").lower()
                    type_l = el.get("type", "").lower()

                    if target_walls and (type_l == "wall" or "wall" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_floors and (type_l == "slab" or "floor" in name_l or "deck" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_glass and (type_l == "window" or "glass" in name_l or "curtain" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                        if "dark" in clause or "tint" in clause or "black" in clause:
                            el["material"]["opacity"] = 0.65
                    elif target_mullions and ("mullion" in name_l or "fascia" in name_l or "frame" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_chairs and ("chair" in name_l or "seat" in name_l or "swivel" in name_l or "stool" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_desks and ("desk" in name_l or "workstation" in name_l or "table" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_sofas and ("sofa" in name_l or "couch" in name_l or "lounge" in name_l):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_furniture and (l_id == "furniture" or any(f in name_l for f in ["sofa", "chair", "desk", "table", "bed", "bench", "pod"])):
                        el.setdefault("material", {})["color"] = clause_color
                    elif target_fixtures and (l_id == "fixtures" or any(f in name_l for f in ["counter", "island", "vanity", "sink", "tub", "wc"])):
                        el.setdefault("material", {})["color"] = clause_color

        # 4. Amenities Additions
        h_floor = 3.8 if current_typology == "commercial" else 3.2
        total_h = current_floors * h_floor

        if "pool" in p and not any("pool" in el.get("name", "").lower() for l in all_layers.values() for el in l.get("elements", [])):
            pool_el = {
                "id": uid("infinity_pool"),
                "layer_id": "structural",
                "type": "slab",
                "name": "Rooftop Infinity Edge Swimming Pool",
                "position": [6.0, total_h + 0.3, 0],
                "dimensions": {"width": 7.0, "height": 0.5, "depth": 10.0},
                "material": {"color": "#06B6D4", "opacity": 0.85, "transmission": 0.8}
            }
            all_layers.setdefault("structural", {"id": "structural", "name": "Structural Framework", "visible": True, "color": "#D4FF32", "elements": []})["elements"].append(pool_el)

        if any(k in p for k in ["solar", "photovoltaic", "pv array"]) and not any("solar" in el.get("name", "").lower() for l in all_layers.values() for el in l.get("elements", [])):
            solar_el = {
                "id": uid("solar_pv"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Rooftop High-Efficiency Photovoltaic Solar Array (18kWp)",
                "position": [0, total_h + 3.2, 0],
                "dimensions": {"width": 14.0, "height": 0.15, "depth": 7.0},
                "material": {"color": "#0284C7"}
            }
            all_layers.setdefault("electrical", {"id": "electrical", "name": "Electrical & HVAC", "visible": True, "color": "#F59E0B", "elements": []})["elements"].append(solar_el)

        if any(k in p for k in ["chiller", "hvac", "cooling tower"]) and not any("chiller" in el.get("name", "").lower() for l in all_layers.values() for el in l.get("elements", [])):
            chiller_el = {
                "id": uid("hvac_chiller"),
                "layer_id": "electrical",
                "type": "fixture",
                "name": "Rooftop Commercial HVAC Chiller Plant & Acoustic Screening",
                "position": [-6.0, total_h + 1.2, 0],
                "dimensions": {"width": 4.5, "height": 2.2, "depth": 3.5},
                "material": {"color": "#475569"}
            }
            all_layers.setdefault("electrical", {"id": "electrical", "name": "Electrical & HVAC", "visible": True, "color": "#F59E0B", "elements": []})["elements"].append(chiller_el)

        # 5. Synchronize version, generated_elements, and metadata
        model["version"] = int(uuid.uuid4().int % 1000000)
        model["generated_elements"] = [el for layer in model.get("layers", {}).values() for el in layer.get("elements", [])]
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

            # 1. Structural Post-Tensioned Concrete Floor Slab
            elements.append({
                "id": uid(f"slab_L{f_num}"),
                "layer_id": "structural",
                "type": "slab",
                "name": f"Level {f_num} Post-Tensioned Floor Slab",
                "position": [0, y_base + 0.15, 0],
                "dimensions": {"width": w_bldg, "height": 0.3, "depth": d_bldg},
                "material": {"color": mats["fascia"], "roughness": 0.7}
            })

            # 2. Finished Flooring
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
            col_x_list = [-w_bldg / 2 + 0.5, -w_bldg / 4, w_bldg / 4, w_bldg / 2 - 0.5]
            col_z_list = [-d_bldg / 2 + 0.5, 0, d_bldg / 2 - 0.5]
            for cx in col_x_list:
                for cz in col_z_list:
                    elements.append({
                        "id": uid(f"col_L{f_num}"),
                        "layer_id": "structural",
                        "type": "column",
                        "name": f"Level {f_num} Structural RC Column",
                        "position": [cx, y_base + h_floor / 2, cz],
                        "dimensions": {"width": 0.5, "height": h_floor, "depth": 0.5},
                        "material": {"color": "#171717"}
                    })

            # 4. Central Core: Dual Elevator Shaft & Fire Exit Stair Core
            elements.append({
                "id": uid(f"lift_shaft_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} Dual Elevator Shaft Core & Lobby",
                "position": [0, y_base + h_floor / 2, -1.5],
                "dimensions": {"width": 3.6, "height": h_floor, "depth": 3.0},
                "material": {"color": mats.get("wall", "#F1F5F9")}
            })
            elements.append({
                "id": uid(f"stair_core_L{f_num}"),
                "layer_id": "structural",
                "type": "wall",
                "name": f"Level {f_num} Fire Escape Stair Core Enclosure",
                "position": [0, y_base + h_floor / 2, 2.0],
                "dimensions": {"width": 3.6, "height": h_floor, "depth": 2.8},
                "material": {"color": mats.get("wall", "#F1F5F9")}
            })

            # 5. Exterior Curtain Glazing & Mullions
            elements.append({
                "id": uid(f"curtain_s_L{f_num}"),
                "layer_id": "architecture",
                "type": "window",
                "name": f"Level {f_num} South Curtain Glass Facade",
                "position": [0, y_base + h_floor / 2, d_bldg / 2],
                "dimensions": {"width": w_bldg, "height": h_floor - 0.2, "depth": 0.08},
                "material": {"color": mats["glass"], "opacity": mats["opacity"], "transmission": 0.92}
            })
            elements.append({
                "id": uid(f"curtain_n_L{f_num}"),
                "layer_id": "architecture",
                "type": "window",
                "name": f"Level {f_num} North Curtain Glass Facade",
                "position": [0, y_base + h_floor / 2, -d_bldg / 2],
                "dimensions": {"width": w_bldg, "height": h_floor - 0.2, "depth": 0.08},
                "material": {"color": mats["glass"], "opacity": mats["opacity"], "transmission": 0.92}
            })
            elements.append({
                "id": uid(f"facade_w_L{f_num}"),
                "layer_id": "architecture",
                "type": "wall",
                "name": f"Level {f_num} West Architectural Shear Wall",
                "position": [-w_bldg / 2, y_base + h_floor / 2, 0],
                "dimensions": {"width": 0.3, "height": h_floor, "depth": d_bldg},
                "material": {"color": mats["wall"]}
            })
            elements.append({
                "id": uid(f"facade_e_L{f_num}"),
                "layer_id": "architecture",
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
                    "layer_id": "architecture",
                    "type": "column",
                    "name": f"Level {f_num} South Aluminum Mullion Rib",
                    "position": [mx, y_base + h_floor / 2, d_bldg / 2 + 0.06],
                    "dimensions": {"width": 0.12, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["mullion"]}
                })
                elements.append({
                    "id": uid(f"mullion_n_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "column",
                    "name": f"Level {f_num} North Aluminum Mullion Rib",
                    "position": [mx, y_base + h_floor / 2, -d_bldg / 2 - 0.06],
                    "dimensions": {"width": 0.12, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["mullion"]}
                })

            # 6. Balconies (Residential Only)
            if spec["has_balcony"] and not is_commercial:
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
                    "layer_id": "architecture",
                    "type": "window",
                    "name": f"Level {f_num} Sunset Balcony Tempered Glass Balustrade",
                    "position": [-w_bldg / 4 - 1.0, y_base + 0.75, d_bldg / 2 + 2.35],
                    "dimensions": {"width": w_bldg / 2 - 2.0, "height": 1.1, "depth": 0.05},
                    "material": {"color": mats["glass"], "opacity": 0.45}
                })

            # =========================================================================
            # CASE A: COMMERCIAL OFFICE FLOORPLATE (PURE OFFICE - ZERO RESIDENTIAL BEDS)
            # =========================================================================
            if is_commercial:
                # 1. Reception & Visitor Waiting Lounge (West Front)
                elements.append({
                    "id": uid(f"com_rec_wall_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "wall",
                    "name": f"L{f_num} Reception Acoustic Timber Feature Wall",
                    "position": [-w_bldg / 4 - 2.0, y_base + h_floor / 2, -d_bldg / 4],
                    "dimensions": {"width": 4.5, "height": h_floor, "depth": 0.15},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"com_rec_desk_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Executive Reception Desk & Granite Top",
                    "position": [-w_bldg / 4 - 2.0, y_base + 0.55, -d_bldg / 4 + 1.2],
                    "dimensions": {"width": 2.8, "height": 1.05, "depth": 0.9},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"com_lounge_sofa_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Visitor Lounge 3-Seater Sofa",
                    "position": [-w_bldg / 4 - 2.0, y_base + 0.45, -d_bldg / 4 + 3.6],
                    "dimensions": {"width": 2.6, "height": 0.8, "depth": 1.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"com_lounge_table_L{f_num}"),
                    "layer_id": "furniture",
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
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": f"L{f_num} 6-Person Sit-Stand Workstation Cluster {pod_idx+1}",
                        "position": [pos_x, y_base + 0.4, pos_z],
                        "dimensions": {"width": 3.6, "height": 0.75, "depth": 1.4},
                        "material": {"color": "#E2E8F0"}
                    })
                    for chair_i, (cx_off, cz_off) in enumerate([
                        (-1.2, -0.9), (0.0, -0.9), (1.2, -0.9),
                        (-1.2, 0.9), (0.0, 0.9), (1.2, 0.9)
                    ]):
                        elements.append({
                            "id": uid(f"com_chair_{pod_idx+1}_{chair_i+1}_L{f_num}"),
                            "layer_id": "furniture",
                            "type": "fixture",
                            "name": f"L{f_num} Ergonomic Mesh Task Chair",
                            "position": [pos_x + cx_off, y_base + 0.45, pos_z + cz_off],
                            "dimensions": {"width": 0.6, "height": 0.9, "depth": 0.6},
                            "material": {"color": "#0F172A"}
                        })

                # 3. 14-Person Executive Boardroom (East Wing)
                elements.append({
                    "id": uid(f"com_boardroom_glass_w_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "window",
                    "name": f"L{f_num} Executive Boardroom Acoustic Glass Partition West",
                    "position": [w_bldg / 4 - 3.5, y_base + h_floor / 2, 2.5],
                    "dimensions": {"width": 0.1, "height": h_floor, "depth": 8.0},
                    "material": {"color": mats["glass"], "opacity": 0.35, "transmission": 0.9}
                })
                elements.append({
                    "id": uid(f"com_boardroom_glass_s_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "window",
                    "name": f"L{f_num} Executive Boardroom Acoustic Glass Partition South",
                    "position": [w_bldg / 4 + 1.0, y_base + h_floor / 2, -1.5],
                    "dimensions": {"width": 9.0, "height": h_floor, "depth": 0.1},
                    "material": {"color": mats["glass"], "opacity": 0.35, "transmission": 0.9}
                })
                elements.append({
                    "id": uid(f"com_boardroom_table_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Solid Walnut 14-Person Conference Table",
                    "position": [w_bldg / 4 + 1.0, y_base + 0.42, 2.5],
                    "dimensions": {"width": 4.8, "height": 0.76, "depth": 1.4},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"com_boardroom_media_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} 85\" 4K Videoconferencing Presentation Wall",
                    "position": [w_bldg / 4 + 5.2, y_base + 1.8, 2.5],
                    "dimensions": {"width": 0.15, "height": 1.6, "depth": 3.2},
                    "material": {"color": "#0F172A"}
                })
                for b_chair_i, b_cz in enumerate([-2.0, -1.2, -0.4, 0.4, 1.2, 2.0]):
                    elements.append({
                        "id": uid(f"com_board_chair_n_{b_chair_i+1}_L{f_num}"),
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": f"L{f_num} Executive Boardroom Swivel Chair",
                        "position": [w_bldg / 4 + 1.0 - 0.9, y_base + 0.48, 2.5 + b_cz],
                        "dimensions": {"width": 0.65, "height": 0.95, "depth": 0.65},
                        "material": {"color": "#1E293B"}
                    })
                    elements.append({
                        "id": uid(f"com_board_chair_s_{b_chair_i+1}_L{f_num}"),
                        "layer_id": "furniture",
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
                        "layer_id": "architecture",
                        "type": "wall",
                        "name": f"L{f_num} Private Acoustic Focus Pod {pod_i+1}",
                        "position": [pod_x, y_base + 1.2, -d_bldg / 4 - 1.5],
                        "dimensions": {"width": 1.4, "height": 2.4, "depth": 1.4},
                        "material": {"color": "#334155"}
                    })
                    elements.append({
                        "id": uid(f"com_focus_door_{pod_i+1}_L{f_num}"),
                        "layer_id": "architecture",
                        "type": "window",
                        "name": f"L{f_num} Focus Pod Acoustic Glass Door",
                        "position": [pod_x, y_base + 1.1, -d_bldg / 4 - 0.8],
                        "dimensions": {"width": 0.8, "height": 2.1, "depth": 0.05},
                        "material": {"color": mats["glass"], "opacity": 0.4}
                    })

                # 5. Breakout Cafe & Pantry
                elements.append({
                    "id": uid(f"com_cafe_island_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Breakout Cafe Waterfall Island Bar",
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
                    "layer_id": "architecture",
                    "type": "wall",
                    "name": f"L{f_num} Core Restroom Battery Enclosure Wall",
                    "position": [0, y_base + h_floor / 2, -d_bldg / 4 - 1.0],
                    "dimensions": {"width": 5.0, "height": h_floor, "depth": 0.15},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"com_wc_m_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Commercial Wall-Hung Sensor WC (Male)",
                    "position": [-1.2, y_base + 0.45, -d_bldg / 4 - 2.2],
                    "dimensions": {"width": 0.4, "height": 0.5, "depth": 0.65},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"com_wc_f_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Commercial Wall-Hung Sensor WC (Female)",
                    "position": [1.2, y_base + 0.45, -d_bldg / 4 - 2.2],
                    "dimensions": {"width": 0.4, "height": 0.5, "depth": 0.65},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"com_vanity_L{f_num}"),
                    "layer_id": "fixtures",
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
            # CASE B: RESIDENTIAL APARTMENTS (2BHK & 3BHK SUITES)
            # =========================================================================
            elif is_apartment:
                # UNIT 1 (WEST 2BHK)
                x_u1 = -w_bldg / 4 - 1.0
                elements.append({
                    "id": uid(f"u1_wall_corridor_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "wall",
                    "name": f"L{f_num} Unit 1 Corridor Wall",
                    "position": [x_u1 + 4.5, y_base + h_floor / 2, -2.0],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": d_bldg / 2 - 1.0},
                    "material": {"color": mats["wall_inner"]}
                })
                elements.append({
                    "id": uid(f"u1_door_entry_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "door",
                    "name": f"L{f_num} Unit 1 Solid Timber Entrance Door",
                    "position": [x_u1 + 4.5, y_base + 1.1, 0.5],
                    "dimensions": {"width": 0.1, "height": 2.2, "depth": 0.9},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u1_sofa_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 L-Sectional Bouclé Sofa & Pillows",
                    "position": [x_u1 - 1.2, y_base + 0.45, -2.5],
                    "dimensions": {"width": 3.4, "height": 0.75, "depth": 2.2},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_coffee_table_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Fluted Oak Coffee Table",
                    "position": [x_u1 - 1.2, y_base + 0.22, -2.5],
                    "dimensions": {"width": 1.6, "height": 0.38, "depth": 0.9},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u1_dining_set_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Solid Walnut Dining Table & 6 Chairs",
                    "position": [x_u1 + 2.2, y_base + 0.45, -1.8],
                    "dimensions": {"width": 2.6, "height": 0.75, "depth": 1.1},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u1_kitchen_island_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Waterfall Island with Faucet & Barstools",
                    "position": [x_u1 + 2.2, y_base + 0.5, -4.5],
                    "dimensions": {"width": 2.8, "height": 0.95, "depth": 1.1},
                    "material": {"color": "#FFFFFF"}
                })
                elements.append({
                    "id": uid(f"u1_master_bed_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 King Platform Bed & Pillows",
                    "position": [x_u1 - 1.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 2.2, "height": 0.55, "depth": 2.4},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_bed2_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Bedroom 2 Queen Bed",
                    "position": [x_u1 + 3.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 1.8, "height": 0.55, "depth": 2.0},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u1_bath_vanity_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Floating Double Vanity & Backlit Mirror",
                    "position": [-w_bldg / 2 + 1.8, y_base + 0.5, 2.5],
                    "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.6},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"u1_bath_wc_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 1 Wall-Hung Concealed Cistern WC",
                    "position": [-w_bldg / 2 + 1.8, y_base + 0.45, 4.2],
                    "dimensions": {"width": 0.4, "height": 0.45, "depth": 0.65},
                    "material": {"color": "#FFFFFF"}
                })

                # UNIT 2 (EAST 3BHK)
                x_u2 = w_bldg / 4 + 1.0
                elements.append({
                    "id": uid(f"u2_wall_corridor_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "wall",
                    "name": f"L{f_num} Unit 2 Corridor Wall",
                    "position": [x_u2 - 4.5, y_base + h_floor / 2, -2.0],
                    "dimensions": {"width": 0.15, "height": h_floor, "depth": d_bldg / 2 - 1.0},
                    "material": {"color": mats["wall_inner"]}
                })
                elements.append({
                    "id": uid(f"u2_door_entry_L{f_num}"),
                    "layer_id": "architecture",
                    "type": "door",
                    "name": f"L{f_num} Unit 2 Solid Timber Entrance Door",
                    "position": [x_u2 - 4.5, y_base + 1.1, 0.5],
                    "dimensions": {"width": 0.1, "height": 2.2, "depth": 0.9},
                    "material": {"color": mats["accent"]}
                })
                elements.append({
                    "id": uid(f"u2_sofa_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 L-Sectional Bouclé Sofa & Pillows",
                    "position": [x_u2 + 1.2, y_base + 0.45, -2.5],
                    "dimensions": {"width": 3.4, "height": 0.75, "depth": 2.2},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_master_bed_L{f_num}"),
                    "layer_id": "furniture",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 King Platform Bed & Pillows",
                    "position": [x_u2 + 1.2, y_base + 0.45, 4.5],
                    "dimensions": {"width": 2.2, "height": 0.55, "depth": 2.4},
                    "material": {"color": mats["furniture"]}
                })
                elements.append({
                    "id": uid(f"u2_bath_vanity_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Floating Double Vanity & Backlit Mirror",
                    "position": [w_bldg / 2 - 1.8, y_base + 0.5, 2.5],
                    "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.6},
                    "material": {"color": "#1E293B"}
                })
                elements.append({
                    "id": uid(f"u2_bath_tub_L{f_num}"),
                    "layer_id": "fixtures",
                    "type": "fixture",
                    "name": f"L{f_num} Unit 2 Freestanding Soaking Tub & Floor Mixer",
                    "position": [w_bldg / 2 - 1.8, y_base + 0.35, -0.8],
                    "dimensions": {"width": 1.7, "height": 0.65, "depth": 0.85},
                    "material": {"color": "#FAFAFA"}
                })

            # =========================================================================
            # CASE C: RESIDENTIAL VILLA / PRIVATE HOUSE (1, 2, 3 STOREY HOMES)
            # =========================================================================
            else:
                if f_num == 1:
                    # Ground Level: Great Room Living Suite, Waterfall Kitchen Island & Dining Table
                    elements.append({
                        "id": uid(f"villa_media_wall_L{f_num}"),
                        "layer_id": "architecture",
                        "type": "wall",
                        "name": "Living Room Media Feature Wall",
                        "position": [-w_bldg / 2 + 1.2, y_base + h_floor / 2, 0],
                        "dimensions": {"width": 0.3, "height": h_floor - 0.2, "depth": 4.5},
                        "material": {"color": mats["accent"]}
                    })
                    elements.append({
                        "id": uid(f"villa_sofa_L{f_num}"),
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": "Living Room Low-Profile Bouclé Sectional Sofa",
                        "position": [-w_bldg / 4, y_base + 0.45, 1.5],
                        "dimensions": {"width": 3.4, "height": 0.75, "depth": 2.2},
                        "material": {"color": mats["furniture"]}
                    })
                    elements.append({
                        "id": uid(f"villa_coffee_table_L{f_num}"),
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": "Calacatta Marble Living Coffee Table",
                        "position": [-w_bldg / 4, y_base + 0.22, 1.5],
                        "dimensions": {"width": 1.6, "height": 0.38, "depth": 0.9},
                        "material": {"color": "#F8FAFC"}
                    })
                    elements.append({
                        "id": uid(f"villa_kitchen_island_L{f_num}"),
                        "layer_id": "fixtures",
                        "type": "fixture",
                        "name": "Waterfall Calacatta Gold Kitchen Island",
                        "position": [w_bldg / 4, y_base + 0.5, -2.5],
                        "dimensions": {"width": 3.2, "height": 0.95, "depth": 1.2},
                        "material": {"color": "#F8FAFC"}
                    })
                    elements.append({
                        "id": uid(f"villa_dining_table_L{f_num}"),
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": "Solid Walnut 8-Seater Dining Table & Chairs",
                        "position": [w_bldg / 4, y_base + 0.45, 2.5],
                        "dimensions": {"width": 2.6, "height": 0.75, "depth": 1.1},
                        "material": {"color": mats["accent"]}
                    })
                else:
                    # Upper Storeys: Master Bedroom Suite & Spa Bathroom
                    elements.append({
                        "id": uid(f"villa_master_bed_L{f_num}"),
                        "layer_id": "furniture",
                        "type": "fixture",
                        "name": f"Level {f_num} Master King Platform Bed & Fluted Headboard",
                        "position": [-w_bldg / 4, y_base + 0.45, 1.5],
                        "dimensions": {"width": 2.3, "height": 0.6, "depth": 2.5},
                        "material": {"color": mats["furniture"]}
                    })
                    elements.append({
                        "id": uid(f"villa_bath_tub_L{f_num}"),
                        "layer_id": "fixtures",
                        "type": "fixture",
                        "name": f"Level {f_num} Master Freestanding Soaking Tub",
                        "position": [w_bldg / 4 + 1.0, y_base + 0.35, -2.0],
                        "dimensions": {"width": 1.7, "height": 0.65, "depth": 0.85},
                        "material": {"color": "#FAFAFA"}
                    })
                    elements.append({
                        "id": uid(f"villa_double_vanity_L{f_num}"),
                        "layer_id": "fixtures",
                        "type": "fixture",
                        "name": f"Level {f_num} Master Floating Double Vanity",
                        "position": [w_bldg / 4 + 1.0, y_base + 0.5, 1.5],
                        "dimensions": {"width": 1.6, "height": 0.85, "depth": 0.6},
                        "material": {"color": "#1E293B"}
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
            "layer_id": "architecture",
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
            "name": f"Vertical {floors}-Story DN150 PVC-U Drainage Wet Stack",
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
            model_name = f"{floors}-Story Modern Villa"

        building_model = {
            "id": project_id,
            "name": model_name,
            "version": int(uuid.uuid4().int % 1000000),
            "description": f"{floors}-Story Hyper-Realistic OpenBIM Model with {spec['style']} interior finishes and connected MEP risers.",
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
                    "name": "Structural Framework",
                    "visible": True,
                    "color": "#D4FF32",
                    "elements": [el for el in elements if el["layer_id"] == "structural"]
                },
                "architecture": {
                    "id": "architecture",
                    "name": "Architectural Shell & Walls",
                    "visible": True,
                    "color": "#E2E8F0",
                    "elements": [el for el in elements if el["layer_id"] == "architecture"]
                },
                "furniture": {
                    "id": "furniture",
                    "name": "Interior Furniture & Workstations",
                    "visible": True,
                    "color": "#A78BFA",
                    "elements": [el for el in elements if el["layer_id"] == "furniture"]
                },
                "fixtures": {
                    "id": "fixtures",
                    "name": "Sanitary & Kitchen Fixtures",
                    "visible": True,
                    "color": "#F43F5E",
                    "elements": [el for el in elements if el["layer_id"] == "fixtures"]
                },
                "electrical": {
                    "id": "electrical",
                    "name": "Electrical & HVAC Infrastructure",
                    "visible": True,
                    "color": "#F59E0B",
                    "elements": [el for el in elements if el["layer_id"] == "electrical"]
                },
                "plumbing": {
                    "id": "plumbing",
                    "name": "Plumbing & Drainage Wet Stacks",
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
    elif any(k in p for k in ["commercial", "office", "headquarters", "workplace", "workstation", "boardroom", "corporate"]):
        typology = BuildingTypology.COMMERCIAL
        occupancy = OccupancyCategory.BUSINESS_OFFICE
        zoning = ZoningClassification.COMMERCIAL_URBAN
    elif any(k in p for k in ["tower", "skyscraper", "high rise", "high-rise"]):
        typology = BuildingTypology.TOWER
        occupancy = OccupancyCategory.RESIDENTIAL_MULTI_FAMILY
        zoning = ZoningClassification.RESIDENTIAL_HIGH_DENSITY
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
    elif any(k in p for k in ["japandi", "scandinavian", "light oak", "light timber"]):
        aesthetic_style = AestheticStyle.JAPANDI_SCANDINAVIAN
    elif any(k in p for k in ["art deco", "artdeco", "glamour"]):
        aesthetic_style = AestheticStyle.ART_DECO
    elif any(k in p for k in ["brutalist", "raw concrete", "monolithic"]):
        aesthetic_style = AestheticStyle.BRUTALIST_CONCRETE
    elif any(k in p for k in ["mediterranean", "terracotta", "warm stone"]):
        aesthetic_style = AestheticStyle.MEDITERRANEAN_WARM
    else:
        aesthetic_style = AestheticStyle.CONTEMPORARY_MODERN

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
    )

    # 6. Storey & Spatial Programs
    storeys_list: List[StoreySpec] = []
    h_floor = 3.8 if typology == BuildingTypology.COMMERCIAL else 3.2

    if typology == BuildingTypology.COMMERCIAL:
        unit_mix = [
            UnitRequirement(
                unit_type=UnitType.COMMERCIAL_OFFICE,
                name="Commercial Office Floorplate",
                target_area_sqm=300.0,
                required_rooms=_build_default_rooms_for_unit(UnitType.COMMERCIAL_OFFICE),
            )
        ]
    elif typology == BuildingTypology.VILLA:
        unit_mix = [
            UnitRequirement(
                unit_type=UnitType.CUSTOM,
                name="Villa Living Suite",
                target_area_sqm=180.0,
                required_rooms=_build_default_rooms_for_unit(UnitType.CUSTOM),
            )
        ]
    elif "1bhk" in p:
        unit_mix = [
            UnitRequirement(
                unit_type=UnitType.BHK1,
                name="1BHK Suite",
                target_area_sqm=65.0,
                required_rooms=_build_default_rooms_for_unit(UnitType.BHK1),
            )
        ]
    else:
        unit_mix = [
            UnitRequirement(
                unit_type=UnitType.BHK2,
                name="Unit 1 2BHK",
                target_area_sqm=90.0,
                required_rooms=_build_default_rooms_for_unit(UnitType.BHK2),
            ),
            UnitRequirement(
                unit_type=UnitType.BHK3,
                name="Unit 2 3BHK",
                target_area_sqm=160.0,
                required_rooms=_build_default_rooms_for_unit(UnitType.BHK3),
            ),
        ]

    for floor_idx in range(floors):
        elev = floor_idx * h_floor
        storeys_list.append(
            StoreySpec(
                storey_index=floor_idx,
                name=f"Level {floor_idx + 1}" if floor_idx > 0 else "Ground Floor",
                elevation_m=elev,
                height_m=h_floor,
                is_ground=(floor_idx == 0),
                is_rooftop=(floor_idx == floors - 1),
                unit_mix=unit_mix,
            )
        )

    site_width = 30.0 + (floors * 0.5)
    site_depth = 40.0 + (floors * 0.5)

    spec = DesignSpec(
        project_name=f"{floors}-Storey {typology.value.title()}",
        site=SiteParameters(
            plot_width_m=site_width,
            plot_depth_m=site_depth,
            total_area_sqm=site_width * site_depth,
            setbacks=SetbackSpec(front_m=4.0, rear_m=3.0, side_left_m=3.0, side_right_m=3.0),
            zoning=zoning,
        ),
        building_typology=typology,
        occupancy_category=occupancy,
        structural_system=structural_sys,
        total_storeys=floors,
        storeys=storeys_list,
        aesthetic_palette=AestheticPalette(style=aesthetic_style),
        mep_strategy=mep,
    )

    return spec
