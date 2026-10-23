# Initial v5 run retained after a numerical failure

Performed offline 2026-10-23, frozen at the timestamp in `selection.json` before
replaying prior held-out inputs. This directory preserves the initial source,
training, freeze, decisions, counts and failures. It is **not the final revision**.

Differential acquisition divided FFT roundoff by effectively zero energy in empty
windows. All 30 zero-background synthetic controls failed acquisition, and two of
three clean capture starts failed. The initial 540 noisy synthetic starts were
all correct. A new independently constructed training-only zero-background burst
reproduced the bug; the final revision masks numerically unresolvable energies
using machine epsilon times total differential energy. No loop setting, candidate
budget or signal threshold was adjusted from held-out results.

The [final revision](../offline-tracking-v5/README.md) retains this run and reports
its sequential, retrospective status. Original v4 sources and results remain
unchanged. Rerun source files from this directory to reproduce the initial failure;
its relative dependencies match the sibling data directories.
