"""Every process that boots from this package boots with the environment it is given.

Nine services run from ``apps/api`` (§3.4) with deliberately different
environments, because a credential a process does not need is a credential it
must not hold: ``worker-ocr`` is the process that tunes the OCR service and so
holds no holdout key (R11.10), and ``worker-beat`` only schedules and so holds no
object-storage key at all. ``worker-ocr``, ``worker-ml`` and ``worker-measure``
are given no ``APP_ENV``.

A settings object that required every variable would load in none of them. The
failure would be at import, at container start, discovered by whoever next ran
``docker compose up`` — so it is checked here instead, by importing each entry
point in a subprocess carrying exactly that service's environment.

This is the check that keeps ``app/settings.py``'s capability grouping honest as
later tasks add settings reads: a subsystem that reaches for a group its process
was not given fails here rather than in a container.

``PYTHONPATH`` is dropped from the copied environment because compose's value
names container paths; the subprocess runs with ``apps/api`` as its working
directory instead, which is the same import root the containers get by mounting
the package there.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

#: How to tell, from a compose command, which module the process imports.
ENTRY_POINTS = {
    "app.main:app": "app.main",
    "app.workers.celery_app": "app.workers.celery_app",
}

_INTERPOLATION = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def resolve(value: str) -> str:
    """Apply compose's ``${NAME:-default}`` interpolation with no outer env set."""
    return _INTERPOLATION.sub(lambda match: match.group(2) or "", value)


def api_processes() -> list[tuple[str, str, dict[str, str]]]:
    """(service, module, environment) for every service booting from this package."""
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    found: list[tuple[str, str, dict[str, str]]] = []
    for service, definition in compose["services"].items():
        command = definition.get("command") or ""
        if not isinstance(command, str):
            continue
        for marker, module in ENTRY_POINTS.items():
            if marker in command:
                entries = definition.get("environment") or []
                env = {}
                for entry in entries:
                    name, _, value = entry.partition("=")
                    if name != "PYTHONPATH":
                        env[name] = resolve(value)
                found.append((service, module, env))
                break
    return found


PROCESSES = api_processes()


def test_compose_declares_processes_booting_from_this_package() -> None:
    """Fail closed: an empty list would make every test below pass vacuously."""
    assert PROCESSES, f"no api or celery entry point found in {COMPOSE_FILE}"


@pytest.mark.parametrize(
    ("service", "module", "env"),
    PROCESSES,
    ids=[f"{service}:{module}" for service, module, _ in PROCESSES],
)
def test_entry_point_imports_with_only_its_own_environment(
    service: str, module: str, env: dict[str, str]
) -> None:
    clean = {
        name: value
        for name, value in os.environ.items()
        if name in {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR"}
    }
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=API_ROOT,
        env=clean | env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"{service} cannot import {module} with the environment compose gives it.\n"
        f"Supplied: {sorted(env)}\n{result.stderr}"
    )
