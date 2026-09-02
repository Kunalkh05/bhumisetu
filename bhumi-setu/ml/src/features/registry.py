"""The feature-extractor seam and its registry (§14.2, §14.3).

A feature is computed by folding the event log into an as-of view and handing that
view to a set of registered extractors. Two of the pipeline's structural
guarantees rest on one thing every extractor must declare — its
``source_attributes`` — so that declaration is part of the protocol, not a
convention:

* **No leakage from the labelled outcome (R17.3).** The label function declares
  its own source attributes; a test (task 18) asserts the two sets are disjoint.
* **No derivation from personal data (§5.4, Property 39).** A feature built on an
  attribute that erasure can later remove would silently change historical
  feature rows and break R17.5's reproducibility. Task 3.3's guard intersects
  every extractor's ``source_attributes`` with the personal-data set from
  ``CATEGORY_MAP`` and fails on any overlap.

Both guards can only see a dependency the extractor names. An extractor that
declared nothing would pass both vacuously, so the guard also refuses an extractor
that declares no sources — the seam is built to fail closed.

This module is the seam only. Concrete extractors and ``FeatureValue`` arrive
with the ML pipeline, but the point-in-time ``AsOfView`` exists now, so the seam
can close over that pure view rather than over a database session.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from features.asof import AsOfView

__all__ = ["FeatureExtractor", "FeatureRegistry", "FEATURE_REGISTRY"]


@runtime_checkable
class FeatureExtractor(Protocol):
    """One named point-in-time feature.

    ``source_attributes`` is the declaration the leakage and personal-data guards
    read. An extractor that reads an attribute must name it here, or the guards
    cannot see the dependency.
    """

    #: A stable identifier for the feature, used in reports and error messages.
    name: str

    #: The attributes this feature reads, as bare column/attribute names. Empty is
    #: not a valid declaration: the guards treat "declares nothing" as a failure.
    source_attributes: frozenset[str]

    def compute(self, view: AsOfView, t: datetime) -> Any:
        """Compute the feature value from an as-of ``view`` at time ``t``.

        No ``Session``, ``Engine``, connection, or repository is passed here:
        all database I/O must finish before extractors run.
        """
        ...


class FeatureRegistry:
    """The set of registered feature extractors.

    Empty until task 14 registers the first extractor. It exists now so the
    disjointness guard (task 3.3) has something to enumerate: with no extractors
    the guard passes, and the day an extractor is added it is checked — the guard
    was never absent.
    """

    def __init__(self) -> None:
        self._extractors: list[FeatureExtractor] = []

    def register(self, extractor: FeatureExtractor) -> FeatureExtractor:
        """Register ``extractor`` and return it, so this also works as a decorator."""
        self._extractors.append(extractor)
        return extractor

    def all(self) -> tuple[FeatureExtractor, ...]:
        """Every registered extractor, in registration order."""
        return tuple(self._extractors)

    def __iter__(self):
        return iter(self._extractors)

    def __len__(self) -> int:
        return len(self._extractors)


#: The one registry the pipeline builds features from and the guards read. Empty
#: at task 3.3.
FEATURE_REGISTRY = FeatureRegistry()
