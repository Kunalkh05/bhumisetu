"""Process configuration, read from the environment and never defaulted.

Three rules shape this module.

**Environment variable names come from ``docker-compose.yml`` and are not
re-invented here.** ``DATABASE_URL``, ``REDIS_URL``, ``OBJECT_STORAGE_*``,
``APP_ENV`` and ``LOG_LEVEL`` are already committed; each field carries the
committed name as its explicit ``validation_alias``, so the literal string
appears in the source and a drift test can read it back
(``tests/test_settings.py``).

**A missing value that changes behaviour refuses rather than defaults.** Every
connection string and credential is required with no fallback, so a
misconfigured process fails at startup instead of quietly connecting somewhere
else. ``LOG_LEVEL`` is the one field with a default, because its absence cannot
produce a wrong answer. ``APP_ENV`` deliberately has no default: a process that
silently believes it is in ``development`` is a security problem, not an
inconvenience.

**Settings are grouped by capability, and a group is validated only when the
process actually uses it.** This is not tidiness. Nine processes run from this
one package (§3.4) and they legitimately hold different environments:
``worker-beat`` only schedules, so it is given no object-storage credential at
all, and ``worker-ocr`` must not hold the holdout credential because it is the
process that tunes the OCR service (R11.10). One settings object requiring
everything would either fail to load in those processes or force the compose
file to hand every process every credential — and the second is the option that
quietly destroys R11.10. So each group has its own accessor, and a process that
never calls it needs nothing from it:

===========================  ===================================  ==================
Group                        Read by                              Variables
===========================  ===================================  ==================
:class:`CoreSettings`        ``app.main``                         ``APP_ENV``, ``LOG_LEVEL``
:class:`DatabaseSettings`    ``app.db.session``                   ``DATABASE_URL``
:class:`BrokerSettings`      ``app.workers.celery_app``           ``REDIS_URL``
:class:`ObjectStorageSettings`  ``Document_Service`` (§13.1)      ``OBJECT_STORAGE_*``
:class:`InternalTokenSettings`  ``/internal/*`` tokens (§9.3)     ``JWT_SECRET``
===========================  ===================================  ==================

The holdout (§13.6) and model (§14.7) buckets get their own groups when the
tasks that read them land, for the same reason: separate credentials are only
separate if separate code asks for them.

This module is *not* the home of statutory periods, thresholds, cutoffs or
weights. Those are ``Policy_Config`` values resolved by state, act and effective
date (§4) and must never appear as a setting, a literal or a column default.

Note on ``JWT_SECRET``: per §3.4 it is retained for ``/internal/*`` service
tokens only. Officer and citizen sessions are opaque tokens in Redis (§19.1)
because R1.5 requires immediate revocation and R2.6 requires a role change to
apply on the next request. The group is therefore named
:class:`InternalTokenSettings` so no call site can mistake it for a session
secret while still reading the committed ``JWT_SECRET`` variable.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["development", "staging", "production"]

_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})

__all__ = [
    "AppEnv",
    "BrokerSettings",
    "CoreSettings",
    "DatabaseSettings",
    "InternalTokenSettings",
    "ObjectStorageSettings",
    "get_broker_settings",
    "get_core_settings",
    "get_database_settings",
    "get_internal_token_settings",
    "get_object_storage_settings",
]


class _EnvSettings(BaseSettings):
    """Base for every group.

    The process environment is the single source; no ``.env`` file is read, so
    there is exactly one place a deployed value can come from.
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        frozen=True,
    )


class CoreSettings(_EnvSettings):
    """What the application process needs to know about itself."""

    app_env: AppEnv = Field(validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @field_validator("log_level")
    @classmethod
    def _known_log_level(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised not in _LOG_LEVELS:
            raise ValueError(
                f"LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}, got {value!r}"
            )
        return normalised

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def log_level_number(self) -> int:
        return logging.getLevelName(self.log_level)  # type: ignore[return-value]


class DatabaseSettings(_EnvSettings):
    """The one PostgreSQL connection. Read by ``app.db.session``."""

    database_url: str = Field(validation_alias="DATABASE_URL")

    @field_validator("database_url")
    @classmethod
    def _is_a_sqlalchemy_url(cls, value: str) -> str:
        # docker-compose commits `postgresql+psycopg://...`, which SQLAlchemy
        # consumes directly. The bare `postgres://` form is rejected rather than
        # rewritten, so the committed value and the value in use stay identical.
        if "://" not in value:
            raise ValueError("DATABASE_URL must be a SQLAlchemy URL")
        return value

    @property
    def url_without_credentials(self) -> str:
        """``DATABASE_URL`` with any userinfo removed, safe to log."""
        scheme, _, rest = self.database_url.partition("://")
        if "@" in rest:
            rest = rest.rsplit("@", 1)[1]
        return f"{scheme}://{rest}"


class BrokerSettings(_EnvSettings):
    """The Celery broker. Read by ``app.workers.celery_app`` and nothing else."""

    redis_url: str = Field(validation_alias="REDIS_URL")


class ObjectStorageSettings(_EnvSettings):
    """The documents bucket and the application's own key.

    Deliberately does not cover the holdout bucket (§13.6) or the models bucket
    (§14.7). Those are separate credentials held by separate processes, and they
    get separate groups when their tasks land.
    """

    endpoint: str = Field(validation_alias="OBJECT_STORAGE_ENDPOINT")
    access_key: str = Field(validation_alias="OBJECT_STORAGE_ACCESS_KEY")
    secret_key: SecretStr = Field(validation_alias="OBJECT_STORAGE_SECRET_KEY")
    bucket: str = Field(validation_alias="OBJECT_STORAGE_BUCKET")


class InternalTokenSettings(_EnvSettings):
    """The ``/internal/*`` service-token secret (§9.3). Never a session secret."""

    secret: SecretStr = Field(validation_alias="JWT_SECRET")


@lru_cache(maxsize=1)
def get_core_settings() -> CoreSettings:
    return CoreSettings()  # type: ignore[call-arg]  # values come from the environment


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_broker_settings() -> BrokerSettings:
    return BrokerSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_object_storage_settings() -> ObjectStorageSettings:
    return ObjectStorageSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_internal_token_settings() -> InternalTokenSettings:
    return InternalTokenSettings()  # type: ignore[call-arg]


def clear_settings_cache() -> None:
    """Drop every cached group. For tests that change the environment."""
    for accessor in (
        get_core_settings,
        get_database_settings,
        get_broker_settings,
        get_object_storage_settings,
        get_internal_token_settings,
    ):
        accessor.cache_clear()
