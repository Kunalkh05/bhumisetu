"""``statutory_notice`` — a statutory notice issued on a case (§6.1, §7.8).

A Statutory_Notice is a formal notification issued on an Acquisition_Case (a
preliminary notification, a declaration, an award notice). Each notice covers a
set of Land_Parcels through ``notice_parcel`` and is served on interested persons,
each service recorded in ``notice_service_record``.

Versioned, because a notice is corrected
----------------------------------------

``statutory_notice`` is on R29.1's list, so it inherits
:class:`~app.db.versioned.Versioned` and carries ``entity_version integer NOT
NULL DEFAULT 1``. A correction to a notice competes with any other officer's edit,
and :class:`VersionedRepository` (§7) arbitrates it.

response_deadline is frozen at issue, which is R7.8 (§7.8)
----------------------------------------------------------

``response_deadline`` is a plain stored ``date`` the Notice_Service writes when the
notice is issued (task 10.2), computed as ``issue_date`` advanced by the
Policy_Config response period effective *on the issue date* (R7.4, R28.6). It is
**not** derived on read and carries **no** computed default: R7.8 requires a later
change to that period to leave already-issued notices untouched, and the only way
to guarantee that structurally is to freeze the resolved date rather than recompute
it. A ``server_default`` here would also be a statutory period buried in DDL, which
task 2.7's guard fails the build on — there is deliberately none.

``policy_snapshot_hash`` records the content hash of the
:class:`~app.services.policy.PolicySnapshot` (§4.2) that produced the deadline, so
a stored date is attributable to the exact configuration state it came from. It is
``NOT NULL``: a frozen deadline with unknown provenance is not attributable, so a
notice never exists without one. The value is supplied at issue; it is not derived
in DDL.

``breach_state`` starts ``'WITHIN'`` and is advanced by the deadline sweep (task
10.3). It is a text state, not date arithmetic, so its default is permitted by the
schema guard.

The geometry lives on notice_service_record, not here
-----------------------------------------------------

A notice itself has no location; a *service* of it does (R15.2). The point
geometry is therefore on :class:`~app.models.notice_service_record.NoticeServiceRecord`.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.versioned import Versioned

__all__ = ["StatutoryNotice"]


class StatutoryNotice(Base, Versioned):
    """A statutory notice issued on an acquisition case."""

    __tablename__ = "statutory_notice"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    case_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("acquisition_case.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The case the notice is issued on. RESTRICT: a case with notices "
        "cannot be deleted from under them.",
    )

    notice_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The kind of notice (preliminary notification, declaration, award "
        "notice). Text, not an enum: an open vocabulary (§4.4).",
    )
    issuing_authority: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The authority that issued the notice (R7.3).",
    )
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="The date the notice was issued (R7.3). The response period "
        "resolves as of this date, not today. No computed default (task 2.7).",
    )
    publication_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="How the notice was published (R7.3). Text, not an enum (§4.4).",
    )

    response_deadline: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "The response deadline, FROZEN at issue (R7.8): issue_date advanced by "
            "the response period effective on the issue date, stored so a later "
            "change to that period leaves this notice unchanged. A stored date, "
            "never a computed default (task 2.7)."
        ),
    )
    policy_snapshot_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The PolicySnapshot content hash (§4.2) of the configuration that "
            "produced response_deadline, so the frozen date is attributable to its "
            "policy state. NOT NULL: no notice without provenance."
        ),
    )

    breach_state: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'WITHIN'"),
        comment=(
            "Deadline state advanced by the deadline sweep (task 10.3). A text "
            "state, not date arithmetic — the guard permits its default."
        ),
    )

    __table_args__ = (
        {
            "comment": (
                "A statutory notice issued on a case (§6.1). Versioned (R29.1); "
                "response_deadline is frozen at issue and policy_snapshot_hash "
                "records the configuration that produced it (R7.8)."
            )
        },
    )

    def __repr__(self) -> str:
        return (
            f"<StatutoryNotice {self.id} case={self.case_id} "
            f"type={self.notice_type} issued={self.issue_date} "
            f"deadline={self.response_deadline} v={self.entity_version}>"
        )
