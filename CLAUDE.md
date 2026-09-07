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
- Deploy: `Dockerfile` (bun build → nginx), built by a Dockerfile-based PaaS from this repo;
  push to `main` redeploys the public instance. Host details: `bd memories deploy`.
- `cloud/` — rented-box workflow: `pack.sh` (local bundle) → `setup.sh` → `run.sh` /
  `run_batch2.sh` (checkpointed, resumable scenario batches). See `cloud/README.md`.

## Critical knowledge (learned the hard way)

- Solver scenarios MUST be compared against `etl/shock_gdx/_reference.gdx` (the zip's
  calibration point), never `baseline.gdx` — they differ 0.3–9% on levels. extract.py
  handles this automatically when `_reference.gdx` exists.
- Full-horizon (2.2M eq) direct factorization needs ~64GB → rented x86 Ubuntu box
  (see `cloud/README.md`). A 16GB laptop manages ≤ ~12-year windows.
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
- LU lifetime (makroskop-xn2): a full-horizon UMFPACK factorization peaks at 40–53 GB *on its own*
  (final LU ~28 GB, base 3–7 GB) on the 62 GB box, so a stale LU must never survive into the next
  factorization. `solve_window` owns the LU through `lu_holder` (taken out on entry, handed back on
  return) and clears `solve_fn`/`matrix`/`jac_window` before `make_direct_solver`; before that fix a
  rebuild held 2–3 LUs (61 GB, two OOM kills). Verified 2026-09-05 on Rente_perm: 15 factorizations,
  RSS back to 3–10 GB between each, peak 53.4 GB. Diagnose memory with 30 s RSS samples of the
  solver pid (`memtest/sample.sh` on the box), not with the end-of-run peak alone.
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
- Window convention (makroskop-7cd): `--from-year` is DREAM's shock_year — the first *solved* year;
  the year before stays at the reference like DREAM's fixed t0 (`set_time_periods(shock_year-1, ...)`
  only has equations for tx0). Batches 2-4 (all 75 published scenarios) used `--from-year 2029` for
  2030 shocks, so 2029 was solved as a free year and every shock was anticipated one year ahead:
  house prices, investment, hiring and wages move in 2029. Measured on an end-of-horizon replica
  (uXMarked +1 %): the anticipated run's year-1 wage response is 2.5× DREAM's and the employment
  peak is 22 % lower than the unanticipated run's. All 76 scenarios were re-solved with
  `--from-year 2030` on 2026-09-05..07 (`cloud/run_all_2030.sh`; `etl/verify_2030.py` checks the
  stamps and the zero-2029 invariant); the 2029 runs are parked in `etl/cache/parked/shock_gdx_2029`
  and on the box in `etl/shock_gdx_2029`. Comparisons with
  DREAM must also scale to their shock sizes (1 % of GDP: export market ×1.26, offentligt varekøb
  ×11.8, offentlig beskæftigelse ×6.55, bundskat ×1.88 of ours) — see `etl/dream_may2025.json`.
- The zip is the plain shock model: the CONVERT dump is `M_base` with `G_endo` (no `*_deep`
  calibration equations, `E_tLukning` present, `uDeltag`/`uh`/`rLoenNash`/`qProdHh_t` exogenous,
  `snLHh`/`shLHh` endogenous), evaluated at the deep-calibration point. Same endogeneity as
  DREAM's standard_shocks.gms — "calibration-configuration exogeneity" is not a source of gaps.

## Conventions

- Danish-first UI; MAKRO brand teal #14AFA6 is UI-only, never a chart series color.
- Scenario GDX naming: `<CatalogShockName><variant>.gdx` (e.g. `Bundskat_ufin.gdx`)
  matching `etl/catalog.py` SHOCKS + VARIATIONS; `_ufin` = no fiscal reaction.
- Commit style: descriptive body, Claude-Session trailer.
