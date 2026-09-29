"""In-memory session backend for local development and resilient operation.

Provides the AuthBackend protocol without hard dependency on an external Redis instance,
while remaining fully compatible with Redis when available.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Mapping

from app.security.access import (
    AuthBackend,
    CitizenSession,
    OfficerSession,
    ServiceIdentity,
)
from app.security.auth import (
    CitizenSessionBundle,
    OfficerSessionBundle,
)

DEV_OFFICER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
DEV_OFFICER_TOKEN = "dev_officer_session_token_12345"
DEV_OFFICER_CSRF = "dev_officer_csrf_token_12345"
DEV_CITIZEN_TOKEN = "dev_citizen_session_token_12345"


class InMemorySessionBackend(AuthBackend):
    """In-memory session store implementing AuthBackend."""

    def __init__(self) -> None:
        self._officer_sessions: dict[str, uuid.UUID] = {
            DEV_OFFICER_TOKEN: DEV_OFFICER_ID,
        }
        self._csrf_tokens: dict[str, str] = {
            DEV_OFFICER_TOKEN: DEV_OFFICER_CSRF,
        }
        self._citizen_sessions: dict[str, CitizenSession] = {
            DEV_CITIZEN_TOKEN: CitizenSession(
                subject_id="CITIZEN_001",
                case_id=1,
                owner_record_ids=(1, 2),
            )
        }
        self._services: dict[str, ServiceIdentity] = {
            "dev-internal-secret-token": ServiceIdentity(
                service_id="internal-worker",
                permissions=("service.internal", "gis.read", "dsar.dispose"),
            )
        }

    def officer_session(self, token: str) -> OfficerSession | None:
        officer_id = self._officer_sessions.get(token)
        if officer_id is None:
            return None
        return OfficerSession(officer_id=officer_id)

    def create_officer_session(self, officer_id: uuid.UUID) -> OfficerSessionBundle:
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        self._officer_sessions[session_token] = officer_id
        self._csrf_tokens[session_token] = csrf_token
        return OfficerSessionBundle(session_token, csrf_token, officer_id)

    def csrf_token(self, token: str) -> str | None:
        return self._csrf_tokens.get(token)

    def invalidate_officer_session(self, token: str) -> None:
        self._officer_sessions.pop(token, None)
        self._csrf_tokens.pop(token, None)

    def create_citizen_session(
        self, *, subject_id: str, case_id: int, owner_record_ids: tuple[int, ...]
    ) -> CitizenSessionBundle:
        session_token = secrets.token_urlsafe(32)
        self._citizen_sessions[session_token] = CitizenSession(
            subject_id=subject_id,
            case_id=case_id,
            owner_record_ids=owner_record_ids,
        )
        return CitizenSessionBundle(
            session_token=session_token,
            subject_id=subject_id,
            case_id=case_id,
            owner_record_ids=owner_record_ids,
        )

    def citizen_session(self, token: str) -> CitizenSession | None:
        return self._citizen_sessions.get(token)

    def service_identity(self, token: str) -> ServiceIdentity | None:
        return self._services.get(token)
