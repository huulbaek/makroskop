# Pakke-værksted — design

Date: 2026-09-03 · Bead: makroskop-snl · Status: approved by assumption (autonomous
session; every decision below is stated so the user can override it).

## Purpose

A page where a reader combines several catalog shocks into one *policy package* — e.g.
"bundskat −1 pct.-point, offentligt forbrug +0,5 pct., overførsler +1 pct." — and reads
off what MAKRO says about it: BNP, beskæftigelse, offentlig saldo, and which part of the
package drives which effect. Audience: party/policy staff ("cost my proposal the way
FM would") and journalists (a permalink and a one-line source stamp per chart).

The package is computed in the browser as a **linear superposition** of already-solved
scenarios: `dev_pakke(key, t) = Σ_i scale_i · dev_i(key, t)`. It is *not* a new model run.
The Scenarier page already does the single-shock version of this (the ×-slider), and the
measured linearity error is ~1–2 % per shock (makro-linearity memory). Interaction terms
between shocks are not measured and are assumed second-order; the caveat is on screen.

## Scope

In:
- New route `/pakke/` ("Pakker" in the nav, eyebrow "Pakke-værksted").
- Component picker: the catalog grouped as on Scenarier; toggle a shock into the package.
- Per component: signed size slider (same steps and per-shock `maxScale` caps as
  Scenarier's slider: −1 … +2 in 0.25 steps; negative = mirrored), readout in the
  instrument's own units, remove button.
- Package-level closure: **Finansieret** (`_perm`, default) or **Ufinansieret** (`_ufin`).
  One closure for the whole package; shocks without that variant are greyed in the picker
  (today: Rente is `_ufin`-only; Oliepris and KapitalProd have no data).
- Headline tiles for three years (2030 = first shock year, 2035, 2050): BNP (pct. and
  mia. 2020-kr.), beskæftigelse (pct. and personer), offentlig saldo (pct.-point af BNP and
  mia. kr.). In financed mode also the lukkeskat reaction (pct.-point).
- Charts (package total): BNP, beskæftigelse, offentlig saldo (pct. af BNP), privat
  forbrug, boligpriser, timeløn, ledighedsgrad, offentlig nettoformue — the same
  LineChart as Scenarier, 2029–2060.
- Contribution table: one indicator at a time (chip: BNP / Beskæftigelse / Saldo), rows =
  components + total, columns = the three headline years.
- Permalink (`?Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm`, address bar kept in
  sync), CSV export of every charted series with provenance + component list, PNG per
  chart with header/footer stamp (existing `svgToPngBlob`).
- Three example packages as links on the empty state, so the page is not blank.

Out (YAGNI): free-text sizes in instrument units (the stepped slider already maps to
units), temporary profiles (`_midl`/`_blip`, unfinanced-only and not yet solved), saving
packages server-side, per-component lines in charts (the table carries the decomposition),
English UI, HBI (not available for solver scenarios).

## Design

### Data
No new ETL. Each component loads its scenario JSON on demand
(`/data/shocks/<name><variant>.json`, ~50 KB) into a client-side cache keyed by file.
Switching closure reloads the files for the other suffix. The baseline (`baseline.json`)
is loaded once for the kr./persons conversions.

### Pure module `app/src/lib/package.ts` (unit-tested)
- `parsePackageQuery(params, shocks, variations)` → `{ components: {name, scale}[], variant }`.
  Param name = shock name, value = scale; unknown names, non-finite or zero scales are
  dropped; `variant` must be a known suffix else `_perm`. Order of params = order of
  components.
- `packageQuery(components, variant)` → search string, inverse of the above; the default
  variant is still written so the link is self-describing.
- `superpose(parts: {scale, values}[])` → `(number|null)[]`: null where *any* part is
  null, else the weighted sum. Scale 1 with one part returns the values unchanged.
- `scaleSteps(maxScale)` → the allowed slider steps (moved out of the Scenarier page so
  both pages share it; Scenarier keeps its own copy untouched in this change to limit
  blast radius — a follow-up can dedupe).
- `headline(dev, baseline, year)` helpers: `pctToLevel(pct, base)` (BNP mia., employment
  persons), `gdpPpToKr(pp, vBNP)`.
- `packageLine(components, closureLabel)` → the one-line description used in exports and
  the page ("Bundskat ×−1 (−1 pct.-point) + Offentligt forbrug ×0,5 (+0,5 pct.) — permanent,
  finansieret").

### Page `app/src/routes/pakke/+page.svelte`
State: `components` (ordered), `variant`, `cache` (Map), `loading`. Derived: the loaded
scenarios, `package` deviations per chart key, headline numbers, contribution rows,
share URL, provenance, scenario line. `$effect` keeps the address bar in sync via
`replaceState`. `onMount` parses the URL. Charts, tiles, share row, PNG/CSV buttons reuse
the Scenarier patterns and `export.ts` (a `packagePermalink`/`packageFilename` pair is
added next to the existing helpers).

Nav: layout gets a fourth link. Scenarier gets a small "Læg i en pakke →" link next to the
share row, pointing at `/pakke/?<name>=<scale>&variant=<variant>`, so single-shock views
flow into the composer.

### Caveats on screen
A "Sådan er pakken regnet" card: linear superposition, not a model run; per-shock
linearity ~1–2 %; interactions not measured; negative sizes are mirrored increases;
closure applies to every component; all sizes relative to MAKROskop's own shock sizes
(not DREAM's 1 %-of-GDP normalisation). Version-mismatch banner as on Scenarier if any
component was solved on another MAKRO version.

### Error handling
A component whose file fails to load shows "kunne ikke hentes" on its row and is excluded
from the sums (the tiles say "n af m stød indlæst"). A shock without the chosen variant
cannot be added; if the closure is switched and a component has no variant for it, the
component stays in the list, greyed, and is excluded until switched back.

### Testing
- vitest: `package.test.ts` for parse/serialize round-trip, superpose (nulls, scales,
  single part identity), conversions, packageLine.
- `svelte-check` and `bun run build` clean.
- Browser check of the built site: add two shocks, change a size, switch closure, copy
  link, reload link reproduces the view, CSV and PNG download.

## Decisions taken without the user (override any of them)
1. Closure is package-wide, financed by default. Mixing closures inside one package would
   make the saldo meaningless.
2. Sizes are the stepped slider, not free numbers, so the per-shock caps and the mirrored
   flag keep working unchanged.
3. Decomposition lives in a table, not in the charts, to keep charts screenshot-clean.
4. URL format uses the shock name as the parameter name for readability.
5. Headline years 2030/2035/2050 (first year, medium run, long run).
