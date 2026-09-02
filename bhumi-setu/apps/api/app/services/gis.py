"""PostGIS-backed geometry writes for parcels, projects, and service points."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Protocol, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.errors import DomainError, ErrorCode

__all__ = [
    "Bbox",
    "ClusterFeature",
    "ParcelBboxResult",
    "ParcelGeometryFeature",
    "ParcelMapResult",
    "TileCache",
    "bump_parcel_geometry_generation",
    "build_redis_tile_cache",
    "get_parcel_map_payload",
    "GeometryWriteResult",
    "InvalidGeometry",
    "list_parcels_in_bbox",
    "parse_bbox",
    "store_geometry",
    "vector_tile",
]

WGS84_SRID = 4326
DEFAULT_TILE_TTL_SECONDS = 300

_AREA_TARGETS = frozenset({"parcel", "project"})
_TARGETS = {
    "parcel": {
        "table": "land_parcel",
        "column": "geom",
        "accepted": frozenset({"Polygon", "MultiPolygon"}),
        "stored": "ST_Multi(:geom_expr)",
        "area_column": "geodesic_area_sqm",
    },
    "project": {
        "table": "project",
        "column": "geom",
        "accepted": frozenset({"Polygon", "MultiPolygon"}),
        "stored": "ST_Multi(:geom_expr)",
        "area_column": None,
    },
    "notice_service_location": {
        "table": "notice_service_record",
        "column": "service_location",
        "accepted": frozenset({"Point"}),
        "stored": ":geom_expr",
        "area_column": None,
    },
}


class InvalidGeometry(DomainError):
    code = ErrorCode.VALIDATION_FAILED
    status_code = 422

    def __init__(
        self,
        message: str,
        *,
        target: str,
        geometry_type: str | None = None,
        reason: str | None = None,
        location: Mapping[str, Any] | None = None,
    ) -> None:
        details: dict[str, Any] = {"target": target}
        if geometry_type is not None:
            details["geometry_type"] = geometry_type
        if reason is not None:
            details["reason"] = reason
        if location is not None:
            details["location"] = dict(location)
        super().__init__(message, details=details)


@dataclass(frozen=True)
class GeometryWriteResult:
    entity_id: int
    target: str
    geojson: dict[str, Any]
    srid: int
    geodesic_area_sqm: Decimal | None


class TileCache(Protocol):
    def get(self, key: str) -> bytes | None:
        ...

    def setex(self, key: str, ttl: int, value: bytes) -> None:
        ...

    def incr(self, key: str) -> int:
        ...


class RedisTileCache:
    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    def get(self, key: str) -> bytes | None:
        return self._redis.get(key)

    def setex(self, key: str, ttl: int, value: bytes) -> None:
        self._redis.setex(key, ttl, value)

    def incr(self, key: str) -> int:
        return int(self._redis.incr(key))


def build_redis_tile_cache(redis_url: str) -> TileCache:
    from redis import Redis

    return RedisTileCache(Redis.from_url(redis_url))


@dataclass(frozen=True)
class Bbox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


@dataclass(frozen=True)
class ParcelGeometryFeature:
    parcel_id: int
    survey_number: str
    sub_division: str | None
    area_code: str
    geojson: dict[str, Any]


@dataclass(frozen=True)
class ParcelBboxResult:
    bbox: Bbox
    simplification_tolerance: float
    limit: int
    features: tuple[ParcelGeometryFeature, ...]


@dataclass(frozen=True)
class ClusterFeature:
    lon: float
    lat: float
    count: int


@dataclass(frozen=True)
class ParcelMapResult:
    mode: str
    bbox: Bbox
    count: int
    cluster_cell_size_deg: float | None
    clusters: tuple[ClusterFeature, ...] = ()
    parcels: tuple[ParcelGeometryFeature, ...] = ()


def parse_bbox(value: str) -> Bbox:
    parts = value.split(",")
    if len(parts) != 4:
        raise InvalidGeometry("bbox must contain four comma-separated numbers", target="bbox")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    except ValueError as exc:
        raise InvalidGeometry("bbox must contain numeric coordinates", target="bbox") from exc
    if min_lon >= max_lon or min_lat >= max_lat:
        raise InvalidGeometry(
            "bbox minimum coordinates must be below maximum coordinates",
            target="bbox",
        )
    if min_lon < -180 or max_lon > 180 or min_lat < -90 or max_lat > 90:
        raise InvalidGeometry("bbox coordinates must be WGS 84 lon/lat degrees", target="bbox")
    return Bbox(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)


def list_parcels_in_bbox(
    session: Session,
    *,
    bbox: Bbox,
    scope_paths: Sequence[str],
    simplification_tolerance: float,
    limit: int = 5000,
) -> ParcelBboxResult:
    if not scope_paths:
        return ParcelBboxResult(
            bbox=bbox,
            simplification_tolerance=simplification_tolerance,
            limit=limit,
            features=(),
        )
    if limit > 5000:
        raise ValueError("parcel bbox queries are capped at 5000 features")
    scope_clause, params = _scope_clause(scope_paths)
    params.update(_bbox_params(bbox))
    params["tolerance"] = simplification_tolerance
    params["limit"] = limit
    rows = session.execute(
        text(
            f"""
            WITH envelope AS (
                SELECT ST_MakeEnvelope(
                           :min_lon, :min_lat, :max_lon, :max_lat, 4326
                       ) AS geom
            )
            SELECT lp.id AS parcel_id,
                   lp.survey_number,
                   lp.sub_division,
                   lp.area_code,
                   ST_AsGeoJSON(
                       ST_ReducePrecision(
                           ST_SimplifyPreserveTopology(lp.geom, :tolerance),
                           0.000001
                       ),
                       6
                   )::jsonb AS geojson
              FROM land_parcel lp
              JOIN administrative_area aa ON lp.area_code = aa.code
              JOIN envelope box ON true
             WHERE lp.geom IS NOT NULL
               AND lp.geom && box.geom
               AND ST_Intersects(lp.geom, box.geom)
               AND ({scope_clause})
             LIMIT :limit
            """
        ),
        params,
    ).mappings()
    features = tuple(
        ParcelGeometryFeature(
            parcel_id=row["parcel_id"],
            survey_number=row["survey_number"],
            sub_division=row["sub_division"],
            area_code=row["area_code"],
            geojson=dict(row["geojson"]),
        )
        for row in rows
    )
    return ParcelBboxResult(
        bbox=bbox,
        simplification_tolerance=simplification_tolerance,
        limit=limit,
        features=features,
    )


def get_parcel_map_payload(
    session: Session,
    *,
    bbox: Bbox,
    scope_paths: Sequence[str],
    simplification_tolerance: float,
    cluster_threshold: int,
    cluster_cell_size_deg: float,
) -> ParcelMapResult:
    count = count_parcels_in_bbox(session, bbox=bbox, scope_paths=scope_paths)
    if count > cluster_threshold:
        return ParcelMapResult(
            mode="clusters",
            bbox=bbox,
            count=count,
            cluster_cell_size_deg=cluster_cell_size_deg,
            clusters=cluster_parcels_in_bbox(
                session,
                bbox=bbox,
                scope_paths=scope_paths,
                cell_size_deg=cluster_cell_size_deg,
            ),
        )
    parcel_result = list_parcels_in_bbox(
        session,
        bbox=bbox,
        scope_paths=scope_paths,
        simplification_tolerance=simplification_tolerance,
    )
    return ParcelMapResult(
        mode="parcels",
        bbox=bbox,
        count=count,
        cluster_cell_size_deg=None,
        parcels=parcel_result.features,
    )


def count_parcels_in_bbox(
    session: Session,
    *,
    bbox: Bbox,
    scope_paths: Sequence[str],
) -> int:
    if not scope_paths:
        return 0
    scope_clause, params = _scope_clause(scope_paths)
    params.update(_bbox_params(bbox))
    return int(
        session.execute(
            text(
                f"""
                WITH envelope AS (
                    SELECT ST_MakeEnvelope(
                               :min_lon, :min_lat, :max_lon, :max_lat, 4326
                           ) AS geom
                )
                SELECT count(*)
                  FROM land_parcel lp
                  JOIN administrative_area aa ON lp.area_code = aa.code
                  JOIN envelope box ON true
                 WHERE lp.geom IS NOT NULL
                   AND lp.geom && box.geom
                   AND ST_Intersects(lp.geom, box.geom)
                   AND ({scope_clause})
                """
            ),
            params,
        ).scalar_one()
    )


def cluster_parcels_in_bbox(
    session: Session,
    *,
    bbox: Bbox,
    scope_paths: Sequence[str],
    cell_size_deg: float,
) -> tuple[ClusterFeature, ...]:
    if not scope_paths:
        return ()
    scope_clause, params = _scope_clause(scope_paths)
    params.update(_bbox_params(bbox))
    params["cell_size_deg"] = cell_size_deg
    rows = session.execute(
        text(
            f"""
            WITH envelope AS (
                SELECT ST_MakeEnvelope(
                           :min_lon, :min_lat, :max_lon, :max_lat, 4326
                       ) AS geom
            ),
            snapped AS (
                SELECT ST_SnapToGrid(
                           ST_Centroid(lp.geom),
                           :cell_size_deg
                       ) AS cell
                  FROM land_parcel lp
                  JOIN administrative_area aa ON lp.area_code = aa.code
                  JOIN envelope box ON true
                 WHERE lp.geom IS NOT NULL
                   AND lp.geom && box.geom
                   AND ST_Intersects(lp.geom, box.geom)
                   AND ({scope_clause})
            )
            SELECT ST_X(cell) AS lon,
                   ST_Y(cell) AS lat,
                   count(*) AS count
              FROM snapped
             GROUP BY cell
             ORDER BY count DESC
            """
        ),
        params,
    ).mappings()
    return tuple(
        ClusterFeature(lon=float(row["lon"]), lat=float(row["lat"]), count=int(row["count"]))
        for row in rows
    )


def vector_tile(
    session: Session,
    *,
    z: int,
    x: int,
    y: int,
    scope_paths: Sequence[str],
    cache: TileCache,
    ttl_seconds: int = DEFAULT_TILE_TTL_SECONDS,
) -> bytes:
    generation = parcel_geometry_generation(cache, scope_paths)
    key = tile_cache_key(z=z, x=x, y=y, scope_paths=scope_paths, generation=generation)
    cached = cache.get(key)
    if cached is not None:
        return cached
    if not scope_paths:
        tile = b""
    else:
        scope_clause, params = _scope_clause(scope_paths)
        params.update({"z": z, "x": x, "y": y})
        tile = (
            session.execute(
                text(
                    f"""
                    WITH bounds AS (
                        SELECT ST_TileEnvelope(:z, :x, :y) AS geom
                    ),
                    mvtgeom AS (
                        SELECT lp.id,
                               lp.survey_number,
                               lp.extent,
                               lp.extent_unit,
                               c.id AS case_id,
                               c.case_reference,
                               c.stage_key,
                               c.risk_band,
                               ST_AsMVTGeom(lp.geom, bounds.geom) AS geom
                          FROM land_parcel lp
                          JOIN case_parcel cp ON cp.parcel_id = lp.id
                          JOIN acquisition_case c ON c.id = cp.case_id
                          JOIN administrative_area aa ON lp.area_code = aa.code
                          JOIN bounds ON true
                         WHERE lp.geom IS NOT NULL
                           AND lp.geom && bounds.geom
                           AND ST_Intersects(lp.geom, bounds.geom)
                           AND ({scope_clause})
                    )
                    SELECT ST_AsMVT(mvtgeom.*, 'parcels', 4096, 'geom')
                      FROM mvtgeom
                    """
                ),
                params,
            ).scalar_one()
            or b""
        )
    cache.setex(key, ttl_seconds, tile)
    return tile


def bump_parcel_geometry_generation(cache: TileCache, *, area_path: str) -> int:
    return cache.incr(parcel_geometry_generation_key(area_path))


def parcel_geometry_generation(cache: TileCache, scope_paths: Sequence[str]) -> int:
    values = [
        int(cache.get(parcel_geometry_generation_key(path)) or 0)
        for path in scope_paths
    ]
    return max(values, default=0)


def tile_cache_key(
    *,
    z: int,
    x: int,
    y: int,
    scope_paths: Sequence[str],
    generation: int,
) -> str:
    return (
        f"gis:mvt:{z}:{x}:{y}:scope={_scope_hash(scope_paths)}:"
        f"parcel_geom_generation={generation}"
    )


def parcel_geometry_generation_key(area_path: str) -> str:
    return f"gis:parcel-geom-generation:{area_path}"


def store_geometry(
    session: Session,
    *,
    target: str,
    entity_id: int,
    geometry: Mapping[str, Any],
    source_srid: int = WGS84_SRID,
    tile_cache: TileCache | None = None,
    affected_area_path: str | None = None,
) -> GeometryWriteResult:
    """Validate, transform, store, and return a geometry as WGS 84 GeoJSON."""
    spec = _target_spec(target)
    submitted_type = _submitted_geometry_type(geometry)
    if submitted_type not in spec["accepted"]:
        raise InvalidGeometry(
            "geometry type is not accepted for this target",
            target=target,
            geometry_type=submitted_type,
        )

    geojson = json.dumps(_geometry_payload(geometry), separators=(",", ":"))
    validation = session.execute(
        text(
            """
            WITH submitted AS (
                SELECT ST_Transform(
                           ST_SetSRID(ST_GeomFromGeoJSON(:geojson), :source_srid),
                           4326
                       ) AS geom
            ),
            normalized AS (
                SELECT CASE
                         WHEN :force_multi THEN ST_Multi(geom)
                         ELSE geom
                       END AS geom
                  FROM submitted
            ),
            detail AS (
                SELECT geom, ST_IsValidDetail(geom) AS validity
                  FROM normalized
            )
            SELECT (validity).valid AS valid,
                   (validity).reason AS reason,
                   ST_AsGeoJSON((validity).location, 6)::jsonb AS location,
                   ST_GeometryType(geom) AS geometry_type,
                   ST_SRID(geom) AS srid,
                   CASE
                     WHEN :compute_area THEN ST_Area(geom::geography)
                     ELSE NULL
                   END AS geodesic_area_sqm,
                   ST_AsGeoJSON(geom, 6)::jsonb AS geojson
              FROM detail
            """
        ),
        {
            "geojson": geojson,
            "source_srid": source_srid,
            "force_multi": target in _AREA_TARGETS,
            "compute_area": target in _AREA_TARGETS,
        },
    ).mappings().one()

    if not validation["valid"]:
        raise InvalidGeometry(
            "geometry is topologically invalid",
            target=target,
            geometry_type=submitted_type,
            reason=validation["reason"],
            location=validation["location"],
        )

    _write_geometry(
        session,
        target=target,
        entity_id=entity_id,
        geojson=geojson,
        source_srid=source_srid,
    )
    if target == "parcel" and tile_cache is not None and affected_area_path is not None:
        bump_parcel_geometry_generation(tile_cache, area_path=affected_area_path)
    return GeometryWriteResult(
        entity_id=entity_id,
        target=target,
        geojson=dict(validation["geojson"]),
        srid=validation["srid"],
        geodesic_area_sqm=validation["geodesic_area_sqm"],
    )


def _write_geometry(
    session: Session,
    *,
    target: str,
    entity_id: int,
    geojson: str,
    source_srid: int,
) -> None:
    if target == "parcel":
        statement = """
            WITH submitted AS (
                SELECT ST_Multi(
                           ST_Transform(
                               ST_SetSRID(ST_GeomFromGeoJSON(:geojson), :source_srid),
                               4326
                           )
                       ) AS geom
            )
            UPDATE land_parcel
               SET geom = submitted.geom,
                   geodesic_area_sqm = ST_Area(submitted.geom::geography)
              FROM submitted
             WHERE land_parcel.id = :entity_id
        """
    elif target == "project":
        statement = """
            WITH submitted AS (
                SELECT ST_Multi(
                           ST_Transform(
                               ST_SetSRID(ST_GeomFromGeoJSON(:geojson), :source_srid),
                               4326
                           )
                       ) AS geom
            )
            UPDATE project
               SET geom = submitted.geom
              FROM submitted
             WHERE project.id = :entity_id
        """
    else:
        statement = """
            WITH submitted AS (
                SELECT ST_Transform(
                           ST_SetSRID(ST_GeomFromGeoJSON(:geojson), :source_srid),
                           4326
                       ) AS geom
            )
            UPDATE notice_service_record
               SET service_location = submitted.geom
              FROM submitted
             WHERE notice_service_record.id = :entity_id
        """
    session.execute(
        text(statement),
        {"geojson": geojson, "source_srid": source_srid, "entity_id": entity_id},
    )
    session.flush()


def _target_spec(target: str) -> Mapping[str, Any]:
    spec = _TARGETS.get(target)
    if spec is None:
        raise InvalidGeometry("unknown geometry target", target=target)
    return spec


def _geometry_payload(geometry: Mapping[str, Any]) -> Mapping[str, Any]:
    if geometry.get("type") == "Feature":
        inner = geometry.get("geometry")
        if isinstance(inner, Mapping):
            return inner
    return geometry


def _submitted_geometry_type(geometry: Mapping[str, Any]) -> str | None:
    payload = _geometry_payload(geometry)
    value = payload.get("type")
    return value if isinstance(value, str) else None


def _bbox_params(bbox: Bbox) -> dict[str, float]:
    return {
        "min_lon": bbox.min_lon,
        "min_lat": bbox.min_lat,
        "max_lon": bbox.max_lon,
        "max_lat": bbox.max_lat,
    }


def _scope_clause(scope_paths: Sequence[str]) -> tuple[str, dict[str, str]]:
    clause = " OR ".join(
        f"aa.path <@ CAST(:scope_path_{index} AS ltree)"
        for index, _ in enumerate(scope_paths)
    )
    params = {f"scope_path_{index}": path for index, path in enumerate(scope_paths)}
    return clause, params


def _scope_hash(scope_paths: Sequence[str]) -> str:
    payload = "\n".join(sorted(scope_paths)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
