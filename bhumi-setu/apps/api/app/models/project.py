"""``project`` — the undertaking land is acquired for (§6.1).

A Project is the government undertaking (a road, a canal, a plant) whose land
requirement one or more Acquisition_Cases satisfy. It carries the sanctioned
extent and the project boundary; the case is where the acquisition lifecycle
actually happens.

Not a versioned entity
----------------------

R29.1 lists the eleven entities that carry optimistic concurrency, and
``project`` is not among them — so it does **not** inherit
:class:`~app.db.versioned.Versioned` and has no ``entity_version`` column. That is
deliberate rather than an omission: a project is reference data set up once at the
top of an undertaking, not a record two officers race to edit mid-flight, which is
what the version column exists to arbitrate (§7). ``acquisition_case``, which
*is* raced on stage transitions, is versioned; ``project`` is not.

``area_code`` is the project's seat in the hierarchy
----------------------------------------------------

``area_code`` references :class:`~app.models.jurisdiction.AdministrativeArea`, so
a project sits at one administrative node and its cases' scope checks resolve
through the ltree hierarchy from there (§8.1). ``RESTRICT`` on delete matches
every other area reference in the schema: an administrative area with projects
hanging off it cannot be deleted out from under them.

``geom`` is nullable, and simplified geometry is a query-time concern
---------------------------------------------------------------------

The project boundary is a ``MultiPolygon`` in SRID 4326 (WGS 84), the one frame
used platform-wide (§12). It is nullable because a project may be recorded before
its boundary is digitised. The GiST index answers the bbox-intersection queries
of §12; the transfer-budget simplification R15.8 needs is applied when geometry is
*served*, not stored, so the column holds full-fidelity geometry.

The column and its index are added by migration 0006 with raw SQL, exactly as
``administrative_area.path`` is in migration 0001: SQLAlchemy has no native
geometry type, and a frozen migration must not import
:mod:`app.db.column_types`. This model names the column with
:class:`~app.db.column_types.Geometry` so ``Base.metadata`` stays a faithful
picture of the table for the schema-guard walk (task 2.7).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.column_types import Geometry

__all__ = ["Project"]


class Project(Base):
    """A government undertaking for which land is acquired."""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(Text, nullable=False)

    implementing_authority: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The body executing the undertaking, e.g. the PWD or NHAI.",
    )

    area_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "The project's seat in the administrative hierarchy. Scope checks on "
            "its cases resolve through the ltree path from here (§8.1). RESTRICT: "
            "an area with projects cannot be deleted from under them."
        ),
    )

    purpose_category: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The acquisition purpose class. Text rather than an enum: the "
            "category set is an open vocabulary and onboarding a state must not be "
            "a migration (§4.4)."
        ),
    )

    sanctioned_extent: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="The total land area sanctioned for the undertaking.",
    )
    extent_unit: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The unit sanctioned_extent is expressed in (hectare, acre). Stored "
            "beside the value so a figure is never divorced from its unit."
        ),
    )

    geom: Mapped[str | None] = mapped_column(
        Geometry("MultiPolygon", 4326),
        nullable=True,
        comment=(
            "Project boundary as a MultiPolygon in SRID 4326. Nullable: a project "
            "may be recorded before its boundary is digitised. Added by migration "
            "0006 with raw SQL; see the module docstring."
        ),
    )

    __table_args__ = (
        # GiST is what makes the bbox-intersection queries of §12 an index scan.
        # The index is created by the migration's raw SQL; declared here so the
        # metadata picture matches the table.
        Index("project_geom_gist", geom, postgresql_using="gist"),
        {
            "comment": (
                "A government undertaking land is acquired for (§6.1). Its cases "
                "hold the acquisition lifecycle; it holds the sanctioned extent "
                "and boundary."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<Project {self.id} {self.name!r} area={self.area_code}>"
