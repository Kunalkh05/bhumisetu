"""``notice_service_record`` — where and how a notice was served (§6.1, R7.5, R15.2).

A Notice_Service_Record captures one service of a
:class:`~app.models.statutory_notice.StatutoryNotice` on one interested person: the
service date, the service mode, the recipient's
:class:`~app.models.ownership_record.OwnershipRecord`, and — where captured — the
point on the ground where service happened.

Versioned, because a service record is corrected
------------------------------------------------

``notice_service_record`` is on R29.1's list (the design adds it to R29.1's ten,
§3.7), so it inherits :class:`~app.db.versioned.Versioned` and carries
``entity_version integer NOT NULL DEFAULT 1``. A correction to a recorded service
competes with any other officer's edit, and :class:`VersionedRepository` (§7)
arbitrates it.

service_location is a point, and why it is raw SQL in the migration
-------------------------------------------------------------------

``service_location`` is a ``geometry(Point, 4326)`` — R15.2 admits point
geometries for service locations, in SRID 4326 (WGS 84), the one frame used
platform-wide (§12). It is nullable: a service can be recorded before its location
is captured, and not every service mode has a meaningful point (a newspaper
publication has none). ``notice_service_location_gist`` is the GiST index that
makes the bbox and proximity queries of §12/§15 an index scan.

Both the column and its index are created by migration 0008 with raw SQL, exactly
as ``project.geom`` is in 0006 and ``land_parcel.geom`` is in 0007: SQLAlchemy has
no native PostGIS type and a frozen migration must not import
:mod:`app.db.column_types`. This model names the column with
:class:`~app.db.column_types.Geometry` and declares the GiST ``Index`` so
``Base.metadata`` stays a faithful picture of the table for the schema-guard walk
(task 2.7).

The dates are plain and undefaulted
-----------------------------------

``service_date`` is a plain date the service supplies; it carries no
``server_default``, because a computed default on a date column is exactly the
buried period task 2.7's guard catches. The deadline that a service is measured
against lives frozen on the notice (``response_deadline``), not here.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.column_types import Geometry
from app.db.versioned import Versioned

__all__ = ["NoticeServiceRecord"]


class NoticeServiceRecord(Base, Versioned):
    """One recorded service of a statutory notice on an interested person."""

    __tablename__ = "notice_service_record"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    notice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("statutory_notice.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The notice that was served. RESTRICT: a notice with service "
        "records cannot be deleted from under them.",
    )
    ownership_record_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ownership_record.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The interested person served, as an ownership record (R7.5). "
        "RESTRICT: a served record cannot be deleted from under the service.",
    )

    service_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="The date service was effected (R7.5). A plain date the service "
        "supplies; no computed default (task 2.7).",
    )
    service_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="How the notice was served (in person, post, publication). Text, "
        "not an enum: an open vocabulary (§4.4).",
    )

    service_location: Mapped[str | None] = mapped_column(
        Geometry("Point", 4326),
        nullable=True,
        comment=(
            "Where service happened, as a Point in SRID 4326 (R15.2). Nullable: "
            "captured after the fact or absent for a mode with no point (e.g. "
            "publication). Added by migration 0008 with raw SQL; see the module "
            "docstring."
        ),
    )

    __table_args__ = (
        # GiST over the point for the bbox and proximity queries of §12/§15. The
        # index is created by the migration's raw SQL; declared here so the
        # metadata picture matches the table.
        Index(
            "notice_service_location_gist",
            service_location,
            postgresql_using="gist",
        ),
        {
            "comment": (
                "Where and how a notice was served on an interested person (§6.1, "
                "R7.5). Versioned (R29.1)."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<NoticeServiceRecord {self.id} notice={self.notice_id} "
            f"owner_record={self.ownership_record_id} served={self.service_date} "
            f"v={self.entity_version}>"
        )
