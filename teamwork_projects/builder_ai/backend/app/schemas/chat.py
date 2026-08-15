from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    prompt: str
    project_id: int
    context: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    generated_elements: Optional[List[Dict[str, Any]]] = None
