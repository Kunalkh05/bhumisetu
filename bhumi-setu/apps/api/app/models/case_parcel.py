"""``case_parcel`` — which parcels an acquisition case acquires (§6.1).

A pure join between :class:`~app.models.acquisition_case.AcquisitionCase` and
:class:`~app.models.land_parcel.LandParcel`. One case acquires many parcels, and a
parcel can in principle be touched by more than one case over time, so the
relationship is many-to-many and this is its association table.

Not a versioned entity
----------------------

``case_parcel`` is not on R29.1's list, so it does **not** inherit
:class:`~app.db.versioned.Versioned` and has no ``entity_version``. That is
correct rather than an omission: there is nothing on the row to *edit* under a
concurrent writer — a membership either exists or it does not. Adding a parcel to
a case is an INSERT and removing it is a DELETE; optimistic concurrency arbitrates
edits to a row's attributes, and this row has none beyond its own identity. The
two entities it links are each versioned in their own right.

The composite primary key is the whole row
-------------------------------------------

``(case_id, parcel_id)`` is the primary key, so the same parcel cannot be linked
to the same case twice and the membership is naturally idempotent. Both columns
reference their parent with ``RESTRICT``: a case or parcel with live links cannot
be deleted from under them, matching every other reference in the schema (nothing
in this platform is hard-deleted out from under a dependent — retention is erasure,
not deletion).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["CaseParcel"]


class CaseParcel(Base):
    """The association of a case with a parcel it acquires."""

    __tablename__ = "case_parcel"

    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        primary_key=True,
        comment="The acquiring case. RESTRICT: a case with parcel links cannot be "
        "deleted from under them.",
    )
    parcel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("land_parcel.id", ondelete="RESTRICT"),
        primary_key=True,
        comment="The acquired parcel. RESTRICT: a parcel with case links cannot be "
        "deleted from under them.",
    )

    __table_args__ = (
        {
            "comment": (
                "Which parcels a case acquires (§6.1). A pure join, so not "
                "versioned and no entity_version."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<CaseParcel case={self.case_id} parcel={self.parcel_id}>"
