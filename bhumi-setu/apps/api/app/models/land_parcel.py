"""``land_parcel`` — a cadastral parcel and its identity (§6.1).

A Land_Parcel is the unit of land an acquisition acts on: it carries the
six-column cadastral identity, the recorded extent, and the boundary geometry. A
case acquires a set of parcels through ``case_parcel``, and each parcel's owners
over time live in ``ownership_record``.

Versioned, because a parcel is edited
-------------------------------------

``land_parcel`` is on R29.1's list, so it inherits
:class:`~app.db.versioned.Versioned` and carries ``entity_version integer NOT
NULL DEFAULT 1``. Two officers correcting the same parcel's extent or geometry
must not silently overwrite one another; :class:`VersionedRepository` (§7)
arbitrates that, and this model owns the columns it reads and writes.

The six-column identity and one unique index
--------------------------------------------

``state_key``, ``district``, ``tehsil``, ``village``, ``survey_number`` and
``sub_division`` are the identity R6.1 records and R6.2 treats as unique.
``parcel_identity`` is that uniqueness, and it is over ``coalesce(sub_division,
'')`` rather than ``sub_division`` directly: a plain unique index treats every
NULL as distinct, so a parcel with a NULL sub-division and one with ``''`` would
both be admitted for otherwise identical identities. Folding NULL to ``''`` makes
the "same parcel" test total, which is what lets one index serve R6.2 (uniqueness),
R6.3 (the rejection returns the matching identifier — task 9.2) and R30.9 (import
duplicate detection).

village_norm is for matching only, never for display
----------------------------------------------------

``village_norm`` is ``village`` run through ``normalize(village, NFC)`` so the
duplicate scan (R30.9) and the R13.5 detection query compare canonical Unicode
rather than tripping over two byte sequences that render identically. It is
**never displayed or exported** — the authoritative ``village`` is what a record
shows. It is a database-generated column: the migration adds it with raw SQL
(``normalize(...)`` has no SQLAlchemy spelling and a frozen migration must not
import :mod:`app.db.column_types`), and it is named here with ``Computed`` so the
metadata walk (task 2.7) sees the real column. ``parcel_dup_scan`` indexes it.

geom, and why it is raw SQL in the migration
--------------------------------------------

``geom`` is the parcel boundary as a ``MultiPolygon`` in SRID 4326 (WGS 84), the
one frame used platform-wide (§12), nullable because a parcel may be recorded
before its boundary is digitised. ``parcel_geom_gist`` answers the bbox queries of
§12/§15. Both the column and its index are created by migration 0007 with raw SQL,
exactly as ``project.geom`` is in 0006 and ``administrative_area.path`` is in 0001;
this model names them with :class:`~app.db.column_types.Geometry` and a GiST
``Index`` so ``Base.metadata`` stays a faithful picture of the table.

``geodesic_area_sqm`` is the computed area of ``geom`` on the ellipsoid, stored so
a discrepancy against the recorded ``extent`` can be surfaced without recomputing
on every read; it is nullable for the same reason ``geom`` is.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.column_types import Geometry
from app.db.versioned import Versioned

__all__ = ["LandParcel"]


class LandParcel(Base, Versioned):
    """A cadastral parcel: identity, extent and boundary geometry."""

    __tablename__ = "land_parcel"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # --- the six-column cadastral identity (R6.1, R6.2) ------------------------
    state_key: Mapped[str] = mapped_column(Text, nullable=False)
    district: Mapped[str] = mapped_column(Text, nullable=False)
    tehsil: Mapped[str] = mapped_column(Text, nullable=False)
    village: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The authoritative village name — what a record displays and "
        "exports. Matching uses village_norm, never this.",
    )
    survey_number: Mapped[str] = mapped_column(Text, nullable=False)
    sub_division: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional sixth identity component. parcel_identity folds a NULL to "
        "'' so a missing sub-division still collides with an empty one.",
    )

    village_norm: Mapped[str | None] = mapped_column(
        Text,
        Computed("normalize(village, NFC)", persisted=True),
        nullable=True,
        comment=(
            "NFC-folded village for matching only (R30.9, R13.5) — never displayed "
            "or exported. Database-generated; the migration adds it with raw SQL "
            "and parcel_dup_scan indexes it."
        ),
    )

    classification: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Land classification (e.g. agricultural, residential). Text, not an "
        "enum: an open vocabulary (§4.4).",
    )

    extent: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        comment="The recorded parcel area (R6.1). Paired with extent_unit so a "
        "figure is never divorced from its unit.",
    )
    extent_unit: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The unit extent is expressed in (hectare, acre).",
    )

    area_code: Mapped[str] = mapped_column(
        Text,
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=False,
        comment=(
            "The parcel's seat in the administrative hierarchy; the bbox and "
            "scope queries of §12/§15 resolve through its ltree path. RESTRICT: an "
            "area with parcels cannot be deleted from under them."
        ),
    )

    geom: Mapped[str | None] = mapped_column(
        Geometry("MultiPolygon", 4326),
        nullable=True,
        comment=(
            "Parcel boundary as a MultiPolygon in SRID 4326. Nullable: recorded "
            "before digitisation. Added by migration 0007 with raw SQL; see the "
            "module docstring."
        ),
    )
    geodesic_area_sqm: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 4),
        nullable=True,
        comment="Ellipsoidal area of geom in square metres, stored so a mismatch "
        "against extent can be surfaced without recomputing on read.",
    )

    __table_args__ = (
        # One unique index for R6.2, R6.3 and R30.9. coalesce(sub_division, '')
        # makes the identity test total over a NULL sub-division. Expression index,
        # created by the migration's raw SQL; declared here so the metadata picture
        # matches the table.
        Index(
            "parcel_identity",
            state_key,
            district,
            tehsil,
            village,
            survey_number,
            text("coalesce(sub_division, '')"),
            unique=True,
        ),
        # GiST over geom for the bbox-intersection queries of §12/§15.
        Index("parcel_geom_gist", geom, postgresql_using="gist"),
        # The duplicate scan (R30.9) compares NFC-folded villages, so it indexes
        # village_norm rather than village.
        Index(
            "parcel_dup_scan",
            state_key,
            district,
            tehsil,
            village_norm,
            survey_number,
        ),
        {
            "comment": (
                "A cadastral parcel: the six-column identity, extent and geometry "
                "(§6.1). Versioned (R29.1)."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<LandParcel {self.id} {self.state_key}/{self.district}/{self.tehsil}/"
            f"{self.village}/{self.survey_number}"
            f"{('/' + self.sub_division) if self.sub_division else ''} "
            f"v={self.entity_version}>"
        )
