# MAKROskop

A public-facing explorer for [MAKRO](https://github.com/DREAM-DK/MAKRO), the macroeconomic
model of Denmark that the DREAM group develops for the Ministry of Finance and others, plus a
**license-free solver** so new scenarios can be computed without GAMS/CONOPT.

Live instance (Danish UI): **https://makroskop.nodalit.com**

> **Dansk:** MAKROskop viser MAKROs grundforløb og stød-scenarier som afvigelser fra
> grundforløbet, lader dig sammensætte politikpakker af løste stød, og dokumenterer den frie
> løser mod GAMS/IPOPT. Ingen GAMS-licens kræves, hverken for at vise eller beregne.

## What it does

| Page | Content |
|---|---|
| **Grundforløb** | The model baseline: national accounts, labour market, public finances, sectors. |
| **Scenarier** | 38 standard shocks (taxes, transfers, public consumption, interest rate, foreign prices, labour supply, …) as deviations from the reference path, in financed and unfinanced variants. |
| **Pakker** | Policy packages as a linear superposition of solved shocks, with permalinks, contribution tables and CSV/PNG export. |
| **Validering** | The free solver cross-checked against GAMS/IPOPT and run at full scale: 2,197,277 equations over the whole horizon. |

## How it works

No GAMS license is needed at any step:

1. `Model/Gdx/baseline.gdx` and `Model/deep_dynamic_calibration.zip` from a MAKRO checkout are
   read with the pip-installable `gamsapi[transfer]` and `gamspy_base` (no GAMS installation).
2. `etl/extract.py` detrends with the model's `fvt/fqt/fpt` factors, computes key ratios and
   writes `app/static/data/*.json`. Shock scenarios in `etl/shock_gdx/*.gdx` become
   `app/static/data/shocks/<Name><variant>.json` as deviations from the reference.
3. `etl/freesolver.py` parses the model's unrolled equation system from the zip and solves
   shocks with Newton's method (non-monotone line search, adaptive shock continuation,
   checkpoints). Linear systems go through a verified backend chain, Pardiso → UMFPACK →
   SuperLU, with row equilibration and iterative refinement. Subcommands: `parse`, `check`,
   `jacobian`, `newton`, `oracle`, `solve-export`, `export-baseline`.
4. The web app is 100 % static and can be hosted anywhere.

A 10-year window (~200,000 equations) solves on a 16 GB laptop. The full horizon (2.2 million
equations) needs about 64 GB and runs on a rented machine; see `cloud/README.md` (Danish).

Shock deviations are **always** measured against `etl/shock_gdx/_reference.gdx`, the zip's
calibration point, which `extract.py` prefers automatically when the file exists. Scenario
files follow the catalogue in `etl/catalog.py`: `<Name><variant>.gdx`, e.g. `Rente_perm.gdx`
(`_perm` = permanent, financed through DREAM's closure tax; `_ufin` = unfinanced;
`_midl`/`_blip` = temporary profiles). Without real shock data the app shows a clearly
marked synthetic demo scenario (`--demo`).

## Repository layout

```
app/    SvelteKit (bun): static web app, adapter-static, Svelte 5 runes
etl/    Python (uv): GDX → JSON for the app, and freesolver.py (the free solver)
cloud/  Runbook and batch scripts for full-horizon solves on a rented 64 GB machine
docs/   Design notes and implementation plans
```

## Running it

```bash
# ETL (needs uv and a MAKRO checkout; default location ../MAKRO, or --makro-root)
cd etl
uv run python extract.py             # --demo for a synthetic shock

# Free solver: parse + residual check + a small shock on a 10-year window
uv run python freesolver.py parse
uv run python freesolver.py check
uv run python freesolver.py newton --from-year 2120 --perturb 1e-4

# App (needs bun)
cd ../app
bun install
bun run dev                          # or: bun run build && bun run preview
bun run test                         # vitest
bun run check                        # svelte-check
```

The data JSON is committed, so the app builds without running the ETL. The `oracle`
subcommand, which compares against GAMS, is the only path that needs a GAMS license.

## Deploying

The site is a static build served by nginx. `Dockerfile` in the repo root builds `app/`
with bun and copies `app/build` into `nginx:alpine` on port 80, with a health check on `/`.
Any container host that builds from a Dockerfile works; the public instance redeploys on
every push to `main`.

```bash
docker build -t makroskop .            # optional: --build-arg APP_COMMIT=$(git rev-parse --short HEAD)
docker run --rm -p 8089:80 makroskop
```

`APP_COMMIT` stamps the commit into the footer next to the model version and build date.
Set `VITE_SITE_HOST` at build time to change the host shown in export provenance stamps.

Publishing new scenarios: solve, run `extract.py`, commit the JSON, push.

## Attribution and license

MAKROskop is released under the MIT License, see `LICENSE`. The model and the data
this site derives from belong to
[DREAM](https://dreamgruppen.dk) and are published under the MIT License in the
[MAKRO repository](https://github.com/DREAM-DK/MAKRO). MAKROskop is an independent project
and is not affiliated with or endorsed by DREAM or the Danish Ministry of Finance.

Scenario deviations are computed from the calibration path in the model zip, not from
DREAM's official baseline, and the shock definitions differ from DREAM's standard
shocks (raw instrument changes rather than revenue-normalised ones). See the Validering
and Scenarier pages for the exact definitions.

## Contributing

See `CONTRIBUTING.md`.
