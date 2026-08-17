from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api.v1 import projects, models, chat, bim, spatial, walls
import app.models.project

# Create database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix=settings.API_V1_STR, tags=["projects"])
app.include_router(models.router, prefix=settings.API_V1_STR, tags=["models"])
app.include_router(chat.router, prefix=settings.API_V1_STR + "/chat", tags=["chat"])
app.include_router(bim.router, prefix=settings.API_V1_STR + "/bim", tags=["bim"])
app.include_router(spatial.router, prefix=settings.API_V1_STR + "/spatial", tags=["spatial"])
app.include_router(spatial.router, prefix="/api/v1/spatial", tags=["spatial_v1"])
app.include_router(walls.router, prefix=settings.API_V1_STR + "/walls", tags=["walls"])
app.include_router(walls.router, prefix="/api/v1/walls", tags=["walls_v1"])

@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}
