"""LOOP 15 — Security Audit: Model Artifact Integrity & Immutability Test Suite.

Verifies:
1. Every production Cox model artifact exists and matches its verified SHA256 digest.
2. Model coefficients, baseline survival tables, eval summaries, and calibration summaries remain frozen.
3. Feature version and model version match exact production contracts.
4. No synthetic data, retraining, or coefficient mutations occurred.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from app.services.survival_service import get_survival_service

GIT_ROOT = Path(__file__).resolve().parents[5]
MODELS_DIR = GIT_ROOT / "models" / "cox_baseline"
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"

import sys
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from calibration.survival_calibration import MODEL_VERSION, PURGED_LEAKAGE_FEATURES
from explainability.survival_explainability import FEATURE_VERSION

EXPECTED_SHA256 = {
    "cox_model_summary.json": "87c8684be336137ecee9fc20048ec02476e8edc3a1fef9742f5eda30f13141e8",
    "cox_calibration_summary.json": "2c4dc8b25c75137d8075c012d2601e83feb9895e528932d8782bfc83bb0f2fd4",
    "cox_eval_summary.json": "dc58ae5db29ebddd2392b3a898de133c0543e15f81f6f588221717f118ba0859",
    "cox_section_11_to_section_19_coefficients.csv": "cb0422704b1add914c1467eb8fc0db0f3032c53ee0f2ee567a8eb4ce1bb4af83",
    "cox_section_11_to_section_19_baseline_survival.csv": "9d8bb6dbbf488df6ddb3395955c65eeab50ceef23e2092f8eb66be565cfd62ff",
    "cox_section_19_to_award_coefficients.csv": "162454d404a28378cdbfaeeb62852f34b29501019ef1527e438d6cd8e2f266fb",
    "cox_section_19_to_award_baseline_survival.csv": "7d1fb36aa816b14270ba30afa1da48fb1749ce28e01563a0494bbcbf95ace1f3",
    "cox_case_initiation_to_milestone_coefficients.csv": "7183dcc2b136b21d793a71c26317e1b76d939d46e20ee69ff2aee588dd327f7e",
    "cox_case_initiation_to_milestone_baseline_survival.csv": "437b331c71eb65a98646f22fc262c81fa03c3329cf5ab97b944b939a1d339ec0",
}


@pytest.mark.parametrize("filename, expected_hash", EXPECTED_SHA256.items())
def test_production_model_artifact_sha256(filename: str, expected_hash: str):
    """Confirm byte-for-byte immutability of all production model artifacts."""
    file_path = MODELS_DIR / filename
    assert file_path.exists(), f"Missing production model artifact: {file_path}"
    actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    assert actual_hash == expected_hash, f"Hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}"


def test_explainer_checksums_match_loop7c_and_loop10():
    """Explainer checksums must strictly match canonical coefficients digests."""
    service = get_survival_service()
    checksums = service._explainer.checksums
    assert checksums == {
        "SECTION_11_TO_SECTION_19": "6cab5d24dbc3587b",
        "SECTION_19_TO_AWARD": "260328f59192648f",
        "CASE_INITIATION_TO_MILESTONE": "2493aa920caf664a",
    }


def test_production_version_contracts():
    """Verify that model version and feature version contracts remain unchanged."""
    assert MODEL_VERSION == "1.0.0-cox-production-baseline"
    assert FEATURE_VERSION == "1.0.0-survival-clean-15feat"
    service = get_survival_service()
    health = service.get_health()
    assert health.model_version == MODEL_VERSION
    assert health.feature_version == FEATURE_VERSION
