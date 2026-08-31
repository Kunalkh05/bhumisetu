#!/bin/sh
# Provision BHUMISETU object storage: buckets, policies, and the two access
# keys that keep the Holdout_Set away from anything that tunes the OCR service.
#
# Design §13.6 / R11.10: the Holdout_Set must be withheld from every process
# that tunes the OCR_Service. That is enforced here with credentials, because a
# comment in a config file is not an access control. Two keys exist:
#
#   bhumisetu-app     read/write on bhumisetu-documents and bhumisetu-models,
#                     explicitly denied on bhumisetu-holdout.
#                     Used by api, worker-ocr, worker-ml, worker-general.
#
#   bhumisetu-holdout read-only on bhumisetu-holdout, nothing else.
#                     Present only in worker-measure's environment.
#
# Read-only is deliberate: R11.10 requires holdout labels to be recorded by
# hand independently of any OCR output, so no automated process may mutate the
# set. Loading holdout documents is an administrative act using root
# credentials, not something the measurement path can do.
#
# This script ends by *testing* the boundary rather than assuming it. If the
# application key can reach the holdout bucket, the container exits non-zero
# and every service that depends on it refuses to start.

set -eu

MC_HOST_ALIAS=local
ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"

DOCUMENTS_BUCKET="${OBJECT_STORAGE_BUCKET:-bhumisetu-documents}"
MODELS_BUCKET="${OBJECT_STORAGE_MODELS_BUCKET:-bhumisetu-models}"
HOLDOUT_BUCKET="${HOLDOUT_STORAGE_BUCKET:-bhumisetu-holdout}"

say() { printf '[minio-init] %s\n' "$*"; }
die() { printf '[minio-init] FAIL: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- connect ----
say "waiting for ${ENDPOINT}"
until mc alias set "$MC_HOST_ALIAS" "$ENDPOINT" \
	"$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
	sleep 1
done
say "connected"

# ---------------------------------------------------------------- buckets ----
for bucket in "$DOCUMENTS_BUCKET" "$MODELS_BUCKET" "$HOLDOUT_BUCKET"; do
	mc mb --ignore-existing "${MC_HOST_ALIAS}/${bucket}"
	say "bucket ready: ${bucket}"
done

# The holdout bucket is versioned so an accidental overwrite of a hand-labelled
# document is recoverable; its labels live in PostgreSQL (design §13.6).
mc version enable "${MC_HOST_ALIAS}/${HOLDOUT_BUCKET}" >/dev/null 2>&1 \
	|| say "note: versioning unavailable on ${HOLDOUT_BUCKET} (single-node dev server)"

# --------------------------------------------------------------- policies ----
# mc renamed these verbs: `policy create`/`attach` on current releases,
# `policy add`/`set` on older ones. Accept either so the stack is not pinned to
# one mc build.
put_policy() {
	name=$1
	file=$2
	mc admin policy create "$MC_HOST_ALIAS" "$name" "$file" >/dev/null 2>&1 \
		|| mc admin policy add "$MC_HOST_ALIAS" "$name" "$file" >/dev/null 2>&1 \
		|| die "could not install policy ${name}"
	say "policy installed: ${name}"
}

attach_policy() {
	name=$1
	user=$2
	mc admin policy attach "$MC_HOST_ALIAS" "$name" --user "$user" >/dev/null 2>&1 \
		|| mc admin policy set "$MC_HOST_ALIAS" "$name" user="$user" >/dev/null 2>&1 \
		|| say "policy ${name} already attached to ${user}"
}

put_policy bhumisetu-app-rw /policies/bhumisetu-app-rw.json
put_policy bhumisetu-holdout-ro /policies/bhumisetu-holdout-ro.json

# ------------------------------------------------------------------- keys ----
# A re-run re-asserts the secret rather than failing; the positive controls at
# the end confirm each key actually works, so tolerating "already exists" here
# cannot hide a broken key.
mc admin user add "$MC_HOST_ALIAS" \
	"$OBJECT_STORAGE_ACCESS_KEY" "$OBJECT_STORAGE_SECRET_KEY" >/dev/null 2>&1 \
	|| say "note: user ${OBJECT_STORAGE_ACCESS_KEY} already present"
attach_policy bhumisetu-app-rw "$OBJECT_STORAGE_ACCESS_KEY"
say "application key provisioned: ${OBJECT_STORAGE_ACCESS_KEY}"

mc admin user add "$MC_HOST_ALIAS" \
	"$HOLDOUT_STORAGE_ACCESS_KEY" "$HOLDOUT_STORAGE_SECRET_KEY" >/dev/null 2>&1 \
	|| say "note: user ${HOLDOUT_STORAGE_ACCESS_KEY} already present"
attach_policy bhumisetu-holdout-ro "$HOLDOUT_STORAGE_ACCESS_KEY"
say "holdout key provisioned: ${HOLDOUT_STORAGE_ACCESS_KEY}"

# ------------------------------------------------------- prove the boundary --
mc alias set app_check "$ENDPOINT" \
	"$OBJECT_STORAGE_ACCESS_KEY" "$OBJECT_STORAGE_SECRET_KEY" >/dev/null
mc alias set holdout_check "$ENDPOINT" \
	"$HOLDOUT_STORAGE_ACCESS_KEY" "$HOLDOUT_STORAGE_SECRET_KEY" >/dev/null

# Negative control: the key held by worker-ocr must be refused on the holdout
# bucket. This is the R11.10 boundary.
if mc ls "app_check/${HOLDOUT_BUCKET}" >/dev/null 2>&1; then
	die "R11.10 violated: the application key can list ${HOLDOUT_BUCKET}"
fi
say "verified: application key refused on ${HOLDOUT_BUCKET}"

if mc cp /policies/bhumisetu-app-rw.json \
	"app_check/${HOLDOUT_BUCKET}/probe.json" >/dev/null 2>&1; then
	mc rm "${MC_HOST_ALIAS}/${HOLDOUT_BUCKET}/probe.json" >/dev/null 2>&1 || true
	die "R11.10 violated: the application key can write to ${HOLDOUT_BUCKET}"
fi
say "verified: application key cannot write to ${HOLDOUT_BUCKET}"

# Positive controls: each key can reach what it is supposed to reach, so a
# passing negative control cannot be the result of a broken key.
mc ls "app_check/${DOCUMENTS_BUCKET}" >/dev/null \
	|| die "application key cannot list ${DOCUMENTS_BUCKET}"
mc ls "app_check/${MODELS_BUCKET}" >/dev/null \
	|| die "application key cannot list ${MODELS_BUCKET}"
mc ls "holdout_check/${HOLDOUT_BUCKET}" >/dev/null \
	|| die "holdout key cannot list ${HOLDOUT_BUCKET}"
say "verified: both keys reach their own buckets"

# The holdout key is scoped to the holdout bucket, so it must not double as an
# application key.
if mc ls "holdout_check/${DOCUMENTS_BUCKET}" >/dev/null 2>&1; then
	die "holdout key is over-scoped: it can list ${DOCUMENTS_BUCKET}"
fi
say "verified: holdout key scoped to ${HOLDOUT_BUCKET} only"

say "object storage ready"
