"""Settings read the committed variable names, refuse rather than default, and
require only what the reading process uses.

The last point has teeth. Nine processes run from this one package (§3.4) with
deliberately different environments: ``worker-beat`` is given no object-storage
credential and ``worker-ocr`` must not hold the holdout credential, because it is
the process that tunes the OCR service (R11.10). A settings object that required
everything would either refuse to start in those processes or push the compose
file into handing every process every credential — and the second is the option
that quietly destroys R11.10.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app import settings as settings_module
from app.settings import (
    BrokerSettings,
    CoreSettings,
    DatabaseSettings,
    InternalTokenSettings,
    ObjectStorageSettings,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

GROUPS = (
    CoreSettings,
    DatabaseSettings,
    BrokerSettings,
    ObjectStorageSettings,
    InternalTokenSettings,
)

FULL_ENV = {
    "APP_ENV": "development",
    "LOG_LEVEL": "INFO",
    "DATABASE_URL": "postgresql+psycopg://u:p@postgres:5432/bhumisetu",
    "REDIS_URL": "redis://redis:6379/0",
    "OBJECT_STORAGE_ENDPOINT": "http://minio:9000",
    "OBJECT_STORAGE_ACCESS_KEY": "bhumisetu-app",
    "OBJECT_STORAGE_SECRET_KEY": "bhumisetu_app_dev_secret",
    "OBJECT_STORAGE_BUCKET": "bhumisetu-documents",
    "JWT_SECRET": "dev-secret-change-in-production",
}


def alias_names(group: type) -> set[str]:
    return {
        str(field.validation_alias)
        for field in group.model_fields.values()
        if field.validation_alias
    }


def all_alias_names() -> set[str]:
    return set().union(*(alias_names(group) for group in GROUPS))


def compose_env_names() -> dict[str, set[str]]:
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {}
    for service, definition in compose["services"].items():
        entries = definition.get("environment") or []
        out[service] = {entry.split("=", 1)[0] for entry in entries}
    return out


def build(group, env: dict[str, str], monkeypatch: pytest.MonkeyPatch):
    for name in all_alias_names():
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return group()


# --------------------------------------------------------------------------
# The names come from compose
# --------------------------------------------------------------------------


def test_no_setting_invents_a_name_compose_does_not_carry() -> None:
    """Drift here is silent: the process reads a variable nothing sets."""
    committed = set().union(*compose_env_names().values())
    assert all_alias_names() <= committed


def test_the_api_service_supplies_every_group() -> None:
    """``api`` runs the whole surface, so it needs all five groups."""
    api = compose_env_names()["api"]
    for group in GROUPS:
        required = {
            str(field.validation_alias)
            for field in group.model_fields.values()
            if field.is_required() and field.validation_alias
        }
        assert required <= api, f"{group.__name__} needs {required - api} in api"


# --------------------------------------------------------------------------
# A missing value refuses
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("group", "missing"),
    [
        (CoreSettings, "APP_ENV"),
        (DatabaseSettings, "DATABASE_URL"),
        (BrokerSettings, "REDIS_URL"),
        (ObjectStorageSettings, "OBJECT_STORAGE_ENDPOINT"),
        (ObjectStorageSettings, "OBJECT_STORAGE_ACCESS_KEY"),
        (ObjectStorageSettings, "OBJECT_STORAGE_SECRET_KEY"),
        (ObjectStorageSettings, "OBJECT_STORAGE_BUCKET"),
        (InternalTokenSettings, "JWT_SECRET"),
    ],
)
def test_a_missing_required_value_refuses(
    group: type, missing: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = {name: value for name, value in FULL_ENV.items() if name != missing}
    with pytest.raises(ValidationError) as raised:
        build(group, env, monkeypatch)
    assert missing in str(raised.value)


def test_app_env_has_no_default() -> None:
    """A process that silently believes it is in development is a security bug."""
    assert CoreSettings.model_fields["app_env"].is_required()


def test_app_env_rejects_an_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValidationError):
        build(CoreSettings, FULL_ENV | {"APP_ENV": "prod"}, monkeypatch)


def test_log_level_defaults_and_normalises(monkeypatch: pytest.MonkeyPatch) -> None:
    env = {name: v for name, v in FULL_ENV.items() if name != "LOG_LEVEL"}
    assert build(CoreSettings, env, monkeypatch).log_level == "INFO"
    assert build(CoreSettings, FULL_ENV | {"LOG_LEVEL": "debug"}, monkeypatch).log_level == "DEBUG"


def test_log_level_rejects_an_unknown_level(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        build(CoreSettings, FULL_ENV | {"LOG_LEVEL": "CHATTY"}, monkeypatch)


# --------------------------------------------------------------------------
# A group is validated only when it is used
# --------------------------------------------------------------------------


def test_the_broker_group_loads_without_any_storage_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``worker-beat`` only schedules, and holds no storage credential.

    ``app.workers.celery_app`` reads this group and nothing else, which is what
    lets a process run with the environment it actually needs.
    """
    assert build(BrokerSettings, {"REDIS_URL": "redis://redis:6379/0"}, monkeypatch)


def test_the_database_group_loads_without_a_broker_or_storage_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = build(
        DatabaseSettings,
        {"DATABASE_URL": "postgresql+psycopg://u:p@postgres:5432/bhumisetu"},
        monkeypatch,
    )
    assert settings.database_url.endswith("/bhumisetu")


def test_a_process_holding_no_storage_credential_fails_only_when_it_asks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal is loud, and it happens at the call, not at import.

    That is the whole mechanism behind credential separation: absence is
    harmless until the code that needs the credential runs, and then it is fatal
    rather than silently defaulted.
    """
    for name in all_alias_names():
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    settings_module.clear_settings_cache()
    try:
        assert settings_module.get_broker_settings().redis_url.startswith("redis://")
        with pytest.raises(ValidationError):
            settings_module.get_object_storage_settings()
    finally:
        settings_module.clear_settings_cache()


# --------------------------------------------------------------------------
# Secrets and logging
# --------------------------------------------------------------------------


def test_the_storage_secret_is_not_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = build(ObjectStorageSettings, FULL_ENV, monkeypatch)
    assert "bhumisetu_app_dev_secret" not in repr(settings)
    assert settings.secret_key.get_secret_value() == "bhumisetu_app_dev_secret"


def test_database_url_can_be_logged_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = build(DatabaseSettings, FULL_ENV, monkeypatch)
    assert settings.url_without_credentials == "postgresql+psycopg://postgres:5432/bhumisetu"
    assert "p@" not in settings.url_without_credentials


def test_database_url_must_be_a_sqlalchemy_url(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValidationError):
        build(DatabaseSettings, FULL_ENV | {"DATABASE_URL": "bhumisetu"}, monkeypatch)


def test_the_internal_token_secret_is_named_for_its_only_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§3.4: ``JWT_SECRET`` mints ``/internal/*`` service tokens, not sessions.

    Officer and citizen sessions are opaque tokens in Redis (§19.1) because R1.5
    needs immediate revocation and R2.6 needs a role change to apply on the next
    request. No group exposes a field a session could plausibly reach for.
    """
    settings = build(InternalTokenSettings, FULL_ENV, monkeypatch)
    assert settings.secret.get_secret_value() == "dev-secret-change-in-production"

    for group in GROUPS:
        assert "jwt" not in " ".join(group.model_fields)
        if group is not InternalTokenSettings:
            assert "JWT_SECRET" not in alias_names(group)


def test_is_production_tracks_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert not build(CoreSettings, FULL_ENV, monkeypatch).is_production
    assert build(CoreSettings, FULL_ENV | {"APP_ENV": "production"}, monkeypatch).is_production
