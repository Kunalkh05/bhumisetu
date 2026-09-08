"""Bulk import throughput benchmark (task 26.5).

Asserts at least 10 000 parcel rows per minute at p95 over 10 batches
of at least 10 000 rows when running under nightly perf, with a smoke profile for local runs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import os
import statistics
import time
from typing import Any

import pytest

from app.models.import_batch import ImportBatch, ImportRow
from app.models.land_parcel import LandParcel
from app.security.access import Principal
from app.services.import_service import (
    ImportRowSubmission,
    _process_import_chunk,
    submit_import_batch,
)
from tests.test_import_service import FakeImportSession, _valid_parcel_payload

pytestmark = pytest.mark.perf

TARGET_ROWS_PER_MINUTE = 10_000


def test_import_throughput_reaches_ten_thousand_rows_per_minute() -> None:
    batch_size = 10_000 if _is_nightly() else 1_000
    batch_count = 10 if _is_nightly() else 3
    actor = Principal(
        kind="OFFICER",
        id="00000000-0000-0000-0000-000000000001",
        permissions=frozenset({"import.submit"}),
    )

    rates: list[float] = []
    for batch_num in range(batch_count):
        session = FakeImportSession()
        rows = tuple(
            ImportRowSubmission(
                ordinal=i,
                entity_type="land_parcel",
                payload=_valid_parcel_payload(f"PERF-{batch_num}-{i}"),
            )
            for i in range(1, batch_size + 1)
        )
        res = submit_import_batch(
            session,  # type: ignore[arg-type]
            principal=actor,
            rows=rows,
            now=datetime(2026, 1, 1, tzinfo=UTC),
        )

        started = time.perf_counter()
        chunk_res = _process_import_chunk(
            session,  # type: ignore[arg-type]
            batch_id=res.batch_id,
            chunk_size=batch_size,
        )
        elapsed = time.perf_counter() - started
        assert chunk_res.committed_count == batch_size

        rows_per_minute = (batch_size / elapsed) * 60.0
        rates.append(rows_per_minute)

    p95_rate = _p95(rates)
    assert p95_rate >= TARGET_ROWS_PER_MINUTE, (
        f"Observed p95 throughput {p95_rate:.1f} rows/min below target {TARGET_ROWS_PER_MINUTE}"
    )


def _is_nightly() -> bool:
    return os.environ.get("BHUMISETU_NIGHTLY_PERF") == "1"


def _p95(values: list[float]) -> float:
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=20, method="inclusive")[18]
