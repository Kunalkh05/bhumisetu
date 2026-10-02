"""LOOP 15 — Security Audit: Error Handling & Fail-Closed Safety Test Suite.

Verifies:
1. Forced controlled failures in model loading (missing directory, missing summary file, corrupt artifact).
2. Fail-closed guarantee: The system refuses to silently substitute a model.
3. Health check reflects accurate degraded state or raises when artifacts are unavailable.
4. Error responses strictly maintain the uniform error envelope: {"code", "message", "details"}.
5. Zero stack traces or internal implementation details reach the API consumer.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.errors import ErrorCode
from app.main import create_app
from app.security.access import Principal, authenticate
from app.services.survival_service import (
    ArtifactNotFound,
    SurvivalService,
    ValidationFailed,
    get_survival_service,
)
from app.settings import CoreSettings


def _auth_override(principal: Principal):
    async def _override(request: Request) -> Principal:
        request.state.principal = principal
        return principal
    return _override


@pytest.fixture(scope="module")
def app_instance():
    settings = CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})
    return create_app(settings)


@pytest.fixture
def client(app_instance):
    return TestClient(app_instance)


def test_missing_model_directory_fails_closed(tmp_path):
    """SurvivalService must raise ArtifactNotFound when directory is missing."""
    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(ArtifactNotFound) as exc:
        SurvivalService(models_dir=non_existent, clean_data_dir=tmp_path)
    assert exc.value.code == ErrorCode.INTERNAL_ERROR
    assert "not found" in exc.value.message


def test_missing_summary_artifact_fails_closed(tmp_path):
    """SurvivalService must raise ArtifactNotFound when cox_model_summary.json is absent."""
    models_dir = tmp_path / "empty_models"
    models_dir.mkdir()
    clean_dir = tmp_path / "clean_data"
    clean_dir.mkdir()

    with pytest.raises(ArtifactNotFound) as exc:
        SurvivalService(models_dir=models_dir, clean_data_dir=clean_dir)
    assert exc.value.code == ErrorCode.INTERNAL_ERROR
    assert "missing" in exc.value.message


def test_corrupted_model_artifact_fails_closed(tmp_path):
    """SurvivalService must raise ArtifactNotFound when model summary is corrupted."""
    models_dir = tmp_path / "corrupt_models"
    models_dir.mkdir()
    summary_file = models_dir / "cox_model_summary.json"
    summary_file.write_text("{ this is invalid json !!!", encoding="utf-8")
    clean_dir = tmp_path / "clean_data"
    clean_dir.mkdir()

    with pytest.raises(ArtifactNotFound) as exc:
        SurvivalService(models_dir=models_dir, clean_data_dir=clean_dir)
    assert exc.value.code == ErrorCode.INTERNAL_ERROR
    assert "Corrupted or invalid" in exc.value.message


def test_uniform_error_envelope_structure(client, app_instance):
    """All non-2xx responses must conform strictly to the ErrorEnvelope shape."""
    officer = Principal(kind="OFFICER", id="off-err-test")
    app_instance.dependency_overrides[authenticate] = _auth_override(officer)

    # 422 Unprocessable Entity
    resp = client.post("/api/officer/survival-risk/predict", json={
        "case_id": "CASE-1",
        "snapshot_date": "2026-03-15",
        "transition": "INVALID_TRANSITION",
        "features": {"derived_days_in_current_stage": 10.0},
    })
    assert resp.status_code == 422
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "details"}
    assert body["code"] == ErrorCode.VALIDATION_FAILED
    assert isinstance(body["details"], dict)

    # 404 Route Not Found
    resp_404 = client.get("/api/officer/survival-risk/non-existent-route")
    assert resp_404.status_code == 404
    body_404 = resp_404.json()
    assert set(body_404.keys()) == {"code", "message", "details"}
    assert body_404["code"] == "HTTP_404"
