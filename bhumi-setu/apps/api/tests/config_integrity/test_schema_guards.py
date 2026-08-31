"""No statutory period may hide in the schema (R7.2, R28.6, §20.7).

The AST lint next door stops a period reaching ``timedelta``. A period can also
reach a *date* without going through Python arithmetic at all:

* ``server_default=text("now() + interval '30 days'")`` on a deadline column;
* ``CHECK (response_deadline <= issue_date + 30)`` on a notice table;
* an ``ENUM`` fixing the stage vocabulary, which makes onboarding a state a
  migration and defeats §4.4.

None of those pass through application code, so the lint cannot see them. These
guards walk the metadata and the live catalogue instead.

Metadata *and* catalogue, deliberately
--------------------------------------

Walking ``Base.metadata`` catches what the models declare. Walking ``pg_constraint``
catches what a migration executed as raw SQL — and migrations here do use raw SQL
for triggers, expression indexes and grants. A guard reading only the models would
have missed every constraint in migration 0001, which is exactly where the
constraint-naming bug came from.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import Connection, Date, DateTime, text

from app.db.base import all_metadata

#: A day count appearing in DDL.
#:
#: Both interval spellings are needed, and finding that out took a planted
#: violation. PostgreSQL does not store DDL as written — pg_get_constraintdef
#: normalises `interval '30 days'` to `'30 days'::interval`, moving the keyword
#: *after* the literal as a cast. A pattern matching only the written form passes
#: the guard's own unit tests (which use the written form) while missing every real
#: constraint in the catalogue, which is the worst possible combination.
DAY_COUNT_IN_DDL = re.compile(
    r"""
      interval \s* '[^']*\d+[^']*'       # interval '30 days'   (as written)
    | '[^']*\d+[^']*' \s* :: \s* interval # '30 days'::interval (as stored)
    | [+\-] \s* \d+ \s* (?: \) | $ | \s )   # date + 30       (date columns only)
    """,
    re.IGNORECASE | re.VERBOSE,
)

#: server_default values that are legitimate on a date column. now() records when
#: something was written, which is not a statutory period.
PERMITTED_DATE_DEFAULTS = frozenset({"now()", "current_timestamp", "clock_timestamp()"})


# ---------------------------------------------------------------------------
# Declared metadata
# ---------------------------------------------------------------------------


def test_metadata_is_not_empty() -> None:
    """Fail closed: an empty walk would make every guard below pass vacuously."""
    tables = all_metadata().tables
    assert tables, "Base.metadata is empty; the model import walk did not run"
    assert "policy_config" in tables


def test_no_date_column_carries_a_computed_default() -> None:
    """A deadline defaulted in DDL is a statutory period in the schema.

    ``now()`` is permitted because it records when a row was written. Anything with
    arithmetic in it is a period, and R28.6 requires periods to resolve from
    Policy_Config as of a statutory event date — which a column default cannot do,
    since it knows neither the state nor the act.
    """
    offences: list[str] = []
    for table in all_metadata().sorted_tables:
        for column in table.columns:
            if not isinstance(column.type, (Date, DateTime)):
                continue
            default = column.server_default
            if default is None:
                continue
            rendered = str(getattr(default, "arg", default)).strip().lower()
            if rendered not in PERMITTED_DATE_DEFAULTS:
                offences.append(f"{table.name}.{column.name} default={rendered!r}")
    assert not offences, (
        "A date column has a computed default. Statutory periods resolve from "
        f"Policy_Config, not from DDL (R7.2, R28.6). Offences: {offences}"
    )


def test_no_declared_check_constraint_contains_a_day_count() -> None:
    offences: list[str] = []
    for table in all_metadata().sorted_tables:
        for constraint in table.constraints:
            sqltext = getattr(constraint, "sqltext", None)
            if sqltext is None:
                continue
            rendered = str(sqltext)
            if DAY_COUNT_IN_DDL.search(rendered):
                offences.append(f"{table.name}.{constraint.name}: {rendered}")
    assert not offences, f"CHECK constraints containing a day count: {offences}"


# ---------------------------------------------------------------------------
# The live catalogue — catches raw SQL a migration executed
# ---------------------------------------------------------------------------


def test_no_live_check_constraint_contains_a_day_count(
    db_connection: Connection,
) -> None:
    """Reads pg_constraint, so a constraint created by raw SQL cannot hide.

    Migrations here legitimately use raw SQL for triggers, expression indexes and
    grants. A guard that only walked the models would have seen none of migration
    0001's constraints.
    """
    rows = db_connection.execute(
        text(
            """
            SELECT c.conname, t.relname, pg_get_constraintdef(c.oid) AS definition
              FROM pg_constraint c
              JOIN pg_class t ON t.oid = c.conrelid
              JOIN pg_namespace n ON n.oid = t.relnamespace
             WHERE c.contype = 'c' AND n.nspname = 'public'
            """
        )
    ).all()
    offences = [
        f"{row.relname}.{row.conname}: {row.definition}"
        for row in rows
        if DAY_COUNT_IN_DDL.search(row.definition)
    ]
    assert not offences, f"live CHECK constraints containing a day count: {offences}"


def test_no_live_date_column_carries_a_computed_default(
    db_connection: Connection,
) -> None:
    rows = db_connection.execute(
        text(
            """
            SELECT table_name, column_name, column_default
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND data_type IN ('date', 'timestamp with time zone',
                                 'timestamp without time zone')
               AND column_default IS NOT NULL
            """
        )
    ).all()
    offences = [
        f"{row.table_name}.{row.column_name} default={row.column_default!r}"
        for row in rows
        if row.column_default.strip().lower() not in PERMITTED_DATE_DEFAULTS
    ]
    assert not offences, f"live date columns with a computed default: {offences}"


def test_no_enum_type_fixes_a_domain_vocabulary(db_connection: Connection) -> None:
    """§4.4: onboarding a state must not be a migration.

    Stage keys, area types, provenance and actor type are all configuration or open
    vocabularies. An enum on any of them turns adding a value into a schema change,
    and adding a *state* into a schema change.
    """
    enums = db_connection.execute(
        text(
            """
            SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder)
                   AS labels
              FROM pg_type t
              JOIN pg_enum e ON e.enumtypid = t.oid
              JOIN pg_namespace n ON n.oid = t.typnamespace
             WHERE n.nspname = 'public'
             GROUP BY t.typname
            """
        )
    ).all()
    assert not enums, (
        "Enum types constrain a domain vocabulary in the schema. Stage sets, area "
        "types and provenance are configuration or open sets; an enum makes adding "
        f"a value a migration (§4.4). Found: {[(e.typname, e.labels) for e in enums]}"
    )


def test_no_constraint_or_index_mentions_stage_key(db_connection: Connection) -> None:
    """R7.2's stage-specific half, asserted before acquisition_case exists (task 8.1).

    Landing this now means the table cannot be created with a stage CHECK in the
    first place.
    """
    constraints = db_connection.scalars(
        text(
            """
            SELECT conname FROM pg_constraint
             WHERE contype = 'c' AND pg_get_constraintdef(oid) ILIKE '%stage_key%'
            """
        )
    ).all()
    assert not constraints, f"a CHECK constrains stage_key: {constraints}"


# ---------------------------------------------------------------------------
# The guards' own tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "definition",
    [
        "CHECK ((response_deadline <= (issue_date + 30)))",
        "CHECK ((expires_at < (now() + interval '15 days')))",
        # The normalised form PostgreSQL actually stores.
        "CHECK ((occurrence_time <= (recording_time + '30 days'::interval)))",
        "CHECK ((expires_at < (now() + '15 minutes'::interval)))",
        "CHECK ((deadline >= (entered_on + 365)))",
    ],
)
def test_the_day_count_pattern_rejects_a_period_in_ddl(definition: str) -> None:
    """Scope note: this targets a day count in *date arithmetic*, not every numeric
    bound in DDL.

    `CHECK (retention_days <= 1095)` is deliberately not matched. A bare numeric
    comparison cannot be universally rejected — `CHECK (confidence <= 1)` is
    legitimate and appears in task 16.1 — and a pattern flagging both is a pattern
    someone disables. What R7.2 forbids is deriving a legally significant *date*
    from an embedded period, which is the shape matched here.
    """
    assert DAY_COUNT_IN_DDL.search(definition), f"{definition!r} should be rejected"


@pytest.mark.parametrize(
    "definition",
    [
        "CHECK ((parent_code IS NULL OR (parent_code <> code)))",
        "CHECK ((parent_code IS NOT NULL OR (area_type = 'state'::text)))",
        "CHECK ((policy_key !~~ 'ocr.threshold.%'::text OR "
        "(justification_report_id IS NOT NULL)))",
        "CHECK ((confidence >= (0)::numeric AND confidence <= (1)::numeric))",
    ],
)
def test_the_day_count_pattern_allows_a_structural_constraint(definition: str) -> None:
    """The real constraints in migrations 0001 and 0002 must not trip the guard.

    A pattern that flags these is a pattern someone will disable, and a disabled
    guard protects nothing.
    """
    assert not DAY_COUNT_IN_DDL.search(definition), f"{definition!r} should be allowed"
