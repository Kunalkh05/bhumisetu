"""``Versioned`` — the column every concurrency-controlled entity must carry (§7).

What R29.1 asks for
-------------------

R29.1 requires an Entity_Version on every Acquisition_Case, Land_Parcel,
Ownership_Record, Statutory_Notice, Objection, Award, Payout, Document,
Extracted_Field and Validation_Issue — and the design adds Notice_Service_Record,
for eleven tables in all (§3.7). The version must *increase on every committed
modification of the entity*, and Property 67 sharpens "increase" to "by exactly
one, when and only when the modification commits, and unchanged when it is
rejected".

Why a mixin rather than a column repeated eleven times
------------------------------------------------------

A version column copied by hand into eleven ``CREATE TABLE`` bodies is a column
that can be *forgotten* on the twelfth table someone adds — and a versioned entity
without ``entity_version`` is not a compile error, it is a silent hole in
concurrency control that surfaces as a lost update in production. Declaring the
column once, here, and having every entity inherit it makes "a new entity type
cannot be added without a version column" a property of how the class is written
rather than of whether its author remembered. A model that means to be
concurrency-controlled inherits :class:`Versioned`; the column comes with it,
identical on every table.

This is the same discipline the event log uses (``entity_id`` is ``bigint``
everywhere because the log says so): the shape of a cross-cutting concern is
declared in one place and the entities conform to it.

Why the column arrives with each table, and there is no migration in task 4.1
-----------------------------------------------------------------------------

The eleven tables do not exist yet — the schema head is ``0005_task_outbox`` and
``acquisition_case`` and friends are created in tasks 8 through 16. A migration in
this task that ran ``ALTER TABLE acquisition_case ADD COLUMN entity_version ...``
would fail ``alembic upgrade head`` against the current schema, because there is no
table to alter. So this task ships the *mechanism*, not a migration: because each
of those entity models will inherit :class:`Versioned`, the ORM carries
``entity_version`` on each of them, and each table's own creating migration
(tasks 8–16) emits the column as part of its ``CREATE TABLE``. The column thus
lands *with* each table rather than as a bulk alter of tables that do not exist,
and every one of them gets the identical definition below.

The definition, and why the default is one
-------------------------------------------

``entity_version integer NOT NULL DEFAULT 1``. ``NOT NULL`` because a versioned
entity is never *without* a version; the default of ``1`` (not ``0``) means an
entity is at version 1 the moment it is created, so the first successful
modification takes it to 2 and the count of committed modifications is
``entity_version - 1``. Integer rather than bigint: a single entity is not
modified two billion times, and the event log — which records
``entity_version_after`` as ``Integer`` — already assumes this width.

How the increment happens (task 4.2, recorded here so the semantics are complete)
---------------------------------------------------------------------------------

This mixin declares the column; it does not increment it. The increment is a
conditional compare-and-set issued by :class:`VersionedRepository` (§7.1, task
4.2):

    UPDATE <entity> SET ..., entity_version = entity_version + 1
     WHERE id = :id AND entity_version = :expected

The ``WHERE entity_version = :expected`` is what makes the increment happen "when
and only when the modification commits": a request presenting a stale version
matches zero rows, so the version is not touched and no event is appended (R29.5).
Two requests presenting the same version race on the row lock, and PostgreSQL's
re-evaluation of the predicate under ``READ COMMITTED`` lets exactly one through
(R29.6). None of that works without the column, which is why it is declared before
the repository and before the first entity that uses it.

Placement
---------

This is plumbing, so it lives under ``app/db/`` beside the repository that drives
it (``versioned_repository.py``, task 4.2) rather than under ``app/models/``.
:class:`Versioned` is *not* a mapped table — it has no ``__tablename__`` and does
not inherit :class:`~app.db.base.Base` — so it does not register anything on
``Base.metadata`` and does not fall under the "tables are declared only under
app/models/" rule (``app/db/base.py``). It only contributes a column to the mapped
classes that inherit it, and those classes live under ``app/models/`` and are
picked up by the metadata walk exactly as any other model.
"""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import Integer, text
from sqlalchemy.orm import Mapped, mapped_column

__all__ = ["Versioned"]


class Versioned:
    """Declarative mixin contributing ``entity_version`` to a mapped entity (§7).

    Inherit alongside :class:`~app.db.base.Base` on any entity R29.1 names::

        class AcquisitionCase(Base, Versioned):
            __tablename__ = "acquisition_case"
            id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
            ...

    and the table gains ``entity_version integer NOT NULL DEFAULT 1``.
    :class:`VersionedRepository` (task 4.2) is the only writer permitted to change
    it, via the conditional UPDATE described in the module docstring.
    """

    #: The version a freshly created entity holds. Used as the column's server
    #: default so the DDL default and the value callers reason about have one
    #: source. ``entity_version - INITIAL_VERSION`` is the number of committed
    #: modifications the entity has seen.
    INITIAL_VERSION: ClassVar[int] = 1

    entity_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text(str(INITIAL_VERSION)),
        comment=(
            "Optimistic concurrency version (§7, R29.1). Starts at 1 and is "
            "incremented by exactly one by VersionedRepository's conditional "
            "UPDATE on every committed modification; a stale-version write matches "
            "no row and leaves it unchanged (Property 67)."
        ),
    )
