"""GIS geometry write contract tests (task 17.1)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.api.routers import officer_router
from app.services.gis import (
    Bbox,
    InvalidGeometry,
    bump_parcel_geometry_generation,
    get_parcel_map_payload,
    list_parcels_in_bbox,
    parse_bbox,
    store_geometry,
    vector_tile,
)


POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [73.0, 18.0],
            [73.1, 18.0],
            [73.1, 18.1],
            [73.0, 18.1],
            [73.0, 18.0],
        ]
    ],
}

POINT = {"type": "Point", "coordinates": [73.05, 18.05]}


def test_store_parcel_geometry_validates_transforms_and_updates_geodesic_area() -> None:
    session = FakeGisSession(
        validation={
            "valid": True,
            "reason": None,
            "location": None,
            "geometry_type": "ST_MultiPolygon",
            "srid": 4326,
            "geodesic_area_sqm": Decimal("123.45"),
            "geojson": {"type": "MultiPolygon", "coordinates": []},
        }
    )
    cache = FakeTileCache()

    result = store_geometry(
        session,  # type: ignore[arg-type]
        target="parcel",
        entity_id=10,
        geometry=POLYGON,
        source_srid=32643,
        tile_cache=cache,
        affected_area_path="IN.MH.PUNE",
    )

    assert result.geojson["type"] == "MultiPolygon"
    assert result.srid == 4326
    assert result.geodesic_area_sqm == Decimal("123.45")
    assert "ST_IsValidDetail" in session.statements[0]
    assert "ST_Transform" in session.statements[0]
    assert "ST_Area(geom::geography)" in session.statements[0]
    assert "UPDATE land_parcel" in session.statements[1]
    assert "geodesic_area_sqm = ST_Area(submitted.geom::geography)" in session.statements[1]
    assert session.params[0]["source_srid"] == 32643
    assert session.flushed is True
    assert cache.values["gis:parcel-geom-generation:IN.MH.PUNE"] == b"1"


def test_store_notice_service_location_accepts_points_only() -> None:
    session = FakeGisSession(
        validation={
            "valid": True,
            "reason": None,
            "location": None,
            "geometry_type": "ST_Point",
            "srid": 4326,
            "geodesic_area_sqm": None,
            "geojson": POINT,
        }
    )

    result = store_geometry(
        session,  # type: ignore[arg-type]
        target="notice_service_location",
        entity_id=20,
        geometry={"type": "Feature", "geometry": POINT, "properties": {}},
    )

    assert result.geojson == POINT
    assert "UPDATE notice_service_record" in session.statements[1]
    assert "service_location = submitted.geom" in session.statements[1]

    with pytest.raises(InvalidGeometry) as raised:
        store_geometry(
            session,  # type: ignore[arg-type]
            target="notice_service_location",
            entity_id=20,
            geometry=POLYGON,
        )
    assert raised.value.details["geometry_type"] == "Polygon"


def test_invalid_geometry_rejection_carries_reason_and_coordinate() -> None:
    session = FakeGisSession(
        validation={
            "valid": False,
            "reason": "Self-intersection",
            "location": {"type": "Point", "coordinates": [73.05, 18.05]},
            "geometry_type": "ST_MultiPolygon",
            "srid": 4326,
            "geodesic_area_sqm": None,
            "geojson": None,
        }
    )

    with pytest.raises(InvalidGeometry) as raised:
        store_geometry(
            session,  # type: ignore[arg-type]
            target="parcel",
            entity_id=10,
            geometry=POLYGON,
        )

    assert raised.value.details["reason"] == "Self-intersection"
    assert raised.value.details["location"]["coordinates"] == [73.05, 18.05]
    assert len(session.statements) == 1


def test_parse_bbox_rejects_non_wgs84_or_inverted_boxes() -> None:
    assert parse_bbox("73,18,74,19") == Bbox(73.0, 18.0, 74.0, 19.0)

    with pytest.raises(InvalidGeometry):
        parse_bbox("74,18,73,19")
    with pytest.raises(InvalidGeometry):
        parse_bbox("73,18,181,19")


def test_bbox_query_uses_index_candidate_exact_filter_scope_and_limit() -> None:
    session = FakeGisSession(
        validation={
            "parcel_id": 10,
            "survey_number": "77",
            "sub_division": None,
            "area_code": "MH-PUNE",
            "geojson": {"type": "MultiPolygon", "coordinates": []},
        }
    )

    result = list_parcels_in_bbox(
        session,  # type: ignore[arg-type]
        bbox=Bbox(73.0, 18.0, 73.5, 18.5),
        scope_paths=("IN.MH.PUNE", "IN.MH.SATARA"),
        simplification_tolerance=0.00001,
    )

    statement = session.statements[0]
    assert result.features[0].parcel_id == 10
    assert "lp.geom && box.geom" in statement
    assert "ST_Intersects(lp.geom, box.geom)" in statement
    assert "ST_SimplifyPreserveTopology(lp.geom, :tolerance)" in statement
    assert "ST_ReducePrecision" in statement
    assert "LIMIT :limit" in statement
    assert "aa.path <@ CAST(:scope_path_0 AS ltree)" in statement
    assert session.params[0]["limit"] == 5000
    assert session.params[0]["scope_path_1"] == "IN.MH.SATARA"


def test_bbox_query_with_empty_scope_fails_closed_without_database_read() -> None:
    session = FakeGisSession(validation={})

    result = list_parcels_in_bbox(
        session,  # type: ignore[arg-type]
        bbox=Bbox(73.0, 18.0, 73.5, 18.5),
        scope_paths=(),
        simplification_tolerance=0.00001,
    )

    assert result.features == ()
    assert session.statements == []


def test_officer_router_exposes_gis_parcel_bbox_endpoint() -> None:
    paths = {route.path for route in officer_router.routes}

    assert "/api/officer/gis/parcels" in paths
    assert "/api/officer/gis/parcels/map" in paths
    assert "/api/officer/gis/tiles/{z}/{x}/{y}.mvt" in paths


def test_map_payload_switches_to_grid_clusters_above_configured_threshold() -> None:
    session = FakeGisSession(
        results=[
            201,
            [
                {"lon": 73.1, "lat": 18.2, "count": 120},
                {"lon": 73.2, "lat": 18.3, "count": 81},
            ],
        ]
    )

    result = get_parcel_map_payload(
        session,  # type: ignore[arg-type]
        bbox=Bbox(73.0, 18.0, 73.5, 18.5),
        scope_paths=("IN.MH.PUNE",),
        simplification_tolerance=0.00001,
        cluster_threshold=200,
        cluster_cell_size_deg=0.05,
    )

    assert result.mode == "clusters"
    assert result.count == 201
    assert [cluster.count for cluster in result.clusters] == [120, 81]
    assert "SELECT count(*)" in session.statements[0]
    assert "ST_SnapToGrid" in session.statements[1]
    assert "ST_ClusterKMeans" not in session.statements[1]


def test_map_payload_returns_individual_parcels_at_or_below_threshold() -> None:
    session = FakeGisSession(
        results=[
            2,
            [
                {
                    "parcel_id": 10,
                    "survey_number": "77",
                    "sub_division": None,
                    "area_code": "MH-PUNE",
                    "geojson": {"type": "MultiPolygon", "coordinates": []},
                }
            ],
        ]
    )

    result = get_parcel_map_payload(
        session,  # type: ignore[arg-type]
        bbox=Bbox(73.0, 18.0, 73.5, 18.5),
        scope_paths=("IN.MH.PUNE",),
        simplification_tolerance=0.00001,
        cluster_threshold=200,
        cluster_cell_size_deg=0.05,
    )

    assert result.mode == "parcels"
    assert result.parcels[0].parcel_id == 10
    assert "ST_SimplifyPreserveTopology" in session.statements[1]


def test_vector_tile_uses_mvt_sql_and_caches_by_scope_hash_and_generation() -> None:
    session = FakeGisSession(results=[b"tile-bytes"])
    cache = FakeTileCache()
    cache.values["gis:parcel-geom-generation:IN.MH.PUNE"] = b"3"

    first = vector_tile(
        session,  # type: ignore[arg-type]
        z=8,
        x=144,
        y=97,
        scope_paths=("IN.MH.PUNE",),
        cache=cache,
        ttl_seconds=60,
    )
    second = vector_tile(
        session,  # type: ignore[arg-type]
        z=8,
        x=144,
        y=97,
        scope_paths=("IN.MH.PUNE",),
        cache=cache,
        ttl_seconds=60,
    )

    assert first == b"tile-bytes"
    assert second == b"tile-bytes"
    assert len(session.statements) == 1
    assert "ST_AsMVTGeom" in session.statements[0]
    assert "ST_AsMVT(mvtgeom.*, 'parcels', 4096, 'geom')" in session.statements[0]
    assert "risk_band" in session.statements[0]
    [tile_key] = [key for key in cache.values if key.startswith("gis:mvt:")]
    assert "parcel_geom_generation=3" in tile_key
    assert cache.ttls[tile_key] == 60


def test_geometry_generation_bump_is_scoped_to_affected_area_path() -> None:
    cache = FakeTileCache()

    assert bump_parcel_geometry_generation(cache, area_path="IN.MH.PUNE") == 1
    assert cache.values["gis:parcel-geom-generation:IN.MH.PUNE"] == b"1"


class FakeMappingResult:
    def __init__(self, rows) -> None:  # type: ignore[no-untyped-def]
        self.rows = rows if isinstance(rows, list) else [rows]

    def mappings(self):  # type: ignore[no-untyped-def]
        return self

    def one(self) -> dict:
        return self.rows[0]

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self.rows)

    def scalar_one(self):  # type: ignore[no-untyped-def]
        return self.rows[0]


class FakeGisSession:
    def __init__(self, *, validation: dict | None = None, results: list | None = None) -> None:
        self.results = list(results or [validation or {}])
        self.statements: list[str] = []
        self.params: list[dict] = []
        self.flushed = False

    def execute(self, stmt, params=None):  # type: ignore[no-untyped-def]
        self.statements.append(str(stmt))
        self.params.append(params or {})
        return FakeMappingResult(self.results.pop(0) if self.results else {})

    def flush(self) -> None:
        self.flushed = True


class FakeTileCache:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> bytes | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: bytes) -> None:
        self.values[key] = value
        self.ttls[key] = ttl

    def incr(self, key: str) -> int:
        value = int(self.values.get(key, b"0")) + 1
        self.values[key] = str(value).encode("ascii")
        return value
