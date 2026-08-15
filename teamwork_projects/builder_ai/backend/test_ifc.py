import ifcopenshell
from app.services.ifc_engine import create_ifc4_project_from_model

sample_model = {
    "name": "Vinewood OpenBIM Villa",
    "layers": {
        "structural": {
            "elements": [
                {"id": "w1", "name": "Ground Exterior Wall", "type": "wall", "position": [0, 1.8, 0], "dimensions": {"width": 12, "height": 3.6, "depth": 0.25}},
                {"id": "s1", "name": "Ground Level Slab", "type": "slab", "position": [0, -0.15, 0], "dimensions": {"width": 14, "height": 0.3, "depth": 14}},
                {"id": "d1", "name": "Entrance Pivot Door", "type": "door", "position": [2, 1.2, 0], "dimensions": {"width": 1.4, "height": 2.6, "depth": 0.15}},
            ]
        },
        "plumbing": {
            "elements": [
                {"id": "p1", "name": "Main Soil Stack DN110", "type": "pipe", "position": [5, 3.6, 0], "dimensions": {"width": 0.15, "height": 7.2, "depth": 0.15}}
            ]
        }
    }
}

ifc_file = create_ifc4_project_from_model(sample_model)
content = ifc_file.to_string()
print("IFC HEADER:")
print("\n".join(content.split("\n")[:12]))
print("\nIFC ENTITIES FOUND:")
for ent in ifc_file.by_type("IfcProduct"):
    print(f" - {ent.is_a()}: {ent.Name}")
