# Pakke-værksted Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `/pakke/` page that superposes several solved catalog shocks (signed sizes, one closure) into a policy package with headline tiles, charts, a contribution table, permalink and CSV/PNG export.

**Architecture:** A pure, unit-tested module `app/src/lib/package.ts` does URL parsing/serialising, superposition and unit conversions. A single Svelte 5 page `app/src/routes/pakke/+page.svelte` holds the state (components, variant, scenario cache) and reuses `LineChart`, `StatTile` and `export.ts`. No ETL changes.

**Tech Stack:** SvelteKit static (Svelte 5 runes), TypeScript, vitest, bun. Danish-first UI.

**Spec:** `docs/superpowers/specs/2026-09-03-pakke-vaerksted-design.md`

## Global Constraints

- Danish-first UI; MAKRO teal (`--makro`) is UI-only, never a chart series colour.
- Conservative git profile: do **not** commit; report changed files at the end.
- Existing `Scenarier` behaviour must not change except for the added "Læg i en pakke" link.
- Tests: `cd app && bun run test`; types: `bun run check`; build: `bun run build`.

---

### Task 1: Pure package module (TDD)

**Files:**
- Create: `app/src/lib/package.ts`
- Test: `app/src/lib/package.test.ts`

**Interfaces (produces):**
```ts
export interface PackageComponent { name: string; scale: number }
export const ALL_SCALE_STEPS: number[]           // [-1,-0.75,…,2]
export function scaleSteps(maxScale: number | null | undefined): number[]
export function parsePackageQuery(params: URLSearchParams, shockNames: Iterable<string>, variantSuffixes: Iterable<string>, defaultVariant?: string): { components: PackageComponent[]; variant: string }
export function packageQuery(components: PackageComponent[], variant: string): string   // "Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm"
export function superpose(parts: { scale: number; values: (number | null)[] }[]): (number | null)[]
export function pctToLevel(pct: number | null, base: number | null | undefined): number | null   // base * pct/100
export function gdpPpToKr(pp: number | null, vBNP: number | null | undefined): number | null    // vBNP * pp/100
export function packageLine(items: { labelDa: string; scale: number; changeDa: string }[], closureLabel: string): string
```

- [ ] Step 1: write `package.test.ts` (round-trip, invalid values dropped, unknown names dropped, variant fallback, superpose nulls/weights/identity, conversions, packageLine wording incl. mirrored marker)
- [ ] Step 2: `bun run test` → fails (module missing)
- [ ] Step 3: implement `package.ts`
- [ ] Step 4: `bun run test` → passes

### Task 2: Export helpers for packages

**Files:**
- Modify: `app/src/lib/export.ts` (add `packagePermalink(origin, query)` and `packageFilename(components, variant, key, ext)`)
- Test: `app/src/lib/export.test.ts` (append cases)

- [ ] Step 1: tests: `packagePermalink('https://x.dk','Bundskat=-1&variant=_perm')` → `https://x.dk/pakke/?Bundskat=-1&variant=_perm`; `packageFilename([{name:'Bundskat',scale:-1},{name:'Moms',scale:1}],'_perm','qBNP','png')` → `makroskop_pakke_Bundskat_x-1_Moms_perm_qBNP.png`
- [ ] Step 2: run → fail; implement; run → pass

### Task 3: The page

**Files:**
- Create: `app/src/routes/pakke/+page.svelte`, `app/src/routes/pakke/+page.ts` (loads `baseline.json`)
- Modify: `app/src/routes/+layout.svelte` (nav link `Pakker`), `app/src/routes/scenarier/+page.svelte` (link "Læg i en pakke →" in the share row)

Behaviour (from spec): picker aside grouped by `shock.group`; toggle adds `{name, scale: 1}` and loads `/data/shocks/<name><variant>.json` into a `Map` cache; closure chips `_perm`/`_ufin`; rows with range slider (`scaleSteps(def.maxScale)`), readout `×s = change`, "spejlet" badge, remove button; tiles for 2030/2035/2050 (BNP pct + mia. 2020-kr., beskæftigelse pct + personer, saldo pp + mia. kr., lukkeskat pp in financed mode); charts (`qBNP nL saldo2bnp qC pBolig vhW ledighedsgrad nettoformue2bnp`) from `superpose`; contribution table with indicator chips; share row (copy link, CSV, PNG per chart); method card with the caveats; empty state with three example links; version-mismatch banner.

- [ ] Step 1: write `+page.ts` and `+page.svelte`
- [ ] Step 2: `npx @sveltejs/mcp svelte-autofixer` on the file, `bun run check`, `bun run build`
- [ ] Step 3: browser check on `bun run preview`: add/remove, slider, closure switch, permalink reload, CSV, PNG

### Task 4: Wrap-up
- [ ] `bun run test`, `bun run check`, `bun run build` all green
- [ ] `bd close makroskop-snl`; report changed files and suggested commit
