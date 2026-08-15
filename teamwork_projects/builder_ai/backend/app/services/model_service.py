import math
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from app.models.project import User, Project, BuildingModel, ModelElement
from app.schemas.project import ProjectCreate, ElementUpdateSchema


def get_or_create_default_user(db: Session) -> User:
    user = db.query(User).filter(User.email == "demo@builderai.com").first()
    if not user:
        user = User(
            email="demo@builderai.com",
            name="Demo Builder",
            hashed_password="hashed_demo_password"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def generate_default_bim_model(db: Session, project_id: int, plot_size: float, floors: int) -> BuildingModel:
    side = math.sqrt(plot_size)
    width = round(side, 2)
    length = round(side, 2)
    height = round(floors * 3.0, 2)

    building_model = BuildingModel(
        project_id=project_id,
        version=1,
        bounds={"width": width, "length": length, "height": height}
    )
    db.add(building_model)
    db.flush()

    elements = []

    # 1. STRUCTURAL LAYER
    # Ground Floor Slab
    elements.append(ModelElement(
        id=f"p{project_id}_struct_slab_01",
        model_id=building_model.id,
        layer_id="structural",
        type="slab",
        name="Ground Floor Slab",
        position=[0.0, -0.1, 0.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": width, "height": 0.2, "depth": length},
        material={"color": "#A0AEC0", "metalness": 0.1, "roughness": 0.8, "opacity": 1.0},
        metadata_info={"concrete_grade": "M30"}
    ))

    # Exterior Walls
    wall_thickness = 0.3
    half_w = width / 2.0
    half_l = length / 2.0
    wall_y = height / 2.0

    # North Wall
    elements.append(ModelElement(
        id=f"p{project_id}_struct_wall_north",
        model_id=building_model.id,
        layer_id="structural",
        type="wall",
        name="North Exterior Wall",
        position=[0.0, wall_y, -half_l + wall_thickness / 2.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": width, "height": height, "depth": wall_thickness},
        material={"color": "#718096", "metalness": 0.0, "roughness": 0.9, "opacity": 1.0},
        metadata_info={"load_bearing": True}
    ))

    # South Wall
    elements.append(ModelElement(
        id=f"p{project_id}_struct_wall_south",
        model_id=building_model.id,
        layer_id="structural",
        type="wall",
        name="South Exterior Wall",
        position=[0.0, wall_y, half_l - wall_thickness / 2.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": width, "height": height, "depth": wall_thickness},
        material={"color": "#718096", "metalness": 0.0, "roughness": 0.9, "opacity": 1.0},
        metadata_info={"load_bearing": True}
    ))

    # East Wall
    elements.append(ModelElement(
        id=f"p{project_id}_struct_wall_east",
        model_id=building_model.id,
        layer_id="structural",
        type="wall",
        name="East Exterior Wall",
        position=[half_w - wall_thickness / 2.0, wall_y, 0.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": wall_thickness, "height": height, "depth": length},
        material={"color": "#718096", "metalness": 0.0, "roughness": 0.9, "opacity": 1.0},
        metadata_info={"load_bearing": True}
    ))

    # West Wall
    elements.append(ModelElement(
        id=f"p{project_id}_struct_wall_west",
        model_id=building_model.id,
        layer_id="structural",
        type="wall",
        name="West Exterior Wall",
        position=[-half_w + wall_thickness / 2.0, wall_y, 0.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": wall_thickness, "height": height, "depth": length},
        material={"color": "#718096", "metalness": 0.0, "roughness": 0.9, "opacity": 1.0},
        metadata_info={"load_bearing": True}
    ))

    # Structural Columns (4 Corners)
    col_size = 0.5
    offset = col_size / 2.0 + 0.1
    corners = [
        ("nw", -half_w + offset, -half_l + offset),
        ("ne", half_w - offset, -half_l + offset),
        ("sw", -half_w + offset, half_l - offset),
        ("se", half_w - offset, half_l - offset)
    ]
    for tag, cx, cz in corners:
        elements.append(ModelElement(
            id=f"p{project_id}_struct_col_{tag}",
            model_id=building_model.id,
            layer_id="structural",
            type="column",
            name=f"Corner Column {tag.upper()}",
            position=[cx, wall_y, cz],
            rotation=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, 1.0],
            dimensions={"width": col_size, "height": height, "depth": col_size},
            material={"color": "#4A5568", "metalness": 0.2, "roughness": 0.7, "opacity": 1.0},
            metadata_info={"rebar_reinforcement": "C35/40"}
        ))

    # 2. ELECTRICAL LAYER
    # Main Distribution Panel
    elements.append(ModelElement(
        id=f"p{project_id}_elec_jbox_01",
        model_id=building_model.id,
        layer_id="electrical",
        type="junction_box",
        name="Main Distribution Panel",
        position=[0.0, 2.2, -half_l + wall_thickness + 0.1],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": 0.5, "height": 0.6, "depth": 0.2},
        material={"color": "#D69E2E", "metalness": 0.8, "roughness": 0.2, "opacity": 1.0},
        metadata_info={"rating": "200A", "circuits": 12}
    ))

    # Main Wall Conduit
    elements.append(ModelElement(
        id=f"p{project_id}_elec_conduit_01",
        model_id=building_model.id,
        layer_id="electrical",
        type="conduit",
        name="Main Electrical Conduit",
        position=[0.0, 2.5, -half_l + wall_thickness + 0.05],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"length": width - 1.0, "radius": 0.04},
        material={"color": "#ECC94B", "metalness": 0.6, "roughness": 0.3, "opacity": 1.0},
        metadata_info={"voltage": "240V", "conduit_type": "PVC Rigid"}
    ))

    # Wall Outlets
    elements.append(ModelElement(
        id=f"p{project_id}_elec_outlet_01",
        model_id=building_model.id,
        layer_id="electrical",
        type="outlet",
        name="North Wall Power Outlet",
        position=[-width / 4.0, 0.5, -half_l + wall_thickness + 0.05],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": 0.15, "height": 0.15, "depth": 0.05},
        material={"color": "#FFCC00", "metalness": 0.5, "roughness": 0.3, "opacity": 1.0},
        metadata_info={"duplex": True, "gfci": True}
    ))

    elements.append(ModelElement(
        id=f"p{project_id}_elec_outlet_02",
        model_id=building_model.id,
        layer_id="electrical",
        type="outlet",
        name="South Wall Power Outlet",
        position=[width / 4.0, 0.5, half_l - wall_thickness - 0.05],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": 0.15, "height": 0.15, "depth": 0.05},
        material={"color": "#FFCC00", "metalness": 0.5, "roughness": 0.3, "opacity": 1.0},
        metadata_info={"duplex": True, "gfci": False}
    ))

    # 3. PLUMBING LAYER
    # Cold Water Main Pipe
    elements.append(ModelElement(
        id=f"p{project_id}_plumb_pipe_main",
        model_id=building_model.id,
        layer_id="plumbing",
        type="pipe",
        name="Cold Water Main Line",
        position=[-half_w + 1.0, 0.4, 0.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"length": length - 2.0, "radius": 0.06},
        material={"color": "#3182CE", "metalness": 0.7, "roughness": 0.2, "opacity": 1.0},
        metadata_info={"fluid": "Potable Water", "pressure_psi": 60}
    ))

    # Main Shutoff Valve
    elements.append(ModelElement(
        id=f"p{project_id}_plumb_valve_01",
        model_id=building_model.id,
        layer_id="plumbing",
        type="valve",
        name="Main Water Shutoff Valve",
        position=[-half_w + 1.0, 0.4, -half_l / 2.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": 0.25, "height": 0.3, "depth": 0.25},
        material={"color": "#2B6CB0", "metalness": 0.9, "roughness": 0.1, "opacity": 1.0},
        metadata_info={"valve_type": "Ball Valve", "state": "open"}
    ))

    # Floor Drain
    elements.append(ModelElement(
        id=f"p{project_id}_plumb_drain_01",
        model_id=building_model.id,
        layer_id="plumbing",
        type="drain",
        name="Utility Floor Drain",
        position=[-half_w + 1.0, 0.05, half_l / 2.0],
        rotation=[0.0, 0.0, 0.0],
        scale=[1.0, 1.0, 1.0],
        dimensions={"width": 0.4, "height": 0.1, "depth": 0.4},
        material={"color": "#718096", "metalness": 0.5, "roughness": 0.5, "opacity": 1.0},
        metadata_info={"drain_type": "Trap Assembly"}
    ))

    for el in elements:
        db.add(el)

    db.commit()
    db.refresh(building_model)
    return building_model


def create_project(db: Session, project_in: ProjectCreate) -> Project:
    user = get_or_create_default_user(db)
    project = Project(
        user_id=user.id,
        name=project_in.name,
        plot_size=project_in.plot_size,
        floors=project_in.floors,
        status="active"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    generate_default_bim_model(db, project.id, project.plot_size, project.floors)
    return project


def get_projects(db: Session) -> List[Project]:
    return db.query(Project).all()


def get_project(db: Session, project_id: int) -> Optional[Project]:
    return db.query(Project).filter(Project.id == project_id).first()


def get_building_model_scene(db: Session, project_id: int) -> Optional[Dict]:
    building_model = db.query(BuildingModel).filter(BuildingModel.project_id == project_id).first()
    if not building_model:
        return None

    layers_dict = {
        "structural": {"id": "structural", "name": "Structural Layer", "visible": True, "elements": []},
        "electrical": {"id": "electrical", "name": "Electrical Layer", "visible": True, "elements": []},
        "plumbing": {"id": "plumbing", "name": "Plumbing Layer", "visible": True, "elements": []}
    }

    for el in building_model.elements:
        l_id = el.layer_id or "structural"
        if l_id not in layers_dict:
            layers_dict[l_id] = {"id": l_id, "name": f"{l_id.capitalize()} Layer", "visible": True, "elements": []}
        layers_dict[l_id]["elements"].append(el)

    return {
        "project_id": project_id,
        "version": building_model.version,
        "bounds": building_model.bounds,
        "layers": layers_dict
    }


def update_model_element(db: Session, project_id: int, element_id: str, element_in: ElementUpdateSchema) -> Optional[ModelElement]:
    building_model = db.query(BuildingModel).filter(BuildingModel.project_id == project_id).first()
    if not building_model:
        return None

    element = db.query(ModelElement).filter(
        ModelElement.id == element_id,
        ModelElement.model_id == building_model.id
    ).first()

    if not element:
        return None

    update_data = element_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(element, field):
            setattr(element, field, value)

    building_model.version += 1
    building_model.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(element)
    return element
