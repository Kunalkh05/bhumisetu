"""Point-in-time feature extraction (§14.2).

``ml/src`` is a source root, so this is the top-level ``features`` package
(imported as ``features.registry``), a sibling of ``labelling`` — the same layout
the AST lint and metadata-walk guards treat ``ml/src`` as (§20.7).

At task 3.3 this package holds only the extractor seam: the
:class:`~features.registry.FeatureExtractor` protocol and an empty
:data:`~features.registry.FEATURE_REGISTRY`. The seam exists before any extractor
so the disjointness guard that protects it is already in force when the first
extractor is written.
"""

from __future__ import annotations

__all__: list[str] = []
