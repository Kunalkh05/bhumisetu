"""Officers, roles, and the jurisdiction scope a role carries.

R2.1 in full: *assign every Officer at least one role and, for each role, a
jurisdiction scope expressed as a set of administrative areas.*

Scope hangs off the role, not the officer
-----------------------------------------

R2.1 says "for each role, a jurisdiction scope", so ``jurisdiction_scope`` keys on
``role_id``. An officer's effective scope is the union over their roles, which is
what ``scoped()`` (§8.1) builds its ``<@`` disjunction from.

The consequence is worth stating because it is easy to design past: the same job
title in two districts is two roles, not one role held by officers in two places.
That is deliberate. If scope hung off the officer, a role would carry permissions
with no territory and R2.2's restriction would have to be assembled from two
unrelated places on every request.

What is *not* enforced by a constraint
--------------------------------------

"At least one role" cannot be a table constraint. The officer row necessarily
exists before any ``officer_role`` row referencing it, so a NOT NULL or a CHECK
would make an officer impossible to create at all. Enforcing it with a deferred
constraint trigger was considered and rejected: it would fire on every officer
insert in every test fixture for a rule whose violation is inert — an officer with
no role has no permissions and no scope, so ``scoped()`` returns nothing and every
authorization check already fails closed.

So this is a service-layer invariant, asserted where officers are created
(task 5.6) and covered by Property 4's scope tests, not a schema guarantee. Said
plainly here because a reader who assumes the database enforces it would be wrong.

Permissions are a text array, validated later
---------------------------------------------

``role.permissions`` holds permission keys. Task 5.6 introduces the ``PERMISSIONS``
registry and the test that fails the build on a key absent from it; until then the
column is unvalidated. A CHECK constraint listing the keys was rejected because
adding a permission would then be a migration, and the registry test gives a
better error than a constraint violation does.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

__all__ = ["JurisdictionScope", "Officer", "OfficerRole", "Role"]


class Role(Base):
    """A named set of permissions plus the territory it applies to."""

    __tablename__ = "role"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment=(
            "Stable machine key, e.g. land_acquisition_officer. Referenced by "
            "fixtures and by the RBAC matrix test (task 5.6)."
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    permissions: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'::text[]"),
        comment=(
            "Permission keys. Validated against the PERMISSIONS registry by the "
            "build in task 5.6, deliberately not by a CHECK constraint: adding a "
            "permission must not require a migration."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    officers: Mapped[list[OfficerRole]] = relationship(
        "OfficerRole", back_populates="role", cascade="all, delete-orphan"
    )
    scopes: Mapped[list[JurisdictionScope]] = relationship(
        "JurisdictionScope", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        {
            "comment": (
                "A role carries both permissions and territory (R2.1), so the "
                "same job in two districts is two roles."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<Role {self.key}>"


class Officer(Base):
    """An authenticated government user of the Officer_Portal."""

    __tablename__ = "officer"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    officer_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        comment=(
            "The identifier presented at sign-in. Unique so R1.3's per-identifier "
            "lockout counts against one account rather than a shared bucket."
        ),
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    designation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Official designation, for display and for the audit trail.",
    )

    credential_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Argon2id (§19.1). Never a reversible encoding, and never logged. "
            "Task 7.1 owns verification; this column only stores the digest."
        ),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment=(
            "Deactivation rather than deletion: R4.1 events reference the actor, "
            "and a deleted officer would leave the audit trail unattributable."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    roles: Mapped[list[OfficerRole]] = relationship(
        "OfficerRole", back_populates="officer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        {
            "comment": (
                "Officers are deactivated, not deleted, so event actors stay "
                "resolvable (R4.1). 'At least one role' (R2.1) is a service "
                "invariant, not a constraint — see the module docstring."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<Officer {self.officer_code}>"


class OfficerRole(Base):
    """Which roles an officer holds. Composite key: the pair is the fact."""

    __tablename__ = "officer_role"

    officer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    officer: Mapped[Officer] = relationship("Officer", back_populates="roles")
    role: Mapped[Role] = relationship("Role", back_populates="officers")

    __table_args__ = (
        # R2.6 requires a role change to apply on the next request, so this is
        # read on every authenticated request and indexed in both directions.
        Index("officer_role_by_role", role_id),
        {"comment": "Officer-to-role grants. Read on every authenticated request."},
    )


class JurisdictionScope(Base):
    """One administrative area a role covers.

    A role with several rows here covers the union. ``scoped()`` turns those rows
    into an ``OR`` of ``path <@ area.path`` (§8.1), so covering a district needs
    exactly one row and reaches every village beneath it.
    """

    __tablename__ = "jurisdiction_scope"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("role.id", ondelete="CASCADE"),
        primary_key=True,
    )
    area_code: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("administrative_area.code", ondelete="RESTRICT"),
        primary_key=True,
        comment=(
            "RESTRICT: silently dropping an area from a role's scope on area "
            "deletion would widen or narrow authorization with no record of it."
        ),
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    role: Mapped[Role] = relationship("Role", back_populates="scopes")

    __table_args__ = (
        UniqueConstraint("role_id", "area_code", name="jurisdiction_scope_unique"),
        Index("jurisdiction_scope_by_area", area_code),
        {
            "comment": (
                "Territory of a role (R2.1). Union across rows; containment is "
                "path <@ area.path so one district row covers its descendants."
            )
        },
    )

    def __repr__(self) -> str:
        return f"<JurisdictionScope role={self.role_id} area={self.area_code}>"
