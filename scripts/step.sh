#!/usr/bin/env bash
# Run a command and save its full output to logs/<name>.log, so Claude can read it.
# Usage: scripts/step.sh <name> <command...>
set -o pipefail
name="$1"; shift
mkdir -p logs
{ echo "\$ $*"; echo "started $(date '+%Y-%m-%d %H:%M:%S')"; } > "logs/$name.log"
"$@" 2>&1 | tee -a "logs/$name.log"
code=${PIPESTATUS[0]}
echo "exit code $code, finished $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "logs/$name.log"
exit "$code"
