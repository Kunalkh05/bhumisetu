"""``notice_parcel`` — which parcels a statutory notice covers (§6.1).

A pure join between :class:`~app.models.statutory_notice.StatutoryNotice` and
:class:`~app.models.land_parcel.LandParcel`. One notice covers many parcels, and a
parcel is covered by many notices over the life of a case, so the relationship is
many-to-many and this is its association table — the exact shape of
:class:`~app.models.case_parcel.CaseParcel`.

Not a versioned entity
----------------------

``notice_parcel`` is not on R29.1's list, so it does **not** inherit
:class:`~app.db.versioned.Versioned` and has no ``entity_version``. There is
nothing on the row to *edit* under a concurrent writer — a membership either
exists or it does not. Adding a parcel to a notice is an INSERT and removing it a
DELETE; optimistic concurrency arbitrates edits to a row's attributes, and this
row has none beyond its own identity. The notice and the parcel it links are each
versioned in their own right.

The composite primary key is the whole row
-------------------------------------------

``(notice_id, parcel_id)`` is the primary key, so the same parcel cannot be linked
to the same notice twice and the membership is naturally idempotent. Both columns
reference their parent with ``RESTRICT``: a notice or parcel with live links
cannot be deleted from under them, matching every other reference in the schema.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["NoticeParcel"]


class NoticeParcel(Base):
    """The association of a statutory notice with a parcel it covers."""

    __tablename__ = "notice_parcel"

    notice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("statutory_notice.id", ondelete="RESTRICT"),
        primary_key=True,
        comment="The covering notice. RESTRICT: a notice with parcel links cannot "
        "be deleted from under them.",
    )
    parcel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("land_parcel.id", ondelete="RESTRICT"),
        primary_key=True,
        comment="The covered parcel. RESTRICT: a parcel with notice links cannot "
        "be deleted from under them.",
    )

    __table_args__ = (
        {
            "comment": (
                "Which parcels a notice covers (§6.1). A pure join, so not "
                "versioned and no entity_version."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<NoticeParcel notice={self.notice_id} parcel={self.parcel_id}>"
