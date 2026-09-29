"""Automated tests for the Educational Kaplan-Meier Estimator (LOOP 7B).

Verifies:
1. Basic event sequence.
2. Right censoring.
3. Tied events.
4. Censoring before later events.
5. All observations censored.
6. No observations (empty input handling).
7. Survival probability monotonicity.
8. Survival probability remains bounded between 0 and 1.
9. Training-only input verification.
10. Deterministic output across multiple runs.
11. Real BhumiSetu transition fits on survival_train_targets.csv.
12. Explicit educational non-production labeling.
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[2]
GIT_ROOT = Path(__file__).resolve().parents[5]
ML_SRC = GIT_ROOT / "bhumi-setu" / "ml" / "src"
CLEAN_DATA = GIT_ROOT / "data" / "real_data" / "clean"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from educational_kaplan_meier import EducationalKaplanMeier, KaplanMeierModel, LABEL


# 1. Basic event sequence (§8.1 & §5)
def test_basic_event_sequence() -> None:
    # Hand-verifiable case from Section 5:
    # Case 1: duration = 10, event = 1
    # Case 2: duration = 20, event = 1
    # Expected: S(10) = 1/2, S(20) = 0
    km = EducationalKaplanMeier()
    model = km.fit([10, 20], [True, True])

    assert len(model.table) == 2
    assert model.predict_survival(5) == 1.0
    assert model.predict_survival(10) == 0.5
    assert model.predict_survival(15) == 0.5
    assert model.predict_survival(20) == 0.0
    assert model.predict_survival(30) == 0.0


# 2. Right censoring (§8.2)
def test_right_censoring() -> None:
    # Case 1: duration = 10, event = 1
    # Case 2: duration = 15, event = 0 (censored)
    # Case 3: duration = 20, event = 1
    # At t=10: at_risk=3, events=1 -> S(10) = 2/3
    # Case 2 censored at 15 -> leaves risk set before t=20
    # At t=20: at_risk=1, events=1 -> S(20) = (2/3) * (1 - 1/1) = 0.0
    km = EducationalKaplanMeier()
    model = km.fit([10, 15, 20], [True, False, True])

    assert len(model.table) == 2  # Event times: 10, 20
    assert pytest.approx(model.predict_survival(10), rel=1e-5) == 2.0 / 3.0
    assert pytest.approx(model.predict_survival(15), rel=1e-5) == 2.0 / 3.0
    assert model.predict_survival(20) == 0.0


# 3. Tied events (§8.3)
def test_tied_events() -> None:
    # Multiple events at the exact same duration
    km = EducationalKaplanMeier()
    model = km.fit([10, 10, 20], [True, True, True])

    assert len(model.table) == 2
    # At t=10: at_risk=3, events=2 -> S(10) = 1 - 2/3 = 1/3
    assert pytest.approx(model.predict_survival(10), rel=1e-5) == 1.0 / 3.0
    # At t=20: at_risk=1, events=1 -> S(20) = (1/3) * (1 - 1/1) = 0.0
    assert model.predict_survival(20) == 0.0

    # Tied event and censoring at exact same time T:
    # Standard rule: event occurs first, both counted in risk set at T
    model_tie_cens = km.fit([10, 10], [True, False])
    assert model_tie_cens.table[0].number_at_risk == 2
    assert model_tie_cens.table[0].number_events == 1
    assert model_tie_cens.table[0].number_censored == 1
    assert model_tie_cens.predict_survival(10) == 0.5


# 4. Censoring before later events (§8.4)
def test_censoring_before_later_events() -> None:
    # Subject censored before first event
    km = EducationalKaplanMeier()
    model = km.fit([5, 10], [False, True])

    assert model.censored_before_first_event == 1
    assert model.predict_survival(4) == 1.0
    assert model.predict_survival(5) == 1.0  # Censoring does not change survival step
    # At t=10: at_risk=1 (subject 1 already censored), event=1 -> S(10) = 0.0
    assert model.table[0].number_at_risk == 1
    assert model.predict_survival(10) == 0.0


# 5. All observations censored (§8.5)
def test_all_observations_censored() -> None:
    km = EducationalKaplanMeier()
    model = km.fit([10, 20, 30], [False, False, False])

    assert model.total_events == 0
    assert model.total_censored == 3
    assert len(model.table) == 0
    assert model.predict_survival(0) == 1.0
    assert model.predict_survival(10) == 1.0
    assert model.predict_survival(50) == 1.0


# 6. No observations (empty input handling) (§8.6)
def test_empty_observations() -> None:
    km = EducationalKaplanMeier()
    with pytest.raises(ValueError, match="Cannot fit Kaplan-Meier on an empty dataset"):
        km.fit([], [])


# 7. Survival probability monotonicity (§8.7)
def test_monotonicity() -> None:
    km = EducationalKaplanMeier()
    durations = [1, 5, 10, 15, 20, 25, 30, 40, 50]
    events = [True, False, True, True, False, True, False, True, False]
    model = km.fit(durations, events)

    times = list(range(0, 60, 5))
    probs = [model.predict_survival(t) for t in times]

    # Every step must be non-increasing: S(t_i) >= S(t_{i+1})
    for i in range(len(probs) - 1):
        assert probs[i] >= probs[i + 1], f"Monotonicity violated: {probs[i]} < {probs[i+1]}"


# 8. Survival probability bounded between 0 and 1 (§8.8)
def test_bounded_between_zero_and_one() -> None:
    km = EducationalKaplanMeier()
    model = km.fit_from_csv(CLEAN_DATA / "survival_train_targets.csv")

    for t in [0, 1, 30, 60, 90, 180, 365, 730, 2000]:
        s = model.predict_survival(t)
        assert 0.0 <= s <= 1.0, f"Survival probability out of bounds: {s} at t={t}"


# 9. Training-only input verification (§8.9 & §1)
def test_training_only_input() -> None:
    train_csv = CLEAN_DATA / "survival_train_targets.csv"
    eval_csv = CLEAN_DATA / "survival_eval_targets.csv"

    with open(train_csv, encoding="utf-8") as f:
        train_keys = {r["snapshot_id"] for r in csv.DictReader(f)}
    with open(eval_csv, encoding="utf-8") as f:
        eval_keys = {r["snapshot_id"] for r in csv.DictReader(f)}

    # Ensure evaluation keys are strictly absent from training target set
    assert train_keys.isdisjoint(eval_keys)

    km = EducationalKaplanMeier()
    model = km.fit_from_csv(train_csv)
    assert model.total_observations == 896
    assert model.total_events == 40
    assert model.total_censored == 856


# 10. Deterministic output (§8.10)
def test_deterministic_output() -> None:
    train_csv = CLEAN_DATA / "survival_train_targets.csv"
    km = EducationalKaplanMeier()

    model1 = km.fit_from_csv(train_csv)
    model2 = km.fit_from_csv(train_csv)

    assert model1.total_observations == model2.total_observations
    assert model1.total_events == model2.total_events
    assert len(model1.table) == len(model2.table)
    for e1, e2 in zip(model1.table, model2.table):
        assert e1 == e2


# 11. Real data transition-specific fits (§6)
def test_real_data_transitions() -> None:
    train_csv = CLEAN_DATA / "survival_train_targets.csv"
    km = EducationalKaplanMeier()

    # SECTION_11_TO_SECTION_19
    m_sec11 = km.fit_from_csv(train_csv, transition="SECTION_11_TO_SECTION_19")
    assert m_sec11.total_observations == 84
    assert m_sec11.total_events == 16
    assert m_sec11.total_censored == 68
    assert len(m_sec11.table) == 7
    # S(365d) should be ~0.8034
    assert pytest.approx(m_sec11.predict_survival(365), rel=1e-3) == 0.8034

    # SECTION_19_TO_AWARD
    m_sec19 = km.fit_from_csv(train_csv, transition="SECTION_19_TO_AWARD")
    assert m_sec19.total_observations == 203
    assert m_sec19.total_events == 6
    assert m_sec19.total_censored == 197
    assert len(m_sec19.table) == 6
    assert pytest.approx(m_sec19.predict_survival(365), rel=1e-3) == 0.9635

    # CASE_INITIATION_TO_MILESTONE
    m_init = km.fit_from_csv(train_csv, transition="CASE_INITIATION_TO_MILESTONE")
    assert m_init.total_observations == 609
    assert m_init.total_events == 18
    assert m_init.total_censored == 591
    assert len(m_init.table) == 9
    assert pytest.approx(m_init.predict_survival(365), rel=1e-3) == 0.9691


# 12. Explicit educational non-production label (§7)
def test_educational_label() -> None:
    km = EducationalKaplanMeier()
    model = km.fit([10], [True])
    assert "Educational Kaplan-Meier estimator — not production survival library" in model.label
    assert LABEL == model.label
