"""``ownership_record`` — who owns a parcel, and when (§6.1).

An Ownership_Record is one owner's interest in one parcel over a validity period.
A parcel's ownership changes over time — a sale, an inheritance, a partition — and
the platform keeps every record rather than overwriting, so ownership as of any
past date is answerable (R6.8). Supersession sets ``valid_to`` on the old record
and inserts a new one; nothing is deleted (task 9.2).

Versioned, because a record is corrected
----------------------------------------

``ownership_record`` is on R29.1's list, so it inherits
:class:`~app.db.versioned.Versioned` and carries ``entity_version integer NOT
NULL DEFAULT 1``. A correction to an owner's share or contact competes with any
other officer's edit, and :class:`VersionedRepository` (§7) arbitrates it.

The validity range is generated, with inclusive bounds
------------------------------------------------------

``validity`` is ``daterange(valid_from, valid_to, '[]')`` computed by the database
from the two date columns. The inclusive-on-both-ends ``'[]'`` bound is the point:
a NULL ``valid_to`` yields an unbounded upper bound, so a still-current record is
an unbounded range and the as-of query (task 9.3) is a plain ``validity @> :d``
with no ``COALESCE`` and no ``OR valid_to IS NULL``. The migration adds the column
with raw SQL (a ``daterange`` generation expression has no SQLAlchemy spelling, and
a frozen migration must not import :mod:`app.db.column_types`); it is named here
with ``Computed`` so the metadata walk (task 2.7) sees the real column.

The GiST index exists; the exclusion constraint does not
--------------------------------------------------------

``ownership_validity_gist`` is a GiST index over ``(parcel_id, validity)`` — it
answers the as-of query and backs the R13.5 overlap-detection query. It is
deliberately **not** promoted to an exclusion constraint on ``(parcel_id,
owner_identity_key, validity)``, though the index makes one available (§6.1). R13.5
requires an overlapping same-owner validity period to raise a ``BLOCKING``
Validation_Issue, not to be rejected by the database; an exclusion constraint
would reject the write instead, contradicting the requirement and breaking the
bulk import's partial-commit semantics (a batch commits the good rows and reports
the bad rather than aborting on the first overlap). Because the index is over a
``bigint`` alongside the range, migration 0007 installs ``btree_gist``.

Erasable personal data, and the retained hash
----------------------------------------------

``owner_name``, ``government_identifier``, ``owner_identity_key``,
``contact_mobile`` and ``contact_mobile_hash`` are personal data (``CATEGORY_MAP``,
§5.4) and erasable — erasure there is an ordinary ``UPDATE ... SET owner_name =
NULL`` because entity rows are mutable by design, unlike event rows. The retained
land-record fields keep the legal interest intact; OTP lookup stops working after
the contact retention period lapses, which is the explicit Q10 default.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import DATERANGE
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["OwnershipRecord"]


class OwnershipRecord(Base, Versioned):
    """One owner's interest in a parcel over a validity period."""

    __tablename__ = "ownership_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    parcel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("land_parcel.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The parcel this interest is in. RESTRICT: a parcel with ownership "
        "records cannot be deleted from under them.",
    )

    owner_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="OWNER_IDENTITY, erasable. NULL once erased (§5.4).",
    )
    owner_identity_key: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Normalised match key for R13.5 duplicate detection — the "
        "same-owner test the overlap rule keys on.",
    )
    government_identifier: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="OWNER_IDENTITY, erasable, masked on output (§8.2).",
    )
    contact_mobile: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="OWNER_CONTACT, erasable. NULL once erased.",
    )
    contact_mobile_hash: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
        comment=(
            "OWNER_CONTACT, erasable with contact_mobile. After erasure citizen "
            "OTP lookup no longer resolves by this owner hash."
        ),
    )

    interest_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The kind of interest (owner, tenant, mortgagee). Text, not an "
        "enum: an open vocabulary (§4.4).",
    )
    share: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        comment="The ownership fraction. Concurrently valid shares for a parcel "
        "must sum to 1 within tolerance (R6.5), checked by validation (task 13).",
    )

    valid_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Start of the validity period. A plain date the service supplies; "
        "no computed default (task 2.7).",
    )
    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="End of the validity period, set on supersession (R6.7). NULL for a "
        "still-current record, which validity turns into an unbounded upper bound.",
    )
    validity: Mapped[object | None] = mapped_column(
        DATERANGE,
        Computed("daterange(valid_from, valid_to, '[]')", persisted=True),
        nullable=True,
        comment=(
            "Database-generated daterange with inclusive '[]' bounds, so an open "
            "valid_to is unbounded and the as-of query (task 9.3) is a plain "
            "validity @> :d. Added by migration 0007 with raw SQL; backed by "
            "ownership_validity_gist."
        ),
    )

    __table_args__ = (
        # GiST over (parcel_id, validity) for the as-of query and the R13.5 overlap
        # scan. Created by the migration's raw SQL (needs btree_gist for the bigint
        # component); declared here so the metadata picture matches the table.
        # NOT an exclusion constraint, by §6.1 — see the module docstring.
        Index(
            "ownership_validity_gist",
            parcel_id,
            validity,
            postgresql_using="gist",
        ),
        # Plain btree on the retained hash for OTP lookup after contact erasure.
        Index("ownership_mobile_hash", contact_mobile_hash),
        {
            "comment": (
                "An owner's interest in a parcel over a validity period (§6.1). "
                "Versioned (R29.1); owner_name, government_identifier and "
                "contact_mobile are erasable personal data."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<OwnershipRecord {self.id} parcel={self.parcel_id} "
            f"share={self.share} [{self.valid_from}..{self.valid_to or ''}] "
            f"v={self.entity_version}>"
        )
