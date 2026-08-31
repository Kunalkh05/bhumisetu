"""The FastAPI application: one process, one error envelope.

§3.3's modular monolith means this application object is the whole API surface —
officer (``/api/officer/*``), citizen (``/c/*`` and ``/api/citizen/*``) and
internal (``/internal/*``) routers are mounted here as their tasks land, and the
domain services they call are imported, not reached over a network.

This module wires two things and deliberately nothing else:

**The §9.4 error envelope.** Every non-2xx response leaves as
``{"code", "message", "details"}``. The handlers below are the only place an
exception becomes a response body, so a subsystem that raises ``DomainError``
with the structured detail its requirement demands gets the right shape without
knowing anything about HTTP. Unhandled exceptions become an
``INTERNAL_ERROR`` envelope with no detail — the traceback goes to the log, not
to the client.

**Log level.** From ``LOG_LEVEL`` (see ``app/settings.py``).

Sessions are not wired here. ``unit_of_work()`` is opened by the route handler,
not by a dependency; ``app/db/session.py`` explains why.

Routers are absent because no route exists yet. The one endpoint below,
``GET /healthz``, is unauthenticated and returns a fixed body with no version,
environment or dependency state, so it discloses only that the process is
answering. Authentication for the real surfaces arrives with §19.1 in task 5.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import DomainError, ErrorCode, ErrorEnvelope
from app.settings import CoreSettings, get_core_settings, get_database_settings

logger = logging.getLogger("bhumisetu")


def _envelope_response(status_code: int, envelope: ErrorEnvelope) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        # A deliberate refusal. `details` carries what the requirement says the
        # caller must be told, so it is passed through untouched.
        return _envelope_response(exc.status_code, exc.envelope())

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _envelope_response(
            422,
            ErrorEnvelope(
                code=ErrorCode.VALIDATION_FAILED,
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # Framework-raised 404s and 405s pass through the same envelope, so a
        # client parses one shape for every failure.
        return _envelope_response(
            exc.status_code,
            ErrorEnvelope(
                code=ErrorCode.VALIDATION_FAILED
                if exc.status_code == 422
                else f"HTTP_{exc.status_code}",
                message=str(exc.detail),
                details={},
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _envelope_response(
            500,
            ErrorEnvelope(
                code=ErrorCode.INTERNAL_ERROR,
                message="Internal error",
                details={},
            ),
        )


def create_app(core: CoreSettings | None = None) -> FastAPI:
    """Build the application. Accepts settings so a test can supply its own."""
    core = core or get_core_settings()
    logging.basicConfig(level=core.log_level_number)
    logger.info(
        "bhumisetu api starting env=%s database=%s",
        core.app_env,
        get_database_settings().url_without_credentials,
    )

    app = FastAPI(
        title="BHUMISETU API",
        # Interactive docs expose the whole surface; off outside development.
        docs_url=None if core.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if core.is_production else "/openapi.json",
    )
    _register_error_handlers(app)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
