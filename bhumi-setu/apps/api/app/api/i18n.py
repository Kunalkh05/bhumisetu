"""Internal i18n telemetry endpoints (task 18.6)."""

from __future__ import annotations

import logging

from fastapi import Depends

from app.api.routers import internal_router
from app.schemas.i18n import MissingI18nKeyIn, MissingI18nKeyOut
from app.security.access import Principal, authenticate

__all__ = []

logger = logging.getLogger("bhumisetu.i18n")


@internal_router.post(
    "/i18n/missing",
    response_model=MissingI18nKeyOut,
)
def report_missing_i18n_key(
    body: MissingI18nKeyIn,
    principal: Principal = Depends(authenticate),
) -> MissingI18nKeyOut:
    logger.warning(
        "missing_i18n_key principal=%s:%s language=%s namespace=%s key=%s",
        principal.kind,
        principal.id,
        body.language,
        body.namespace,
        body.key,
    )
    return MissingI18nKeyOut(accepted=True)
