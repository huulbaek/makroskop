# MAKROskop

Public-facing explorer + license-free solver for MAKRO (DREAM's macroeconomic model
of Denmark, used by the Finance Ministry). Upstream model: `~/vserver/MAKRO`
(pristine clone — never modify; we read `Model/deep_dynamic_calibration.zip` and
`Model/Gdx/baseline.gdx` from it).

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Layout

- `app/` — SvelteKit static site (Svelte 5 runes, bun). Pages: Grundforløb (baseline),
  Scenarier (shock explorer), Pakker (`/pakke/`: policy packages as a linear superposition of
  solved shocks, `?Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm`; pure logic in
  `lib/package.ts`), Validering (two-solver comparison). Build: `bun run build`.
- `etl/` — Python (uv). `extract.py` writes `app/static/data/*.json` from GDX files.
  `freesolver.py` is the license-free solver: parse / check / jacobian / newton /
  oracle / solve-export / export-baseline. Cache in `etl/cache/` (regenerable).
- Deploy: `Dockerfile` (bun build → nginx) as a Dokploy Application on the `nodalit` host
  (ssh alias; UI ployduck.nodalit.com), domain makroskop.nodalit.com; push to `main` redeploys.
- `cloud/` — Hetzner box workflow: `pack.sh` (local bundle) → `setup.sh` → `run.sh` /
  `run_batch2.sh` (checkpointed, resumable scenario batches). See `cloud/README.md`.

## Critical knowledge (learned the hard way)

- Solver scenarios MUST be compared against `etl/shock_gdx/_reference.gdx` (the zip's
  calibration point), never `baseline.gdx` — they differ 0.3–9% on levels. extract.py
  handles this automatically when `_reference.gdx` exists.
- Full-horizon (2.2M eq) direct factorization needs ~64GB → rented Hetzner box
  (CCX43/53, x86, Ubuntu). A 16GB laptop manages ≤ ~12-year windows.
- Linear solvers: verified backend chain in `make_direct_solver` (Pardiso probe-tested,
  falls back to UMFPACK/kvxopt — the reliable workhorse — then SuperLU). Never trust an
  unverified Pardiso factorization. Rows are equilibrated; refinement runs to 1e-11.
- Newton needs non-monotone acceptance (NPV variables legitimately spike the residual
  on full steps) + adaptive shock-size continuation with per-stage disk checkpoints.
  The spike allowance (1000× start residual) is a coin flip on the full horizon —
  legitimate tBund steps spiked 500–800× — so `solve_window` also has *look-ahead*
  acceptance: a chord follow-up step with the LU in hand; if it lands below the start
  residual the full step is kept. Never backtrack to tiny alpha on this system: it never
  recovers and each attempt burns a factorization (batch2.log, 2026-08-25/26).
  Continuation stages start from a *secant predictor* (extrapolation of the last two
  converged stages; the checkpoint carries `prev_x`/`prev_share`), falling back to the
  zero-order start when its residual is lower — 2–80× smaller start residuals on the
  12-year test, identical solution to 1e-11.
- THE POLE: in the calibration configuration the implied-rate j-terms `jrUdlAktRenter`,
  `jrUdlPasRenter`, `jrUdlAktOmv`, `jrUdlPasOmv` are endogenous (`jr = income·fv/stock − r`),
  and `vUdlAkt(Obl)` crosses zero in 2064/65 → jr has a pole that every shock moves. That
  single equation instance caused all the "line search failed"/tiny-alpha grinds (found with
  the worst-residual diagnostic, 2026-08-26). `Window` drops those equations and freezes the
  j-terms (`POLE_JTERMS`) — exact for all other variables since the j-terms appear nowhere
  else; frozen j-terms export at reference values. Diagnose future stalls the same way: read
  the `worst residual (...)` lines before touching the solver.
- KEEP `pardiso` FIRST in the backend chain even though its factorizations get rejected:
  importing pypardiso loads MKL, and UMFPACK's BLAS then runs on MKL (parallel,
  `openmp_worker` threads). kvxopt's bundled OpenBLAS is a serial build, so
  `FREESOLVER_BACKEND=umfpack,...` makes full-horizon factorizations 4–5× slower
  (1400–2700 s vs 330–680 s on the same box). Don't set OPENBLAS/OMP_NUM_THREADS either.
- Long box runs: launch batch scripts with `setsid nohup`; a dead parent shell silently
  ends the batch after the current scenario. `cloud/relaunch_after_stage.sh` restarts a
  batch at the next checkpoint (e.g. after pushing a new freesolver.py) without losing work.
- GAMS oracle runs (freesolver oracle) need the user's personal GAMS license
  (network-validated → run Bash with sandbox disabled) and gamspy_base's `gams` binary.
- GAMS gotcha: `*` is a comment only in column 1; indented `*` is multiplication.
- Memory safety on 16GB laptops: run factorizations in killable subprocesses or with
  swap-growth watchdogs; the first uncapped run swap-froze and crashed the machine.
- Shock design: instruments must be exogenous (`is_fixed`). Mapped: tBund, tAMbidrag,
  tSelskab, tEjd, uG (offentligt forbrug), uvOvfSats (overførsler), uXMarked, nPop
  (single ages), rRenteECB, pOlieBrent (NB: propagates to almost nothing in this
  configuration — needs the foreign-price bundle from standard_shocks.gms).
- Labour supply (makroskop-6wz): `uDeltag`/`uh` are DISUTILITY parameters — `shLHh = 1/uh`
  exactly, and `uDeltag` sits on the cost side of the participation FOC — so ×1.01 LOWERS
  labour supply. DREAM's Arbejdsudbud shocks are exo/endo swaps; reproduce them with
  `--shock-name snLHh --endogenize uDeltag --shock-factor 1.01` (fixes the target
  instance-for-instance and frees the parameter; verified +1.0000 % on all ages, 11-year
  window) and `--shock-name uh --shock-factor 0.990099` (= 1/1.01).
- Financed closure (makroskop-b8o): in the calibration zip `tLukning` is FREE (=0) and the revenue
  `vtLukning(tot,t)` is data-fixed — not the other way round. `--closure tax-reaction` frees
  vtLukning and appends DREAM's two linear equations (tLukning[t] = tLukning[2129]; vOff13Net/vBNP
  at 2129 = reference) as `ExtraEquations` rows on the Window (`window.residuals/jacobian_csc`);
  the last model year is 2129, not 2130. `System.jacobian_csc` shape follows `len(free_ids)`.

## Conventions

- Danish-first UI; MAKRO brand teal #14AFA6 is UI-only, never a chart series color.
- Scenario GDX naming: `<CatalogShockName><variant>.gdx` (e.g. `Bundskat_ufin.gdx`)
  matching `etl/catalog.py` SHOCKS + VARIATIONS; `_ufin` = no fiscal reaction.
- Commit style: descriptive body, Claude-Session trailer.
