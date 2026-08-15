import os
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.models.project import Project, BuildingModel, ModelElement
from app.services.meta_agent import meta_architect_agent
from app.services.architect_agent_flow import architect_conversation_agent, DISCOVERY_SESSIONS

router = APIRouter()

def _save_elements_to_db(db: Session, project_id: int, model_data: Dict[str, Any]):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        project = Project(
            id=project_id,
            name=model_data.get("name", "Synthesized Building"),
            plot_size=400.0,
            floors=model_data.get("meta", {}).get("floors", 2),
            status="active"
        )
        db.add(project)
        db.commit()
    else:
        project.name = model_data.get("name", project.name)
        project.floors = model_data.get("meta", {}).get("floors", project.floors)
        db.commit()

    building_model = db.query(BuildingModel).filter(BuildingModel.project_id == project.id).first()
    if not building_model:
        building_model = BuildingModel(project_id=project.id, bounds={"width": 30, "length": 30, "height": 10})
        db.add(building_model)
        db.commit()

    # Clear existing elements for this model
    db.query(ModelElement).filter(ModelElement.model_id == building_model.id).delete()

    # Extract all elements from layers
    elements_data = []
    if "layers" in model_data:
        for layer in model_data["layers"].values():
            elements_data.extend(layer.get("elements", []))
    elif "generated_elements" in model_data:
        elements_data = model_data.get("generated_elements", [])

    for el in elements_data:
        db_el = ModelElement(
            id=el.get("id", str(uuid.uuid4())),
            model_id=building_model.id,
            layer_id=el.get("layer_id", "structural"),
            parent_id=el.get("parent_id"),
            hierarchy_level=el.get("hierarchy_level", "element"),
            type=el.get("type", "slab"),
            name=el.get("name", "Generated Element"),
            position=el.get("position", [0, 0, 0]),
            rotation=el.get("rotation", [0, 0, 0]),
            scale=el.get("scale", [1, 1, 1]),
            dimensions=el.get("dimensions", {"width": 1, "height": 1, "depth": 1}),
            material=el.get("material", {})
        )
        db.add(db_el)

    building_model.version += 1
    db.commit()

@router.post("/message")
async def chat_turn(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Multi-step Conversational Agent Endpoint:
    Receives user messages, maintains active model state and discovery brief, supports in-place edits, and returns dynamic question chips and actions.
    """
    session_id = payload.get("session_id") or f"session_{uuid.uuid4().hex[:8]}"
    message = payload.get("message", "").strip()
    project_id = payload.get("project_id", 1)
    current_model = payload.get("current_model")
    synthesize_now = payload.get("synthesize_now", False)

    result = architect_conversation_agent.process_turn(
        session_id=session_id,
        user_message=message,
        current_model=current_model,
        synthesize_now=synthesize_now
    )

    if result.get("model"):
        _save_elements_to_db(db, project_id, result["model"])

    return result

@router.post("/generate")
async def generate_layout(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    prompt = payload.get("prompt", "")
    project_id = payload.get("project_id", 1)
    current_model = payload.get("current_model")

    # If an existing model is passed, attempt incremental mutation first
    if current_model:
        modified_model = meta_architect_agent.modify_existing_model(current_model, prompt)
        _save_elements_to_db(db, project_id, modified_model)
        return {
            "message": f"Updated model based on '{prompt[:35]}...'",
            "model": modified_model,
            "generated_elements": modified_model.get("generated_elements", []),
            "meta": modified_model.get("meta", {})
        }

    synthesized_model = meta_architect_agent.synthesize_model(prompt, project_id)
    _save_elements_to_db(db, project_id, synthesized_model)

    return {
        "message": f"Synthesized {len(synthesized_model['generated_elements'])} 3D entities for '{prompt[:35]}...'",
        "model": synthesized_model,
        "generated_elements": synthesized_model["generated_elements"],
        "meta": synthesized_model.get("meta", {})
    }
