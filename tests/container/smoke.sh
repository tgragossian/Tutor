#!/usr/bin/env bash
# Container smoke test: build the image, check it runs as uid 10001 without Node, migrates
# a /data volume owned by 10001, serves /readyz, grades one real answer through the API,
# logs each request once, refuses to start without a secret, and that deploy/compose.yaml
# is valid. With E2E=1 it also runs the browser test (tools/e2e) against the container.
# Run from the repo root: bash tests/container/smoke.sh   (or: E2E=1 bash ...)
set -euo pipefail

IMAGE=mathtutor:local
NAME=mathtutor-smoke-$$
VOLUME=mathtutor-smoke-data-$$
JAR=$(mktemp)
BODY=$(mktemp)
CREATED_ENV=0

cleanup() {
  docker rm -f "$NAME" "$NAME-nosecret" >/dev/null 2>&1 || true
  docker volume rm -f "$VOLUME" >/dev/null 2>&1 || true
  rm -f "$JAR" "$BODY"
  if [ "$CREATED_ENV" = 1 ]; then rm -f deploy/.env; fi
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

docker build -t "$IMAGE" .

uid=$(docker run --rm "$IMAGE" id -u)
[ "$uid" = 10001 ] || fail "runs as uid $uid, expected 10001"

node=$(docker run --rm "$IMAGE" sh -c 'command -v node || echo none')
[ "$node" = none ] || fail "node found in image at $node"

secret=$(head -c 48 /dev/urandom | base64 | tr -d '\n')

# Migrations: a one-shot run against a fresh volume, as compose's `migrate` service does.
docker volume create "$VOLUME" >/dev/null
docker run --rm -e MATHTUTOR_SECRET_KEY="$secret" -v "$VOLUME:/data" "$IMAGE" \
  alembic upgrade head || fail "alembic upgrade head failed"
owner=$(docker run --rm -v "$VOLUME:/data" "$IMAGE" stat -c %u /data)
[ "$owner" = 10001 ] || fail "/data owned by uid $owner, expected 10001"
docker run --rm -v "$VOLUME:/data" "$IMAGE" test -s /data/mathtutor.db \
  || fail "migrations did not create /data/mathtutor.db"

# Port published for this test only; compose never publishes 8000.
docker run -d --name "$NAME" -e MATHTUTOR_SECRET_KEY="$secret" -v "$VOLUME:/data" \
  -p 127.0.0.1:18000:8000 "$IMAGE" >/dev/null

body=""
for _ in $(seq 1 30); do
  if body=$(curl -fsS http://127.0.0.1:18000/readyz 2>/dev/null); then break; fi
  sleep 1
done
[ -n "$body" ] || { docker logs "$NAME" >&2; fail "/readyz did not return 200 within 30 s"; }
case "$body" in
  *'"servable":22'*) ;;
  *) fail "/readyz body lacks \"servable\":22: $body" ;;
esac

# One real answer through the API and the real verifier pool (exercise 221).
base=http://127.0.0.1:18000
csrf=$(curl -fsS -c "$JAR" -H 'content-type: application/json' \
  -d '{"username":"smoke_user","password":"smoke-password-1"}' "$base/api/auth/register" \
  | sed -n 's/.*"csrf_token":"\([^"]*\)".*/\1/p')
[ -n "$csrf" ] || fail "register did not return a CSRF token"
# The production cookie is Secure; curl will not send it back over http, so pass it by hand.
cookie=$(awk '$6 == "mt_session" {print $7}' "$JAR")
[ -n "$cookie" ] || fail "register did not set the mt_session cookie"
api() {
  curl -fsS -H "Cookie: mt_session=$cookie" -H 'content-type: application/json' \
    -H "X-CSRF-Token: $csrf" "$@"
}
sid=$(api -d '{"topics":["derivatives.chain_rule"]}' "$base/api/sessions" \
  | sed -n 's/.*"session_id":\([0-9]*\).*/\1/p')
[ -n "$sid" ] || fail "could not start a session"
current=$(api "$base/api/sessions/$sid/current")
# Skip ahead to exercise 221 (easier chain-rule items come first in textbook order).
for _ in 1 2 3 4 5 6 7 8; do
  case "$current" in *'"exercise":221'*) break ;; esac
  item=$(echo "$current" | sed -n 's/.*"session_item_id":\([0-9]*\).*/\1/p')
  rev=$(echo "$current" | sed -n 's/.*"revision":\([0-9]*\).*/\1/p')
  current=$(api -d "{\"session_item_id\": $item, \"item_revision\": $rev}" \
    "$base/api/sessions/$sid/skip")
done
case "$current" in *'"exercise":221'*) ;; *) fail "never reached chain-rule item 221: $current" ;; esac
item=$(echo "$current" | sed -n 's/.*"session_item_id":\([0-9]*\).*/\1/p')
# MathJSON captured from Compute Engine 0.151.0 (raw form) for 18x\left(3x^2+1\right)^2.
cat > "$BODY" <<JSON
{"submission_id": "$(cat /proc/sys/kernel/random/uuid)", "session_item_id": $item,
 "item_revision": 0, "answer": {"kind": "expression", "latex": "18x(3x^2+1)^2",
 "mathjson": ["InvisibleOperator", 18, "x",
   ["Power", ["Delimiter", ["Add", ["InvisibleOperator", 3, ["Power", "x", 2]], 1]], 2]]}}
JSON
result=$(api --data-binary "@$BODY" "$base/api/sessions/$sid/submit")
case "$result" in
  *'"status":"correct"'*) ;;
  *) docker logs "$NAME" >&2; fail "submit was not graded correct: $result" ;;
esac

# The app writes its own request log; uvicorn's access log is off (no request logged twice).
if docker logs "$NAME" 2>&1 | grep -q '" [0-9][0-9][0-9]'; then
  docker logs "$NAME" >&2; fail "uvicorn access log is on: requests are logged twice"
fi
docker logs "$NAME" 2>&1 | grep -q '"route": "/api/sessions/{session_id}/submit"'   || fail "the app's request log has no line for the submit"

# Browser test on the production image. localhost, not 127.0.0.1: Chromium keeps the Secure
# session cookie over plain http only for localhost.
if [ "${E2E:-0}" = 1 ]; then
  BASE_URL=http://localhost:18000 npm run e2e --prefix tools     || { docker logs "$NAME" >&2; fail "browser e2e failed against the container"; }
fi

set +e
timeout 10 docker run --rm --name "$NAME-nosecret" "$IMAGE" >/dev/null 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ] || fail "started without MATHTUTOR_SECRET_KEY"
[ "$rc" -ne 124 ] || fail "still running after 10 s without MATHTUTOR_SECRET_KEY"

# compose reads env_file deploy/.env; supply the example if none exists.
if [ ! -f deploy/.env ]; then cp deploy/.env.example deploy/.env; CREATED_ENV=1; fi
SITE_ADDRESS=localhost docker compose -f deploy/compose.yaml --env-file deploy/.env.example config -q

echo "container smoke test: PASS"
