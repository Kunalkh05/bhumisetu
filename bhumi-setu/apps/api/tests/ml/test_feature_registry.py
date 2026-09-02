from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from features.leakage import (  # noqa: E402
    LeakageGuardViolation,
    no_database_access,
)
from features.registry import FeatureExtractor  # noqa: E402


def test_feature_extractor_compute_accepts_only_an_as_of_view_and_time() -> None:
    signature = inspect.signature(FeatureExtractor.compute)

    assert tuple(signature.parameters) == ("self", "view", "t")
    rendered = str(signature)
    assert "AsOfView" in rendered
    assert "Session" not in rendered
    assert "Engine" not in rendered
    assert "Connection" not in rendered


def test_no_database_access_raises_on_first_sql(transactional_sqlite_engine) -> None:
    session = Session(bind=transactional_sqlite_engine)
    session.execute(text("SELECT 0")).scalar_one()

    with pytest.raises(LeakageGuardViolation, match="SELECT 1"):
        with no_database_access(session):
            session.execute(text("SELECT 1")).scalar_one()

    session.rollback()
    assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_no_database_access_is_production_feature_code() -> None:
    assert no_database_access.__module__ == "features.leakage"
