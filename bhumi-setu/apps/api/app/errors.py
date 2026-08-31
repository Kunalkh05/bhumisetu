"""The §9.4 error envelope, as a type rather than a convention.

Every refusal the platform makes leaves the process as one shape::

    {"code": "ENTITY_VERSION_CONFLICT", "message": "…", "details": {...}}

``code`` is a stable machine string, ``details`` carries the structured payload
the requirement asks for — the per-attribute diff for R29.3, the policy key and
date for R28.5, the issue identifiers for R5.7, the permitted successors for
R5.4. Requirements are specific about what a refusal must *tell* the caller, so
the envelope is a declared model and the handler in ``app.main`` is the only
place that turns an exception into a response body.

``DomainError`` subclasses live with the subsystem that raises them
(``PolicyValueMissing`` in ``app.services.policy``, and so on). The code
constants are declared here so that the set in §9.4 exists in one place and a
subsystem references a name rather than repeating a string literal.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict


class ErrorCode:
    """The stable machine codes named in §9.4.

    Not an ``Enum``: these strings cross the API boundary and appear in client
    code, so they are constants whose value is the contract. Subsystems add
    their own codes here as they land.
    """

    ENTITY_VERSION_CONFLICT = "ENTITY_VERSION_CONFLICT"
    POLICY_VALUE_MISSING = "POLICY_VALUE_MISSING"
    BLOCKING_ISSUES_OPEN = "BLOCKING_ISSUES_OPEN"
    STAGE_TRANSITION_INVALID = "STAGE_TRANSITION_INVALID"
    DUPLICATE_PARCEL = "DUPLICATE_PARCEL"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    PAYOUT_EXCEEDS_AWARD = "PAYOUT_EXCEEDS_AWARD"
    NOT_AUTHORISED = "NOT_AUTHORISED"

    # Envelope codes for failures that are not domain refusals.
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorEnvelope(BaseModel):
    """The response body of every non-2xx response."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] = {}


class DomainError(Exception):
    """A refusal the platform makes deliberately, with a machine code.

    Subclasses set ``code`` and ``status_code`` as class attributes and pass the
    structured ``details`` the governing requirement demands.
    """

    code: str = ErrorCode.INTERNAL_ERROR
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details or {})

    def envelope(self) -> ErrorEnvelope:
        return ErrorEnvelope(code=self.code, message=self.message, details=self.details)


class NotAuthorised(DomainError):
    """R2.3: a 403 carries no body detail, so nothing is disclosed by refusing."""

    code = ErrorCode.NOT_AUTHORISED
    status_code = 403

    def __init__(self) -> None:
        super().__init__("Not authorised", details={})
