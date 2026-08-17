"""
FastAPI Router for Parametric Wall Engine and Hosted Openings (Milestone 3).

Endpoints:
- POST /api/v1/walls/generate-from-floorplan
- POST /api/v1/walls/generate-from-rooms
- POST /api/v1/walls/host-opening
- POST /api/v1/walls/validate-volume
- POST /api/v1/walls/batch-subsegment
"""

from __future__ import annotations

from typing import List, Union

from fastapi import APIRouter, HTTPException, status

from app.schemas.wall import (
    BatchSubSegmentRequest,
    BatchSubSegmentResponse,
    HostOpeningRequest,
    HostedOpeningRequest,
    ParametricWall,
    VolumeValidationRequest,
    VolumeValidationResponse,
    WallExtractionResponse,
    WallGenerationFromFloorplanRequest,
    WallGenerationFromRoomsRequest,
)
from app.services.wall_engine import WallEngine

router = APIRouter()


@router.post(
    "/generate-from-floorplan",
    response_model=WallExtractionResponse,
    summary="Extract Parametric Walls from Floorplan Layout",
    description="Extracts exterior and interior parametric walls with shared edge deduplication from a FloorplanLayout.",
)
def generate_walls_from_floorplan_endpoint(
    req: WallGenerationFromFloorplanRequest,
) -> WallExtractionResponse:
    try:
        walls = WallEngine.extract_walls_from_floorplan(
            layout=req.layout,
            exterior_thickness=req.exterior_thickness,
            interior_thickness=req.interior_thickness,
            wall_height=req.wall_height,
        )
        ext_count = sum(1 for w in walls if w.is_exterior)
        int_count = sum(1 for w in walls if not w.is_exterior)
        total_len = sum(w.length for w in walls)
        total_vol = sum(w.gross_volume for w in walls)

        return WallExtractionResponse(
            walls=walls,
            total_walls=len(walls),
            exterior_walls_count=ext_count,
            interior_walls_count=int_count,
            total_linear_length_m=round(total_len, 3),
            total_gross_volume_m3=round(total_vol, 3),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Wall extraction from floorplan failed: {str(e)}",
        )


@router.post(
    "/generate-from-rooms",
    response_model=WallExtractionResponse,
    summary="Extract Parametric Walls from Room Polygons",
    description="Extracts exterior and interior parametric walls from a list of RoomBoundary polygons.",
)
def generate_walls_from_rooms_endpoint(
    req: WallGenerationFromRoomsRequest,
) -> WallExtractionResponse:
    try:
        walls = WallEngine.extract_walls_from_room_boundaries(
            rooms=req.rooms,
            exterior_thickness=req.exterior_thickness,
            interior_thickness=req.interior_thickness,
            wall_height=req.wall_height,
            base_elevation=req.base_elevation,
            storey_index=req.storey_index,
        )
        ext_count = sum(1 for w in walls if w.is_exterior)
        int_count = sum(1 for w in walls if not w.is_exterior)
        total_len = sum(w.length for w in walls)
        total_vol = sum(w.gross_volume for w in walls)

        return WallExtractionResponse(
            walls=walls,
            total_walls=len(walls),
            exterior_walls_count=ext_count,
            interior_walls_count=int_count,
            total_linear_length_m=round(total_len, 3),
            total_gross_volume_m3=round(total_vol, 3),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Wall extraction from rooms failed: {str(e)}",
        )


@router.post(
    "/host-opening",
    response_model=ParametricWall,
    summary="Host Opening on Parametric Wall",
    description="Hosts a door or window on a host wall run and sub-segments the wall into PRE, POST, LINTEL, SILL.",
)
def host_opening_endpoint(req: Union[HostOpeningRequest, HostedOpeningRequest]) -> ParametricWall:
    try:
        updated_wall = WallEngine.host_opening_on_wall(wall=req.wall, opening=req.opening)
        return updated_wall
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid opening hosting: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to host opening on wall: {str(e)}",
        )


@router.post(
    "/validate-volume",
    response_model=VolumeValidationResponse,
    summary="Validate Wall Volume Conservation Invariant",
    description="Verifies Invariant 4: Volume(Solid Wall) == Sum(SubSegments) + Sum(Openings).",
)
def validate_volume_endpoint(wall_input: Union[ParametricWall, VolumeValidationRequest]) -> VolumeValidationResponse:
    try:
        target_wall = wall_input.wall if isinstance(wall_input, VolumeValidationRequest) else wall_input
        res = WallEngine.validate_volume_conservation(target_wall)
        return VolumeValidationResponse(**res)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Volume validation failed: {str(e)}",
        )


@router.post(
    "/batch-subsegment",
    response_model=BatchSubSegmentResponse,
    summary="Batch Subsegment Parametric Walls",
    description="Recalculates sub-segments for a batch of walls and verifies volume conservation across all walls.",
)
def batch_subsegment_endpoint(req: BatchSubSegmentRequest) -> BatchSubSegmentResponse:
    try:
        processed_walls: List[ParametricWall] = []
        all_conserved = True
        for w in req.walls:
            w.sub_segments = WallEngine.compute_wall_subsegments(w)
            val = WallEngine.validate_volume_conservation(w)
            if not val["is_valid"]:
                all_conserved = False
            processed_walls.append(w)

        return BatchSubSegmentResponse(
            walls=processed_walls,
            total_walls_processed=len(processed_walls),
            all_volumes_conserved=all_conserved,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch subsegmentation failed: {str(e)}",
        )
