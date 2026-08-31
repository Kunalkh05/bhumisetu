"""No feature derives from personal data (§5.4, Property 39, R17.3/R32.2).

*For any registered feature extractor, its declared source attributes are disjoint
from the set of attributes assigned to a personal-data Data_Category.*

Why this test lives here, with the event log, and not with the ML tasks
-----------------------------------------------------------------------

The Feature_Builder computes features by replaying the event log. If a feature
derived from a personal-data attribute, erasing that attribute later would
silently change historical feature rows and break R17.5's reproducibility — the
same replay would produce a different row after an erasure. So the invariant that
protects erasure is a constraint on feature engineering, and it belongs beside the
log's erasure design. It is in force from task 3.3, before any extractor exists,
which is the point: the guard is never added *after* the code it polices.

Failing closed
--------------

With an empty registry the disjointness check has nothing to catch, so two things
keep it from passing vacuously. First, an extractor that declared *no* source
attributes would pass the intersection trivially while potentially reading
anything, so the guard treats "declares nothing" as a violation. Second, if the
personal-data set were ever empty the intersection would be empty for every
extractor, so the guard asserts that set is non-empty before trusting it. The
guard's own behaviour is exercised below on fabricated extractors, because a guard
never observed rejecting anything is a guess (the same discipline as the AST lint
in ``tests/config_integrity``).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# ``ml/src`` is a source root (a sibling of ``apps/api``), not on the API test
# path by default. Locate it the way the config-integrity tests locate sibling
# roots — from the repo root above ``apps/`` — and make ``features`` importable.
API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
if str(ML_SRC) not in sys.path:
    sys.path.insert(0, str(ML_SRC))

from app.retention.categories import (  # noqa: E402  (after sys.path setup)
    CATEGORY_MAP,
    OWNER_IDENTITY,
    personal_data_attributes,
)
from features.registry import (  # noqa: E402
    FEATURE_REGISTRY,
    FeatureExtractor,
    FeatureRegistry,
)


def _disjointness_violations(extractors, personal: frozenset[str]) -> list[str]:
    """Return a human-readable violation for each extractor that fails the rule.

    Two failure modes: an extractor that declares no sources (fails closed), and
    one whose sources overlap the personal-data set.
    """
    violations: list[str] = []
    for extractor in extractors:
        name = getattr(extractor, "name", "<unnamed>")
        sources = getattr(extractor, "source_attributes", None)
        if not sources:
            violations.append(f"{name}: declares no source_attributes")
            continue
        overlap = set(sources) & personal
        if overlap:
            violations.append(f"{name}: derives from personal data {sorted(overlap)}")
    return violations


# ---------------------------------------------------------------------------
# The guard itself
# ---------------------------------------------------------------------------


def test_features_do_not_derive_from_personal_data() -> None:
    personal = personal_data_attributes(CATEGORY_MAP)
    assert personal, (
        "the personal-data attribute set is empty, so this guard would pass "
        "vacuously — CATEGORY_MAP must classify some attribute as personal"
    )
    violations = _disjointness_violations(FEATURE_REGISTRY.all(), personal)
    assert not violations, (
        "A feature extractor derives from personal data. Erasing that attribute "
        "would silently change historical feature rows and break R17.5. Derive "
        f"the feature from a non-personal attribute instead. Offences: {violations}"
    )


# ---------------------------------------------------------------------------
# The guard's own behaviour, on fabricated extractors
# ---------------------------------------------------------------------------


class _FakeExtractor:
    def __init__(self, name: str, source_attributes) -> None:
        self.name = name
        self.source_attributes = frozenset(source_attributes)

    def compute(self, view, t: datetime):  # pragma: no cover - never called
        raise NotImplementedError


def test_the_guard_rejects_an_extractor_that_reads_personal_data() -> None:
    personal = personal_data_attributes(CATEGORY_MAP)
    assert "owner_name" in personal  # precondition for the case below
    reads_pd = _FakeExtractor("owner_name_length", {"owner_name", "days_in_stage"})
    violations = _disjointness_violations([reads_pd], personal)
    assert violations and "owner_name" in violations[0]


def test_the_guard_rejects_an_extractor_that_declares_no_sources() -> None:
    personal = personal_data_attributes(CATEGORY_MAP)
    silent = _FakeExtractor("declares_nothing", set())
    assert _disjointness_violations([silent], personal)


def test_the_guard_allows_an_extractor_over_non_personal_attributes() -> None:
    """A count or a duration is allowed — the design's "owner count is allowed,
    owner names are not"."""
    personal = personal_data_attributes(CATEGORY_MAP)
    ok = _FakeExtractor("days_in_current_stage", {"stage_entered_on", "owner_count"})
    assert not _disjointness_violations([ok], personal)


# ---------------------------------------------------------------------------
# The seam: the protocol declares source_attributes and the registry works
# ---------------------------------------------------------------------------


def test_the_protocol_declares_source_attributes() -> None:
    """The whole point of the seam at task 3.3: an extractor must declare where it
    reads from, so the guards can see it."""
    assert "source_attributes" in FeatureExtractor.__annotations__
    assert "name" in FeatureExtractor.__annotations__


def test_a_fresh_registry_is_empty_and_records_registrations() -> None:
    registry = FeatureRegistry()
    assert registry.all() == ()
    assert len(registry) == 0

    extractor = _FakeExtractor("f", {"stage_key"})
    returned = registry.register(extractor)
    assert returned is extractor  # usable as a decorator
    assert registry.all() == (extractor,)
    assert list(registry) == [extractor]
