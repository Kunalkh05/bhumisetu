"""Write-time validation of policy values (§4.5).

R28.7 and R28.8 are about configuration that is *structurally* wrong rather than
merely unusual: a risk band set that leaves a gap, an OCR threshold pair the wrong
way round. Both are checked here, before the row can take effect.

Why validate on write rather than on read
-----------------------------------------

A broken cutoff set read at scoring time gives every case in the gap no band at
all, and the officer sees a blank where a risk should be. Read-time validation
would turn that into an exception per scored case, which is a worse outcome than
refusing the write once: the value is wrong in one place, and that is where it
should be rejected.

The stronger reason is that write-time validation lets ``classify`` be total by
construction. Because :func:`validate_partitions_unit_interval` has already
rejected any non-covering set, band lookup does not re-check its own input on every
call — a check that would otherwise run on every prediction for the life of the
platform.

Pattern keys
------------

The registry is keyed on a ``policy_key`` pattern rather than an exact key, because
``ocr.threshold.auto_accept`` and ``ocr.threshold.review`` share a rule, and
``retention.period.OWNER_CONTACT`` shares one with every other category. Exact
matches take precedence over patterns, so a specific key can override the family
rule without the family rule needing to know about it.

An unmatched key is **allowed**, deliberately. Most policy values are a plain
number or string whose only meaningful validation is the type the caller expects,
and requiring a validator per key would mean every new configuration value is
blocked on writing one — which is the friction that gets worked around by not using
Policy_Config at all.
"""

from __future__ import annotations

import fnmatch
from typing import Any, Callable

from app.errors import DomainError, ErrorCode

__all__ = [
    "PolicyValueInvalid",
    "VALIDATORS",
    "validate_non_negative_days",
    "validate_partitions_unit_interval",
    "validate_policy_value",
    "validate_review_below_auto_accept",
    "validate_stage_graph",
    "validate_weights_normalisable",
]


class PolicyValueInvalid(DomainError):
    """A submitted policy value is structurally wrong (R28.7, R28.8).

    409 rather than 422: the request is well formed, and what is being rejected is
    the configuration it would create. ``details`` names the key and the specific
    defect, because "invalid value" leaves an administrator guessing which of five
    bands overlapped.
    """

    code = ErrorCode.POLICY_VALUE_INVALID
    status_code = 409

    def __init__(self, key: str, reason: str, **extra: Any) -> None:
        super().__init__(
            f"{key}: {reason}", details={"policy_key": key, "reason": reason, **extra}
        )
        self.policy_key = key
        self.reason = reason


# ---------------------------------------------------------------------------
# R28.7 — risk band cutoffs partition [0, 1]
# ---------------------------------------------------------------------------

_BANDS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def validate_partitions_unit_interval(key: str, value: Any) -> None:
    """R28.7: the bands must cover [0, 1] contiguously with no overlap.

    This is what makes ``band_for`` total. A gap means a probability that maps to no
    band, and R19.4 says every probability maps to exactly one — so the failure is
    not a crash but a case displaying no risk at all, which reads as "not scored"
    and is indistinguishable from a model that never ran (R16.6 gives that state its
    own meaning, so conflating them is worse than an error).

    Expected shape, upper bounds exclusive except the last::

        {"LOW": 0.25, "MEDIUM": 0.50, "HIGH": 0.75, "CRITICAL": 1.0}
    """
    if not isinstance(value, dict):
        raise PolicyValueInvalid(key, "expected an object mapping band name to upper bound")

    missing = [band for band in _BANDS if band not in value]
    if missing:
        raise PolicyValueInvalid(
            key, f"missing bands: {missing}", expected_bands=list(_BANDS)
        )
    unknown = sorted(set(value) - set(_BANDS))
    if unknown:
        raise PolicyValueInvalid(key, f"unknown bands: {unknown}", expected_bands=list(_BANDS))

    bounds: list[float] = []
    for band in _BANDS:
        bound = value[band]
        if isinstance(bound, bool) or not isinstance(bound, (int, float)):
            raise PolicyValueInvalid(key, f"{band} upper bound is not a number")
        bounds.append(float(bound))

    if any(b <= 0.0 or b > 1.0 for b in bounds):
        raise PolicyValueInvalid(
            key, "every upper bound must lie in (0, 1]", bounds=bounds
        )
    if bounds != sorted(bounds):
        raise PolicyValueInvalid(
            key, "bounds must increase across LOW < MEDIUM < HIGH < CRITICAL", bounds=bounds
        )
    if len(set(bounds)) != len(bounds):
        # Equal consecutive bounds make a band that no probability can fall in,
        # so a band exists in configuration and can never be assigned.
        raise PolicyValueInvalid(key, "bounds must be strictly increasing", bounds=bounds)
    if bounds[-1] != 1.0:
        raise PolicyValueInvalid(
            key,
            "the highest band must have an upper bound of exactly 1.0, or a "
            "probability above it maps to no band",
            bounds=bounds,
        )


# ---------------------------------------------------------------------------
# R28.8 — OCR thresholds ordered
# ---------------------------------------------------------------------------


def validate_review_below_auto_accept(key: str, value: Any) -> None:
    """R28.8: the review threshold must be strictly below auto-accept.

    Inverted, every field lands in exactly one branch and the other becomes
    unreachable: with review above auto-accept nothing is ever ``PENDING_REVIEW``,
    so R12.2's human review step silently stops existing while the system looks
    healthy.

    Applies to the whole ``ocr.threshold.*`` family, so it receives the individual
    value and checks range only; the cross-field ordering is checked when the set is
    submitted together, via :func:`validate_ocr_threshold_set`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PolicyValueInvalid(key, "expected a number between 0 and 1")
    if not 0.0 <= float(value) <= 1.0:
        raise PolicyValueInvalid(key, f"confidence threshold {value} is outside [0, 1]")


def validate_ocr_threshold_set(key: str, value: Any) -> None:
    """R28.8 across the set: review < auto_accept, and rejection below both."""
    if not isinstance(value, dict):
        raise PolicyValueInvalid(key, "expected an object of threshold name to value")

    required = ("auto_accept", "review", "document_rejection")
    missing = [name for name in required if name not in value]
    if missing:
        raise PolicyValueInvalid(key, f"missing thresholds: {missing}")

    for name in required:
        validate_review_below_auto_accept(f"{key}.{name}", value[name])

    if not float(value["review"]) < float(value["auto_accept"]):
        raise PolicyValueInvalid(
            key,
            "review threshold must be strictly below auto_accept, or no field is "
            "ever routed to human review (R12.2)",
            review=value["review"],
            auto_accept=value["auto_accept"],
        )


# ---------------------------------------------------------------------------
# Stage graph
# ---------------------------------------------------------------------------


def validate_stage_graph(key: str, value: Any) -> None:
    """Reachability, at least one terminal, no orphan, no stranded stage.

    The stranded case is the one worth naming: a non-terminal stage with no
    successors accepts cases and can never release them. Nothing errors — the case
    simply cannot advance, and R5.4 dutifully reports an empty set of permitted
    successors, which looks like correct behaviour.
    """
    if not isinstance(value, dict) or "stages" not in value:
        raise PolicyValueInvalid(key, "expected an object with a 'stages' array")
    stages = value["stages"]
    if not isinstance(stages, list) or not stages:
        raise PolicyValueInvalid(key, "'stages' must be a non-empty array")

    keys: list[str] = []
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict) or "key" not in stage:
            raise PolicyValueInvalid(key, f"stage at index {index} has no 'key'")
        keys.append(stage["key"])
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        raise PolicyValueInvalid(key, f"duplicate stage keys: {duplicates}")

    known = set(keys)
    terminals: list[str] = []
    for stage in stages:
        stage_key = stage["key"]
        successors = stage.get("successors", [])
        if not isinstance(successors, list):
            raise PolicyValueInvalid(key, f"{stage_key}: 'successors' must be an array")
        unknown = sorted(set(successors) - known)
        if unknown:
            raise PolicyValueInvalid(
                key, f"{stage_key} declares unknown successors: {unknown}"
            )
        terminal = bool(stage.get("terminal", False))
        if terminal:
            terminals.append(stage_key)
            if successors:
                raise PolicyValueInvalid(
                    key, f"{stage_key} is terminal but declares successors {successors}"
                )
        elif not successors:
            raise PolicyValueInvalid(
                key,
                f"{stage_key} is not terminal and has no successors, so a case "
                "entering it can never advance",
            )

    if not terminals:
        raise PolicyValueInvalid(
            key, "no terminal stage: no case could ever complete"
        )

    # Reachability from the first declared stage. An unreachable stage is dead
    # configuration, and worse, R32.3's retention start depends on cases reaching a
    # terminal stage — an unreachable terminal is a case that never ages out.
    start = keys[0]
    reached = {start}
    frontier = [start]
    by_key = {stage["key"]: stage for stage in stages}
    while frontier:
        current = frontier.pop()
        for successor in by_key[current].get("successors", []):
            if successor not in reached:
                reached.add(successor)
                frontier.append(successor)
    orphans = sorted(known - reached)
    if orphans:
        raise PolicyValueInvalid(
            key, f"stages unreachable from {start!r}: {orphans}", start_stage=start
        )
    if not any(t in reached for t in terminals):
        raise PolicyValueInvalid(
            key, f"no terminal stage is reachable from {start!r}", start_stage=start
        )


# ---------------------------------------------------------------------------
# Retention periods and priority weights
# ---------------------------------------------------------------------------


def validate_non_negative_days(key: str, value: Any) -> None:
    """A retention period must be a non-negative whole number of days.

    Zero is permitted and means "erase as soon as the retention start is
    determined", which is a legitimate policy. Negative would make the erasure date
    precede the retention start, and the sweep would erase data belonging to a case
    that had only just closed.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolicyValueInvalid(key, "expected a whole number of days")
    if value < 0:
        raise PolicyValueInvalid(key, f"{value} is negative")


def validate_weights_normalisable(key: str, value: Any) -> None:
    """R21.4: the weights must be able to produce a score in [0, 100].

    Only negatives and an all-zero set are rejected. The weights need not sum to
    one, because :func:`priority_score` normalises by their total — which is exactly
    why a zero total has to be refused here: it would divide by zero on every score.
    Rejecting anything that does not sum to one would instead force an administrator
    to rescale by hand for no gain.
    """
    if not isinstance(value, dict) or not value:
        raise PolicyValueInvalid(key, "expected a non-empty object of weight name to number")

    total = 0.0
    for name, weight in value.items():
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise PolicyValueInvalid(key, f"weight {name!r} is not a number")
        if weight < 0:
            raise PolicyValueInvalid(key, f"weight {name!r} is negative")
        total += float(weight)
    if total <= 0.0:
        raise PolicyValueInvalid(
            key, "weights sum to zero, so no score could be computed"
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

#: Exact key -> validator. Checked before the patterns below.
_EXACT: dict[str, Callable[[str, Any], None]] = {
    "risk.band_cutoffs": validate_partitions_unit_interval,
    "policy.stage_set": validate_stage_graph,
    "priority.weights": validate_weights_normalisable,
    "ocr.thresholds": validate_ocr_threshold_set,
}

#: fnmatch pattern -> validator, for key families sharing one rule.
_PATTERNS: tuple[tuple[str, Callable[[str, Any], None]], ...] = (
    ("ocr.threshold.*", validate_review_below_auto_accept),
    ("retention.period.*", validate_non_negative_days),
    ("period.*", validate_non_negative_days),
)

#: Read by tests and by task 2.5's write path. Exposed as one mapping for
#: introspection; resolution order is exact-then-pattern (see validate_policy_value).
VALIDATORS: dict[str, Callable[[str, Any], None]] = {
    **_EXACT,
    **{pattern: fn for pattern, fn in _PATTERNS},
}


def validate_policy_value(key: str, value: Any) -> None:
    """Apply the validator for ``key``, if one is registered.

    An unmatched key passes. See the module docstring: requiring a validator per key
    would block every new configuration value on writing one, and the workaround for
    that friction is to stop using Policy_Config, which is far worse than an
    unvalidated integer.
    """
    validator = _EXACT.get(key)
    if validator is None:
        for pattern, candidate in _PATTERNS:
            if fnmatch.fnmatchcase(key, pattern):
                validator = candidate
                break
    if validator is not None:
        validator(key, value)
