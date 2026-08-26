#!/bin/bash
# One-shot: wait for the running scenario to checkpoint its current stage, then restart
# run_batch2.sh so the updated freesolver.py (look-ahead acceptance) takes over from that checkpoint.
cd "$(dirname "$0")/.."
CK=$(ls -t etl/cache/ckpt_*.npz 2>/dev/null | head -1)   # the running scenario's checkpoint
M=$(stat -c %Y "$CK" 2>/dev/null)
P=$(pgrep -f "python3 freesolver.py" | head -1)             # the running scenario's solver process
echo "[relaunch] waiting for the next checkpoint of $CK (currently $(date -d @${M:-0} -Is)) or exit of pid $P"
# Trigger on a new checkpoint OR on that process ending (scenario finished or gave up) — not on
# "any solver running", or a stalled scenario would let the batch move on with the old code.
while [ "$(stat -c %Y "$CK" 2>/dev/null)" = "$M" ] && kill -0 "$P" 2>/dev/null; do sleep 10; done
echo "[relaunch] $(date -Is) stage checkpointed (or process ended); restarting with look-ahead solver"
pkill -f "bash cloud/run_batch2.sh"; sleep 1
pkill -f "freesolver.py solve-export"; sleep 6
pgrep -f "freesolver.py solve-export" >/dev/null && { echo "[relaunch] solver still alive, SIGKILL"; pkill -9 -f "freesolver.py solve-export"; sleep 3; }
echo "=== RELAUNCH $(date -Is): freesolver.py with look-ahead acceptance, resume from checkpoint ===" >> batch2.log
setsid nohup bash cloud/run_batch2.sh >> batch2.log 2>&1 < /dev/null &
sleep 5; pgrep -fa "run_batch2|freesolver.py solve-export" | cut -c1-90
