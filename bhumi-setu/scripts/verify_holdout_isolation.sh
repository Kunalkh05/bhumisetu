#!/usr/bin/env bash
# Live check of the R11.10 holdout boundary against a running stack.
#
# The compose guard in apps/api/tests/infra/test_compose_topology.py proves the
# credential is absent from worker-ocr's environment. This proves the stronger
# claim: the credential worker-ocr actually holds is refused by MinIO on the
# holdout bucket. Requires Docker.
#
#   ./scripts/verify_holdout_isolation.sh
#
# Exits non-zero on the first violation.

set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE=${COMPOSE:-docker compose}
HOLDOUT_BUCKET=${HOLDOUT_STORAGE_BUCKET:-bhumisetu-holdout}
DOCUMENTS_BUCKET=${OBJECT_STORAGE_BUCKET:-bhumisetu-documents}

pass() { printf '  ok   %s\n' "$*"; }
fail() { printf '  FAIL %s\n' "$*" >&2; exit 1; }

# Read the credentials the OCR worker is actually running with, from the
# container itself rather than from the compose file, so an override file or a
# hand-edited container is caught too.
ocr_env() {
	$COMPOSE exec -T worker-ocr printenv "$1" 2>/dev/null || true
}

echo "R11.10 holdout isolation check"

ocr_key=$(ocr_env OBJECT_STORAGE_ACCESS_KEY)
ocr_secret=$(ocr_env OBJECT_STORAGE_SECRET_KEY)
[ -n "$ocr_key" ] || fail "worker-ocr is not running, or has no object storage key"

# 1. No holdout variable of any kind inside the running OCR worker.
leaked=$($COMPOSE exec -T worker-ocr sh -c 'printenv | grep -i holdout || true')
[ -z "$leaked" ] || fail "worker-ocr environment leaks holdout config: ${leaked}"
pass "worker-ocr environment carries no holdout variable"

# 2. The key worker-ocr holds is refused on the holdout bucket. Run mc as a
#    throwaway container on the compose network using those exact credentials.
mc() {
	$COMPOSE run --rm --no-deps --entrypoint /bin/sh minio-init -c "$1"
}

probe="mc alias set probe http://minio:9000 '${ocr_key}' '${ocr_secret}' >/dev/null"

if mc "${probe} && mc ls probe/${HOLDOUT_BUCKET} >/dev/null 2>&1"; then
	fail "worker-ocr's key can LIST ${HOLDOUT_BUCKET}"
fi
pass "worker-ocr's key is refused on LIST ${HOLDOUT_BUCKET}"

if mc "${probe} && echo probe > /tmp/p && mc cp /tmp/p probe/${HOLDOUT_BUCKET}/p >/dev/null 2>&1"; then
	fail "worker-ocr's key can WRITE to ${HOLDOUT_BUCKET}"
fi
pass "worker-ocr's key is refused on WRITE ${HOLDOUT_BUCKET}"

# 3. Positive control. A key that cannot reach anything would pass step 2 for
#    the wrong reason.
if ! mc "${probe} && mc ls probe/${DOCUMENTS_BUCKET} >/dev/null 2>&1"; then
	fail "worker-ocr's key cannot list ${DOCUMENTS_BUCKET} either — the checks above prove nothing"
fi
pass "worker-ocr's key still reaches ${DOCUMENTS_BUCKET}"

# 4. The measurement worker can read the holdout set, or the measurement
#    R11.10 requires cannot run.
measure_key=$($COMPOSE exec -T worker-measure printenv HOLDOUT_STORAGE_ACCESS_KEY 2>/dev/null || true)
measure_secret=$($COMPOSE exec -T worker-measure printenv HOLDOUT_STORAGE_SECRET_KEY 2>/dev/null || true)
[ -n "$measure_key" ] || fail "worker-measure has no holdout key"
[ "$measure_key" != "$ocr_key" ] || fail "worker-measure and worker-ocr share one key"

mprobe="mc alias set mprobe http://minio:9000 '${measure_key}' '${measure_secret}' >/dev/null"
if ! mc "${mprobe} && mc ls mprobe/${HOLDOUT_BUCKET} >/dev/null 2>&1"; then
	fail "worker-measure cannot read ${HOLDOUT_BUCKET}"
fi
pass "worker-measure reads ${HOLDOUT_BUCKET}"

if mc "${mprobe} && mc ls mprobe/${DOCUMENTS_BUCKET} >/dev/null 2>&1"; then
	fail "the holdout key is over-scoped: it can list ${DOCUMENTS_BUCKET}"
fi
pass "holdout key scoped to ${HOLDOUT_BUCKET} only"

echo "R11.10 holdout isolation: enforced"
