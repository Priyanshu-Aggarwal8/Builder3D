from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Residential Villa"})
    plot_size: float = Field(..., gt=0, json_schema_extra={"example": 400.0})
    floors: int = Field(default=1, ge=1, le=100, json_schema_extra={"example": 1})


class ProjectResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    plot_size: float
    floors: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ModelElementResponse(BaseModel):
    id: str
    model_id: int
    parent_id: Optional[str] = None
    hierarchy_level: str
    layer_id: str
    type: str
    name: str
    position: List[float]
    rotation: List[float]
    scale: List[float]
    dimensions: Dict[str, float]
    material: Dict[str, Any]
    metadata_info: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ElementUpdateSchema(BaseModel):
    position: Optional[List[float]] = Field(None, description="[x, y, z] position array")
    rotation: Optional[List[float]] = Field(None, description="[rx, ry, rz] euler rotation in radians")
    scale: Optional[List[float]] = Field(None, description="[sx, sy, sz] scale array")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Updated dimensions dict")
    name: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None


class LayerGroupResponse(BaseModel):
    id: str
    name: str
    visible: bool = True
    elements: List[ModelElementResponse]


class BuildingModelSceneResponse(BaseModel):
    project_id: int
    version: int
    bounds: Dict[str, float]
    layers: Dict[str, LayerGroupResponse]
