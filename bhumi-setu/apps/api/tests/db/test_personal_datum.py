"""``personal_datum``'s single permitted transition (§5.4, R4.2, R32.12).

§5.4 concedes that something in the log's read path has to be mutable, and confines
it to this table with "exactly one permitted transition". That sentence is a comment
unless a trigger enforces it, so these tests are the difference between a design
claim and a guarantee.

Unlike the ``event`` tests, these do **not** need ``SET ROLE``. A trigger applies to
everyone including the table owner, which is why a trigger is the right mechanism
here — a grant cannot express "one specific update is allowed" — and
``test_the_trigger_applies_to_the_owner_too`` asserts that difference rather than
assuming it.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import Connection, text

ERASED_AT = datetime(2031, 2, 1, tzinfo=timezone.utc)


@pytest.fixture
def datum(db_connection: Connection):
    """One unerased personal datum."""

    def _make(
        *,
        category: str = "OWNER_IDENTITY",
        entity_type: str = "ownership_record",
        entity_id: int = 1,
        attribute: str = "owner_name",
        value: bytes = b"ciphertext",
    ) -> int:
        return db_connection.execute(
            text(
                """
                INSERT INTO personal_datum
                    (data_category, entity_type, entity_id, attribute_name,
                     value_ciphertext, key_version)
                VALUES (:c, :et, :ei, :a, :v, 1)
                RETURNING id
                """
            ),
            {"c": category, "et": entity_type, "ei": entity_id, "a": attribute, "v": value},
        ).scalar_one()

    return _make


def erase(connection: Connection, datum_id: int, *, event_id: int | None = None) -> None:
    connection.execute(
        text(
            """
            UPDATE personal_datum
               SET value_ciphertext = NULL,
                   erased_at = :at,
                   erasure_event_id = :ev
             WHERE id = :id
            """
        ),
        {"id": datum_id, "at": ERASED_AT, "ev": event_id},
    )


def row(connection: Connection, datum_id: int):
    return connection.execute(
        text(
            "SELECT value_ciphertext, erased_at, erasure_event_id, data_category "
            "FROM personal_datum WHERE id = :id"
        ),
        {"id": datum_id},
    ).one()


def make_event(connection: Connection) -> int:
    return connection.execute(
        text(
            """
            INSERT INTO event (event_type, entity_type, entity_id, actor_type,
                               actor_id, occurrence_time, payload)
            VALUES ('PERSONAL_DATA_ERASED', 'ownership_record', 1, 'SYSTEM',
                    'retention_sweep', now(), '{}'::jsonb)
            RETURNING id
            """
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# The one permitted transition
# ---------------------------------------------------------------------------


def test_erasure_is_permitted(db_connection: Connection, datum) -> None:
    datum_id = datum()
    erase(db_connection, datum_id)
    stored = row(db_connection, datum_id)
    assert stored.value_ciphertext is None
    assert stored.erased_at == ERASED_AT


def test_erasure_keeps_the_category_and_timestamp_the_resolver_needs(
    db_connection: Connection, datum
) -> None:
    """R32.13's read path returns {'$erased': {data_category, erased_at}}.

    Both survive erasure, which is why the row is nulled rather than deleted — a
    delete would leave the resolver unable to say anything about what was there.
    """
    datum_id = datum(category="OWNER_CONTACT")
    erase(db_connection, datum_id)
    stored = row(db_connection, datum_id)
    assert stored.data_category == "OWNER_CONTACT"
    assert stored.erased_at is not None


def test_erasure_records_its_compensating_event(
    db_connection: Connection, datum
) -> None:
    """R32.12: the only write erasure performs on the log is appending one event."""
    datum_id = datum()
    event_id = make_event(db_connection)
    erase(db_connection, datum_id, event_id=event_id)
    assert row(db_connection, datum_id).erasure_event_id == event_id


# ---------------------------------------------------------------------------
# Everything else is refused
# ---------------------------------------------------------------------------


def test_a_row_cannot_be_deleted(db_connection: Connection, datum) -> None:
    """A deleted row leaves every event payload referencing it resolving to nothing,
    which is indistinguishable from a bug."""
    datum_id = datum()
    with pytest.raises(Exception, match="cannot be deleted"):
        db_connection.execute(
            text("DELETE FROM personal_datum WHERE id = :id"), {"id": datum_id}
        )


def test_the_ciphertext_cannot_be_replaced_with_a_new_value(
    db_connection: Connection, datum
) -> None:
    """This is the back door. Event payloads reference this row, so rewriting the
    value rewrites history without touching a single event row — which is exactly
    what R4.2 exists to prevent."""
    datum_id = datum()
    with pytest.raises(Exception, match="only permitted update"):
        db_connection.execute(
            text("UPDATE personal_datum SET value_ciphertext = :v WHERE id = :id"),
            {"id": datum_id, "v": b"different"},
        )


def test_nulling_the_ciphertext_without_setting_erased_at_is_refused(
    db_connection: Connection, datum
) -> None:
    """Half an erasure is worse than none: the value is gone and the resolver has no
    erased_at to report, so R32.13's marker cannot be produced."""
    datum_id = datum()
    with pytest.raises(Exception, match="only permitted update"):
        db_connection.execute(
            text("UPDATE personal_datum SET value_ciphertext = NULL WHERE id = :id"),
            {"id": datum_id},
        )


def test_setting_erased_at_while_keeping_the_value_is_refused(
    db_connection: Connection, datum
) -> None:
    """The inverse, and worse: the row claims to be erased while still holding the
    personal data."""
    datum_id = datum()
    with pytest.raises(Exception, match="only permitted update"):
        db_connection.execute(
            text("UPDATE personal_datum SET erased_at = :at WHERE id = :id"),
            {"id": datum_id, "at": ERASED_AT},
        )


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("data_category", "'MODEL_FEATURE'"),
        ("entity_type", "'land_parcel'"),
        ("entity_id", "999"),
        ("attribute_name", "'contact_mobile'"),
        ("key_version", "2"),
    ],
)
def test_identity_columns_are_immutable(
    db_connection: Connection, datum, column: str, value: str
) -> None:
    """Moving a row's identity re-points existing event payloads at a different
    value, without touching an event."""
    datum_id = datum()
    with pytest.raises(Exception, match="identity is immutable"):
        db_connection.execute(
            text(f"UPDATE personal_datum SET {column} = {value} WHERE id = :id"),
            {"id": datum_id},
        )


# ---------------------------------------------------------------------------
# Erasure is irreversible
# ---------------------------------------------------------------------------


def test_an_erased_value_cannot_be_restored(db_connection: Connection, datum) -> None:
    """R32.10. A reversible erasure is not an erasure."""
    datum_id = datum()
    erase(db_connection, datum_id)
    with pytest.raises(Exception, match="cannot be restored"):
        db_connection.execute(
            text("UPDATE personal_datum SET value_ciphertext = :v WHERE id = :id"),
            {"id": datum_id, "v": b"restored"},
        )


def test_erased_at_cannot_be_cleared(db_connection: Connection, datum) -> None:
    datum_id = datum()
    erase(db_connection, datum_id)
    with pytest.raises(Exception, match="set once"):
        db_connection.execute(
            text("UPDATE personal_datum SET erased_at = NULL WHERE id = :id"),
            {"id": datum_id},
        )


def test_erased_at_cannot_be_changed_to_a_different_time(
    db_connection: Connection, datum
) -> None:
    """It would make the $erased marker in R32.13's read path disagree with the
    timestamp on the compensating event."""
    datum_id = datum()
    erase(db_connection, datum_id)
    with pytest.raises(Exception, match="set once"):
        db_connection.execute(
            text("UPDATE personal_datum SET erased_at = now() WHERE id = :id"),
            {"id": datum_id},
        )


def test_re_erasing_with_the_same_timestamp_is_idempotent(
    db_connection: Connection, datum
) -> None:
    """The sweep guards with `WHERE erased_at IS NULL`, but a redelivered task must
    not fail loudly if it slips through — R32.10's sweep is idempotent by design."""
    datum_id = datum()
    erase(db_connection, datum_id)
    erase(db_connection, datum_id)
    assert row(db_connection, datum_id).erased_at == ERASED_AT


def test_the_erasure_event_cannot_be_deleted(db_connection: Connection, datum) -> None:
    """RESTRICT: an erasure whose event was removed would be unattributable."""
    datum_id = datum()
    event_id = make_event(db_connection)
    erase(db_connection, datum_id, event_id=event_id)
    with pytest.raises(Exception, match="violates foreign key constraint"):
        db_connection.execute(text("DELETE FROM event WHERE id = :id"), {"id": event_id})


# ---------------------------------------------------------------------------
# Mechanism notes
# ---------------------------------------------------------------------------


def test_the_trigger_applies_to_the_owner_too(db_connection: Connection, datum) -> None:
    """Why a trigger rather than a grant.

    `event` uses REVOKE UPDATE, DELETE because it needs no updates at all. This
    table needs exactly one, which a privilege cannot express. The compensating
    benefit is that a trigger binds the owner as well — this connection is a
    superuser, and the refusal still happens.
    """
    assert db_connection.execute(text("SELECT current_user")).scalar_one() != "bhumisetu_app"
    datum_id = datum()
    with pytest.raises(Exception, match="only permitted update"):
        db_connection.execute(
            text("UPDATE personal_datum SET value_ciphertext = :v WHERE id = :id"),
            {"id": datum_id, "v": b"owner bypass attempt"},
        )


def test_the_application_role_cannot_delete(db_connection: Connection, datum) -> None:
    """Belt and braces: the trigger refuses DELETE for everyone, and the revoke means
    the application role fails at the privilege check before reaching plpgsql."""
    datum()
    db_connection.execute(text("SET LOCAL ROLE bhumisetu_app"))
    with pytest.raises(Exception, match="permission denied|cannot be deleted"):
        db_connection.execute(text("DELETE FROM personal_datum"))


def test_the_category_index_only_covers_unerased_rows(
    db_connection: Connection,
) -> None:
    """Partial index, so the sweep's working set shrinks as data ages out."""
    definition = db_connection.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'personal_datum_category'")
    ).scalar_one()
    assert "WHERE" in definition and "erased_at IS NULL" in definition, definition
