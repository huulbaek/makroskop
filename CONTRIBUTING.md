# Contributing to MAKROskop

Thanks for your interest. Bug reports, corrections to economic labels and explanations,
and solver improvements are all welcome.

## Filing issues

Use GitHub Issues. The maintainers track their own work with
[beads](https://github.com/gastownhall/beads) (`bd`), whose config lives in `.beads/`;
you do not need it, and issues filed on GitHub are mirrored as needed.

## Development

- `app/`: `bun install`, `bun run dev`, `bun run test`, `bun run check`. Svelte 5 with
  runes; Danish-first UI. The MAKRO brand teal `#14AFA6` is reserved for UI chrome and is
  never a chart series colour.
- `etl/`: `uv run python extract.py`. Needs a MAKRO checkout (default `../MAKRO`). Never
  modify that checkout; the ETL only reads from it.
- Tests: `bun run test` in `app/`. Run `bun run check` before opening a pull request.

## Things that are easy to get wrong

These are documented in more depth in `CLAUDE.md`, which also serves as the maintainer notes.

- **Reference path.** Solver scenarios must be compared against `etl/shock_gdx/_reference.gdx`
  (the zip's calibration point), never `baseline.gdx`. The two differ by 0.3–9 % on levels.
- **Naming.** Scenario GDX files are `<CatalogShockName><variant>.gdx` and must match
  `etl/catalog.py`.
- **Solver backends.** Keep `pardiso` first in the backend chain even where its factorizations
  are rejected: importing it loads MKL, which makes UMFPACK 4–5× faster.
- **Model versions.** All scenarios are deviations from one model version. When the upstream
  zip changes, every scenario must be re-solved and published together with the new baseline.
  See `cloud/README.md`.
- **Labour supply and financing.** The `uDeltag`/`uh` parameters are disutilities, so scaling
  them up lowers labour supply. The financed closure adds two linear equations on top of the
  parsed system. Both are explained in `CLAUDE.md`.

## Pull requests

- Keep commits focused, with a descriptive body explaining the why.
- Do not commit anything under `etl/cache/`, `etl/shock_gdx/*.gdx` or the cloud bundle;
  they are ignored for a reason.
- Changes to the data JSON in `app/static/data/` should come from `extract.py`, not by hand.

## Agent instructions

`CLAUDE.md`, `AGENTS.md`, `.codex/` and `.agents/` hold instructions for AI coding agents
used in development. They are committed on purpose; treat `CLAUDE.md` as the project's
engineering notes.
