from fastapi import APIRouter, UploadFile, File, Response, Body, HTTPException
from typing import Dict, Any, List
from app.services.ifc_engine import create_ifc4_project_from_model, parse_ifc_content
import json

router = APIRouter()

# In-memory Speckle Version History store
SPECKLE_VERSIONS_DB: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "version": 1,
            "commit_id": "c_init_89a1",
            "author": "Principal Architect AI",
            "timestamp": "2026-08-15 12:00:00",
            "message": "v1.0: Initial massing & structural grid (Forma site layout)",
            "element_count": 28,
            "lod": "LOD 200",
        },
        {
            "version": 2,
            "commit_id": "c_mep_90b2",
            "author": "MagiCAD MEP Engine",
            "timestamp": "2026-08-15 14:30:00",
            "message": "v2.0: Routed 110mm wet stack, electrical conduits & HVAC chillers",
            "element_count": 48,
            "lod": "LOD 350",
        },
        {
            "version": 3,
            "commit_id": "c_arch_91c3",
            "author": "OpenBIM Studio",
            "timestamp": "2026-08-15 18:00:00",
            "message": "v3.0: High-detail interior suites, Calacatta island, pool & PBR shaders",
            "element_count": 73,
            "lod": "LOD 400",
        },
    ]
}

@router.post("/upload-ifc")
async def upload_ifc_file(file: UploadFile = File(...)):
    """
    Ingests an OpenBIM .ifc file and parses it using IfcOpenShell into our real-estate model format.
    """
    try:
        content = await file.read()
        parsed_data = parse_ifc_content(content)
        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse IFC file: {str(e)}")

@router.post("/export-ifc")
async def export_ifc_file(model_data: Dict[str, Any] = Body(...)):
    """
    Generates a valid ISO 10303-21 IFC4 file using IfcOpenShell from current building model.
    """
    try:
        ifc_file = create_ifc4_project_from_model(model_data)
        ifc_text = ifc_file.to_string()
        filename = f"{model_data.get('name', 'BuilderAI_Project').replace(' ', '_')}.ifc"
        
        return Response(
            content=ifc_text,
            media_type="application/x-step",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate IFC: {str(e)}")

@router.get("/spatial-tree/{project_id}")
async def get_spatial_tree(project_id: int):
    """
    Returns the Cesium 3D Tiles / ThatOpen Spatial Hierarchy:
    City -> Society -> Tower -> Storeys -> Spaces -> Elements
    """
    return {
        "id": "city_01",
        "name": "Metropolitan Smart City District",
        "type": "City / Campus (LOD 100)",
        "children": [
            {
                "id": "society_01",
                "name": "Vinewood Hills Luxury Estate Masterplan",
                "type": "Society / Masterplan (LOD 200)",
                "children": [
                    {
                        "id": "tower_01",
                        "name": "Villa Aurora (Main Residence)",
                        "type": "Building (LOD 300)",
                        "children": [
                            {
                                "id": "storey_01",
                                "name": "Level 1: Ground Living & Island Kitchen",
                                "type": "Storey (LOD 350)",
                                "spaces": ["Great Living Room", "Chef Kitchen", "Grand Foyer", "Guest Suite", "Powder Room"]
                            },
                            {
                                "id": "storey_02",
                                "name": "Level 2: Master Suite & Terrace",
                                "type": "Storey (LOD 400)",
                                "spaces": ["Master King Bedroom", "Spa Ensuite Bathroom", "Walk-in Dressing", "Balcony Deck"]
                            },
                            {
                                "id": "storey_03",
                                "name": "Level 3: Rooftop Mechanical & Solar Plant",
                                "type": "Storey (LOD 500)",
                                "spaces": ["HVAC Chiller Plant", "Solar Array", "Elevator Penthouse", "Sky Lounge"]
                            }
                        ]
                    }
                ]
            }
        ]
    }

@router.get("/magicad-mep-specs/{project_id}")
async def get_magicad_mep_specs(project_id: int):
    """
    Returns MagiCAD MEP technical product specifications and calculated flow capacities.
    """
    return {
        "project_id": project_id,
        "standard": "MagiCAD 2026.1 / DIN EN 12056 / IBC Mechanical",
        "systems": [
            {
                "system": "Sanitary Drainage Soil Stack",
                "type": "IfcFlowSegment",
                "specification": "PVC-U Solvent-Weld High Acoustic Pipe (DN110 / Ø110mm x 3.2mm)",
                "capacity": "4.5 L/s gravity discharge flow",
                "compliance": "DIN EN 12056-2 (System I)"
            },
            {
                "system": "Potable Domestic Hot & Cold Water",
                "type": "IfcFlowSegment",
                "specification": "Multi-layer Composite PE-RT / AL / PE-RT (DN25 / Ø25mm)",
                "pressure_rating": "PN16 @ 70°C",
                "compliance": "WRAS / DVGW Certified"
            },
            {
                "system": "Electrical High-Voltage Distribution",
                "type": "IfcElectricDistributionBoard",
                "specification": "3-Phase 415V 200A Main Switchboard with Type 2 Surge Protection",
                "circuits": "24 Miniature Circuit Breakers (RCBO 30mA)",
                "compliance": "IEC 61439-2"
            },
            {
                "system": "HVAC Chilled Water Air Handling",
                "type": "IfcUnitaryEquipment",
                "specification": "Variable Refrigerant Flow (VRF) Rooftop Heat Pump (28 kW Cooling)",
                "air_flow": "1,400 CFM Galvanized Duct Network (300mm x 150mm)",
                "efficiency": "SEER 18.5"
            }
        ]
    }

@router.get("/speckle-versions/{project_id}")
async def get_speckle_versions(project_id: int):
    """
    Returns Speckle-style version history object graph.
    """
    return SPECKLE_VERSIONS_DB.get(project_id, SPECKLE_VERSIONS_DB[1])
