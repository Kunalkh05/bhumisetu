"""Uniform versioning guards for mutating routes and write paths (task 4.5).

Task 4.2 gives the platform one optimistic write primitive:
``VersionedRepository.update``. Task 4.3 gives routes two legal ways to receive the
caller-observed version: a ``VersionedWrite.expected_version`` body field or the
``If-Match`` dependency. This file is the future-facing guard that keeps those two
facts uniform as endpoints land:

* every mutating route must declare one of the two version inputs;
* no module outside ``app/db`` may import or call raw SQLAlchemy ``update``.

The shipped app has no domain mutating endpoints yet, so the route guard passes
mostly over an empty set. The meta-tests below make the guard prove it bites against
deliberately broken routes and raw-update files rather than merely passing today.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable, get_args

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.api.versioning import IfMatchVersion, VersionedWrite, if_match_version
from app.main import create_app
from app.settings import CoreSettings


MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
APP_ROOT = Path(__file__).resolve().parents[1] / "app"
NON_VERSIONED_FORM_POSTS = frozenset(
    {
        "/c/request-code",
        "/c/verify",
        "/c/language",
        "/c/correction",
        "/api/officer/dsar/{request_id}/disposal",
    }
)


def _core() -> CoreSettings:
    return CoreSettings.model_validate({"APP_ENV": "development", "LOG_LEVEL": "WARNING"})


def _unwrap_models(annotation: object) -> set[type]:
    """Return model classes reachable through a possibly generic annotation."""
    if isinstance(annotation, type):
        found = {annotation}
    else:
        found = set()
    for argument in get_args(annotation):
        found.update(_unwrap_models(argument))
    return found


def _model_has_expected_version(model: type) -> bool:
    """Whether ``model`` is a legal body carrier for the presented entity version."""
    return issubclass(model, VersionedWrite) or "expected_version" in getattr(
        model, "model_fields", {}
    )


def _route_body_has_expected_version(route: APIRoute) -> bool:
    """Check the request body side of the R29.2 contract."""
    body_field = getattr(route, "body_field", None)
    if body_field is None:
        return False
    candidates = set()
    for attr in ("type_", "annotation"):
        value = getattr(body_field, attr, None)
        if value is not None:
            candidates.update(_unwrap_models(value))
    return any(_model_has_expected_version(model) for model in candidates)


def _dependant_calls(dependant) -> Iterable[object]:  # type: ignore[no-untyped-def]
    """Yield every dependency callable FastAPI attached to a route."""
    for dependency in getattr(dependant, "dependencies", ()):
        yield getattr(dependency, "call", None)
        yield from _dependant_calls(dependency)


def _route_depends_on_if_match(route: APIRoute) -> bool:
    return any(call is if_match_version for call in _dependant_calls(route.dependant))


def _version_contract_offences(app: FastAPI) -> list[str]:
    """Every mutating route lacking both accepted version inputs."""
    offences: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        methods = set(route.methods or ())
        if not methods.intersection(MUTATING_METHODS):
            continue
        if route.path in NON_VERSIONED_FORM_POSTS:
            continue
        if _route_body_has_expected_version(route) or _route_depends_on_if_match(route):
            continue
        offences.append(
            f"{sorted(methods.intersection(MUTATING_METHODS))} {route.path} "
            "declares neither VersionedWrite.expected_version nor If-Match"
        )
    return offences


def test_every_mutating_route_declares_the_presented_version() -> None:
    """R29.10: every mutation route has a version contract before it can ship."""
    offences = _version_contract_offences(create_app(_core()))
    assert not offences, "mutating routes without a presented entity version: " + "; ".join(offences)


class _VersionedPatch(VersionedWrite):
    value: str


class _PlainPatch(BaseModel):
    value: str


def _app_with(router: APIRouter) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_route_guard_accepts_a_versioned_write_body() -> None:
    router = APIRouter()

    @router.patch("/case")
    async def _patch(body: _VersionedPatch) -> dict[str, int]:
        return {"expected_version": body.expected_version}

    assert _version_contract_offences(_app_with(router)) == []


def test_route_guard_accepts_an_if_match_dependency() -> None:
    router = APIRouter()

    @router.patch("/case")
    async def _patch(expected_version: IfMatchVersion) -> dict[str, int]:
        return {"expected_version": expected_version}

    assert _version_contract_offences(_app_with(router)) == []


def test_route_guard_flags_a_mutation_without_a_version_contract() -> None:
    router = APIRouter()

    @router.patch("/case")
    async def _patch(body: _PlainPatch) -> dict[str, str]:
        return {"value": body.value}

    offences = _version_contract_offences(_app_with(router))
    assert any("/case" in offence and "neither" in offence for offence in offences)


def test_route_guard_treats_nested_dependencies_as_if_match() -> None:
    router = APIRouter()

    def _nested(version: IfMatchVersion) -> int:
        return version

    @router.delete("/case")
    async def _delete(expected_version: int = Depends(_nested)) -> dict[str, int]:
        return {"expected_version": expected_version}

    assert _version_contract_offences(_app_with(router)) == []


def _python_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and path.is_file()
    ]


def _is_under_db(path: Path, app_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(app_root.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] == "db"


class _RawUpdateVisitor(ast.NodeVisitor):
    """Detect imports/calls of SQLAlchemy's raw ``update`` primitive."""

    def __init__(self) -> None:
        self.sqlalchemy_aliases: set[str] = set()
        self.update_names: set[str] = set()
        self.offences: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "sqlalchemy":
                self.sqlalchemy_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            if module in {"sqlalchemy", "sqlalchemy.sql"} and alias.name == "update":
                self.update_names.add(alias.asname or alias.name)
                self.offences.append(
                    f"line {node.lineno}: imports sqlalchemy.update as {alias.asname or alias.name}"
                )
            if module in {"sqlalchemy.sql.dml", "sqlalchemy.sql.expression"} and alias.name == "Update":
                self.offences.append(f"line {node.lineno}: imports raw SQLAlchemy Update")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in self.update_names:
            self.offences.append(f"line {node.lineno}: calls raw sqlalchemy.update()")
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "update"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in self.sqlalchemy_aliases
        ):
            self.offences.append(f"line {node.lineno}: calls raw sqlalchemy.update()")
        self.generic_visit(node)


def _raw_update_offences(paths: Iterable[Path], app_root: Path = APP_ROOT) -> list[str]:
    """Every non-``app/db`` module importing or executing raw SQLAlchemy UPDATE."""
    offences: list[str] = []
    for path in paths:
        if _is_under_db(path, app_root):
            continue
        visitor = _RawUpdateVisitor()
        visitor.visit(ast.parse(path.read_text(), filename=str(path)))
        offences.extend(f"{path}: {offence}" for offence in visitor.offences)
    return offences


def test_no_raw_sqlalchemy_update_outside_app_db() -> None:
    """R29.10: versioned writes cannot bypass ``VersionedRepository`` quietly."""
    offences = _raw_update_offences(_python_files(APP_ROOT))
    assert not offences, (
        "raw SQLAlchemy UPDATE outside app/db bypasses VersionedRepository and the "
        "entity_version/event invariant: " + "; ".join(offences)
    )


def test_raw_update_guard_accepts_app_db_as_the_single_write_boundary(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    db_file = app_root / "db" / "repo.py"
    db_file.parent.mkdir(parents=True)
    db_file.write_text("from sqlalchemy import update\nupdate(Thing)\n")

    assert _raw_update_offences([db_file], app_root) == []


def test_raw_update_guard_flags_direct_imports_outside_app_db(tmp_path: Path) -> None:
    service = tmp_path / "app" / "services" / "case.py"
    service.parent.mkdir(parents=True)
    service.write_text("from sqlalchemy import update as sa_update\nsa_update(Thing)\n")

    offences = _raw_update_offences([service], tmp_path / "app")
    assert any("imports sqlalchemy.update" in offence for offence in offences)
    assert any("calls raw sqlalchemy.update" in offence for offence in offences)


def test_raw_update_guard_flags_sqlalchemy_namespace_calls(tmp_path: Path) -> None:
    route = tmp_path / "app" / "api" / "case.py"
    route.parent.mkdir(parents=True)
    route.write_text("import sqlalchemy as sa\nsa.update(Thing)\n")

    offences = _raw_update_offences([route], tmp_path / "app")
    assert any("calls raw sqlalchemy.update" in offence for offence in offences)
