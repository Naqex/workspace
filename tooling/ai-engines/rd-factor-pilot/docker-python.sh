#!/bin/sh
set -eu
test "$#" -eq 1 && test "$1" = "$PWD/factor.py"
: "${NAQEX_RD_IMAGE:?}" "${NAQEX_RD_DATA:?}"
name="naqex-rd-factor-$$"
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT INT TERM
timeout --foreground 50s docker run --rm --pull never --name "$name" \
  --network none --read-only --user 1000:1000 --cpus 1 --memory 512m \
  --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --mount "type=bind,src=$PWD,dst=/work" \
  --mount "type=bind,src=$NAQEX_RD_DATA,dst=$NAQEX_RD_DATA,readonly" \
  --env OPENBLAS_NUM_THREADS=1 --env OMP_NUM_THREADS=1 \
  "$NAQEX_RD_IMAGE" python /work/factor.py
