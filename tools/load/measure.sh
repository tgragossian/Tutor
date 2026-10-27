#!/usr/bin/env bash
# Task 16 memory sizing, run on the host from /srv/mathtutor:
#   bash tools/load/measure.sh https://tutor.thomasgragossian.dev
# Samples memory once a second while submit_burst.py runs, then prints the peaks to paste
# into docs/ops/host.md. The burst leaves 16 accounts named load_<run>_NN in the database.
set -euo pipefail

BASE_URL=${1:?usage: bash tools/load/measure.sh <base-url> [users] [grading|help] [help-users]}
USERS=${2:-16}
# Optional: "help" also fires HELP_USERS hint requests at the same moment and reports grading
# and help latency separately (milestone C1 task 15).
MODE=${3:-grading}
HELP_USERS=${4:-20}
APP=deploy-app-1
OUT=$(mktemp -d)

echo "== before"
free -m
sudo docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}'

sample() {
  while :; do
    sudo docker stats --no-stream --format '{{.Name}} {{.MemUsage}}' >> "$OUT/stats"
    free -m | awk '/^Mem:/ {print $7}' >> "$OUT/available"
    sleep 1
  done
}
sample &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true; rm -rf "$OUT"' EXIT

sleep 2  # a baseline sample before the burst
# Keep the burst's exit status (review B-R4): memory is still printed for a failed run, but
# the script then exits non-zero so the numbers are not mistaken for a usable sizing run.
rc=0
python3 tools/load/submit_burst.py --base-url "$BASE_URL" --users "$USERS" \
  --mode "$MODE" --help-users "$HELP_USERS" || rc=$?
sleep 3  # catch the tail of the burst
kill "$SAMPLER" 2>/dev/null || true
wait "$SAMPLER" 2>/dev/null || true

echo "== peak container memory (docker stats)"
awk '{print $1, $2}' "$OUT/stats" | sort -k1,1 -k2,2h \
  | awk '{peak[$1] = $2} END {for (k in peak) print "  " k, peak[k]}'

echo "== peak RSS per process in $APP since it started (VmHWM; MiB)"
# docker top prints host PIDs; the spawned verifier worker's command line mentions multiprocessing.
sudo docker top "$APP" -o pid,args | awk 'NR > 1' | while read -r pid args; do
  kind=app; case "$args" in *multiprocessing*) kind=worker ;; esac
  hwm=$(sudo awk '/^VmHWM:/ {print $2}' "/proc/$pid/status" 2>/dev/null || echo 0)
  echo "  $kind pid $pid: $((hwm / 1024)) MiB"
done

echo "== lowest available memory during the run (MiB)"
sort -n "$OUT/available" | head -1 | sed 's/^/  /'

echo "== after"
free -m

if [ "$rc" -ne 0 ]; then
  echo "FAIL: the burst failed (exit $rc); do not use these numbers for sizing" >&2
fi
exit "$rc"
