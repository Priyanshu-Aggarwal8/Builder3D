from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    plot_size = Column(Float, nullable=False)
    floors = Column(Integer, default=1)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    building_model = relationship("BuildingModel", back_populates="project", uselist=False, cascade="all, delete-orphan")


class BuildingModel(Base):
    __tablename__ = "building_models"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, nullable=False)
    version = Column(Integer, default=1)
    bounds = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="building_model")
    elements = relationship("ModelElement", back_populates="model", cascade="all, delete-orphan")


class ModelElement(Base):
    __tablename__ = "model_elements"

    id = Column(String, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("building_models.id"), nullable=False)
    parent_id = Column(String, ForeignKey("model_elements.id"), nullable=True)
    hierarchy_level = Column(String, default="element", nullable=False) # society, building, floor, room, element
    layer_id = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    position = Column(JSON, nullable=False)
    rotation = Column(JSON, nullable=False)
    scale = Column(JSON, nullable=False)
    dimensions = Column(JSON, nullable=False)
    material = Column(JSON, nullable=False)
    metadata_info = Column(JSON, nullable=True)

    model = relationship("BuildingModel", back_populates="elements")
    parent = relationship("ModelElement", remote_side=[id])
