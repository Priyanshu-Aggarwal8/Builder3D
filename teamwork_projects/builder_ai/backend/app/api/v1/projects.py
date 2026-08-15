from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services import model_service

router = APIRouter()


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    return model_service.create_project(db, project_in)


@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return model_service.get_projects(db)


@router.get("/projects/{id}", response_model=ProjectResponse)
def get_project(id: int, db: Session = Depends(get_db)):
    project = model_service.get_project(db, id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
