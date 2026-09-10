# Share cards for scenario views

Date: 2026-09-10. Status: approved in chat, spec for review before planning.

## Goal

A link to one scenario view — shock, closure variant and scale, e.g. the ECB hike as
`/scenarier/Rente_ufin/0.5/` — must unfurl in Slack, X, LinkedIn, Facebook, WhatsApp, iMessage,
Bluesky and Mastodon with a title, description and image that state *that view's* result.
Today every such link shows the generic Scenarier card, because the site is static and crawlers
do not run JavaScript.

Justification for the framing: the shock-year probe (makroskop-azw, 2026-09-10) showed that a
Rente shock solved from 2027 and from 2030 agree within 1–3 % on all headline series when
aligned by years since the shock. The published 2030 runs can therefore be presented as
"year 1, year 2, …" after the shock.

## Non-goals

- No change to the solver, the data pipeline or the nginx config.
- No years-since-shock axis on the page's charts (separate decision).
- No per-shock "lead metric" tile (possible follow-up: house prices for Rente).
- No dark-theme image: a static card cannot follow the viewer's theme.

## URLs and routes

- `/scenarier/<scenario>/` — the solved size. `<scenario>` is the GDX stem, e.g. `Rente_ufin`.
- `/scenarier/<scenario>/<skala>/` — one page per allowed scale step, `<skala>` written as the
  JavaScript number (`0.5`, `-0.75`, `1.25`, `2`). Step `1` has no page: it is the bare route.
- New SvelteKit route `src/routes/scenarier/[scenario]/[[skala]]/` with `+page.server.ts`
  (`prerender = true`, `entries()`, `load()`) and `+page.svelte`. `entries()` lists every
  `(scenario, skala)` from `static/data/meta.json` (`shocks[].available`) and the scenario
  files' `definition.maxScale` (a cap trims both signs). Expected count: 78 scenarios × up to 12
  steps ≈ 940 pages.
- `/scenarier/` and its `?stod=&variant=&skala=` deep links keep working unchanged.
- `permalink()` in `lib/export.ts` and the page's "Kopiér link" emit the path form; the
  `?stod=` form is no longer produced.

## Page behaviour

- `load()` runs only at build time (adapter-static, prerender). It returns `card`: title,
  description, image URL, image alt, canonical URL (also used as `og:url`), and the initial selection
  `{ name, variation, scale }`. It does NOT return the scenario data: SvelteKit would inline
  it into every page (~55 KB each). The page fetches the scenario JSON on the client exactly
  as the deep-link path does today; until it arrives the page shows the shell and the card's
  three numbers, never the demo scenario.
- The Scenarier page body moves into `src/lib/components/ScenarioExplorer.svelte` with props
  `{ meta, initial?: { name, variation, scale } }`; `/scenarier/+page.svelte` and the new
  route both render it. Behaviour of the existing page is unchanged (same URL sync, share
  row, exports).
- `+layout.svelte` emits the meta tags. When `page.data.card` is present it uses the card's
  title, description, image, alt, `og:url` and `<link rel="canonical">`; otherwise the
  current per-page defaults. The new route's `+page.svelte` sets `<title>` to the card title
  (pages own `<title>` today; the bare route keeps "Scenarier · MAKROskop"). Exactly one of
  each tag is emitted.

## Card content (`src/lib/card.ts`, pure, unit-tested)

Inputs: `ShockMeta`, `Scenario` (definition + deviations), `Meta` (variations, year range,
model name), baseline levels for `nL` and `vBNP` in the shock year, and `scale`.

- **Change in words** — the page's rule: `delta ≠ 0` → `±x pct.-point`, else `±(factor−1)·100
  pct.`, times `scale`, Danish formatting (`formatSigned`).
- **Instrument name** — `definition.instrumentDa` when it is 24 characters or shorter, else
  the shock's `labelDa` (e.g. "Udenlandske priser" instead of the long import-price label).
- **Profile word** — `_perm`/`_ufin`: "varigt"; `_midl`: "midlertidigt"; `_blip`: "i ét år".
- **Closure word** — `_perm`: "finansieret via lukkeskat"; otherwise "ufinansieret".
- **Three fixed tiles** (years counted from `definition.firstYear` = year 1):
  1. `BNP, år 3` — `qBNP` deviation in year 3, "pct.".
  2. `Beskæftigelse, år 1` — `nL` deviation in year 1 converted to persons:
     `pct / 100 × nL_baseline(firstYear) × 1000`, rounded to the nearest 100 (nearest 10 below
     1 000), "personer".
  3. `Offentlig saldo, år 1` — `saldo2bnp` deviation in year 1, "pct. af BNP".
  A missing series renders the tile as "–" and the number is left out of the text.
- **Number format** — one decimal when |v| ≥ 0.1, two decimals otherwise, always signed,
  Danish separators. All values are already multiplied by `scale`.
- **Title** — `<instrument> <change>: BNP <tile1> efter 3 år`, e.g.
  "ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år".
- **Description** — one paragraph:
  "Hvad sker der i MAKRO, hvis <instrument> <profile word> ændres med <change>?
  Beskæftigelse <tile2> i år 1, offentlig saldo <tile3>, BNP <tile1> efter 3 år.
  <Closure word, capitalised>. MAKROs standardstød (stødår <firstYear>) vist som år efter stødet<scaling>."
  `<scaling>` is empty at scale 1, ", lineært skaleret" for other positive scales, and
  ", spejlet stød (lineær tilnærmelse)" for negative scales.
- **Image alt** — the description's first sentence plus "Tre nøgletal: BNP efter 3 år,
  beskæftigelse og offentlig saldo i år 1."
- **Paths** — `viewPath(name, variation, scale)` and `parseSkala(param)` round-trip every
  allowed step; `shareViews(meta, definitions)` is the list `entries()` uses.

## Image

1200 × 630 PNG, light palette only, the editorial system of the existing `static/og.png`:

- Ground, ink, muted ink, rule and series-1 blue are the light-theme values from `app.css`,
  copied into `card.ts` with a comment naming the tokens.
- Wordmark "MAKROskop" top-left (Newsreader, teal "skop" as on og.png). Kicker to its right in
  muted IBM Plex Sans: "Scenarie · <closure word> · stødår <firstYear>, vist som år efter stødet".
- Headline: `<instrument> <change>` in Newsreader SemiBold, 72 px, at most two lines; the
  profile word as a muted 28 px subline ("Varigt stød" / "Midlertidigt stød" / "1-årigt stød").
- A faint `qBNP` sparkline for years 0–15 after the shock (300 × 110 px, series blue at 60 %
  opacity, zero line) to the right of the headline. Texture, not the message.
- Three tiles across the lower half: label (Plex Sans Medium 22 px, muted), value
  (Newsreader 84 px, ink), unit (Plex Sans 26 px, muted). Negative values keep the true minus.
- Footer rule; left "MAKRO 2026-June · MAKROskops frie løser" (muted 22 px), right
  "makroskop.nodalit.com" (Plex Mono).
- Layout order of the tiles is Beskæftigelse · BNP · Offentlig saldo, so the BNP tile — the
  title's number — sits in the centre. Square crops are rare (Slack, X, LinkedIn, Facebook and
  WhatsApp show 1.91:1 or 2:1) and a centred BNP tile still carries the message in one.
- Safe zone: all text inside 72 px margins.

## Generation

- `app/scripts/og-images.ts`, run by `bun run build` after `vite build`
  (`"build": "vite build && bun run scripts/og-images.ts"`). It reads `static/data/meta.json`,
  `static/data/shocks/*.json` and `static/data/baseline.json`, calls `card.ts` for each view,
  renders an SVG string and rasterises it with `@resvg/resvg-js` to
  `build/og/<scenario>.png` and `build/og/<scenario>_<skala>.png` (`0.5` → `0.5`, `-0.75` →
  `-0.75`). Head tags reference `https://makroskop.nodalit.com/og/<file>`.
- Fonts vendored under `app/fonts/` as static TTF instances with their OFL licence files:
  Newsreader Medium and SemiBold, IBM Plex Sans Regular and Medium, IBM Plex Mono Regular.
  Static instances, not variable fonts: resvg ignores variation axes.
- The script fails the build loudly if any view cannot be rendered or a font is missing.
- Images are build artefacts, never committed. Expected ≈ 940 files, ≈ 35 MB, under a minute.
- Dockerfile unchanged: it already runs `bun run build`.

## Error handling

- `entries()` only lists scenarios whose JSON exists; a scenario named in meta.json without
  a file fails the build with the name in the message.
- A view whose scenario lacks `qBNP`, `nL` or `saldo2bnp` still builds; the tile shows "–".
- On the client, a failed scenario fetch on the new route shows the existing "endnu ikke
  beregnet" state, not the demo.

## Testing

- `src/lib/card.test.ts` (vitest): title, description, alt and tiles for Rente_ufin at scale
  1, 0.5 and −0.5 using fixture data; persons rounding; `_blip`/`_midl` wording; instrument
  fallback to `labelDa`; `viewPath`/`parseSkala` round-trip for all 12 steps; `shareViews`
  honours `maxScale`.
- `scripts/og-images.test.ts`: renders one card through resvg and asserts a 1200 × 630 PNG.
- `scripts/verify-build.ts`: after `bun run build`, counts `build/scenarier/*/index.html`
  pages and `build/og/*.png`, and asserts that `build/scenarier/Rente_ufin/0.5/index.html`
  carries exactly one `og:title`, `og:description`, `og:image` and `<title>`, and that
  `build/scenarier/index.html` still carries the generic ones.
- Manual: `docker build` locally and open one page; check the unfurl with a Slack DM to self
  and with opengraph.xyz; check the PNG in the browser at feed size.

## Risks

- `@resvg/resvg-js` under bun in the `oven/bun:1` image: the platform package for
  linux-x64-gnu must be in `bun.lock`. Verified by the local `docker build` before pushing.
- HTML volume: ≈ 940 pages × ≈ 40 KB shell ≈ 40 MB, plus images ≈ 35 MB. Acceptable for nginx;
  if it ever matters, trim the scale steps that get pages.
- Build time: prerendering ≈ 940 pages plus rendering; expected 1–3 extra minutes.
- The Scenarier page refactor into a component must not change behaviour; verified by the
  existing browser checks (URL sync, share row, CSV/PNG export) on both routes.
