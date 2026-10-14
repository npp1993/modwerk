#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run under lockf -k /tmp/modwerk-check.lock. Emulator only; never connects to a unit.
# run-sites.sh EMULATOR BUILD NEW-OUT CARD PACKAGE [PACKAGE...]
set -euo pipefail
emulator=${1:?EMULATOR}; build=${2:?BUILD}; out=${3:?NEW-OUT}; card=${4:?CARD}; shift 4
first=${1:?PACKAGE}; shift
second=$(IFS=,; echo "$*")
mkdir "$out"
cp "$card" "$out/card.img"
socket_dir=$(mktemp -d)
pid=
cleanup() {
  if [ -n "$pid" ]; then kill "$pid" 2>/dev/null || true; fi
  rm -f "$out/card.img"
  rm -rf "$socket_dir"
}
trap cleanup EXIT
verifier=scripts/verify-octatrack-dsp-loader.mjs
read -r -a dumps <<< "$(node "$verifier" dumps "$build" "$out")"
"$emulator" --image "$build/MAIN.raw" --card "$out/card.img" --set MODWERK --project TEMPLATE   --mount --load-ms 20000 --frame --dsp --usb-host "$socket_dir/ot.sock" --usb-hold-ms 600000   "${dumps[@]}" > "$out/log.txt" 2>&1 &
pid=$!
while [ ! -S "$socket_dir/ot.sock" ]; do kill -0 "$pid"; sleep 0.2; done
node "$verifier" drive "$socket_dir/ot.sock" "$build" sites "$first" "$second" | tee "$out/drive.txt"
wait "$pid"
pid=
node "$verifier" check "$build" "$out" sites
