#!/usr/bin/env bash
# Live check that the proxy actually serves brotli and advertises HTTP/3.
#
# R24.1's 150 KB citizen budget is compressed bytes, and the CI budget test
# (design §10.5) measures brotli at quality 11. If this check fails, that test
# is measuring something the citizen never receives. Requires Docker and a
# running stack.
#
#   ./scripts/verify_proxy_encoding.sh [path]

set -euo pipefail

cd "$(dirname "$0")/.."

SITE=${BHUMISETU_SITE_ADDRESS:-localhost}
CITIZEN_PATH=${1:-/c/case}
COMPOSE=${COMPOSE:-docker compose}

pass() { printf '  ok   %s\n' "$*"; }
fail() { printf '  FAIL %s\n' "$*" >&2; exit 1; }

echo "proxy encoding check against https://${SITE}${CITIZEN_PATH}"

# The build itself asserts the encoder is present; re-assert on the running
# container in case a stale image is in use.
$COMPOSE exec -T proxy caddy list-modules \
	| grep -qx 'http.encoders.br' \
	|| fail "the running proxy has no brotli encoder compiled in"
pass "brotli encoder present in the running binary"

$COMPOSE exec -T proxy caddy validate --config /etc/caddy/Caddyfile \
	|| fail "Caddyfile is not valid"
pass "Caddyfile validates"

# -k because a development stack uses Caddy's internal CA.
headers=$(curl -ksS -o /dev/null -D - \
	-H 'Accept-Encoding: br, gzip' \
	"https://${SITE}${CITIZEN_PATH}")

grep -qi '^content-encoding:[[:space:]]*br' <<<"$headers" \
	|| fail "citizen path served without brotli. Headers:
${headers}"
pass "citizen path served with Content-Encoding: br"

grep -qi '^alt-svc:.*h3' <<<"$headers" \
	|| fail "no HTTP/3 advertisement in Alt-Svc (R24.3)"
pass "HTTP/3 advertised via Alt-Svc"

# Officer prefix must reach the Vite dev server with the prefix intact.
officer_status=$(curl -ksS -o /dev/null -w '%{http_code}' "https://${SITE}/officer/")
[ "$officer_status" != "404" ] || fail "/officer/ did not reach web:3000"
pass "/officer/ routed to the officer portal (HTTP ${officer_status})"

echo "proxy encoding and routing: confirmed"
