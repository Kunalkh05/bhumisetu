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
