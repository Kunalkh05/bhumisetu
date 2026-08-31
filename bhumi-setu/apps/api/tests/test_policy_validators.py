"""Write-time policy validation (§4.5), Property 65.

*Configuration is validated before it can take effect.* The pattern throughout is
to generate a **valid** value and then introduce exactly one defect, so a failure
names the rule that was broken rather than leaving it to be inferred from a random
malformed blob.

No database: these are pure functions over a value, and keeping them that way is
what lets task 2.5's write path call them before it has a row.
"""

from __future__ import annotations

import copy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.policy_validators import (
    PolicyValueInvalid,
    VALIDATORS,
    validate_non_negative_days,
    validate_ocr_threshold_set,
    validate_partitions_unit_interval,
    validate_policy_value,
    validate_stage_graph,
    validate_weights_normalisable,
)
from tests.strategies import st_band_cutoffs, st_stage_graph

BANDS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# R28.7 — risk band cutoffs partition [0, 1]
# ---------------------------------------------------------------------------


@given(cutoffs=st_band_cutoffs())
@settings(max_examples=100)
def test_a_strictly_increasing_set_ending_at_one_is_accepted(cutoffs) -> None:
    validate_partitions_unit_interval("risk.band_cutoffs", cutoffs)


@given(cutoffs=st_band_cutoffs())
@settings(max_examples=100)
def test_a_top_bound_below_one_leaves_probabilities_unbanded(cutoffs) -> None:
    """The defect that produces a blank risk rather than an error.

    R19.4 says every probability maps to exactly one band. A top bound below 1.0
    means a high probability maps to none — and the officer sees "not scored", which
    R16.6 gives its own distinct meaning. Conflating a configuration error with "the
    model never ran" is worse than either.
    """
    # Must stay strictly above HIGH, or the ordering rule fires first and the test
    # asserts on a different defect than the one it names. Hypothesis found that
    # with a fixed 0.9: it shrank to HIGH=0.9375, where 0.9 is out of order.
    broken = dict(cutoffs, CRITICAL=(cutoffs["HIGH"] + 1.0) / 2)
    assert cutoffs["HIGH"] < broken["CRITICAL"] < 1.0
    with pytest.raises(PolicyValueInvalid, match="upper bound of exactly 1.0"):
        validate_partitions_unit_interval("risk.band_cutoffs", broken)


@given(cutoffs=st_band_cutoffs())
@settings(max_examples=100)
def test_equal_consecutive_bounds_create_an_unassignable_band(cutoffs) -> None:
    """A band that exists in configuration and no probability can ever fall in."""
    broken = dict(cutoffs, MEDIUM=cutoffs["LOW"])
    with pytest.raises(PolicyValueInvalid, match="strictly increasing"):
        validate_partitions_unit_interval("risk.band_cutoffs", broken)


@given(cutoffs=st_band_cutoffs(), omitted=st.sampled_from(BANDS))
@settings(max_examples=60)
def test_omitting_any_band_is_refused(cutoffs, omitted: str) -> None:
    broken = {k: v for k, v in cutoffs.items() if k != omitted}
    with pytest.raises(PolicyValueInvalid, match="missing bands"):
        validate_partitions_unit_interval("risk.band_cutoffs", broken)


def test_out_of_order_bounds_are_refused() -> None:
    with pytest.raises(PolicyValueInvalid, match="must increase"):
        validate_partitions_unit_interval(
            "risk.band_cutoffs",
            {"LOW": 0.5, "MEDIUM": 0.25, "HIGH": 0.75, "CRITICAL": 1.0},
        )


def test_an_unknown_band_name_is_refused() -> None:
    """R19.4 names four bands. A fifth would be scored and never displayed."""
    with pytest.raises(PolicyValueInvalid, match="unknown bands"):
        validate_partitions_unit_interval(
            "risk.band_cutoffs",
            {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0, "EXTREME": 1.0},
        )


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_bounds_outside_the_unit_interval_are_refused(bad: float) -> None:
    with pytest.raises(PolicyValueInvalid):
        validate_partitions_unit_interval(
            "risk.band_cutoffs",
            {"LOW": bad, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0},
        )


@pytest.mark.parametrize("bad", [True, "0.25", None, [0.25]])
def test_a_non_numeric_bound_is_refused(bad) -> None:
    """``True`` is included on purpose: it is an int in Python, so a naive
    isinstance check accepts it and a band bound becomes 1."""
    with pytest.raises(PolicyValueInvalid):
        validate_partitions_unit_interval(
            "risk.band_cutoffs",
            {"LOW": bad, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0},
        )


# ---------------------------------------------------------------------------
# R28.8 — OCR thresholds ordered
# ---------------------------------------------------------------------------


def test_a_correctly_ordered_threshold_set_is_accepted() -> None:
    validate_ocr_threshold_set(
        "ocr.thresholds",
        {"auto_accept": 0.95, "review": 0.60, "document_rejection": 0.50},
    )


def test_review_at_or_above_auto_accept_is_refused() -> None:
    """Inverted, nothing is ever PENDING_REVIEW: R12.2's human review step stops
    existing while the system looks entirely healthy."""
    with pytest.raises(PolicyValueInvalid, match="strictly below auto_accept"):
        validate_ocr_threshold_set(
            "ocr.thresholds",
            {"auto_accept": 0.60, "review": 0.95, "document_rejection": 0.50},
        )


def test_equal_thresholds_are_refused() -> None:
    with pytest.raises(PolicyValueInvalid, match="strictly below auto_accept"):
        validate_ocr_threshold_set(
            "ocr.thresholds",
            {"auto_accept": 0.95, "review": 0.95, "document_rejection": 0.50},
        )


@pytest.mark.parametrize("value", [-0.1, 1.1])
def test_a_threshold_outside_zero_to_one_is_refused(value: float) -> None:
    with pytest.raises(PolicyValueInvalid, match="outside"):
        validate_policy_value("ocr.threshold.auto_accept", value)


# ---------------------------------------------------------------------------
# Stage graph
# ---------------------------------------------------------------------------


@given(graph=st_stage_graph())
@settings(max_examples=100)
def test_a_chain_ending_in_a_terminal_stage_is_accepted(graph) -> None:
    validate_stage_graph("policy.stage_set", graph)


@given(graph=st_stage_graph(min_stages=3))
@settings(max_examples=100)
def test_a_non_terminal_stage_with_no_successors_strands_cases(graph) -> None:
    """Nothing errors at runtime, which is what makes this worth refusing.

    A case entering the stage simply cannot advance, and R5.4 reports an empty set
    of permitted successors — which looks like correct behaviour.
    """
    broken = copy.deepcopy(graph)
    broken["stages"][0]["successors"] = []
    with pytest.raises(PolicyValueInvalid, match="can never advance"):
        validate_stage_graph("policy.stage_set", broken)


@given(graph=st_stage_graph(min_stages=3))
@settings(max_examples=100)
def test_an_unreachable_stage_is_refused(graph) -> None:
    """An unreachable terminal is a case that never ages out of retention (R32.3)."""
    broken = copy.deepcopy(graph)
    broken["stages"].append(
        {"key": "ORPHAN", "successors": [], "period_key": None, "terminal": True}
    )
    with pytest.raises(PolicyValueInvalid, match="unreachable"):
        validate_stage_graph("policy.stage_set", broken)


@given(graph=st_stage_graph())
@settings(max_examples=100)
def test_a_graph_with_no_terminal_stage_is_refused(graph) -> None:
    broken = copy.deepcopy(graph)
    last = broken["stages"][-1]
    last["terminal"] = False
    last["successors"] = [broken["stages"][0]["key"]]
    with pytest.raises(PolicyValueInvalid, match="no terminal stage"):
        validate_stage_graph("policy.stage_set", broken)


@given(graph=st_stage_graph())
@settings(max_examples=100)
def test_an_unknown_successor_is_refused(graph) -> None:
    broken = copy.deepcopy(graph)
    broken["stages"][0]["successors"] = ["NOT_A_STAGE"]
    with pytest.raises(PolicyValueInvalid, match="unknown successors"):
        validate_stage_graph("policy.stage_set", broken)


@given(graph=st_stage_graph())
@settings(max_examples=60)
def test_a_terminal_stage_declaring_successors_is_refused(graph) -> None:
    broken = copy.deepcopy(graph)
    broken["stages"][-1]["successors"] = [broken["stages"][0]["key"]]
    with pytest.raises(PolicyValueInvalid, match="terminal but declares successors"):
        validate_stage_graph("policy.stage_set", broken)


@given(graph=st_stage_graph(min_stages=2))
@settings(max_examples=60)
def test_duplicate_stage_keys_are_refused(graph) -> None:
    broken = copy.deepcopy(graph)
    broken["stages"][1]["key"] = broken["stages"][0]["key"]
    with pytest.raises(PolicyValueInvalid, match="duplicate stage keys"):
        validate_stage_graph("policy.stage_set", broken)


# ---------------------------------------------------------------------------
# Retention periods and priority weights
# ---------------------------------------------------------------------------


@given(days=st.integers(min_value=0, max_value=36500))
@settings(max_examples=60)
def test_a_non_negative_whole_day_count_is_accepted(days: int) -> None:
    validate_non_negative_days("retention.period.OWNER_CONTACT", days)


def test_zero_days_is_a_legitimate_retention_policy() -> None:
    """Erase as soon as the retention start is determined. Unusual, not invalid."""
    validate_non_negative_days("retention.period.OWNER_CONTACT", 0)


@given(days=st.integers(max_value=-1))
@settings(max_examples=60)
def test_a_negative_period_is_refused(days: int) -> None:
    """It would put the erasure date before the retention start, so the sweep would
    erase data for a case that had only just closed."""
    with pytest.raises(PolicyValueInvalid, match="negative"):
        validate_non_negative_days("retention.period.OWNER_CONTACT", days)


@pytest.mark.parametrize("bad", [1.5, "365", True, None])
def test_a_non_integer_period_is_refused(bad) -> None:
    with pytest.raises(PolicyValueInvalid):
        validate_non_negative_days("retention.period.OWNER_CONTACT", bad)


def test_weights_need_not_sum_to_one() -> None:
    """priority_score normalises by the total, so demanding a sum of one would make
    an administrator rescale by hand for no gain."""
    validate_weights_normalisable("priority.weights", {"risk": 3, "deadline": 1})


def test_all_zero_weights_are_refused() -> None:
    """This is the one that has to be caught here: normalising by the total would
    divide by zero on every score computed for the life of the deployment."""
    with pytest.raises(PolicyValueInvalid, match="sum to zero"):
        validate_weights_normalisable("priority.weights", {"risk": 0, "deadline": 0})


def test_a_negative_weight_is_refused() -> None:
    with pytest.raises(PolicyValueInvalid, match="negative"):
        validate_weights_normalisable("priority.weights", {"risk": -1, "deadline": 2})


# ---------------------------------------------------------------------------
# Registry dispatch
# ---------------------------------------------------------------------------


def test_pattern_keys_reach_the_family_validator() -> None:
    with pytest.raises(PolicyValueInvalid):
        validate_policy_value("retention.period.OWNER_IDENTITY", -1)
    with pytest.raises(PolicyValueInvalid):
        validate_policy_value("period.pn.to_declaration", -30)


def test_an_exact_key_takes_precedence_over_a_pattern() -> None:
    """`ocr.thresholds` is a set with its own cross-field rule; `ocr.threshold.*` is
    a single value. The exact match must win or the set is checked as a number."""
    with pytest.raises(PolicyValueInvalid, match="strictly below auto_accept"):
        validate_policy_value(
            "ocr.thresholds",
            {"auto_accept": 0.5, "review": 0.9, "document_rejection": 0.4},
        )


def test_an_unregistered_key_is_allowed() -> None:
    """Deliberate. Requiring a validator per key would block every new
    configuration value on writing one, and the workaround for that friction is to
    stop using Policy_Config — far worse than an unvalidated integer."""
    validate_policy_value("some.new.key", {"anything": [1, 2, 3]})


def test_every_registered_validator_rejects_something() -> None:
    """A validator that accepts everything is worse than none: it reports coverage
    it does not provide."""
    for key, validator in VALIDATORS.items():
        with pytest.raises((PolicyValueInvalid, TypeError, AttributeError)):
            validator(key, object())

# ---------------------------------------------------------------------------
# Property 65, the biconditional form — "accepted exactly when"
# ---------------------------------------------------------------------------
#
# The tests above generate a *valid* value and break it one way at a time, which
# proves the rejection side one defect per test. Task 2.8 asks for the other
# direction as a property: over arbitrary values, drawn to straddle the boundary,
# acceptance must coincide *exactly* with the specification predicate. A validator
# that accepted one malformed set in a thousand, or rejected one legal set, would
# pass every single-defect test above and fail here.
#
# The oracle is written from the specification (a contiguous partition of [0, 1];
# review strictly below auto-accept), not by copying the validator — the two are
# only allowed to agree because both are correct, and that agreement is the claim.


def _is_accepted(validator, key: str, value) -> bool:
    """True when ``validator`` admits ``value``; False when it raises the domain
    error. Any other exception propagates — an ``AttributeError`` from a generator
    that wandered outside the input space is a bug in the test, not a rejection."""
    try:
        validator(key, value)
        return True
    except PolicyValueInvalid:
        return False


# --- Risk band cutoffs (R28.7) ---------------------------------------------

# Exactly representable, and chosen to straddle every boundary the predicate turns
# on: 0.0 (excluded — the first band would be empty), 1.0 (the only legal top), and
# 1.5 (above the interval). Independent draws produce out-of-order and duplicate
# sets far more often than valid ones, so the accept branch is fed separately.
_CUTOFF_POOL = (0.0, 0.1, 0.25, 0.5, 0.6, 0.75, 0.9, 1.0, 1.5)


@st.composite
def st_maybe_valid_cutoffs(draw) -> dict:
    """A cutoff set that is valid about half the time and malformed the rest.

    The valid half comes from :func:`st_band_cutoffs`, so the accept branch is
    actually exercised rather than left to chance; the other half draws each bound
    independently and sometimes drops or adds a band, covering the gap, overlap,
    wrong-top, missing-band and unknown-band failures in one generator."""
    if draw(st.booleans()):
        return dict(draw(st_band_cutoffs()))
    value = {band: draw(st.sampled_from(_CUTOFF_POOL)) for band in BANDS}
    shape = draw(st.sampled_from(["as_is", "as_is", "as_is", "drop", "add"]))
    if shape == "drop":
        del value[draw(st.sampled_from(BANDS))]
    elif shape == "add":
        value["EXTREME"] = draw(st.sampled_from(_CUTOFF_POOL))
    return value


def _partitions_unit_interval(value) -> bool:
    """The R28.7 predicate, straight from the spec: the four bands, as ascending
    upper bounds, tile (0, 1] with no gap, no overlap, and a top of exactly 1.0."""
    if not isinstance(value, dict) or set(value) != set(BANDS):
        return False
    bounds = [value[band] for band in BANDS]
    if any(isinstance(b, bool) or not isinstance(b, (int, float)) for b in bounds):
        return False
    if any(b <= 0.0 or b > 1.0 for b in bounds):
        return False
    if bounds != sorted(bounds) or len(set(bounds)) != len(bounds):
        return False
    return bounds[-1] == 1.0


@given(cutoffs=st_maybe_valid_cutoffs())
@settings(max_examples=200)
def test_a_cutoff_set_is_accepted_exactly_when_it_partitions_the_unit_interval(
    cutoffs: dict,
) -> None:
    """Feature: bhumisetu, Property 65: for any submitted Risk_Band cutoff set, the
    change is accepted exactly when the bands partition the interval 0 to 1 into
    contiguous non-overlapping ranges covering every probability."""
    accepted = _is_accepted(validate_partitions_unit_interval, "risk.band_cutoffs", cutoffs)
    assert accepted == _partitions_unit_interval(cutoffs), cutoffs


# --- OCR thresholds (R28.8) -------------------------------------------------

# Straddles the [0, 1] range (−0.1 and 1.1 are out) and packs values near the
# auto-accept/review boundary so the ordering rule is exercised, not just the range
# check. 0.0 and 1.0 are inside the interval for thresholds, unlike a band bound.
_THRESHOLD_POOL = (-0.1, 0.0, 0.4, 0.5, 0.6, 0.9, 0.95, 1.0, 1.1)
_THRESHOLD_KEYS = ("auto_accept", "review", "document_rejection")


@st.composite
def st_maybe_valid_threshold_set(draw) -> dict:
    """An OCR threshold set drawn to land on both sides of ``review < auto_accept``,
    sometimes out of range, sometimes missing one of the three keys."""
    value = {name: draw(st.sampled_from(_THRESHOLD_POOL)) for name in _THRESHOLD_KEYS}
    if draw(st.integers(min_value=0, max_value=4)) == 0:
        del value[draw(st.sampled_from(_THRESHOLD_KEYS))]
    return value


def _review_below_auto_accept(value) -> bool:
    """The R28.8 predicate: the three named thresholds are present and in [0, 1],
    and review is strictly below auto-accept. document_rejection carries no ordering
    constraint of its own — the set turns solely on review versus auto-accept."""
    if not isinstance(value, dict) or any(name not in value for name in _THRESHOLD_KEYS):
        return False
    for name in _THRESHOLD_KEYS:
        bound = value[name]
        if isinstance(bound, bool) or not isinstance(bound, (int, float)):
            return False
        if not 0.0 <= float(bound) <= 1.0:
            return False
    return float(value["review"]) < float(value["auto_accept"])


@given(thresholds=st_maybe_valid_threshold_set())
@settings(max_examples=200)
def test_an_ocr_threshold_set_is_accepted_exactly_when_review_is_below_auto_accept(
    thresholds: dict,
) -> None:
    """Feature: bhumisetu, Property 65: for any submitted OCR threshold set, the
    change is accepted exactly when the review threshold is strictly below the
    auto-accept threshold."""
    accepted = _is_accepted(validate_ocr_threshold_set, "ocr.thresholds", thresholds)
    assert accepted == _review_below_auto_accept(thresholds), thresholds
