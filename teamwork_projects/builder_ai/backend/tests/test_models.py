from app.schemas.project import ProjectCreate, ElementUpdateSchema
from app.services import model_service


def test_create_project_and_model_generation(db):
    project_in = ProjectCreate(name="Test Villa", plot_size=300.0, floors=2)
    project = model_service.create_project(db, project_in)

    assert project.id is not None
    assert project.name == "Test Villa"
    assert project.plot_size == 300.0
    assert project.floors == 2

    scene = model_service.get_building_model_scene(db, project.id)
    assert scene is not None
    assert "layers" in scene
    assert "structural" in scene["layers"]
    assert "electrical" in scene["layers"]
    assert "plumbing" in scene["layers"]

    structural_elements = scene["layers"]["structural"]["elements"]
    electrical_elements = scene["layers"]["electrical"]["elements"]
    plumbing_elements = scene["layers"]["plumbing"]["elements"]

    assert len(structural_elements) >= 5
    assert len(electrical_elements) >= 3
    assert len(plumbing_elements) >= 3


def test_update_element_transform(db):
    project_in = ProjectCreate(name="Patch Test Villa", plot_size=250.0, floors=1)
    project = model_service.create_project(db, project_in)

    scene = model_service.get_building_model_scene(db, project.id)
    first_element = scene["layers"]["structural"]["elements"][0]
    element_id = first_element.id

    patch_in = ElementUpdateSchema(
        position=[10.0, 5.0, -2.0],
        rotation=[0.0, 1.57, 0.0],
        dimensions={"width": 20.0, "height": 0.3, "depth": 20.0}
    )

    updated = model_service.update_model_element(db, project.id, element_id, patch_in)
    assert updated is not None
    assert updated.position == [10.0, 5.0, -2.0]
    assert updated.rotation == [0.0, 1.57, 0.0]
    assert updated.dimensions["width"] == 20.0
