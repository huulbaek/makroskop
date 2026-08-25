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
  Scenarier (shock explorer), Validering (two-solver comparison). Build: `bun run build`.
- `etl/` — Python (uv). `extract.py` writes `app/static/data/*.json` from GDX files.
  `freesolver.py` is the license-free solver: parse / check / jacobian / newton /
  oracle / solve-export / export-baseline. Cache in `etl/cache/` (regenerable).
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
- GAMS oracle runs (freesolver oracle) need the user's personal GAMS license
  (network-validated → run Bash with sandbox disabled) and gamspy_base's `gams` binary.
- GAMS gotcha: `*` is a comment only in column 1; indented `*` is multiplication.
- Memory safety on 16GB laptops: run factorizations in killable subprocesses or with
  swap-growth watchdogs; the first uncapped run swap-froze and crashed the machine.
- Shock design: instruments must be exogenous (`is_fixed`). Mapped: tBund, tAMbidrag,
  tSelskab, tEjd, uG (offentligt forbrug), uvOvfSats (overførsler), uXMarked, nPop
  (single ages), rRenteECB, pOlieBrent (NB: propagates to almost nothing in this
  configuration — needs the foreign-price bundle from standard_shocks.gms).

## Conventions

- Danish-first UI; MAKRO brand teal #14AFA6 is UI-only, never a chart series color.
- Scenario GDX naming: `<CatalogShockName><variant>.gdx` (e.g. `Bundskat_ufin.gdx`)
  matching `etl/catalog.py` SHOCKS + VARIATIONS; `_ufin` = no fiscal reaction.
- Commit style: descriptive body, Claude-Session trailer.
