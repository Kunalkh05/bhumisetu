"""Officer GIS endpoints."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Iterator

from fastapi import Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.routers import officer_router
from app.db.session import get_engine
from app.schemas.gis import (
    BboxOut,
    ClusterFeatureOut,
    ParcelBboxOut,
    ParcelGeometryFeatureOut,
    ParcelMapOut,
)
from app.security.access import Principal, authenticate
from app.services.gis import (
    build_redis_tile_cache,
    get_parcel_geometry,
    get_parcel_map_payload,
    list_parcels_in_bbox,
    parse_bbox,
    vector_tile,
)
from app.services.policy import PLATFORM_WIDE, PolicyResolver
from app.settings import get_broker_settings

__all__ = []

DEFAULT_SIMPLIFICATION_TOLERANCE = 0.00001
DEFAULT_CLUSTER_CELL_SIZE_DEG = 0.05
GIS_CLUSTER_THRESHOLD_KEY = "gis.cluster_threshold"
MAX_BBOX_FEATURES = 5000


@contextmanager
def _read_session() -> Iterator[Session]:
    session = Session(bind=get_engine())
    try:
        yield session
    finally:
        session.close()


@officer_router.get(
    "/gis/parcels",
    response_model=ParcelBboxOut,
)
def parcels_in_bbox(
    bbox: str = Query(...),
    tolerance: float = Query(DEFAULT_SIMPLIFICATION_TOLERANCE, ge=0),
    principal: Principal = Depends(authenticate),
) -> ParcelBboxOut:
    """Query land parcels intersecting a bounding box with viewport simplification.

    The response explicitly declares `geometry_simplified=True`, `simplification_tolerance`,
    and `coordinate_decimals=6`. This simplification is what allows 5000 parcels to transfer
    in ~250-400 KB and meet the R15.8 2-second p95 latency target (unsimplified 5000 parcels
    exceed 5 MB and take > 8 s at 5 Mbps).

    Full-fidelity survey-grade geometry is served on GET /gis/parcels/{parcel_id}/geometry.
    """
    with _read_session() as session:
        result = list_parcels_in_bbox(
            session,
            bbox=parse_bbox(bbox),
            scope_paths=principal.scope_paths,
            simplification_tolerance=tolerance,
            limit=MAX_BBOX_FEATURES,
        )
    return ParcelBboxOut(
        bbox=BboxOut.model_validate(result.bbox),
        simplification_tolerance=result.simplification_tolerance,
        limit=result.limit,
        geometry_simplified=True,
        coordinate_decimals=6,
        features=[
            ParcelGeometryFeatureOut.model_validate(feature)
            for feature in result.features
        ],
    )


@officer_router.get(
    "/gis/parcels/{parcel_id}/geometry",
    response_model=ParcelGeometryFeatureOut,
)
def parcel_full_fidelity_geometry(
    parcel_id: int,
    principal: Principal = Depends(authenticate),
) -> ParcelGeometryFeatureOut:
    """Return full-fidelity survey-grade geometry for a single parcel without simplification.

    R15.8 requires that 5000 parcels intersecting a viewport bounding box return
    within 2 s p95. To achieve that latency and payload budget (~250-400 KB vs ~5 MB),
    the bbox endpoint (/gis/parcels?bbox=) returns simplified geometry with viewport-derived
    tolerance and 6-decimal coordinate truncation.

    Full-fidelity, unsimplified survey-grade geometry is served exclusively through this
    single-parcel endpoint.
    """
    with _read_session() as session:
        feature = get_parcel_geometry(
            session,
            parcel_id=parcel_id,
            scope_paths=principal.scope_paths,
        )
    return ParcelGeometryFeatureOut.model_validate(feature)


@officer_router.get(
    "/gis/parcels/map",
    response_model=ParcelMapOut,
)
def parcel_map_payload(
    bbox: str = Query(...),
    tolerance: float = Query(DEFAULT_SIMPLIFICATION_TOLERANCE, ge=0),
    cell_size_deg: float = Query(DEFAULT_CLUSTER_CELL_SIZE_DEG, gt=0),
    principal: Principal = Depends(authenticate),
) -> ParcelMapOut:
    with _read_session() as session:
        cluster_threshold = int(
            PolicyResolver(session).get(
                GIS_CLUSTER_THRESHOLD_KEY,
                state=PLATFORM_WIDE,
                act=None,
                as_of=date.today(),
            )
        )
        result = get_parcel_map_payload(
            session,
            bbox=parse_bbox(bbox),
            scope_paths=principal.scope_paths,
            simplification_tolerance=tolerance,
            cluster_threshold=cluster_threshold,
            cluster_cell_size_deg=cell_size_deg,
        )
    return ParcelMapOut(
        mode=result.mode,
        bbox=BboxOut.model_validate(result.bbox),
        count=result.count,
        cluster_cell_size_deg=result.cluster_cell_size_deg,
        clusters=[ClusterFeatureOut.model_validate(cluster) for cluster in result.clusters],
        parcels=[
            ParcelGeometryFeatureOut.model_validate(parcel)
            for parcel in result.parcels
        ],
    )


@officer_router.get("/gis/tiles/{z}/{x}/{y}.mvt")
def parcel_vector_tile(
    z: int,
    x: int,
    y: int,
    principal: Principal = Depends(authenticate),
) -> Response:
    with _read_session() as session:
        body = vector_tile(
            session,
            z=z,
            x=x,
            y=y,
            scope_paths=principal.scope_paths,
            cache=build_redis_tile_cache(get_broker_settings().redis_url),
        )
    return Response(content=body, media_type="application/vnd.mapbox-vector-tile")
