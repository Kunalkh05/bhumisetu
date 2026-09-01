"""PostGIS bbox benchmark for task 17.5.

Runs only when a PostgreSQL/PostGIS test database is available. Locally it skips
cleanly; CI can make the skip fatal with ``BHUMISETU_REQUIRE_POSTGRES=1``.
"""

from __future__ import annotations

import statistics
import time

import pytest
from sqlalchemy import text

from tests.postgres import skip_without_postgres

PR_SMOKE_PARCELS = 5_000
NIGHTLY_PARCELS = 50_000
TARGET_RESULT_COUNT = 5_000
P95_BUDGET_SECONDS = 2.0


pytestmark = pytest.mark.perf


@pytest.fixture(scope="session")
def postgis_ready(migrated_engine):
    skip_without_postgres()
    with migrated_engine.begin() as conn:
        available = conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
        ).scalar_one()
        if not available:
            pytest.skip("PostGIS extension is not installed in the migrated database")
    return migrated_engine


def test_bbox_query_p95_under_two_seconds_with_plan_capture(postgis_ready) -> None:
    parcel_count = NIGHTLY_PARCELS if _nightly_perf_enabled() else PR_SMOKE_PARCELS
    with postgis_ready.begin() as conn:
        _seed_benchmark_parcels(conn, parcel_count=parcel_count)
        boxes = _benchmark_boxes(parcel_count=parcel_count)
        timings: list[float] = []
        observed_counts: list[int] = []
        for min_lon, min_lat, max_lon, max_lat in boxes:
            started = time.perf_counter()
            rows = conn.execute(
                _bbox_query(),
                {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat,
                    "scope_path": "IN.MH.PUNE",
                },
            ).all()
            timings.append(time.perf_counter() - started)
            observed_counts.append(len(rows))

        if any(count != TARGET_RESULT_COUNT for count in observed_counts):
            pytest.fail(
                "bbox benchmark boxes did not contain 5000 parcels: "
                f"{observed_counts[:10]} plan:\n{_explain(conn, boxes[0])}"
            )
        p95 = statistics.quantiles(timings, n=20, method="inclusive")[18]
        if p95 > P95_BUDGET_SECONDS:
            pytest.fail(
                f"bbox query p95 {p95:.3f}s exceeded {P95_BUDGET_SECONDS:.3f}s; "
                f"plan:\n{_explain(conn, boxes[timings.index(max(timings))])}"
            )


def _nightly_perf_enabled() -> bool:
    import os

    return os.environ.get("BHUMISETU_NIGHTLY_PERF") == "1"


def _seed_benchmark_parcels(conn, *, parcel_count: int) -> None:
    conn.execute(text("DELETE FROM case_parcel"))
    conn.execute(text("DELETE FROM land_parcel"))
    conn.execute(text("DELETE FROM acquisition_case"))
    conn.execute(text("DELETE FROM project"))
    conn.execute(text("DELETE FROM administrative_area"))
    conn.execute(
        text(
            """
            INSERT INTO administrative_area
                (code, area_type, name, parent_code, state_key, path)
            VALUES
                ('IN', 'country', 'India', NULL, 'IN', 'IN'),
                ('MH', 'state', 'Maharashtra', 'IN', 'MH', 'IN.MH'),
                ('PUNE', 'district', 'Pune', 'MH', 'MH', 'IN.MH.PUNE')
            ON CONFLICT DO NOTHING
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO project
                (id, name, implementing_authority, area_code, purpose_category,
                 sanctioned_extent, extent_unit)
            VALUES
                (9001, 'GIS benchmark', 'PWD', 'PUNE', 'road', 1, 'hectare')
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO acquisition_case
                (id, case_reference, project_id, state_key, act_key, area_code,
                 stage_key, stage_set_effective_from, stage_entered_on,
                 deadline_breached, is_terminal)
            VALUES
                (9001, 'GIS-BENCH', 9001, 'MH', 'RFCTLARR_2013', 'PUNE',
                 'AWARD', DATE '2024-01-01', DATE '2024-01-01', false, false)
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO land_parcel
                (id, state_key, district, tehsil, village, survey_number,
                 classification, extent, extent_unit, area_code, geom,
                 geodesic_area_sqm)
            SELECT
                gs,
                'MH',
                'Pune',
                'Haveli',
                'Village ' || (gs % 100),
                gs::text,
                'agricultural',
                1,
                'hectare',
                'PUNE',
                ST_Translate(
                    ST_Buffer(
                        ST_SetSRID(ST_Point(73 + ((gs - 1) % 5000) * 0.0001, 18), 4326),
                        0.00004,
                        20
                    ),
                    ((gs - 1) / 5000) * 0.000001,
                    0
                )::geometry(MultiPolygon, 4326),
                ST_Area(
                    ST_Translate(
                        ST_Buffer(
                            ST_SetSRID(ST_Point(73 + ((gs - 1) % 5000) * 0.0001, 18), 4326),
                            0.00004,
                            20
                        ),
                        ((gs - 1) / 5000) * 0.000001,
                        0
                    )::geography
                )
              FROM generate_series(1, :parcel_count) AS gs
            """
        ),
        {"parcel_count": parcel_count},
    )
    conn.execute(
        text(
            """
            INSERT INTO case_parcel (case_id, parcel_id)
            SELECT 9001, id FROM land_parcel
            """
        )
    )
    conn.execute(text("ANALYZE administrative_area"))
    conn.execute(text("ANALYZE land_parcel"))
    conn.execute(text("ANALYZE case_parcel"))


def _benchmark_boxes(*, parcel_count: int) -> list[tuple[float, float, float, float]]:
    return [
        (73.0, 17.9998, 73.49995, 18.0002)
        for _ in range(100 if parcel_count >= NIGHTLY_PARCELS else 10)
    ]


def _bbox_query():
    return text(
        """
        WITH envelope AS (
            SELECT ST_MakeEnvelope(
                       :min_lon, :min_lat, :max_lon, :max_lat, 4326
                   ) AS geom
        )
        SELECT lp.id
          FROM land_parcel lp
          JOIN administrative_area aa ON lp.area_code = aa.code
          JOIN envelope box ON true
         WHERE lp.geom IS NOT NULL
           AND lp.geom && box.geom
           AND ST_Intersects(lp.geom, box.geom)
           AND aa.path <@ CAST(:scope_path AS ltree)
         LIMIT 5000
        """
    )


def _explain(conn, box: tuple[float, float, float, float]) -> str:
    min_lon, min_lat, max_lon, max_lat = box
    plan = conn.execute(
        text(
            """
            EXPLAIN (ANALYZE, BUFFERS)
            WITH envelope AS (
                SELECT ST_MakeEnvelope(
                           :min_lon, :min_lat, :max_lon, :max_lat, 4326
                       ) AS geom
            )
            SELECT lp.id
              FROM land_parcel lp
              JOIN administrative_area aa ON lp.area_code = aa.code
              JOIN envelope box ON true
             WHERE lp.geom IS NOT NULL
               AND lp.geom && box.geom
               AND ST_Intersects(lp.geom, box.geom)
               AND aa.path <@ CAST(:scope_path AS ltree)
             LIMIT 5000
            """
        ),
        {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "scope_path": "IN.MH.PUNE",
        },
    )
    return "\n".join(row[0] for row in plan)
