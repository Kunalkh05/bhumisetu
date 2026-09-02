"""Point-in-time feature extraction (§14.2).

``ml/src`` is a source root, so this is the top-level ``features`` package
(imported as ``features.registry``), a sibling of ``labelling`` — the same layout
the AST lint and metadata-walk guards treat ``ml/src`` as (§20.7).

The extractor seam arrived before any extractor so the disjointness guard was
already in force when the first feature was written. Importing the package now
also registers the current default extractor set.
"""

from __future__ import annotations

from features.extractors import register_default_extractors

register_default_extractors()

__all__ = ["register_default_extractors"]
