"""The administrative hierarchy that jurisdiction scope is expressed over.

R2.1: a role's jurisdiction scope is *a set of administrative areas*. R2.2: a
case list is restricted to cases whose area falls **within** that scope. "Within"
is the whole difficulty — an officer scoped to a district covers every tehsil and
village beneath it, and those descendants are not listed anywhere.

Shape
-----

``code`` is the primary key rather than a surrogate id. Administrative codes are
externally assigned, stable, and appear in the government records this platform
ingests; a surrogate would add a join to every scope check and an
import-time lookup to every parcel row for no gain.

``path`` is the same hierarchy as ``parent_code``, materialised for the index.
Two representations of one fact is a correctness risk, so **the application never
writes it**: migration 0001 installs a trigger that derives ``path`` from the
parent's ``path``, and derives ``state_key`` the same way. A caller supplying
either gets it overwritten. The alternative — trusting every insert path,
including the bulk import of task 26 — has no failure mode that surfaces early.

Why ``state_key`` is denormalised onto every row
------------------------------------------------

Every ``Policy_Config`` lookup is keyed by state (§4.1), and policy is resolved
constantly: a stage deadline, an OCR threshold, a risk band cutoff. Walking to
the root of the hierarchy to discover which state a village is in, on each of
those, is a recursive query in the hot path. It is denormalised, and the trigger
is what keeps it honest.

``area_type`` is text, not an enum
----------------------------------

India's administrative levels are not uniform: some states have divisions between
state and district, some have blocks rather than tehsils, and a few have neither.
An enum would make onboarding a state a migration, which is the thing §4.4 exists
to avoid. The trigger enforces the structural rule that actually matters — a
non-root area has a parent, and its path extends the parent's — and leaves the
vocabulary to configuration.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.column_types import Ltree

__all__ = ["AdministrativeArea"]


class AdministrativeArea(Base):
    """One node of the administrative hierarchy: a state, district, tehsil, village."""

    __tablename__ = "administrative_area"

    code: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Authoritative government code. Not transliterated; see path.",
    )

    area_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment=(
            "state | division | district | subdivision | tehsil | block | "
            "village. Text rather than an enum: administrative levels are not "
            "uniform across states and onboarding one must not need a migration."
        ),
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment=(
            "Display name in the source script, stored without normalisation "
            "(R27.5: a value read back equals the value written)."
        ),
    )

    parent_code: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        nullable=True,
        comment="NULL only for a root area. RESTRICT: deleting a parent that "
        "still has children would orphan every descendant path.",
    )

    state_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment=(
            "Policy_Config state key (§4.1). Denormalised from the root because "
            "policy is resolved on nearly every request and walking to the root "
            "each time would put a recursive query in the hot path. Maintained "
            "by trigger, never by the application."
        ),
    )

    path: Mapped[str] = mapped_column(
        Ltree,
        nullable=False,
        comment=(
            "Materialised ancestry over transliterated codes, for the <@ "
            "containment test in scoped() (§8.1). Derived by trigger from the "
            "parent's path; a supplied value is overwritten."
        ),
    )

    parent: Mapped[AdministrativeArea | None] = relationship(
        "AdministrativeArea",
        remote_side=[code],
        back_populates="children",
    )
    children: Mapped[list[AdministrativeArea]] = relationship(
        "AdministrativeArea",
        back_populates="parent",
        cascade="save-update",
    )

    __table_args__ = (
        # GiST is what makes `path <@ scope` an index scan rather than a filter.
        # Without it every scoped list query in the platform degrades to a scan
        # of the whole area table per candidate row.
        Index("administrative_area_path_gist", path, postgresql_using="gist"),
        # Ancestor lookups and the trigger's parent read.
        Index("administrative_area_parent", parent_code),
        # Every Policy_Config resolution filters by state.
        Index("administrative_area_state", state_key),
        CheckConstraint(
            "parent_code IS NULL OR parent_code <> code",
            name="area_not_its_own_parent",
        ),
        # A root area is where state_key originates, so it must name itself.
        # Without this a mis-seeded root silently gives every descendant the
        # wrong policy state, which surfaces as a wrong statutory deadline.
        CheckConstraint(
            "parent_code IS NOT NULL OR area_type = 'state'",
            name="root_area_is_a_state",
        ),
        {
            "comment": (
                "Administrative hierarchy. Jurisdiction scope (R2.1) is a set of "
                "rows here; scope containment (R2.2) is path <@ scope_path."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<AdministrativeArea {self.code} {self.area_type} path={self.path}>"
