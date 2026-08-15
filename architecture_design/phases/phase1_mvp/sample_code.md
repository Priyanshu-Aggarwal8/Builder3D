# Phase 1 Sample Code
## Python (FastAPI Backend)  
**repositories/project_repository.py:** Handles database  
```python
from sqlalchemy.orm import Session
from app.models.project import Project

class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db
    def create_project(self, project_data: dict) -> Project:
        try:
            project = Project(**project_data)
            self.db.add(project); self.db.commit(); self.db.refresh(project)
            return project
        except Exception as e:
            self.db.rollback()
            raise e
    def get_project(self, project_id: int) -> Project:
        return self.db.query(Project).filter(Project.id == project_id).first()
```  
**services/project_service.py:** Business rules  
```python
from app.repositories.project_repository import ProjectRepository

class ProjectService:
    def __init__(self, repo: ProjectRepository):
        self.repo = repo
    def create_project(self, data: dict):
        # business logic, validation
        if data["plot_size"] <= 0:
            raise ValueError("Plot size must be positive")
        return self.repo.create_project(data)
```  
**api/project_controller.py:** FastAPI router  
```python
from fastapi import APIRouter, Depends, HTTPException
from app.services.project_service import ProjectService
from app.schemas.project_schema import ProjectCreate

router = APIRouter(prefix="/projects")

@router.post("/", status_code=201)
def create_project(data: ProjectCreate, 
    service: ProjectService = Depends()):
    try:
        project = service.create_project(data.dict())
        return project
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal error")
```  
**Angular (TypeScript) - project.service.ts:** Calling backend API  
```typescript
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({providedIn: 'root'})
export class ProjectService {
  constructor(private http: HttpClient) {}
  createProject(data: any) {
    return this.http.post('/api/projects', data);
  }
}
```  
**Angular component (create-project.component.ts):** Uses the service  
```typescript
import { Component } from '@angular/core';
import { ProjectService } from '../services/project.service';

@Component({selector: 'app-create-project', template: `...`})
export class CreateProjectComponent {
  projectData = {plot_size: 1000, floors: 1, rooms: ['bedroom', 'kitchen']};
  constructor(private projectSvc: ProjectService) {}
  submit() {
    this.projectSvc.createProject(this.projectData)
      .subscribe(res => console.log(res), err => console.error(err));
  }
}
```  
These examples show **layered structure**: controllers use services via DI, which use repositories to access the DB. No layer skips the others. Errors are caught and mapped to HTTP exceptions.
