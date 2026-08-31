"""Structural guards on the deployment topology (design §3.4).

Three of the §3.4 deviations are security or measurement boundaries rather than
conveniences, and each of them is a single line away from being silently undone
by a later edit:

* R11.10 — the Holdout_Set is withheld from every process that tunes the
  OCR_Service. Enforced by credentials (design §13.6). Someone pasting the
  holdout key into ``worker-ocr`` to "debug the measurement" would remove the
  boundary with no test failing anywhere else.
* R24.1 — the 150 KB citizen budget is stated in compressed bytes, and the
  budget test measures brotli at quality 11 (design §10.5). If the proxy
  compresses at a different quality, or not at all, the test measures bytes no
  citizen ever receives.
* R24.3 — HTTP/3 0-RTT resumption materially affects whether the paint target
  is reachable (design §2), which needs the QUIC listener actually published.

These assertions are cheap and run without Docker, so they hold in CI even
where the stack cannot be brought up.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]  # -> bhumi-setu/
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
CADDYFILE = REPO_ROOT / "deployment" / "proxy" / "Caddyfile"
APP_POLICY = REPO_ROOT / "deployment" / "minio" / "policies" / "bhumisetu-app-rw.json"
VITE_CONFIG = REPO_ROOT / "apps" / "web" / "vite.config.ts"
BUDGET_TEST = REPO_ROOT / "apps" / "api" / "tests" / "perf" / "test_citizen_budget.py"

HOLDOUT_BUCKET = "bhumisetu-holdout"

# The quality the proxy compresses at. Task 19.5's BROTLI_Q must equal this.
PROXY_BROTLI_QUALITY = 11


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


def environment_of(compose: dict, service: str) -> dict[str, str]:
    """Normalise both compose environment forms to a mapping.

    Values are returned uninterpolated, so ``${HOLDOUT_STORAGE_SECRET_KEY:-x}``
    stays visible as text. That is what we want: the guard should catch a
    credential referenced by variable name just as surely as a literal.
    """
    env = compose["services"][service].get("environment") or {}
    if isinstance(env, dict):
        return {str(k): "" if v is None else str(v) for k, v in env.items()}
    pairs = {}
    for entry in env:
        key, _, value = str(entry).partition("=")
        pairs[key] = value
    return pairs


# --------------------------------------------------------------------------
# R11.10 — holdout credential separation
# --------------------------------------------------------------------------


def test_worker_ocr_holds_no_holdout_credential(compose: dict) -> None:
    env = environment_of(compose, "worker-ocr")
    blob = "\n".join(f"{k}={v}" for k, v in env.items())

    offenders = [k for k in env if "HOLDOUT" in k.upper()]
    assert not offenders, (
        f"worker-ocr must not carry holdout credentials, found {offenders}. "
        "R11.10 requires the Holdout_Set to be withheld from every process "
        "that tunes the OCR_Service; worker-ocr is that process."
    )
    assert HOLDOUT_BUCKET not in blob, (
        f"worker-ocr must not reference {HOLDOUT_BUCKET} (R11.10)"
    )


def test_worker_ocr_does_not_use_object_storage_root_credentials(
    compose: dict,
) -> None:
    """Root credentials read every bucket, holdout included.

    An application service holding them defeats the policy separation no
    matter how the policies are written.
    """
    env = environment_of(compose, "worker-ocr")
    values = " ".join(env.values())
    assert "minioadmin" not in values, (
        "worker-ocr is using MinIO root credentials, which can read the "
        "holdout bucket regardless of the bhumisetu-app-rw policy (R11.10)"
    )
    assert "MINIO_ROOT" not in " ".join(env), (
        "worker-ocr references MinIO root credentials (R11.10)"
    )


def test_holdout_credential_confined_to_provisioner_and_measurement(
    compose: dict,
) -> None:
    """"Present only in the measurement task's environment" (design §13.6)."""
    permitted = {"minio-init", "worker-measure"}
    holders = {
        name
        for name in compose["services"]
        if any("HOLDOUT" in key.upper() for key in environment_of(compose, name))
    }
    assert holders <= permitted, (
        f"holdout credential leaked into {sorted(holders - permitted)}; "
        f"only {sorted(permitted)} may hold it (design §13.6)"
    )
    assert "worker-measure" in holders, (
        "the measurement worker must hold the holdout credential, otherwise "
        "R11.10's accuracy measurement cannot read the Holdout_Set"
    )


def test_application_policy_explicitly_denies_holdout_bucket() -> None:
    """Implicit deny is enough until someone broadens a Resource to ``*``."""
    policy = json.loads(APP_POLICY.read_text())
    denies = [
        statement
        for statement in policy["Statement"]
        if statement.get("Effect") == "Deny"
        and any(
            HOLDOUT_BUCKET in resource
            for resource in statement.get("Resource", [])
        )
    ]
    assert denies, (
        f"{APP_POLICY.name} must explicitly Deny the application key on "
        f"{HOLDOUT_BUCKET} (R11.10)"
    )
    assert any("s3:*" in d.get("Action", []) for d in denies), (
        "the holdout Deny must cover all s3 actions, not a subset"
    )


def test_no_application_statement_grants_holdout_bucket() -> None:
    policy = json.loads(APP_POLICY.read_text())
    for statement in policy["Statement"]:
        if statement.get("Effect") != "Allow":
            continue
        for resource in statement.get("Resource", []):
            assert HOLDOUT_BUCKET not in resource, (
                f"Allow statement {statement.get('Sid')} grants "
                f"{resource} to the application key (R11.10)"
            )


def test_services_wait_for_provisioning_to_succeed(compose: dict) -> None:
    """The boundary is proven by minio-init before anything can use storage.

    ``service_completed_successfully`` is what turns the init script's checks
    into a gate: if it cannot enforce the separation, the stack does not come
    up with storage access.
    """
    for service in ("api", "worker-ocr", "worker-measure", "worker-general"):
        depends = compose["services"][service]["depends_on"]
        assert depends["minio-init"]["condition"] == "service_completed_successfully", (
            f"{service} must wait for minio-init to succeed"
        )


# --------------------------------------------------------------------------
# R24.1 / R24.3 — the proxy
# --------------------------------------------------------------------------


def test_proxy_enables_brotli_at_the_quality_ci_measures() -> None:
    caddyfile = CADDYFILE.read_text()
    match = re.search(r"^\s*br\s+(\d+)", caddyfile, re.MULTILINE)
    assert match, (
        "the proxy must enable brotli: R24.1's budget is stated in compressed "
        "bytes and CI measures brotli, so serving gzip or identity would make "
        "the budget test measure bytes no citizen receives"
    )
    assert int(match.group(1)) == PROXY_BROTLI_QUALITY, (
        f"proxy brotli quality is {match.group(1)}, expected "
        f"{PROXY_BROTLI_QUALITY} to match the budget test (design §10.5)"
    )


def test_proxy_brotli_is_preferred_over_zstd_and_gzip() -> None:
    """Caddy picks the first listed encoder absent a client q-factor."""
    encode_block = re.search(
        r"encode\s*\{(.*?)\}", CADDYFILE.read_text(), re.DOTALL
    )
    assert encode_block, "no encode block in the Caddyfile"
    encoders = [
        line.split()[0]
        for line in encode_block.group(1).splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert encoders and encoders[0] == "br", (
        f"brotli must be listed first to be preferred, got {encoders}"
    )


@pytest.mark.skipif(
    not BUDGET_TEST.exists(), reason="citizen budget test lands in task 19.5"
)
def test_budget_test_compresses_at_the_proxy_quality() -> None:
    match = re.search(r"^BROTLI_Q\s*=\s*(\d+)", BUDGET_TEST.read_text(), re.MULTILINE)
    assert match, "the budget test must declare BROTLI_Q"
    assert int(match.group(1)) == PROXY_BROTLI_QUALITY, (
        "the budget test and the proxy must compress at the same quality, "
        "or R24.1 is measured against bytes that are never transferred"
    )


def test_proxy_enables_http3_and_publishes_the_quic_listener(compose: dict) -> None:
    assert re.search(
        r"protocols\s+.*\bh3\b", CADDYFILE.read_text()
    ), "HTTP/3 must be enabled (design §2, R24.3)"
    ports = [str(p) for p in compose["services"]["proxy"]["ports"]]
    assert any("443:443/udp" in p for p in ports), (
        "HTTP/3 is QUIC over UDP; without the UDP listener the h3 "
        "advertisement cannot be taken up (R24.3)"
    )


def test_proxy_terminates_tls() -> None:
    assert re.search(r"^\s*(\{\$BHUMISETU_TLS_DIRECTIVE:)?tls\s", CADDYFILE.read_text(), re.MULTILINE), (
        "the proxy must terminate TLS (design §3.4)"
    )


# --------------------------------------------------------------------------
# Routing split and the officer-only web surface
# --------------------------------------------------------------------------


def test_officer_prefix_routes_to_web_and_the_rest_to_api() -> None:
    caddyfile = CADDYFILE.read_text()
    assert re.search(r"path\s+/officer\s+/officer/\*", caddyfile), (
        "/officer and /officer/* must both match the officer route"
    )
    assert "reverse_proxy web:3000" in caddyfile
    assert "reverse_proxy api:8000" in caddyfile
    assert "handle_path /officer" not in caddyfile, (
        "handle_path strips the prefix, which breaks asset URLs emitted under "
        "Vite base '/officer/'"
    )


def test_vite_base_matches_the_proxy_prefix() -> None:
    assert re.search(r"base:\s*'/officer/'", VITE_CONFIG.read_text()), (
        "the officer bundle must be built with base '/officer/' (design §10.6)"
    )


def test_citizen_react_scaffolding_is_gone() -> None:
    """The citizen surface is Jinja2 under apps/api/app/citizen/ (design §10)."""
    assert not (REPO_ROOT / "apps" / "web" / "src" / "citizen").exists(), (
        "apps/web/src/citizen/ must not exist: a React citizen portal cannot "
        "meet R24.1's 150 KB budget, so the surface is server-rendered"
    )


# --------------------------------------------------------------------------
# Worker topology (design §13.7)
# --------------------------------------------------------------------------


def test_scheduler_and_general_worker_exist(compose: dict) -> None:
    services = compose["services"]
    assert "worker-beat" in services, (
        "no scheduler: R7.6/7.7, R19.2, R31.1/31.5, R22.5 and R32.10 all "
        "require periodic work"
    )
    assert "beat" in services["worker-beat"]["command"]

    general = services["worker-general"]["command"]
    assert "import" in general and "maintenance" in general, (
        "worker-general must consume the import and maintenance queues so "
        "R30.11's throughput is not starved behind OCR jobs"
    )


def test_ocr_queues_are_split_across_processes(compose: dict) -> None:
    """`ocr_bulk` cannot share a process with `ocr`.

    §13.7 places both on worker-ocr, but the measurement task on ``ocr_bulk``
    needs the holdout credential and worker-ocr must not have it (§13.6). The
    queues therefore split across two processes, which also preserves §13.7's
    stated reason for the separate queue: a long measurement must not starve
    interactive extraction.
    """
    ocr = compose["services"]["worker-ocr"]["command"]
    measure = compose["services"]["worker-measure"]["command"]
    assert "ocr_bulk" not in ocr, (
        "worker-ocr must not consume ocr_bulk, or it would need the holdout "
        "credential (R11.10)"
    )
    assert "ocr_bulk" in measure
    # The Celery app sets worker_prefetch_multiplier = 1 process-wide, so
    # §13.7's "prefetch 1" for ocr_bulk is delivered by a single-slot worker.
    assert "--concurrency=1" in measure, (
        "the measurement worker must run one slot, or one long measurement "
        "reserves several jobs (§13.7)"
    )


def test_every_celery_process_runs_the_one_declared_app(compose: dict) -> None:
    """A second Celery app would not carry §13.7's routes.

    ``task_routes`` and ``task_queues`` are declared once, in
    ``app/workers/celery_app.py``. A worker booting its own app consumes a
    topology the publisher does not use, so tasks would be published to one
    place and awaited in another.
    """
    celery_services = {
        name: service["command"]
        for name, service in compose["services"].items()
        if "celery" in str(service.get("command", ""))
    }
    assert celery_services, "no celery services found"
    for name, command in celery_services.items():
        assert "-A app.workers.celery_app" in command, (
            f"{name} does not run the declared Celery app: {command!r}"
        )


def test_consumed_queues_are_declared_by_the_celery_app(compose: dict) -> None:
    """A ``-Q`` typo produces a worker that consumes nothing, silently.

    ``task_create_missing_queues = False`` catches the publish side; nothing
    catches the consume side, so it is checked here.
    """
    source = (
        REPO_ROOT / "apps" / "api" / "app" / "workers" / "celery_app.py"
    ).read_text()
    declared = set(
        re.findall(
            r'"([a-z_]+)"',
            re.search(r"QUEUE_NAMES:[^=]*=\s*\((.*?)\)", source, re.DOTALL).group(1),
        )
    )
    assert declared, "could not read QUEUE_NAMES from the Celery app"

    for name, service in compose["services"].items():
        command = str(service.get("command", ""))
        match = re.search(r"-Q\s+([\w,]+)", command)
        if not match:
            continue
        consumed = set(match.group(1).split(","))
        assert consumed <= declared, (
            f"{name} consumes {sorted(consumed - declared)}, which the Celery "
            f"app does not declare (declared: {sorted(declared)})"
        )


# --------------------------------------------------------------------------
# JWT_SECRET narrowed to /internal/* service tokens
# --------------------------------------------------------------------------


def test_jwt_secret_retained_only_on_the_api_service(compose: dict) -> None:
    """§3.4: JWT is retained for internal service tokens only.

    Officer and citizen sessions are opaque Redis-backed tokens, because R1.5
    needs immediate revocation and R2.6 needs a role change to apply on the
    next request.
    """
    holders = {
        name
        for name in compose["services"]
        if "JWT_SECRET" in environment_of(compose, name)
    }
    assert holders == {"api"}, (
        f"JWT_SECRET should exist on the api service only, found {sorted(holders)}"
    )
    assert "SESSION_STORE_URL" in environment_of(compose, "api"), (
        "the api service needs a session store: sessions are server-side "
        "opaque tokens, not JWTs (R1.5, R2.6)"
    )
