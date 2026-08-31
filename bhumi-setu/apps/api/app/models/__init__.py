"""Mapped classes. Every table in the platform is declared in this package.

Registration is by disk walk, not by a hand-written import list
---------------------------------------------------------------

A declarative class registers its table on ``Base.metadata`` as a side effect of
its module being imported. An import list in this file would be a list someone
can forget to extend, and the cost of forgetting is silent: the table would be
absent from ``Base.metadata``, and the guards in tasks 2.7 and 25.2 that walk it
would pass over the new table without ever seeing it — a column with a
statutory-period default or an unclassified personal-data column would ship.

:func:`load_all_models` therefore derives the module set from the package
contents at call time. **Creating a module under ``app/models/`` is the whole of
the registration step.** ``app/db/base.py`` explains the other half of the rule:
a mapped table is declared here and nowhere else.

This package is empty at task 1.1; the schema arrives from task 1.2 onward.
"""

from __future__ import annotations

import importlib
import pkgutil

__all__ = ["load_all_models"]


def load_all_models() -> frozenset[str]:
    """Import every module in this package and return their dotted names.

    Idempotent: repeated calls hit ``sys.modules``. Import errors are not
    swallowed — a model module that cannot be imported must fail loudly here
    rather than leave a gap in ``Base.metadata``.
    """
    loaded: set[str] = set()
    for module_info in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        leaf = module_info.name.rsplit(".", 1)[-1]
        if leaf.startswith("_"):
            continue
        importlib.import_module(module_info.name)
        loaded.add(module_info.name)
    return frozenset(loaded)
