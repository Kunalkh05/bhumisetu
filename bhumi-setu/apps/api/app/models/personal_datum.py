"""``personal_datum`` — how erasure coexists with an append-only log (§5.4).

The conflict this resolves
-------------------------

R4.2 forbids updating or deleting a stored event. R32.13 requires the log to stop
returning an erased value in *any* event payload, while still returning every event
with its actor, entity, both timestamps and ordering unchanged. Taken literally
those cannot both hold if a payload contains the value.

The route taken: **event payloads never store a personal-data value inline.** They
store a reference. A payload that would have carried ``{"owner_name": "…"}`` carries
``{"owner_name": {"$pd": 91827}}``, and erasure nulls the referent. No event row is
ever touched, so ordering, actor and timestamps come straight from the untouched
rows and R32.13's invariance clause holds by construction.

Non-personal attributes stay inline: ``{"share": {"from": 0.5, "to": 0.34}}``. The
indirection is a cost, so it is paid only where it buys something.

Something has to be mutable, and it is this
-------------------------------------------

That is the honest tradeoff. The mutation surface is deliberately one narrow table
with exactly one permitted transition — ``value_ciphertext`` to NULL and
``erased_at`` to a timestamp, once, irreversibly — enforced by a trigger that
rejects every other update. Compare the alternative: a mutation surface spread
across every event type's payload shape, forever.

The trigger is what makes the claim true rather than aspirational. Without it,
"personal_datum is mutable but only in one specific way" is a comment.

Two rejected alternatives, recorded because they look better than they are
-------------------------------------------------------------------------

**A tombstone consulted on read, over inline payloads.** Correctness would depend on
maintaining a registry of which JSON paths in which event types hold which
attributes, forever. A new event type with a new payload shape leaks by default —
silent, and worsening as the codebase grows.

**Crypto-shredding as the primary mechanism** (per-subject key, discard the key).
Payloads could stay inline. Rejected because Q10 requires *per-category* erasure with
different periods, so it needs a key per (subject, category) and key lifecycle
becomes the dominant complexity; and because whether retained ciphertext constitutes
erasure is a legal question this design cannot settle. ``value_ciphertext`` is
nonetheless encrypted with a per-category key as defence in depth, so the mechanism
is available if Q10's confirmation demands it.

Entity tables keep plain columns
--------------------------------

``ownership_record.owner_name`` will be ``text``, not a reference. Erasure there is an
ordinary ``UPDATE ... SET owner_name = NULL``, which is fine because entity rows are
mutable by design. This indirection exists solely because event rows are not. So
erasure has two arms — generated ``UPDATE``s over entity columns, and these rows —
both driven from the one registry in task 25.2.

The constraint this places on feature engineering
-------------------------------------------------

The Feature_Builder replays events. If any feature derived from a personal-data
attribute, erasure would silently change historical feature rows and break R17.5's
determinism. So **no feature may derive from a personal-data-classified attribute** —
owner count is allowed, owner names are not. Task 3.3 enforces it by intersecting the
feature registry against the category registry.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

__all__ = ["PersonalDatum"]


class PersonalDatum(Base):
    """One personal-data value, referenced from event payloads and erasable."""

    __tablename__ = "personal_datum"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    data_category: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "OWNER_CONTACT, OWNER_IDENTITY, MODEL_FEATURE. Text rather than an enum "
            "because Q10 has not confirmed the category set and §4.4 forbids making "
            "a vocabulary change a migration."
        ),
    )

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attribute_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "The (entity_type, entity_id, attribute_name) triple is what the "
            "retention sweep erases by, driven from CATEGORY_MAP in task 25.2."
        ),
    )

    value_ciphertext: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
        comment=(
            "NULL once erased. Encrypted with a per-category key as defence in "
            "depth, which keeps crypto-shredding available if Q10's confirmation "
            "requires it (§5.4)."
        ),
    )
    key_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment=(
            "Which encryption key encrypted this value. Needed so a key rotation "
            "does not make older rows unreadable, and so a discarded key is "
            "identifiable if crypto-shredding is ever adopted."
        ),
    )

    erased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Set once, irreversibly, by the retention sweep. The read-time resolver "
            "returns {'$erased': {...}} using this and data_category (R32.13)."
        ),
    )
    erasure_event_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("event.id", ondelete="RESTRICT"),
        nullable=True,
        comment=(
            "R32.12: the compensating PERSONAL_DATA_ERASED event. RESTRICT because "
            "an erasure whose event was removed would be unattributable."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # The retention sweep and the entity-arm erasure both look up by target.
        Index("personal_datum_target", entity_type, entity_id, attribute_name),
        # Partial: the sweep only ever scans rows not yet erased, so the index
        # shrinks as data ages out rather than growing forever.
        Index(
            "personal_datum_category",
            data_category,
            postgresql_where=erased_at.is_(None),
        ),
        {
            "comment": (
                "Personal-data values referenced from event payloads (§5.4). The "
                "only mutable thing in the log's read path, with exactly one "
                "permitted transition, enforced by trigger."
            )
        },
    )

    @property
    def is_erased(self) -> bool:
        return self.erased_at is not None

    def __repr__(self) -> str:
        state = "erased" if self.is_erased else "present"
        return (
            f"<PersonalDatum {self.id} {self.data_category} "
            f"{self.entity_type}:{self.entity_id}.{self.attribute_name} {state}>"
        )
