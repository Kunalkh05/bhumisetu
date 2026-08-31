"""Retention and data-subject-rights subsystem (§17).

At task 3.3 this package holds only the declarative attribute classification —
:mod:`app.retention.categories` — because two mechanisms need it before the
retention sweep itself exists:

* the event log's payload externalisation (task 3.4) consults it to decide which
  attributes become ``personal_datum`` references rather than inline values;
* the ML feature-registry disjointness guard (task 3.3) intersects the
  personal-data attribute set it derives against every feature extractor's
  declared sources, so a feature can never derive from a value that erasure would
  later remove (§5.4).

The erasure sweep, the DSAR handlers, and the metadata-walk completeness test
arrive with task 25; they all read the same registry declared here.
"""

from __future__ import annotations

__all__: list[str] = []
