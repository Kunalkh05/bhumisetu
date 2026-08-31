"""Jurisdiction scope over real ``ltree`` containment, and the R2.6 freshness rule
(task 5.1, §8.1). Correctness Properties 4, 5 and 6.

These need the real database: the whole point of :func:`scoped` for an officer is
that PostgreSQL's ``path <@ scope`` reaches every descendant of a scoped area
without those descendants being listed anywhere, and that is an ``ltree``/GiST fact,
not something a stand-in can stand in for. The officer/role/scope rows are written
through the ORM on a savepoint that the ``db_connection`` fixture always rolls back,
so nothing here survives the test — the same isolation the other db/ tests use.

What is deferred: ``AcquisitionCase`` (task 8.1) does not exist, so the scope clause
is exercised against throwaway probe tables standing in for the case and parcel
tables it will eventually guard. The clause is the column-composed one that will
guard them; only the table is a stand-in.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    Integer,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.orm import Session

from app.models.officer import JurisdictionScope, Officer, OfficerRole, Role
from app.security.access import (
    OFFICER_SESSION_COOKIE,
    CitizenSession,
    OfficerSession,
    Principal,
    ServiceIdentity,
    principal_from_request,
    resolve_officer_principal,
    scoped,
)

# Transliterated paths the trigger derives, so the assertions can name them.
PATH = {
    "MH": "MH",
    "MH.PUNE": "MH.MH_PUNE",
    "MH.SATARA": "MH.MH_SATARA",
    "HAVELI-1": "MH.MH_PUNE.HAVELI_1",
    "WAGHOLI": "MH.MH_PUNE.HAVELI_1.WAGHOLI",
    "KESNAND": "MH.MH_PUNE.HAVELI_1.KESNAND",
}


@pytest.fixture
def session(db_connection: Connection) -> Session:
    """An ORM session on a savepoint inside the fixture's rolled-back transaction,
    the same pattern the other db/ tests use for ORM writes."""
    return Session(bind=db_connection, join_transaction_mode="create_savepoint")


@pytest.fixture
def tree(area_factory) -> None:
    """MH ⊃ {PUNE ⊃ HAVELI-1 ⊃ {WAGHOLI, KESNAND}, SATARA}. The codes carry a
    separator and a hyphen so the paths exercise transliteration, matching the
    hierarchy tests."""
    area_factory("MH", "state", "Maharashtra")
    area_factory("MH.PUNE", "district", "Pune", "MH")
    area_factory("MH.SATARA", "district", "Satara", "MH")
    area_factory("HAVELI-1", "tehsil", "Haveli", "MH.PUNE")
    area_factory("WAGHOLI", "village", "Wagholi", "HAVELI-1")
    area_factory("KESNAND", "village", "Kesnand", "HAVELI-1")


def _make_officer(
    session: Session,
    *,
    permissions=(),
    area_codes=(),
    code: str = "OFF1",
    active: bool = True,
) -> Officer:
    """One officer holding one role with the given permissions and scope areas."""
    role = Role(key=f"role-{code}", name=f"Role {code}", permissions=list(permissions))
    officer = Officer(
        officer_code=code,
        display_name="Officer",
        credential_hash="x",
        is_active=active,
    )
    session.add_all([role, officer])
    session.flush()
    session.add(OfficerRole(officer_id=officer.id, role_id=role.id))
    for area in area_codes:
        session.add(JurisdictionScope(role_id=role.id, area_code=area))
    session.flush()
    return officer


def _scope_probe(db_connection: Connection, area_codes) -> Table:
    """A throwaway table with one row per given area code, standing in for a
    scope-restricted case/parcel table until task 8.1."""
    table = Table(
        "scope_probe",
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("area_code", String),
    )
    table.create(db_connection)
    db_connection.execute(
        table.insert(),
        [{"id": i, "area_code": code} for i, code in enumerate(area_codes)],
    )
    return table


def _codes_visible(db_connection: Connection, table: Table, principal: Principal) -> set[str]:
    stmt = scoped(select(table.c.id, table.c.area_code), principal, table.c.area_code)
    return {row.area_code for row in db_connection.execute(stmt)}


# ---------------------------------------------------------------------------
# Property 4 — jurisdiction scope confines a collection, reaching descendants
# ---------------------------------------------------------------------------


def test_officer_scope_reaches_every_descendant(session, tree, db_connection) -> None:
    """A district scope sees the district and everything beneath it, and nothing
    outside — the ltree fact scoped() exists for."""
    officer = _make_officer(session, area_codes=["MH.PUNE"])
    principal = resolve_officer_principal(session, officer.id)
    assert set(principal.scope_paths) == {PATH["MH.PUNE"]}

    probe = _scope_probe(db_connection, list(PATH))
    assert _codes_visible(db_connection, probe, principal) == {
        "MH.PUNE",
        "HAVELI-1",
        "WAGHOLI",
        "KESNAND",
    }


def test_officer_scope_is_the_union_of_its_areas(session, tree, db_connection) -> None:
    """Two scope rows are an OR of two subtrees: a leaf village and a sibling
    district, with the leaf's sibling correctly excluded."""
    officer = _make_officer(session, area_codes=["WAGHOLI", "MH.SATARA"])
    principal = resolve_officer_principal(session, officer.id)
    assert set(principal.scope_paths) == {PATH["WAGHOLI"], PATH["MH.SATARA"]}

    probe = _scope_probe(db_connection, list(PATH))
    assert _codes_visible(db_connection, probe, principal) == {"WAGHOLI", "MH.SATARA"}


def test_officer_with_no_scope_sees_nothing(session, tree, db_connection) -> None:
    """Fail closed against a live query: an officer whose role has no jurisdiction
    row matches no rows, rather than every row."""
    officer = _make_officer(session, area_codes=[])
    principal = resolve_officer_principal(session, officer.id)
    assert principal.scope_paths == ()

    probe = _scope_probe(db_connection, list(PATH))
    assert _codes_visible(db_connection, probe, principal) == set()


def test_citizen_scope_confines_to_its_single_case(db_connection) -> None:
    """A citizen sees exactly the rows of its one case (R3.7)."""
    table = Table(
        "case_probe",
        MetaData(),
        Column("id", Integer, primary_key=True, autoincrement=False),
        Column("case_id", BigInteger),
    )
    table.create(db_connection)
    db_connection.execute(
        table.insert(),
        [
            {"id": 1, "case_id": 100},
            {"id": 2, "case_id": 100},
            {"id": 3, "case_id": 200},
            {"id": 4, "case_id": 300},
        ],
    )
    citizen = Principal(kind="CITIZEN", id="c", case_id=100)
    stmt = scoped(select(table.c.id), citizen, case_col=table.c.case_id)
    assert {row.id for row in db_connection.execute(stmt)} == {1, 2}


# ---------------------------------------------------------------------------
# resolve_officer_principal — permissions, activeness, absence
# ---------------------------------------------------------------------------


def test_permissions_are_the_union_across_roles(session, tree) -> None:
    officer = Officer(
        officer_code="OFF-MULTI", display_name="O", credential_hash="x"
    )
    role_a = Role(key="role-a", name="A", permissions=["case.transition"])
    role_b = Role(key="role-b", name="B", permissions=["config.write", "import.submit"])
    session.add_all([officer, role_a, role_b])
    session.flush()
    session.add_all(
        [
            OfficerRole(officer_id=officer.id, role_id=role_a.id),
            OfficerRole(officer_id=officer.id, role_id=role_b.id),
        ]
    )
    session.flush()

    principal = resolve_officer_principal(session, officer.id)
    assert principal.permissions == frozenset(
        {"case.transition", "config.write", "import.submit"}
    )
    assert len(principal.role_ids) == 2


def test_inactive_officer_resolves_to_no_principal(session) -> None:
    """A deactivated officer's still-valid-looking session resolves to nothing, so
    the request is unauthenticated (fail closed)."""
    officer = _make_officer(session, permissions=["case.transition"], active=False)
    assert resolve_officer_principal(session, officer.id) is None


def test_unknown_officer_resolves_to_no_principal(session) -> None:
    assert resolve_officer_principal(session, uuid.uuid4()) is None


# ---------------------------------------------------------------------------
# Property 6 — a permission or scope change applies on the next request
# ---------------------------------------------------------------------------


def test_permission_change_applies_on_the_next_resolution(session, tree) -> None:
    """R2.6 without re-authentication: the second resolution reads the changed
    permissions because nothing authorization-bearing was cached between them."""
    officer = _make_officer(session, permissions=["case.transition"], area_codes=["MH.PUNE"])
    role = session.get(Role, resolve_officer_principal(session, officer.id).role_ids[0])

    before = resolve_officer_principal(session, officer.id)
    assert before.permissions == frozenset({"case.transition"})

    role.permissions = ["case.transition", "config.write"]
    session.flush()

    after = resolve_officer_principal(session, officer.id)
    assert after.permissions == frozenset({"case.transition", "config.write"})


def test_scope_change_applies_on_the_next_resolution(session, tree) -> None:
    officer = _make_officer(session, area_codes=["MH.PUNE"])
    role_id = resolve_officer_principal(session, officer.id).role_ids[0]

    before = resolve_officer_principal(session, officer.id)
    assert set(before.scope_paths) == {PATH["MH.PUNE"]}

    session.add(JurisdictionScope(role_id=role_id, area_code="MH.SATARA"))
    session.flush()

    after = resolve_officer_principal(session, officer.id)
    assert set(after.scope_paths) == {PATH["MH.PUNE"], PATH["MH.SATARA"]}


# ---------------------------------------------------------------------------
# Property 5 — the decision is the principal, not the transport
# ---------------------------------------------------------------------------


@dataclass
class _Creds:
    cookies: dict
    headers: dict


class _Backend:
    def __init__(self, officer_id: uuid.UUID) -> None:
        self._officer_id = officer_id

    def officer_session(self, token: str) -> OfficerSession | None:
        return OfficerSession(self._officer_id) if token == "tok" else None

    def citizen_session(self, token: str) -> CitizenSession | None:
        return None

    def service_identity(self, token: str) -> ServiceIdentity | None:
        return None


def test_officer_principal_is_db_sourced_not_token_sourced(session, tree) -> None:
    """The officer session carried only an id; every permission and scope path on the
    resulting principal came from the database. So the principal a request is judged
    on does not depend on which cookie carried the token — Property 5 at this layer.
    """
    officer = _make_officer(
        session, permissions=["case.transition"], area_codes=["MH.PUNE"]
    )
    backend = _Backend(officer.id)
    creds = _Creds(cookies={OFFICER_SESSION_COOKIE: "tok"}, headers={})

    via_request = principal_from_request(creds, backend=backend, session=session)
    direct = resolve_officer_principal(session, officer.id)

    assert via_request == direct
    assert via_request.permissions == frozenset({"case.transition"})
    assert set(via_request.scope_paths) == {PATH["MH.PUNE"]}
