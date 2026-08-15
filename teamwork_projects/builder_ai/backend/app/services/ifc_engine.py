import ifcopenshell
import ifcopenshell.api
import uuid
from typing import Dict, Any, List, Optional

def create_ifc4_project_from_model(model_data: Dict[str, Any]) -> ifcopenshell.file:
    """
    Creates a valid ISO 10303-21 IFC4 OpenBIM file from our real-estate building model
    using standard IfcOpenShell API methods.
    """
    # 1. Initialize IFC4 file
    f = ifcopenshell.file(schema="IFC4")
    
    # 2. Setup Project & Context
    project_name = model_data.get("name", "BuilderAI Architectural Project")
    project = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcProject", name=project_name)
    
    # Setup standard metric units (meters)
    ifcopenshell.api.run("unit.assign_unit", f, length={"is_metric": True, "raw": "METRE"})
    
    # Setup Geometric Representation Context
    context = ifcopenshell.api.run("context.add_context", f, context_type="Model")
    body_context = ifcopenshell.api.run(
        "context.add_context", f,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=context
    )
    
    # 3. Spatial Hierarchy: Site -> Building -> Storeys
    site = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcSite", name="Main Site")
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=project, products=[site])
    
    building = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuilding", name="Main Building")
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=site, products=[building])
    
    storey_l1 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 1 (Ground)")
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey_l1])
    
    storey_l2 = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 2 (First Floor)")
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey_l2])
    
    storey_roof = ifcopenshell.api.run("root.create_entity", f, ifc_class="IfcBuildingStorey", name="Level 3 (Roof & Plant)")
    ifcopenshell.api.run("aggregate.assign_object", f, relating_object=building, products=[storey_roof])

    # 4. Iterate and Map Elements
    layers = model_data.get("layers", {})
    all_elements: List[Dict[str, Any]] = []
    
    for layer in layers.values():
        all_elements.extend(layer.get("elements", []))
        
    for el in all_elements:
        name = el.get("name", "BIM Element")
        el_type = el.get("type", "wall").lower()
        pos = el.get("position", [0, 0, 0])
        dims = el.get("dimensions", {"width": 1, "height": 1, "depth": 1})
        y = pos[1] if len(pos) > 1 else 0
        
        # Determine storey
        target_storey = storey_l1
        if y >= 6.5:
            target_storey = storey_roof
        elif y >= 3.0:
            target_storey = storey_l2
            
        # Map element type to IFC entity
        ifc_class = "IfcBuildingElementProxy"
        if el_type == "wall":
            ifc_class = "IfcWall"
        elif el_type == "slab":
            ifc_class = "IfcSlab"
        elif el_type == "column":
            ifc_class = "IfcColumn"
        elif el_type == "door":
            ifc_class = "IfcDoor"
        elif el_type == "window":
            ifc_class = "IfcWindow"
        elif el_type in ["pipe", "conduit"]:
            ifc_class = "IfcFlowSegment"
        elif el_type == "fixture":
            if "hvac" in name.lower() or "chiller" in name.lower():
                ifc_class = "IfcUnitaryEquipment"
            elif "tub" in name.lower() or "sink" in name.lower() or "faucet" in name.lower():
                ifc_class = "IfcSanitaryTerminal"
            elif "panel" in name.lower() or "switchboard" in name.lower():
                ifc_class = "IfcElectricDistributionBoard"
            else:
                ifc_class = "IfcFurnishingElement"
        elif el_type == "light":
            ifc_class = "IfcLightFixture"

        # Create entity
        try:
            entity = ifcopenshell.api.run("root.create_entity", f, ifc_class=ifc_class, name=name)
            ifcopenshell.api.run("spatial.assign_container", f, relating_structure=target_storey, products=[entity])
            
            # Add Pset_Common properties
            pset_name = f"Pset_{ifc_class}Common"
            properties = {
                "Reference": str(el.get("id", uid("el"))),
                "Status": "APPROVED",
                "Width": float(dims.get("width", 1.0)),
                "Height": float(dims.get("height", 1.0)),
                "Depth": float(dims.get("depth", 1.0)),
            }
            if ifc_class == "IfcWall":
                properties["LoadBearing"] = True
                properties["IsExternal"] = "north" in name.lower() or "facade" in name.lower()
            elif ifc_class == "IfcFlowSegment":
                properties["NominalDiameter"] = 110.0 if "soil" in name.lower() else 25.0
                
            ifcopenshell.api.run("pset.add_pset", f, product=entity, name=pset_name)
            ifcopenshell.api.run("pset.edit_pset", f, pset=pset_name, properties=properties)
        except Exception:
            pass

    return f

def parse_ifc_content(ifc_str_or_bytes) -> Dict[str, Any]:
    """
    Parses IFC ISO-10303 content using IfcOpenShell and converts into our real-estate model format.
    """
    if isinstance(ifc_str_or_bytes, str):
        f = ifcopenshell.file.from_string(ifc_str_or_bytes)
    else:
        f = ifcopenshell.file.from_string(ifc_str_or_bytes.decode('utf-8', errors='ignore'))
        
    projects = f.by_type("IfcProject")
    project_name = projects[0].Name if projects else "Imported IFC Project"
    
    extracted_elements: List[Dict[str, Any]] = []
    
    supported_classes = [
        ("IfcWall", "wall", "structural"),
        ("IfcSlab", "slab", "structural"),
        ("IfcColumn", "column", "structural"),
        ("IfcDoor", "door", "structural"),
        ("IfcWindow", "window", "structural"),
        ("IfcFlowSegment", "pipe", "plumbing"),
        ("IfcSanitaryTerminal", "fixture", "plumbing"),
        ("IfcElectricDistributionBoard", "fixture", "electrical"),
        ("IfcLightFixture", "light", "electrical"),
        ("IfcUnitaryEquipment", "fixture", "electrical"),
        ("IfcFurnishingElement", "fixture", "structural"),
    ]
    
    for ifc_type, local_type, layer_id in supported_classes:
        entities = f.by_type(ifc_type)
        for idx, ent in enumerate(entities):
            name = ent.Name or f"{ifc_type} #{ent.id()}"
            
            pos = [0.0, 1.5, 0.0]
            dims = {"width": 3.0, "height": 3.0, "depth": 0.25}
            
            if local_type == "slab":
                pos = [0.0, 0.0, 0.0]
                dims = {"width": 14.0, "height": 0.3, "depth": 12.0}
            elif local_type == "column":
                dims = {"width": 0.45, "height": 3.6, "depth": 0.45}
            elif local_type == "door":
                dims = {"width": 1.2, "height": 2.4, "depth": 0.15}
            elif local_type == "window":
                dims = {"width": 2.5, "height": 2.0, "depth": 0.08}
            elif local_type == "pipe":
                dims = {"width": 0.15, "height": 3.6, "depth": 0.15}
                
            color = "#E2E8F0"
            if layer_id == "electrical":
                color = "#F59E0B"
            elif layer_id == "plumbing":
                color = "#06B6D4"
            elif local_type == "window":
                color = "#38BDF8"
            elif local_type == "slab":
                color = "#1E293B"
                
            extracted_elements.append({
                "id": f"ifc_{ent.id()}_{uuid.uuid4().hex[:4]}",
                "name": name,
                "type": local_type,
                "layer_id": layer_id,
                "position": pos,
                "dimensions": dims,
                "material": {"color": color},
                "properties": {
                    "ifc_id": ent.id(),
                    "ifc_type": ifc_type,
                    "global_id": getattr(ent, "GlobalId", None),
                }
            })
            
    return {
        "id": 1,
        "name": project_name,
        "description": f"Imported OpenBIM model containing {len(extracted_elements)} IFC entities.",
        "generated_elements": extracted_elements,
    }

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"
