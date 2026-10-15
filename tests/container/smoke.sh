#!/usr/bin/env bash
# Container smoke test: build the image, check it runs as uid 10001 without Node,
# serves /readyz with the real bundle, refuses to start without a secret, and that
# deploy/compose.yaml is valid. Run from the repo root: bash tests/container/smoke.sh
set -euo pipefail

IMAGE=mathtutor:local
NAME=mathtutor-smoke-$$
CREATED_ENV=0

cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  if [ "$CREATED_ENV" = 1 ]; then rm -f deploy/.env; fi
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

docker build -t "$IMAGE" .

uid=$(docker run --rm "$IMAGE" id -u)
[ "$uid" = 10001 ] || fail "runs as uid $uid, expected 10001"

node=$(docker run --rm "$IMAGE" sh -c 'command -v node || echo none')
[ "$node" = none ] || fail "node found in image at $node"

# Port published for this test only; compose never publishes 8000.
secret=$(head -c 48 /dev/urandom | base64 | tr -d '\n')
docker run -d --name "$NAME" -e MATHTUTOR_SECRET_KEY="$secret" \
  -p 127.0.0.1:18000:8000 "$IMAGE" >/dev/null

body=""
for _ in $(seq 1 30); do
  if body=$(curl -fsS http://127.0.0.1:18000/readyz 2>/dev/null); then break; fi
  sleep 1
done
[ -n "$body" ] || { docker logs "$NAME" >&2; fail "/readyz did not return 200 within 30 s"; }
case "$body" in
  *'"servable":6'*) ;;
  *) fail "/readyz body lacks \"servable\":6: $body" ;;
esac

set +e
timeout 10 docker run --rm "$IMAGE" >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "started without MATHTUTOR_SECRET_KEY"
[ "$rc" -ne 124 ] || fail "still running after 10 s without MATHTUTOR_SECRET_KEY"

# compose reads env_file deploy/.env; supply the example if none exists.
if [ ! -f deploy/.env ]; then cp deploy/.env.example deploy/.env; CREATED_ENV=1; fi
docker compose -f deploy/compose.yaml --env-file deploy/.env.example config -q

echo "container smoke test: PASS"
