"""``Base.metadata`` is the single registry, and the walk over it is complete.

Tasks 2.7 and 25.2 fail the build by walking ``Base.metadata``: 2.7 on a date
column with a computed default or a CHECK constraint containing a day count,
25.2 on a column no ``Data_Category`` classifies. A walk is only a guard if
nothing can hide from it, and there are exactly two ways a table could:

* it belongs to a second registry, so it is not in ``Base.metadata`` at all;
* its module is never imported, so its table is never registered.

These tests close both, before there are any tables for them to be wrong about.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app import models
from app.db.base import Base, all_metadata

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
APP_PACKAGE = API_ROOT / "app"
MODELS_PACKAGE = APP_PACKAGE / "models"
REGISTRY_MODULE = APP_PACKAGE / "db" / "base.py"

#: Everywhere the platform's Python lives. `ml/src` and `workers` import the same
#: service modules (§3.2, §3.3), so a table declared there would be as invisible
#: to the walk as one declared in a service module.
SOURCE_ROOTS = (APP_PACKAGE, REPO_ROOT / "ml" / "src", REPO_ROOT / "workers")


def python_files() -> list[Path]:
    found: list[Path] = []
    for root in SOURCE_ROOTS:
        if root.exists():
            found.extend(
                path
                for path in root.rglob("*.py")
                if ".venv" not in path.parts and "site-packages" not in path.parts
            )
    return found


def parsed(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def called_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def test_all_metadata_returns_the_declarative_metadata() -> None:
    assert all_metadata() is Base.metadata


def test_load_all_models_covers_every_module_on_disk() -> None:
    """The registration step is a disk walk, so it cannot fall behind the disk.

    If this ever fails, a model module exists that ``Base.metadata`` does not
    know about, and both metadata-walk guards are passing over it.
    """
    on_disk = {
        f"app.models.{path.stem}"
        for path in MODELS_PACKAGE.rglob("*.py")
        if not path.stem.startswith("_")
    }
    assert models.load_all_models() == on_disk


def test_load_all_models_is_idempotent() -> None:
    assert models.load_all_models() == models.load_all_models()


def test_base_metadata_is_the_only_registry() -> None:
    """No second ``MetaData`` or declarative base anywhere in the platform.

    A second registry is the quiet failure: its tables are absent from
    ``Base.metadata``, so the guards in 2.7 and 25.2 report success over a schema
    they never saw.
    """
    offences: list[str] = []
    for path in python_files():
        if path == REGISTRY_MODULE:
            continue
        tree = parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and called_name(node) in {
                "MetaData",
                "declarative_base",
            }:
                offences.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} "
                                f"{called_name(node)}()")
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "DeclarativeBase":
                        offences.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno} "
                            f"class {node.name}(DeclarativeBase)"
                        )
    assert offences == [], (
        "Tables must be registered on app.db.base.Base.metadata. A second "
        "registry hides its tables from the metadata-walk guards in tasks 2.7 "
        f"and 25.2. Found: {offences}"
    )


def test_tables_are_declared_only_under_app_models() -> None:
    """A mapped table lives in ``app/models/``, which is what the walk imports.

    Service modules operate on tables; they do not declare them. ``event_log.py``
    holds the append logic (§3.2) while the ``event`` table is declared in
    ``app/models/`` — otherwise the table would sit outside the import walk and
    therefore outside both guards.
    """
    offences: list[str] = []
    for path in python_files():
        if MODELS_PACKAGE in path.parents:
            continue
        tree = parsed(path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        offences.append(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno} __tablename__"
                        )
            if isinstance(node, ast.AnnAssign):
                target = node.target
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    offences.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno} __tablename__"
                    )
            if isinstance(node, ast.Call) and called_name(node) == "Table":
                offences.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} Table()")
    assert offences == [], (
        "Declare mapped tables in app/models/ so app.models.load_all_models() "
        f"registers them on Base.metadata. Found: {offences}"
    )


@pytest.mark.parametrize("package", ["app.models", "app.db"])
def test_platform_packages_import_cleanly(package: str) -> None:
    __import__(package)
