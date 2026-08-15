from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.project import BuildingModelSceneResponse, ModelElementResponse, ElementUpdateSchema
from app.services import model_service

router = APIRouter()


@router.get("/projects/{id}/model", response_model=BuildingModelSceneResponse)
def get_project_model(id: int, db: Session = Depends(get_db)):
    scene = model_service.get_building_model_scene(db, id)
    if not scene:
        raise HTTPException(status_code=404, detail="Building model for project not found")
    return scene


@router.patch("/projects/{id}/elements/{element_id}", response_model=ModelElementResponse)
def patch_model_element(
    id: int,
    element_id: str,
    element_in: ElementUpdateSchema,
    db: Session = Depends(get_db)
):
    updated_element = model_service.update_model_element(db, id, element_id, element_in)
    if not updated_element:
        raise HTTPException(status_code=404, detail="Element or project not found")
    return updated_element
