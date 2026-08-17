"""
API Router for Deterministic Spatial Solver and 2D Floorplan Topology.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

from app.schemas.design_spec import DesignSpec
from app.schemas.spatial import SpatialNode
from app.schemas.spatial_solver import FloorplanLayout
from app.services.spatial_solver import SpatialSolver

router = APIRouter()


@router.post(
    "/solve",
    response_model=List[FloorplanLayout],
    summary="Solve DesignSpec into 2D Floorplan Layouts",
    description="Deterministically solves building footprint and room boundary polygons for all storeys in a DesignSpec.",
)
def solve_floorplans_endpoint(spec: DesignSpec) -> List[FloorplanLayout]:
    try:
        layouts = SpatialSolver.solve_floorplans(spec)
        return layouts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Spatial solver failed: {str(e)}",
        )


@router.post(
    "/tree-with-geometry",
    response_model=SpatialNode,
    summary="Compile Canonical Spatial Hierarchy Enriched with 2D Geometry",
    description="Compiles a DesignSpec into a 6-tier SpatialNode tree with room boundary polygons populated.",
)
def compile_tree_with_geometry_endpoint(spec: DesignSpec) -> SpatialNode:
    try:
        tree = SpatialSolver.compile_spatial_tree_with_geometry(spec)
        return tree
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Compilation of spatial tree with geometry failed: {str(e)}",
        )
