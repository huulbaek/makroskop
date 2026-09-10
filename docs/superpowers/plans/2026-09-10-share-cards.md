# Share Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every scenario view (shock, closure variant, scale) gets its own prerendered page at `/scenarier/<scenario>/<skala>/` whose title, description and build-time og:image state that view's result.

**Architecture:** A pure module `src/lib/card.ts` turns one scenario view into copy, three headline tiles and paths; `src/lib/card-svg.ts` turns that into a 1200×630 SVG. A build step (`scripts/og-images.ts`, bun + resvg) rasterises one PNG per view into `build/og/`. A new SvelteKit route `[scenario]/[[skala]]` prerenders one page per view from `entries()`, returning only the head data; the Scenarier page body becomes a shared `ScenarioExplorer` component that both routes render. The layout swaps its meta tags when `page.data.card` is present.

**Tech Stack:** SvelteKit 2 (adapter-static, prerender), Svelte 5 runes, bun, vitest, `@resvg/resvg-js`, vendored static TTF fonts (OFL).

**Spec:** `docs/superpowers/specs/2026-09-10-share-cards-design.md`

## Global Constraints

- Danish-first UI copy; MAKRO teal `#0f9a92` is UI-only (wordmark), never a data colour.
- Svelte 5 runes only (`$props`, `$state`, `$derived`, `$effect`); bun for scripts and installs.
- URLs: `/scenarier/<scenario>/` for scale 1, `/scenarier/<scenario>/<skala>/` for other steps, `<skala>` written as the JavaScript number (`0.5`, `-0.75`, `1.25`, `2`); trailing slashes always.
- Scale steps: `[-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2]`, trimmed by `definition.maxScale` on magnitude.
- Tiles, in layout order: `Beskæftigelse, år 1` (persons), `BNP, år 3` (pct.), `Offentlig saldo, år 1` (pct. af BNP). Year 1 = `definition.firstYear`.
- Number format: one decimal when |v| ≥ 0.1 else two, signed, Danish separators, true minus `−` (U+2212). Persons rounded to the nearest 100 (nearest 10 below 1 000).
- Words: `_perm`/`_ufin` → "varigt", `_midl` → "midlertidigt", `_blip` → "i ét år"; closure `_perm` → "finansieret via lukkeskat", else "ufinansieret".
- Honesty line: "MAKROs standardstød (stødår <firstYear>) vist som år efter stødet" + "" | ", lineært skaleret" | ", spejlet stød (lineær tilnærmelse)".
- Image: 1200 × 630, light palette from `src/app.css` `:root`, 72 px margins, never committed; fonts are static TTF instances (resvg ignores variation axes).
- No change to `app/nginx.conf`, `Dockerfile`, the ETL or the data JSON.
- Commits: descriptive body plus trailer `Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z`. Do not push; the last task asks first.
- All commands below run from `app/` unless stated otherwise. Beads issue: `makroskop-4w1` (claim at Task 1, close at Task 9).

---

## File structure

| File | Responsibility |
|---|---|
| `src/lib/site.ts` (new) | `SITE_URL` constant, shared by layout, route and card |
| `src/lib/text.ts` (new) | `wrapLines` (moved out of `export.ts`, which re-exports it) |
| `src/lib/card.ts` (new) | pure view → copy, tiles, paths, scale steps, `shareViews` |
| `src/lib/card.test.ts` (new) | unit tests for the above |
| `src/lib/card-svg.ts` (new) | pure `CardData` → SVG string; palette; headline fitting; sparkline |
| `src/lib/card-svg.test.ts` (new) | string tests |
| `src/lib/server/scenarios.ts` (new) | fs readers for meta/baseline/scenario JSON (build time only), memoised |
| `fonts/fetch.ts`, `fonts/README.md`, `fonts/*.ttf`, `fonts/OFL.txt` (new) | vendored static font instances |
| `scripts/render-card.ts` (new) | resvg wrapper: `renderPng`, `pngSize`, `assertFonts` |
| `scripts/render-card.test.ts` (new) | renders one card, asserts 1200 × 630 PNG |
| `scripts/og-images.ts` (new) | build step: one PNG per view into `build/og/` |
| `scripts/verify-build.ts` (new) | post-build assertions on pages, tags and images |
| `src/lib/components/ScenarioExplorer.svelte` (new) | the Scenarier page body, extracted; adds the Nøgletal row |
| `src/routes/scenarier/+page.svelte` (modify) | thin wrapper: title + `<ScenarioExplorer>` |
| `src/routes/scenarier/[scenario]/[[skala]]/+page.server.ts`, `+page.svelte` (new) | per-view prerendered pages |
| `src/routes/+layout.svelte` (modify) | card-aware meta tags, canonical, og:url |
| `src/lib/export.ts`, `src/lib/export.test.ts` (modify) | `permalink` emits the path form |
| `package.json` (modify) | `build` runs the image step; `og`, `verify:build` scripts; `@resvg/resvg-js` devDependency |
| `README.md` (app) and `../CLAUDE.md` (modify) | document the share pages, fonts and build step |

---

### Task 1: `card.ts` — copy, tiles and paths (pure)

**Files:**
- Create: `src/lib/site.ts`, `src/lib/card.ts`, `src/lib/card.test.ts`

**Interfaces:**
- Consumes: `ShockMeta`, `Scenario`, `ScenarioDefinition` from `src/lib/data.ts`; `formatSigned` from `src/lib/format.ts`.
- Produces (used by Tasks 2–8):
  - `ALL_SCALE_STEPS: number[]`, `scaleSteps(maxScale: number | null | undefined): number[]`
  - `changeText(def: Pick<ScenarioDefinition, 'delta' | 'factor'>, scale: number): string`
  - `formatTileValue(v: number): string`, `formatPersons(v: number): string`
  - `interface CardLevels { nL: number; vBNP: number }`
  - `interface CardTile { key: 'nL' | 'qBNP' | 'saldo2bnp'; label: string; year: number; value: string | null; unit: string }`
  - `interface CardData { name; variation; scale; path; image; title; description; imageAlt; headline; subline; kicker; closure; tiles: CardTile[]; sparkline: (number | null)[]; model: string }`
  - `interface CardHead { title; description; imageAlt; image; url; initial: { name; variation; scale }; tiles: CardTile[] }`
  - `buildCard(input: { shock: ShockMeta; scenario: Scenario; yearStart: number; modelName: string; levels: CardLevels | null; scale: number }): CardData | null`
  - `viewPath(name, variation, scale): string`, `imageFile(name, variation, scale): string`
  - `parseSkala(param: string | undefined): number | null`, `splitView(param: string, suffixes: string[]): { name: string; variation: string } | null`
  - `shareViews(meta: Pick<Meta, 'shocks'>, maxScales: Record<string, number | null>): { scenario: string; skala?: string }[]`
  - `SITE_URL` from `src/lib/site.ts`

- [ ] **Step 1: Claim the issue and create `site.ts`**

```bash
cd .. && bd update makroskop-4w1 --claim && cd app
```

`src/lib/site.ts`:
```ts
/** Public origin, for tags that must be absolute (og:image, og:url, canonical). */
export const SITE_URL = 'https://makroskop.nodalit.com';
```

- [ ] **Step 2: Write the failing tests**

`src/lib/card.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import type { Scenario, ShockMeta } from './data';
import {
	ALL_SCALE_STEPS, buildCard, changeText, formatPersons, formatTileValue, imageFile, parseSkala,
	scaleSteps, shareViews, splitView, viewPath
} from './card';

const YEAR_START = 1985;
const N_YEARS = 2100 - 1985 + 1;

/** Deviation column over 1985..2100 with values at the given years, null elsewhere. */
function series(at: Record<number, number>): (number | null)[] {
	const out: (number | null)[] = Array(N_YEARS).fill(null);
	for (const [year, value] of Object.entries(at)) out[Number(year) - YEAR_START] = value;
	return out;
}

const rente: ShockMeta = { name: 'Rente', labelDa: 'Rente (ECB)', labelEn: 'Interest rate (ECB)', group: 'Udland', available: ['_perm', '_ufin'] };

function scenario(overrides: Partial<Scenario> = {}): Scenario {
	return {
		shock: 'Rente', variation: '_ufin', synthetic: false, hbi: null,
		definition: {
			instrument: 'rRenteECB', instrumentDa: 'ECB-renten', changeDa: '+1 pct.-point (100 basispoint)',
			factor: 1.0, delta: 0.01, firstYear: 2030, lastYear: 2129, profileDa: '', closureDa: '', dreamDa: '',
			seriesKey: 'rRenteECB', solver: '', linearityDa: '', maxScale: null, maxScaleDa: null
		},
		modelVersion: null,
		deviations: {
			qBNP: series({ 2030: -0.842, 2031: -1.093, 2032: -1.159, 2035: -1.15, 2045: -1.4 }),
			nL: series({ 2030: -0.347, 2031: -0.355 }),
			saldo2bnp: series({ 2030: -0.97, 2031: -0.958 })
		},
		...overrides
	};
}

const levels = { nL: 3152.44, vBNP: 3877.49 };
const build = (scale: number, s: Scenario = scenario()) =>
	buildCard({ shock: rente, scenario: s, yearStart: YEAR_START, modelName: 'MAKRO 2026-June', levels, scale })!;

describe('scale steps', () => {
	it('offers all twelve steps without a cap and trims by magnitude with one', () => {
		expect(scaleSteps(null)).toEqual(ALL_SCALE_STEPS);
		expect(scaleSteps(1)).toEqual([-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1]);
	});
});

describe('formatting', () => {
	it('uses one decimal from 0.1 and two below, with a true minus', () => {
		expect(formatTileValue(-0.5795)).toBe('−0,6');
		expect(formatTileValue(0.04)).toBe('+0,04');
		expect(formatTileValue(-1.159)).toBe('−1,2');
	});
	it('rounds persons to hundreds, tens below a thousand', () => {
		expect(formatPersons(-10939)).toBe('−10.900');
		expect(formatPersons(-5469.5)).toBe('−5.500');
		expect(formatPersons(347)).toBe('+350');
	});
	it('words the change in the instrument unit', () => {
		expect(changeText({ delta: 0.01, factor: 1 }, 0.5)).toBe('+0,5 pct.-point');
		expect(changeText({ delta: 0, factor: 1.01 }, 2)).toBe('+2 pct.');
		expect(changeText({ delta: 0.01, factor: 1 }, -0.5)).toBe('−0,5 pct.-point');
	});
});

describe('buildCard', () => {
	it('states the halved ECB hike as years after the shock', () => {
		const card = build(0.5);
		expect(card.title).toBe('ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år');
		expect(card.description).toBe(
			'Hvad sker der i MAKRO, hvis ECB-renten varigt ændres med +0,5 pct.-point? ' +
				'Beskæftigelse −5.500 personer i år 1, offentlig saldo −0,5 pct. af BNP, BNP −0,6 pct. efter 3 år. ' +
				'Ufinansieret. MAKROs standardstød (stødår 2030) vist som år efter stødet, lineært skaleret.'
		);
		expect(card.tiles.map((t) => [t.key, t.year, t.value, t.unit])).toEqual([
			['nL', 1, '−5.500', 'personer'],
			['qBNP', 3, '−0,6', 'pct.'],
			['saldo2bnp', 1, '−0,5', 'pct. af BNP']
		]);
		expect(card.headline).toBe('ECB-renten +0,5 pct.-point');
		expect(card.subline).toBe('Varigt stød');
		expect(card.kicker).toBe('Scenarie · ufinansieret · stødår 2030, vist som år efter stødet');
		expect(card.path).toBe('/scenarier/Rente_ufin/0.5/');
		expect(card.image).toBe('Rente_ufin_0.5.png');
		expect(card.sparkline).toHaveLength(16);
		expect(card.sparkline[0]).toBeCloseTo(-0.421, 3);
		expect(card.imageAlt).toContain('Tre nøgletal');
	});
	it('drops the scaling suffix at the solved size and marks mirrored views', () => {
		expect(build(1).description).toMatch(/vist som år efter stødet\.$/);
		expect(build(1).path).toBe('/scenarier/Rente_ufin/');
		expect(build(-0.5).description).toContain('spejlet stød (lineær tilnærmelse)');
		expect(build(-0.5).headline).toBe('ECB-renten −0,5 pct.-point');
	});
	it('words the financed and temporary variants', () => {
		const perm = build(1, scenario({ variation: '_perm' }));
		expect(perm.description).toContain('Finansieret via lukkeskat.');
		expect(perm.kicker).toContain('finansieret via lukkeskat');
		const blip = build(1, scenario({ variation: '_blip' }));
		expect(blip.description).toContain('ECB-renten i ét år ændres');
		expect(blip.subline).toBe('1-årigt stød');
		expect(build(1, scenario({ variation: '_midl' })).subline).toBe('Midlertidigt stød (AR-profil)');
	});
	it('falls back to the catalog label for long instrument names', () => {
		const s = scenario();
		s.definition!.instrumentDa = 'Importpriser (alle varegrupper) og eksportkonkurrerende priser';
		expect(build(1, s).headline).toBe('Rente (ECB) +1 pct.-point');
	});
	it('leaves a tile empty and out of the text when its series is missing', () => {
		const s = scenario();
		delete s.deviations.saldo2bnp;
		const card = build(1, s);
		expect(card.tiles[2].value).toBeNull();
		expect(card.description).not.toContain('offentlig saldo');
		expect(card.description).toContain('Beskæftigelse −10.900 personer i år 1, BNP −1,2 pct. efter 3 år.');
	});
	it('needs baseline levels for persons and a definition at all', () => {
		const card = buildCard({ shock: rente, scenario: scenario(), yearStart: YEAR_START, modelName: 'M', levels: null, scale: 1 })!;
		expect(card.tiles[0].value).toBeNull();
		expect(buildCard({ shock: rente, scenario: scenario({ definition: null }), yearStart: YEAR_START, modelName: 'M', levels, scale: 1 })).toBeNull();
	});
});

describe('paths', () => {
	it('round-trips every step through viewPath and parseSkala', () => {
		for (const step of ALL_SCALE_STEPS) {
			const path = viewPath('Rente', '_ufin', step);
			const skala = path.replace('/scenarier/Rente_ufin/', '').replace('/', '') || undefined;
			expect(parseSkala(skala)).toBe(step);
		}
		expect(viewPath('Rente', '_ufin', 1)).toBe('/scenarier/Rente_ufin/');
		expect(viewPath('Rente', '_ufin', -0.75)).toBe('/scenarier/Rente_ufin/-0.75/');
	});
	it('rejects non-canonical or unknown scale params', () => {
		expect(parseSkala('1')).toBeNull();
		expect(parseSkala('0.50')).toBeNull();
		expect(parseSkala('3')).toBeNull();
		expect(parseSkala('abc')).toBeNull();
	});
	it('names image files and splits views at the variation suffix', () => {
		expect(imageFile('Rente', '_ufin', 1)).toBe('Rente_ufin.png');
		expect(imageFile('Rente', '_ufin', -0.5)).toBe('Rente_ufin_-0.5.png');
		const suffixes = ['_blip', '_midl', '_perm', '_ufin'];
		expect(splitView('Offentligt_forbrug_ufin', suffixes)).toEqual({ name: 'Offentligt_forbrug', variation: '_ufin' });
		expect(splitView('Rente', suffixes)).toBeNull();
	});
	it('lists one entry per view, honouring caps', () => {
		const views = shareViews({ shocks: [rente] }, { Rente_ufin: null, Rente_perm: 1 });
		expect(views).toHaveLength(12 + 8);
		expect(views).toContainEqual({ scenario: 'Rente_ufin' });
		expect(views).toContainEqual({ scenario: 'Rente_ufin', skala: '-0.75' });
		expect(views.filter((v) => v.scenario === 'Rente_perm' && v.skala === '2')).toHaveLength(0);
	});
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `bun run test -- src/lib/card.test.ts`
Expected: FAIL — cannot resolve `./card`.

- [ ] **Step 4: Implement `card.ts`**

```ts
/** Share-card content for one scenario view (shock, closure variant, scale): the copy behind
 *  <title>, the meta description and the og:image, the three headline tiles the page shows,
 *  and the view's URL and image names. Pure and alias-free (relative imports only) so
 *  `scripts/og-images.ts` — bun, outside SvelteKit — computes exactly what the pages carry.
 *  Wording rules: docs/superpowers/specs/2026-09-10-share-cards-design.md. */
import type { Meta, Scenario, ScenarioDefinition, ShockMeta } from './data';
import { formatSigned } from './format';

/** Slider steps offered for every solved scenario. Negative steps mirror the shock. */
export const ALL_SCALE_STEPS = [-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

/** Steps a scenario allows: a catalog cap (`definition.maxScale`) trims the magnitude. */
export function scaleSteps(maxScale: number | null | undefined): number[] {
	const steps = maxScale == null ? ALL_SCALE_STEPS : ALL_SCALE_STEPS.filter((s) => Math.abs(s) <= maxScale);
	return steps.includes(1) ? steps : [...steps, 1].sort((a, b) => a - b);
}

export interface CardLevels {
	/** baseline structural employment in the shock year, thousand persons */
	nL: number;
	/** baseline nominal GDP in the shock year, mia. kr. */
	vBNP: number;
}

export interface CardTile {
	key: 'nL' | 'qBNP' | 'saldo2bnp';
	label: string;
	/** year counted from the shock year (1 = the shock year) */
	year: number;
	/** formatted, or null when the series or the levels are missing */
	value: string | null;
	unit: string;
}

export interface CardData {
	name: string;
	variation: string;
	scale: number;
	path: string;
	image: string;
	title: string;
	description: string;
	imageAlt: string;
	headline: string;
	subline: string;
	kicker: string;
	closure: string;
	tiles: CardTile[];
	/** qBNP deviation in years 0..15 after the shock, scaled */
	sparkline: (number | null)[];
	model: string;
}

/** What a prerendered view page hands the layout and the explorer. */
export interface CardHead {
	title: string;
	description: string;
	imageAlt: string;
	image: string;
	url: string;
	initial: { name: string; variation: string; scale: number };
	tiles: CardTile[];
}

const MINUS = '−';
const da1 = new Intl.NumberFormat('da-DK', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const da2 = new Intl.NumberFormat('da-DK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const da0 = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 0 });

function signed(text: string, value: number): string {
	return (value > 0 ? '+' : '') + text.replace('-', MINUS);
}

/** One decimal from 0.1 upwards, two below; signed; true minus. */
export function formatTileValue(value: number): string {
	return signed((Math.abs(value) >= 0.1 ? da1 : da2).format(value), value);
}

/** Persons: nearest 100, nearest 10 below a thousand. */
export function formatPersons(value: number): string {
	const unit = Math.abs(value) >= 1000 ? 100 : 10;
	const rounded = Math.round(value / unit) * unit;
	return signed(da0.format(rounded), rounded);
}

/** The shock size in the instrument's own unit, the page's rule. */
export function changeText(def: Pick<ScenarioDefinition, 'delta' | 'factor'>, scale: number): string {
	const text = def.delta !== 0
		? `${formatSigned(def.delta * 100 * scale)} pct.-point`
		: `${formatSigned((def.factor - 1) * 100 * scale)} pct.`;
	return text.replace('-', MINUS);
}

const PROFILE_WORD: Record<string, string> = { _perm: 'varigt', _ufin: 'varigt', _midl: 'midlertidigt', _blip: 'i ét år' };
const PROFILE_SUBLINE: Record<string, string> = {
	_perm: 'Varigt stød', _ufin: 'Varigt stød', _midl: 'Midlertidigt stød (AR-profil)', _blip: '1-årigt stød'
};
const MAX_INSTRUMENT_CHARS = 24;

function closureWord(variation: string): string {
	return variation === '_perm' ? 'finansieret via lukkeskat' : 'ufinansieret';
}

function capitalize(text: string): string {
	return text.charAt(0).toUpperCase() + text.slice(1);
}

export function viewPath(name: string, variation: string, scale: number): string {
	return `/scenarier/${name}${variation}/${scale === 1 ? '' : `${scale}/`}`;
}

export function imageFile(name: string, variation: string, scale: number): string {
	return `${name}${variation}${scale === 1 ? '' : `_${scale}`}.png`;
}

/** The `[[skala]]` route param: absent = solved size; otherwise a canonical, allowed step. */
export function parseSkala(param: string | undefined): number | null {
	if (param === undefined) return 1;
	const value = Number(param);
	if (!Number.isFinite(value) || String(value) !== param || value === 1) return null;
	return ALL_SCALE_STEPS.includes(value) ? value : null;
}

/** `Offentligt_forbrug_ufin` → name + variation suffix; shock names may contain underscores. */
export function splitView(param: string, suffixes: string[]): { name: string; variation: string } | null {
	for (const variation of suffixes) {
		if (param.endsWith(variation) && param.length > variation.length) {
			return { name: param.slice(0, -variation.length), variation };
		}
	}
	return null;
}

/** Every prerendered view: one entry per solved scenario and allowed step. */
export function shareViews(
	meta: Pick<Meta, 'shocks'>, maxScales: Record<string, number | null>
): { scenario: string; skala?: string }[] {
	const views: { scenario: string; skala?: string }[] = [];
	for (const shock of meta.shocks) {
		for (const variation of shock.available) {
			const file = `${shock.name}${variation}`;
			for (const step of scaleSteps(maxScales[file])) {
				views.push(step === 1 ? { scenario: file } : { scenario: file, skala: String(step) });
			}
		}
	}
	return views;
}

export function buildCard(input: {
	shock: ShockMeta; scenario: Scenario; yearStart: number; modelName: string; levels: CardLevels | null; scale: number;
}): CardData | null {
	const { shock, scenario, yearStart, levels, scale } = input;
	const def = scenario.definition;
	if (!def) return null;
	const at = (key: string, year: number): number | null => {
		const value = scenario.deviations[key]?.[year - yearStart];
		return value == null ? null : value * scale;
	};
	const y1 = def.firstYear;
	const employment = at('nL', y1);
	const gdp = at('qBNP', y1 + 2);
	const balance = at('saldo2bnp', y1);
	const tiles: CardTile[] = [
		{ key: 'nL', label: 'Beskæftigelse', year: 1, unit: 'personer',
			value: employment == null || levels == null ? null : formatPersons((employment / 100) * levels.nL * 1000) },
		{ key: 'qBNP', label: 'BNP', year: 3, unit: 'pct.', value: gdp == null ? null : formatTileValue(gdp) },
		{ key: 'saldo2bnp', label: 'Offentlig saldo', year: 1, unit: 'pct. af BNP', value: balance == null ? null : formatTileValue(balance) }
	];
	const [persons, bnp, saldo] = tiles;

	const instrument = def.instrumentDa.length <= MAX_INSTRUMENT_CHARS ? def.instrumentDa : shock.labelDa;
	const change = changeText(def, scale);
	const headline = `${instrument} ${change}`;
	const closure = closureWord(scenario.variation);
	const question = `Hvad sker der i MAKRO, hvis ${instrument} ${PROFILE_WORD[scenario.variation] ?? 'varigt'} ændres med ${change}?`;
	const numbers = [
		persons.value == null ? null : `beskæftigelse ${persons.value} personer i år 1`,
		saldo.value == null ? null : `offentlig saldo ${saldo.value} pct. af BNP`,
		bnp.value == null ? null : `BNP ${bnp.value} pct. efter 3 år`
	].filter((part): part is string => part != null);
	const scaling = scale === 1 ? '' : scale < 0 ? ', spejlet stød (lineær tilnærmelse)' : ', lineært skaleret';
	const honesty = `MAKROs standardstød (stødår ${y1}) vist som år efter stødet${scaling}.`;
	const description = [
		question,
		numbers.length ? `${capitalize(numbers.join(', '))}.` : null,
		`${capitalize(closure)}.`,
		honesty
	].filter((part): part is string => part != null).join(' ');

	return {
		name: shock.name,
		variation: scenario.variation,
		scale,
		path: viewPath(shock.name, scenario.variation, scale),
		image: imageFile(shock.name, scenario.variation, scale),
		title: bnp.value == null ? headline : `${headline}: BNP ${bnp.value} pct. efter 3 år`,
		description,
		imageAlt: `${question} Tre nøgletal: BNP efter 3 år, beskæftigelse og offentlig saldo i år 1.`,
		headline,
		subline: PROFILE_SUBLINE[scenario.variation] ?? 'Varigt stød',
		kicker: `Scenarie · ${closure} · stødår ${y1}, vist som år efter stødet`,
		closure,
		tiles,
		sparkline: Array.from({ length: 16 }, (_, k) => at('qBNP', y1 + k)),
		model: input.modelName
	};
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `bun run test -- src/lib/card.test.ts`
Expected: PASS (all describe blocks). If `formatTileValue(0.04)` yields `+0,04` but the minus tests fail, check that `Intl` in bun emits U+002D for negatives (the `signed` helper replaces it).

- [ ] **Step 6: Commit**

```bash
git add src/lib/site.ts src/lib/card.ts src/lib/card.test.ts
git commit -F - <<'MSG'
Share cards: card.ts — view copy, tiles and paths (makroskop-4w1)

Pure module behind the per-view share pages: title/description/alt, the three fixed
tiles (beskæftigelse år 1 in persons, BNP år 3, offentlig saldo år 1), the honesty line
"MAKROs standardstød (stødår N) vist som år efter stødet", the /scenarier/<view>/<skala>/
path scheme and the prerender entry list. Relative imports only so the bun build script
can share it with the routes.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 2: `card-svg.ts` — the 1200 × 630 card as SVG (pure)

**Files:**
- Create: `src/lib/text.ts`, `src/lib/card-svg.ts`, `src/lib/card.fixture.ts`, `src/lib/card-svg.test.ts`
- Modify: `src/lib/export.ts` (move `wrapLines` out, re-export it)

**Interfaces:**
- Consumes: `CardData`, `CardTile` from Task 1; `wrapLines(measure, text, maxWidth)` from `text.ts`.
- Produces: `cardSvg(card: CardData): string`; `fitHeadline(text: string): { size: number; lines: string[] }`; `sparklinePath(values, box): { line: string; zeroY: number }`; `escapeXml(s: string): string`; `LIGHT` palette; `FONT_FAMILIES = { display: 'Newsreader', body: 'IBM Plex Sans', mono: 'IBM Plex Mono' }`.

- [ ] **Step 1: Move `wrapLines` into `src/lib/text.ts`**

`src/lib/text.ts`:
```ts
/** Greedy word wrap against a width function (canvas measureText, or a heuristic). */
export function wrapLines(measure: (text: string) => number, text: string, maxWidth: number): string[] {
	const lines: string[] = [];
	let current = '';
	for (const word of text.split(' ')) {
		const candidate = current ? `${current} ${word}` : word;
		if (current && measure(candidate) > maxWidth) {
			lines.push(current);
			current = word;
		} else {
			current = candidate;
		}
	}
	if (current) lines.push(current);
	return lines;
}
```

In `src/lib/export.ts`: delete the `wrapLines` function body (lines 64–78) and add near the top:
```ts
import { wrapLines } from './text';
export { wrapLines };
```
Run: `bun run test` — Expected: PASS (export.test.ts still imports `wrapLines` from `./export`).

- [ ] **Step 2: Write the failing tests**

`src/lib/card.fixture.ts` (a plain module, so several test files can share it without re-registering tests):
```ts
import type { CardData } from './card';

/** Rente_ufin at ×0.5 as buildCard produces it, with one tile left empty on purpose. */
export const sample: CardData = {
	name: 'Rente', variation: '_ufin', scale: 0.5, path: '/scenarier/Rente_ufin/0.5/', image: 'Rente_ufin_0.5.png',
	title: 'ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år',
	description: 'x', imageAlt: 'x',
	headline: 'ECB-renten +0,5 pct.-point', subline: 'Varigt stød',
	kicker: 'Scenarie · ufinansieret · stødår 2030, vist som år efter stødet', closure: 'ufinansieret',
	tiles: [
		{ key: 'nL', label: 'Beskæftigelse', year: 1, value: '−5.500', unit: 'personer' },
		{ key: 'qBNP', label: 'BNP', year: 3, value: '−0,6', unit: 'pct.' },
		{ key: 'saldo2bnp', label: 'Offentlig saldo', year: 1, value: null, unit: 'pct. af BNP' }
	],
	sparkline: [-0.42, -0.55, -0.58, -0.58, -0.57, -0.58, -0.6, -0.62, -0.64, -0.65, -0.66, -0.67, -0.68, -0.69, -0.7, -0.71],
	model: 'MAKRO 2026-June'
};
```

`src/lib/card-svg.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { sample } from './card.fixture';
import { cardSvg, escapeXml, fitHeadline, sparklinePath } from './card-svg';

describe('escapeXml', () => {
	it('escapes the five XML specials', () => {
		expect(escapeXml('a & b < c > "d" \'e\'')).toBe('a &amp; b &lt; c &gt; &quot;d&quot; &apos;e&apos;');
	});
});

describe('fitHeadline', () => {
	it('keeps a short headline on one 72 px line', () => {
		expect(fitHeadline('Rente +1 pct.-point')).toEqual({ size: 72, lines: ['Rente +1 pct.-point'] });
	});
	it('wraps to two lines before shrinking, and shrinks before allowing three', () => {
		const two = fitHeadline('Skattepligtige overførsler +1 pct.');
		expect(two.lines.length).toBeLessThanOrEqual(2);
		const long = fitHeadline('Offentlig beskæftigelse og offentligt varekøb +12,5 pct. i alle brancher');
		expect(long.size).toBeLessThan(72);
		expect(long.lines.length).toBeLessThanOrEqual(3);
	});
});

describe('sparklinePath', () => {
	it('draws a polyline through the box with the zero line inside it', () => {
		const { line, zeroY } = sparklinePath([0, -1, 1, null, 0.5], { x: 100, y: 200, w: 300, h: 100 });
		expect(line.startsWith('M100')).toBe(true);
		expect(line.split(/[ML]/).filter(Boolean)).toHaveLength(4);
		expect(zeroY).toBeGreaterThan(200);
		expect(zeroY).toBeLessThan(300);
	});
});

describe('cardSvg', () => {
	const svg = cardSvg(sample);
	it('is a 1200×630 document in the light palette', () => {
		expect(svg).toContain('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"');
		expect(svg).toContain('fill="#fbfbf8"');
	});
	it('carries the headline, subline, kicker, tiles and footer', () => {
		for (const text of ['ECB-renten +0,5 pct.-point', 'Varigt stød', 'stødår 2030', '−5.500', 'personer', 'Beskæftigelse, år 1', 'BNP, år 3', '−0,6', 'Offentlig saldo, år 1', 'MAKRO 2026-June', 'makroskop.nodalit.com']) {
			expect(svg).toContain(text);
		}
	});
	it('renders a missing tile value as an en dash and escapes text', () => {
		expect(svg).toContain('>–<');
		expect(cardSvg({ ...sample, headline: 'A & B' })).toContain('A &amp; B');
	});
});
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `bun run test -- src/lib/card-svg.test.ts`
Expected: FAIL — cannot resolve `./card-svg`.

- [ ] **Step 4: Implement `card-svg.ts`**

```ts
/** The share card as an SVG string: wordmark, kicker, headline, sparkline, three tiles,
 *  footer. Light palette only — a static image cannot follow the viewer's theme — with the
 *  light-theme tokens of src/app.css (:root). Rasterised by scripts/render-card.ts. */
import type { CardData } from './card';
import { wrapLines } from './text';

/** src/app.css :root light tokens: --page, --ink, --ink-secondary, --ink-muted, --rule, --axis, --series-1, --makro */
export const LIGHT = {
	page: '#fbfbf8',
	ink: '#171d1c',
	secondary: '#4e5957',
	muted: '#67746f',
	rule: 'rgba(23, 29, 28, 0.16)',
	axis: '#848e8a',
	series: '#2a78d6',
	makro: '#0f9a92'
};

export const FONT_FAMILIES = { display: 'Newsreader', body: 'IBM Plex Sans', mono: 'IBM Plex Mono' };

const W = 1200;
const H = 630;
const M = 72;
const HEADLINE_WIDTH = 690; // leaves room for the sparkline on the right
const HEADLINE_SIZES = [72, 62, 54];
const DISPLAY_EM = 0.46; // average advance of Newsreader SemiBold, em per character

export function escapeXml(text: string): string {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

/** Largest size at which the headline fits two lines; three lines at the smallest size otherwise. */
export function fitHeadline(text: string): { size: number; lines: string[] } {
	for (const size of HEADLINE_SIZES) {
		const lines = wrapLines((t) => t.length * DISPLAY_EM * size, text, HEADLINE_WIDTH);
		if (lines.length <= 2) return { size, lines };
	}
	const size = HEADLINE_SIZES[HEADLINE_SIZES.length - 1];
	return { size, lines: wrapLines((t) => t.length * DISPLAY_EM * size, text, HEADLINE_WIDTH).slice(0, 3) };
}

/** Polyline through the non-null values, y scaled to the box with zero inside it. */
export function sparklinePath(
	values: (number | null)[], box: { x: number; y: number; w: number; h: number }
): { line: string; zeroY: number } {
	const present = values.filter((v): v is number => v != null);
	const lo = Math.min(0, ...present);
	const hi = Math.max(0, ...present);
	const span = hi - lo || 1;
	const y = (v: number) => box.y + box.h - ((v - lo) / span) * box.h;
	const step = values.length > 1 ? box.w / (values.length - 1) : 0;
	let line = '';
	values.forEach((v, i) => {
		if (v == null) return;
		line += `${line ? 'L' : 'M'}${(box.x + i * step).toFixed(1)} ${y(v).toFixed(1)}`;
	});
	return { line, zeroY: y(0) };
}

function text(x: number, y: number, content: string, attrs: string): string {
	return `<text x="${x}" y="${y}" ${attrs}>${escapeXml(content)}</text>`;
}

export function cardSvg(card: CardData): string {
	const { display, body, mono } = FONT_FAMILIES;
	const parts: string[] = [];
	parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`);
	parts.push(`<rect width="${W}" height="${H}" fill="${LIGHT.page}"/>`);

	// wordmark and kicker
	parts.push(`<text x="${M}" y="96" font-family="${display}" font-size="40" font-weight="500" fill="${LIGHT.ink}">MAKRO<tspan font-style="italic" fill="${LIGHT.makro}">skop</tspan></text>`);
	parts.push(text(W - M, 94, card.kicker, `text-anchor="end" font-family="${body}" font-size="20" font-weight="500" fill="${LIGHT.muted}"`));

	// headline + subline
	const { size, lines } = fitHeadline(card.headline);
	const lineHeight = size * 1.08;
	let y = 190 + size;
	for (const line of lines) {
		parts.push(text(M, Math.round(y), line, `font-family="${display}" font-size="${size}" font-weight="600" fill="${LIGHT.ink}"`));
		y += lineHeight;
	}
	parts.push(text(M, Math.round(y + 14), card.subline, `font-family="${body}" font-size="26" fill="${LIGHT.muted}"`));

	// sparkline: qBNP years 0..15 after the shock, texture at the right
	const box = { x: 828, y: 168, w: 300, h: 110 };
	const { line, zeroY } = sparklinePath(card.sparkline, box);
	parts.push(`<line x1="${box.x}" y1="${zeroY.toFixed(1)}" x2="${box.x + box.w}" y2="${zeroY.toFixed(1)}" stroke="${LIGHT.axis}" stroke-width="1"/>`);
	if (line) parts.push(`<path d="${line}" fill="none" stroke="${LIGHT.series}" stroke-width="3" stroke-opacity="0.6" stroke-linejoin="round" stroke-linecap="round"/>`);
	parts.push(text(box.x, box.y + box.h + 28, 'BNP, år 0–15 efter stødet', `font-family="${body}" font-size="18" fill="${LIGHT.muted}"`));

	// three tiles
	const column = (W - 2 * M) / 3;
	card.tiles.forEach((tile, i) => {
		const x = M + i * column;
		parts.push(text(x, 404, `${tile.label}, år ${tile.year}`, `font-family="${body}" font-size="22" font-weight="500" fill="${LIGHT.muted}"`));
		if (tile.value == null) {
			parts.push(text(x, 494, '–', `font-family="${display}" font-size="84" font-weight="500" fill="${LIGHT.muted}"`));
		} else {
			parts.push(text(x, 494, tile.value, `font-family="${display}" font-size="84" font-weight="500" fill="${LIGHT.ink}"`));
			parts.push(text(x, 534, tile.unit, `font-family="${body}" font-size="24" fill="${LIGHT.muted}"`));
		}
	});

	// footer
	parts.push(`<line x1="${M}" y1="566" x2="${W - M}" y2="566" stroke="${LIGHT.rule}" stroke-width="1"/>`);
	parts.push(text(M, 602, `${card.model} · MAKROskops frie løser`, `font-family="${body}" font-size="20" fill="${LIGHT.muted}"`));
	parts.push(text(W - M, 602, 'makroskop.nodalit.com', `text-anchor="end" font-family="${mono}" font-size="20" fill="${LIGHT.muted}"`));
	parts.push('</svg>');
	return parts.join('\n');
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `bun run test -- src/lib/card-svg.test.ts`
Expected: PASS. The width heuristic (0.46 em per character) is what the rendered check in Task 3 validates by eye.

- [ ] **Step 6: Commit**

```bash
git add src/lib/text.ts src/lib/export.ts src/lib/card-svg.ts src/lib/card.fixture.ts src/lib/card-svg.test.ts
git commit -F - <<'MSG'
Share cards: card-svg.ts — the 1200x630 card as SVG (makroskop-4w1)

Light-palette editorial layout in the style of static/og.png: wordmark, kicker, a
Newsreader headline fitted to two lines, a faint qBNP sparkline for years 0-15, three
tiles (Beskæftigelse · BNP · Offentlig saldo, BNP centred for crops) and the footer.
wrapLines moves to lib/text.ts so the card code does not import the DOM-facing export.ts.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 3: Fonts and the resvg renderer

**Files:**
- Create: `fonts/fetch.ts`, `fonts/README.md`, `fonts/OFL.txt`, `fonts/*.ttf` (6 files), `scripts/render-card.ts`, `scripts/render-card.test.ts`
- Modify: `package.json` (add `@resvg/resvg-js` devDependency)

**Interfaces:**
- Consumes: `cardSvg` and the `sample` fixture from Task 2.
- Produces: `FONT_FILES: string[]` (absolute paths), `assertFonts(): void`, `renderPng(svg: string): Uint8Array`, `pngSize(png: Uint8Array): { width: number; height: number }`.

- [ ] **Step 1: Add resvg and write the font fetcher**

```bash
bun add -d @resvg/resvg-js@2.6.2
grep -c "resvg-js-linux-x64-gnu" bun.lock   # expected: 1 or more — the Docker build needs it
```

`fonts/fetch.ts`:
```ts
/** Vendors static TTF instances of the site's fonts for the build-time card renderer.
 *  Google Fonts serves modern browsers variable fonts, which resvg cannot instance (it
 *  ignores variation axes), but hands a `curl` User-Agent format('truetype') static
 *  instances at the requested weights. Run `bun fonts/fetch.ts` and commit the result.
 *  Licences: SIL Open Font License 1.1 for all three families (fonts/OFL.txt). */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const CSS =
	'https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;1,500' +
	'&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400';
const OFL = 'https://openfontlicense.org/documents/OFL.txt';
const dir = fileURLToPath(new URL('./', import.meta.url));

const css = await (await fetch(CSS, { headers: { 'User-Agent': 'curl/8.0' } })).text();
const faces = [...css.matchAll(/@font-face\s*{([^}]*)}/g)].map((m) => m[1]);
let count = 0;
for (const face of faces) {
	const family = /font-family:\s*'([^']+)'/.exec(face)?.[1];
	const style = /font-style:\s*(\w+)/.exec(face)?.[1];
	const weight = /font-weight:\s*(\d+)/.exec(face)?.[1];
	const url = /url\((https:[^)]+\.ttf)\)/.exec(face)?.[1];
	if (!family || !style || !weight || !url) throw new Error(`unexpected @font-face block:\n${face}`);
	const name = `${family.replace(/\s+/g, '')}-${style}-${weight}.ttf`;
	writeFileSync(`${dir}${name}`, new Uint8Array(await (await fetch(url)).arrayBuffer()));
	console.log(`${name} <- ${url}`);
	count++;
}
writeFileSync(`${dir}OFL.txt`, await (await fetch(OFL)).text());
if (count !== 6) throw new Error(`expected 6 font files, got ${count}`);
```

Run: `bun fonts/fetch.ts`
Expected: six lines naming `Newsreader-normal-500.ttf`, `Newsreader-normal-600.ttf`, `Newsreader-italic-500.ttf`, `IBMPlexSans-normal-400.ttf`, `IBMPlexSans-normal-500.ttf`, `IBMPlexMono-normal-400.ttf`, plus `OFL.txt`. If the OFL URL 404s, fetch `https://raw.githubusercontent.com/googlefonts/newsreader/main/OFL.txt` instead.

- [ ] **Step 2: Verify the files are static instances at the right weights**

```bash
cd .. && for f in app/fonts/*.ttf; do uv run --with fonttools python -c "
import sys; from fontTools.ttLib import TTFont
f = TTFont(sys.argv[1]); n = f['name']
print(sys.argv[1].split('/')[-1], 'variable' if 'fvar' in f else 'static', n.getDebugName(4), f['OS/2'].usWeightClass)" "$f"; done; cd app
```
Expected: every line says `static` and the weight class matches the file name (500/600/400).

`fonts/README.md`:
```markdown
# Fonts for the build-time share cards

Static TrueType instances of the site's web fonts, used only by `scripts/og-images.ts`
(resvg cannot instance variable fonts). Regenerate with `bun fonts/fetch.ts`.

- Newsreader 500, 600, italic 500 — © Production Type, SIL Open Font License 1.1
- IBM Plex Sans 400, 500 and IBM Plex Mono 400 — © IBM Corp., SIL Open Font License 1.1

Licence text: `OFL.txt`. The site itself loads the same families from Google Fonts.
```

- [ ] **Step 3: Write the failing renderer test**

`scripts/render-card.test.ts`:
```ts
import { describe, expect, it } from 'vitest';
import { cardSvg } from '../src/lib/card-svg';
import { sample } from '../src/lib/card.fixture';
import { assertFonts, pngSize, renderPng } from './render-card';

describe('renderPng', () => {
	it('finds the vendored fonts', () => {
		expect(() => assertFonts()).not.toThrow();
	});
	it('rasterises a card to a 1200×630 PNG', () => {
		const png = renderPng(cardSvg(sample));
		expect(Array.from(png.slice(0, 4))).toEqual([0x89, 0x50, 0x4e, 0x47]);
		expect(pngSize(png)).toEqual({ width: 1200, height: 630 });
		expect(png.byteLength).toBeGreaterThan(10_000);
	});
});
```

Run: `bun run test -- scripts/render-card.test.ts`
Expected: FAIL — cannot resolve `./render-card`.

- [ ] **Step 4: Implement `scripts/render-card.ts`**

```ts
/** SVG → PNG for the share cards, with the vendored fonts and nothing from the system, so
 *  the image is identical on a laptop and in the Docker build. */
import { Resvg } from '@resvg/resvg-js';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const FONT_NAMES = [
	'Newsreader-normal-500.ttf', 'Newsreader-normal-600.ttf', 'Newsreader-italic-500.ttf',
	'IBMPlexSans-normal-400.ttf', 'IBMPlexSans-normal-500.ttf', 'IBMPlexMono-normal-400.ttf'
];
export const FONT_FILES = FONT_NAMES.map((name) => fileURLToPath(new URL(`../fonts/${name}`, import.meta.url)));

export function assertFonts(): void {
	const missing = FONT_FILES.filter((file) => !existsSync(file));
	if (missing.length) throw new Error(`missing font files (run: bun fonts/fetch.ts):\n${missing.join('\n')}`);
}

export function renderPng(svg: string): Uint8Array {
	const resvg = new Resvg(svg, {
		fitTo: { mode: 'width', value: 1200 },
		font: { fontFiles: FONT_FILES, loadSystemFonts: false, defaultFontFamily: 'IBM Plex Sans' }
	});
	return resvg.render().asPng();
}

/** Width and height from the IHDR chunk. */
export function pngSize(png: Uint8Array): { width: number; height: number } {
	const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
	return { width: view.getUint32(16), height: view.getUint32(20) };
}
```

- [ ] **Step 5: Run the test, then look at the picture**

Run: `bun run test -- scripts/render-card.test.ts`
Expected: PASS.

Then render the sample to a file and open it:
```bash
bun -e "
import { cardSvg } from './src/lib/card-svg';
import { sample } from './src/lib/card.fixture';
import { renderPng } from './scripts/render-card';
import { writeFileSync } from 'node:fs';
writeFileSync('/tmp/card-sample.png', renderPng(cardSvg(sample)));" && open /tmp/card-sample.png
```
Check with your eyes (or the Read tool on the PNG): Newsreader is used for the headline and the numbers (serif, semibold headline), the "skop" is teal italic, æ/ø/å and the true minus render, nothing touches the 72 px margins, the sparkline sits right of the headline. If a glyph shows as a box, that font lacks it: replace `−` by `-` in `card.ts`'s `signed()` only if Newsreader lacks U+2212 (check with `uv run --with fonttools python -c "from fontTools.ttLib import TTFont; print(0x2212 in TTFont('fonts/Newsreader-normal-500.ttf').getBestCmap())"`).

- [ ] **Step 6: Commit**

```bash
git add package.json bun.lock fonts scripts/render-card.ts scripts/render-card.test.ts
git commit -F - <<'MSG'
Share cards: vendored static fonts and the resvg renderer (makroskop-4w1)

fonts/fetch.ts pulls static TTF instances (Newsreader 500/600/italic 500, IBM Plex Sans
400/500, IBM Plex Mono 400) from Google Fonts by asking as curl — resvg ignores variation
axes, so the variable fonts browsers get are no use. OFL 1.1, see fonts/README.md.
scripts/render-card.ts rasterises a card SVG with only those fonts, so laptop and Docker
produce the same pixels; the test asserts a 1200x630 PNG.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 4: Data readers and the `og-images` build step

**Files:**
- Create: `src/lib/server/scenarios.ts`, `scripts/og-images.ts`, `scripts/og-images.test.ts`
- Modify: `package.json` scripts

**Interfaces:**
- Consumes: `buildCard`, `imageFile`, `scaleSteps`, `CardLevels` (Task 1); `cardSvg` (Task 2); `assertFonts`, `renderPng` (Task 3); `Meta`, `Baseline`, `Scenario` types.
- Produces: `readMeta(): Meta`, `readBaseline(): Baseline`, `readScenario(file: string): Scenario` (throws naming the file), `scenarioExists(file: string): boolean`, `levelsAt(baseline: Baseline, year: number): CardLevels | null`, `maxScales(meta: Meta): Record<string, number | null>`; `generateCards(outDir: string): number`.

- [ ] **Step 1: Write the failing tests**

`scripts/og-images.test.ts`:
```ts
import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { levelsAt, maxScales, readBaseline, readMeta, readScenario, scenarioExists } from '../src/lib/server/scenarios';
import { generateCards } from './og-images';

describe('scenario readers', () => {
	it('read the committed data from static/data', () => {
		const meta = readMeta();
		expect(meta.shocks.length).toBeGreaterThan(30);
		expect(scenarioExists('Rente_ufin')).toBe(true);
		expect(scenarioExists('Nope_ufin')).toBe(false);
		expect(readScenario('Rente_ufin').definition?.firstYear).toBe(2030);
		expect(() => readScenario('Nope_ufin')).toThrow(/Nope_ufin/);
		const levels = levelsAt(readBaseline(), 2030)!;
		expect(levels.nL).toBeGreaterThan(3000);
		expect(levels.vBNP).toBeGreaterThan(3000);
		expect(Object.keys(maxScales(meta)).length).toBe(meta.shocks.reduce((n, s) => n + s.available.length, 0));
	});
});

describe('generateCards', () => {
	const out = mkdtempSync(join(tmpdir(), 'og-'));
	afterAll(() => rmSync(out, { recursive: true, force: true }));
	it('writes one PNG per view for a single scenario', () => {
		const count = generateCards(out, ['Rente_ufin']);
		expect(count).toBe(12);
		const files = readdirSync(out).sort();
		expect(files).toContain('Rente_ufin.png');
		expect(files).toContain('Rente_ufin_-0.75.png');
		expect(files).toContain('Rente_ufin_2.png');
		expect(existsSync(join(out, 'Rente_ufin_1.png'))).toBe(false);
	});
});
```

Run: `bun run test -- scripts/og-images.test.ts`
Expected: FAIL — cannot resolve the modules.

- [ ] **Step 2: Implement `src/lib/server/scenarios.ts`**

```ts
/** Build-time readers for the committed data JSON (static/data). Used by the prerendered
 *  view route (+page.server.ts) and by scripts/og-images.ts, so both see the same files.
 *  Paths resolve from the working directory, which is app/ for `vite build`, `vite dev`
 *  and the bun scripts (the Dockerfile's WORKDIR is /app). Relative imports only: the bun
 *  script has no `$lib` alias. */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { CardLevels } from '../card';
import type { Baseline, Meta, Scenario } from '../data';

const DATA_DIR = join(process.cwd(), 'static', 'data');
const cache = new Map<string, unknown>();

function readJson<T>(relative: string): T {
	if (!cache.has(relative)) {
		const path = join(DATA_DIR, relative);
		if (!existsSync(path)) throw new Error(`missing data file ${relative} (looked in ${DATA_DIR})`);
		cache.set(relative, JSON.parse(readFileSync(path, 'utf8')));
	}
	return cache.get(relative) as T;
}

export const readMeta = (): Meta => readJson<Meta>('meta.json');
export const readBaseline = (): Baseline => readJson<Baseline>('baseline.json');
export const readScenario = (file: string): Scenario => readJson<Scenario>(`shocks/${file}.json`);
export const scenarioExists = (file: string): boolean => existsSync(join(DATA_DIR, 'shocks', `${file}.json`));

/** Baseline levels the persons tile needs, in the shock year. */
export function levelsAt(baseline: Baseline, year: number): CardLevels | null {
	const index = baseline.years.indexOf(year);
	const nL = baseline.series.nL?.[index];
	const vBNP = baseline.series.vBNP?.[index];
	return nL == null || vBNP == null ? null : { nL, vBNP };
}

/** `definition.maxScale` per solved scenario file, for the entry list and the image step. */
export function maxScales(meta: Meta): Record<string, number | null> {
	const caps: Record<string, number | null> = {};
	for (const shock of meta.shocks) {
		for (const variation of shock.available) {
			const file = `${shock.name}${variation}`;
			caps[file] = readScenario(file).definition?.maxScale ?? null;
		}
	}
	return caps;
}
```

- [ ] **Step 3: Implement `scripts/og-images.ts`**

```ts
/** Build step: one 1200x630 og:image per scenario view into build/og/. Runs after
 *  `vite build` (see package.json "build"); the pages reference the files by name
 *  (card.image) and the Dockerfile copies build/ as is. Fails loudly on a missing font,
 *  scenario or definition — a page with a broken card is worse than a failed build. */
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { buildCard, scaleSteps } from '../src/lib/card';
import { cardSvg } from '../src/lib/card-svg';
import { levelsAt, readBaseline, readMeta, readScenario } from '../src/lib/server/scenarios';
import { assertFonts, renderPng } from './render-card';

/** Renders every view (or only the named scenario files) and returns the count. */
export function generateCards(outDir: string, only?: string[]): number {
	assertFonts();
	mkdirSync(outDir, { recursive: true });
	const meta = readMeta();
	const baseline = readBaseline();
	let count = 0;
	for (const shock of meta.shocks) {
		for (const variation of shock.available) {
			const file = `${shock.name}${variation}`;
			if (only && !only.includes(file)) continue;
			const scenario = readScenario(file);
			if (!scenario.definition) throw new Error(`${file}: no shock definition, cannot build a card`);
			const levels = levelsAt(baseline, scenario.definition.firstYear);
			for (const scale of scaleSteps(scenario.definition.maxScale)) {
				const card = buildCard({ shock, scenario, yearStart: meta.yearStart, modelName: meta.model.name, levels, scale });
				if (!card) throw new Error(`${file}: no card at scale ${scale}`);
				writeFileSync(join(outDir, card.image), renderPng(cardSvg(card)));
				count++;
			}
		}
	}
	return count;
}

function main(): void {
	const build = join(process.cwd(), 'build');
	if (!existsSync(build)) throw new Error('build/ is missing — run `vite build` first (package.json "build" does both)');
	const started = Date.now();
	const count = generateCards(join(build, 'og'));
	console.log(`og-images: ${count} cards in ${((Date.now() - started) / 1000).toFixed(1)} s → build/og/`);
}

if ((import.meta as { main?: boolean }).main) main();
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `bun run test -- scripts/og-images.test.ts`
Expected: PASS (the second test renders 12 PNGs, a few seconds).

- [ ] **Step 5: Wire the build and run it once**

In `package.json` `scripts`, change `"build"` and add two entries:
```json
"build": "vite build && bun run scripts/og-images.ts",
"og": "bun run scripts/og-images.ts",
"verify:build": "bun run scripts/verify-build.ts",
```
(`verify:build` is implemented in Task 8; leave the entry now so the scripts block is edited once.)

Run: `bun run build`
Expected: the SvelteKit build as before, then `og-images: 936 cards in N s → build/og/` (the count is 78 scenarios × 12 minus capped steps; note the exact number for Task 8) and `ls build/og | wc -l` matches. Look at two more cards: `open build/og/Bundskat_ufin.png build/og/Offentligt_forbrug_perm_2.png` — check long headlines wrap or shrink cleanly.

- [ ] **Step 6: Commit**

```bash
git add src/lib/server/scenarios.ts scripts/og-images.ts scripts/og-images.test.ts package.json
git commit -F - <<'MSG'
Share cards: og-images build step (makroskop-4w1)

`bun run build` now renders one PNG per scenario view into build/og/ after vite build:
static/data readers (memoised, cwd-relative, shared with the view route), a generator
that walks meta.shocks x available x scaleSteps(maxScale), and a loud failure on any
missing font, file or definition. Images are build artefacts, never committed.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 5: Extract `ScenarioExplorer.svelte` (behaviour-preserving) with the Nøgletal row

**Files:**
- Create: `src/lib/components/ScenarioExplorer.svelte`
- Modify: `src/routes/scenarier/+page.svelte` (becomes a wrapper)

**Interfaces:**
- Consumes: `ALL_SCALE_STEPS`, `scaleSteps`, `changeText`, `buildCard`, `CardTile`, `CardLevels` (Task 1); `levelsAt`-equivalent on the client (implemented inline from `loadBaseline`).
- Produces: `<ScenarioExplorer meta initialScenario initial initialTiles />` with props
  `{ meta: Meta; initialScenario: Scenario | null; initial?: { name: string; variation: string; scale: number } | null; initialTiles?: CardTile[] | null }`.

- [ ] **Step 1: Create the component from the page**

Move everything in `src/routes/scenarier/+page.svelte` — the `<script>`, the markup and the `<style>` — into `src/lib/components/ScenarioExplorer.svelte`, then apply exactly these edits inside the new file:

1. Props. Replace
   ```ts
   let { data } = $props();

   const meta = $derived(data.meta);
   ```
   with
   ```ts
   import type { CardTile } from '$lib/card';
   import { ALL_SCALE_STEPS, buildCard, changeText, scaleSteps as stepsFor } from '$lib/card';
   import { loadBaseline, type Meta } from '$lib/data';
   import StatTile from '$lib/components/StatTile.svelte';

   let {
   	meta,
   	initialScenario,
   	initial = null,
   	initialTiles = null
   }: {
   	meta: Meta;
   	initialScenario: Scenario | null;
   	/** Preselected view (the prerendered /scenarier/<view>/ pages); otherwise the ?stod= query. */
   	initial?: { name: string; variation: string; scale: number } | null;
   	/** The view's tiles as prerendered, shown until the scenario JSON has loaded. */
   	initialTiles?: CardTile[] | null;
   } = $props();
   ```
   (keep the existing `StatTile` import if one is already there — one import only) and replace every `data.initialScenario` with `initialScenario`.
2. Scale steps. Delete the `ALL_SCALE_STEPS` constant and the `scaleSteps` `$derived.by` block; replace with
   ```ts
   const UNSCALED = 1;
   const scaleSteps = $derived(stepsFor(scenario?.definition?.maxScale));
   ```
3. Change wording. Replace the body of `scaledChange` with `return changeText(def, scale);` keeping the early return for a missing definition.
4. Deep link. Replace the `onMount(() => { ... })` block with
   ```ts
   /** Which view to open: the prerendered page's own, else the ?stod=&variant=&skala= query
    *  (used by the Validering page and by old links). */
   function wantedView(): { name: string; variation: string; scale: number } | null {
   	if (initial) return initial;
   	const name = page.url.searchParams.get('stod');
   	if (!name) return null;
   	const variant = page.url.searchParams.get('variant') ?? '';
   	const skala = Number(page.url.searchParams.get('skala'));
   	return { name, variation: variant, scale: Number.isFinite(skala) && skala !== 0 ? skala : 1 };
   }

   onMount(() => {
   	// Baseline levels for the persons tile (55 KB, browser-cached); every solved scenario needs them.
   	void loadBaseline(fetch).then((baseline) => {
   		levelsByYear = Object.fromEntries(
   			baseline.years.map((year, i) => [year, { nL: baseline.series.nL?.[i] ?? null, vBNP: baseline.series.vBNP?.[i] ?? null }])
   		);
   	});
   	const wanted = wantedView();
   	const shock = wanted ? meta.shocks.find((s) => s.name === wanted.name) : undefined;
   	if (!wanted || !shock) return;
   	const variation = shock.available.includes(wanted.variation)
   		? wanted.variation
   		: (shock.available[0] ?? meta.variations[1]?.suffix ?? '_midl');
   	void select(shock.name, variation).then(() => {
   		if (scaleSteps.includes(wanted.scale)) scaleIdx = scaleSteps.indexOf(wanted.scale);
   	});
   });
   ```
   and add near the other state declarations:
   ```ts
   /** Baseline nL/vBNP by year (persons tile), fetched once after mount. */
   let levelsByYear: Record<number, { nL: number | null; vBNP: number | null }> = $state.raw({});
   ```
5. Tiles. Add after the `scenarioLine` derived:
   ```ts
   /** The three headline figures, the same function the share cards use; the prerendered
    *  values bridge the gap until the scenario JSON has loaded. */
   const tiles = $derived.by((): CardTile[] | null => {
   	if (scenario && shareable && scenario.definition) {
   		const year = scenario.definition.firstYear;
   		const at = levelsByYear[year];
   		const levels = at && at.nL != null && at.vBNP != null ? { nL: at.nL, vBNP: at.vBNP } : null;
   		return buildCard({ shock: selectedShock, scenario, yearStart: meta.yearStart, modelName: meta.model.name, levels, scale })?.tiles ?? null;
   	}
   	return loading ? initialTiles : null;
   });
   ```
6. URL sync. Replace the `$effect` body with
   ```ts
   $effect(() => {
   	if (!shareable) return;
   	const url = new URL(shareUrl);
   	if (url.pathname + url.search !== location.pathname + location.search) replaceState(url, {});
   });
   ```
   and in `select()` replace
   `if (name === '_demo' && location.search) replaceState(resolve('/scenarier/'), {});`
   with
   `if (name === '_demo' && (location.pathname !== resolve('/scenarier/') || location.search)) replaceState(resolve('/scenarier/'), {});`
7. Head. Delete the `<svelte:head>…</svelte:head>` block (the layout owns `<title>` from Task 6).
8. Markup: directly ABOVE `{#if scenario.hbi != null}` (inside `{#if scenario}`) insert
   ```svelte
   {#if tiles}
   	<div class="key-figures" role="group" aria-label="Nøgletal">
   		{#each tiles as tile (tile.key)}
   			<StatTile label={`${tile.label}, år ${tile.year}`} value={tile.value ?? '–'} unit={tile.value == null ? '' : tile.unit} />
   		{/each}
   	</div>
   {/if}
   ```
   and change the chart/pending branch from `{#if scenario} … {:else} <div class="pending card">` to
   ```svelte
   {#if scenario}
   	…unchanged…
   {:else if loading}
   	<div class="card loading-card" aria-hidden="true">
   		{#if tiles}
   			<div class="key-figures">
   				{#each tiles as tile (tile.key)}
   					<StatTile label={`${tile.label}, år ${tile.year}`} value={tile.value ?? '–'} unit={tile.value == null ? '' : tile.unit} />
   				{/each}
   			</div>
   		{/if}
   		<p>Henter scenariet …</p>
   	</div>
   {:else}
   	<div class="pending card">
   ```
9. Styles: append to the `<style>` block
   ```css
   .key-figures {
   	display: grid;
   	grid-template-columns: repeat(3, minmax(0, 1fr));
   	gap: 18px;
   	max-width: 720px;
   	margin-bottom: 18px;
   	border-top: 1px solid var(--rule-strong);
   	padding-top: 12px;
   }

   .key-figures :global(.figure) {
   	border-left: 0;
   	padding-left: 0;
   }

   .loading-card p {
   	color: var(--ink-muted);
   	font-size: 14px;
   	margin: 0;
   }

   @media (max-width: 520px) {
   	.key-figures {
   		grid-template-columns: 1fr;
   	}
   }
   ```

- [ ] **Step 2: Rewrite the page as a wrapper**

`src/routes/scenarier/+page.svelte` (no `<svelte:head>`: Task 6 makes the layout the only owner of `<title>`):
```svelte
<script lang="ts">
	import ScenarioExplorer from '$lib/components/ScenarioExplorer.svelte';

	let { data } = $props();
</script>

<ScenarioExplorer meta={data.meta} initialScenario={data.initialScenario} />
```
Until Task 6 lands the tab reads "MAKROskop" on this route — which is what the current build already shows (the layout's title wins over the page's on /scenarier/ and /pakke/).

- [ ] **Step 3: Type-check and test**

Run: `bun run check && bun run test`
Expected: 0 errors, 0 warnings from svelte-check; all vitest suites pass. Fix any `Scenario` type import the component needs (`import { loadScenario, type Scenario, type ShockMeta } from '$lib/data';` already exists — merge with the new `loadBaseline, type Meta` import into one line).

- [ ] **Step 4: Check the page in a browser**

```bash
bun run build && bun run preview
```
Open `http://localhost:4173/scenarier/` and check, in order:
1. The demo scenario shows as before; the URL stays `/scenarier/`.
2. Click "Rente (ECB)": the URL becomes `/scenarier/Rente_ufin/` (path form now), the Nøgletal row shows three figures (persons appear once baseline.json has loaded), charts render.
3. Move the slider to ×0,5: the URL becomes `/scenarier/Rente_ufin/0.5/`, the tiles halve (BNP år 3 −0,6).
4. "Kopiér link" copies that URL; "Hent tal (CSV)" downloads; "Læg i en pakke →" still points at `/pakke/?Rente=0.5&variant=_ufin`.
5. Open `http://localhost:4173/scenarier/?stod=Rente&variant=_ufin&skala=0.5`: loads the same view.
6. Click "Syntetisk demo-scenarie": the URL returns to `/scenarier/`.
Stop the preview server afterwards.

- [ ] **Step 5: Commit**

```bash
git add src/lib/components/ScenarioExplorer.svelte src/routes/scenarier/+page.svelte
git commit -F - <<'MSG'
Scenarier: extract ScenarioExplorer with a Nøgletal row (makroskop-4w1)

The page body becomes a component both the bare route and the per-view share pages
render. Props: meta, initialScenario, an optional preselected view and its prerendered
tiles. New: a Nøgletal row (Beskæftigelse år 1 in persons, BNP år 3, Offentlig saldo år 1)
computed by the same buildCard the share cards use, a "Henter scenariet" state instead of
the demo while a deep link loads, and URL sync on pathname + search so the address bar
carries the path form. Scale steps and the change wording now come from lib/card.ts.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 6: The `[scenario]/[[skala]]` route and card-aware layout tags

**Files:**
- Create: `src/routes/scenarier/[scenario]/[[skala]]/+page.server.ts`, `src/routes/scenarier/[scenario]/[[skala]]/+page.svelte`
- Modify: `src/routes/+layout.svelte:36-79`, and remove the `<svelte:head><title>…</title></svelte:head>` blocks from `src/routes/+page.svelte`, `src/routes/pakke/+page.svelte`, `src/routes/validering/+page.svelte` (the layout becomes the only owner of `<title>`; today the built HTML shows the layout's "MAKROskop" winning over the page title on /scenarier/ and /pakke/ but not on / and /validering/, so per-page titles are not reliable).

**Interfaces:**
- Consumes: `buildCard`, `parseSkala`, `scaleSteps`, `shareViews`, `splitView`, `CardHead` (Task 1); `SITE_URL`; readers from Task 4; `ScenarioExplorer` (Task 5).
- Produces: page data `{ card: CardHead }` on the new route; the layout reads `page.data.card`.

- [ ] **Step 1: `+page.server.ts`**

```ts
/** One prerendered page per scenario view (shock + variant + scale) so link unfurls carry
 *  that view's title, description and og:image — crawlers do not run JavaScript and a
 *  static site cannot vary HTML by query string. Only the head data is returned: the
 *  scenario JSON itself is fetched on the client, as the ?stod= deep links do. */
import { error } from '@sveltejs/kit';
import type { EntryGenerator, PageServerLoad } from './$types';
import { buildCard, parseSkala, scaleSteps, shareViews, splitView, type CardHead } from '$lib/card';
import { levelsAt, maxScales, readBaseline, readMeta, readScenario, scenarioExists } from '$lib/server/scenarios';
import { SITE_URL } from '$lib/site';

export const prerender = true;

export const entries: EntryGenerator = () => {
	const meta = readMeta();
	return shareViews(meta, maxScales(meta));
};

export const load: PageServerLoad = ({ params }): { card: CardHead } => {
	const meta = readMeta();
	const view = splitView(params.scenario, meta.variations.map((v) => v.suffix));
	const scale = parseSkala(params.skala);
	const shock = view && meta.shocks.find((s) => s.name === view.name);
	if (!view || scale == null || !shock || !shock.available.includes(view.variation) || !scenarioExists(params.scenario)) {
		error(404, 'Ukendt scenarie');
	}
	const scenario = readScenario(params.scenario);
	if (!scenario.definition || !scaleSteps(scenario.definition.maxScale).includes(scale)) error(404, 'Ukendt scenarie');
	const card = buildCard({
		shock, scenario, yearStart: meta.yearStart, modelName: meta.model.name,
		levels: levelsAt(readBaseline(), scenario.definition.firstYear), scale
	});
	if (!card) error(404, 'Ukendt scenarie');
	return {
		card: {
			title: card.title,
			description: card.description,
			imageAlt: card.imageAlt,
			image: card.image,
			url: `${SITE_URL}${card.path}`,
			initial: { name: view.name, variation: view.variation, scale },
			tiles: card.tiles
		}
	};
};
```

- [ ] **Step 2: `+page.svelte`**

```svelte
<script lang="ts">
	import ScenarioExplorer from '$lib/components/ScenarioExplorer.svelte';

	let { data } = $props();
</script>

<ScenarioExplorer meta={data.meta} initialScenario={null} initial={data.card.initial} initialTiles={data.card.tiles} />
```

- [ ] **Step 3: Layout tags**

In `src/routes/+layout.svelte`, replace the `SITE_URL` constant and the `description`/`ogTitle` deriveds with:
```ts
import { SITE_URL } from '$lib/site';
import type { CardHead } from '$lib/card';

/** A prerendered scenario view hands its own card up through page data. */
const card = $derived(page.data.card as CardHead | undefined);
const current = $derived(links.find((link) => isActive(link.href)));
const description = $derived(card?.description ?? current?.description ?? SITE_DESCRIPTION);
const ogTitle = $derived(card?.title ?? (current ? `${current.label} · MAKROskop` : 'MAKROskop – udforsk MAKRO uden licens'));
/** The tab title: the card's headline number, else the page name. Only the layout sets <title>. */
const title = $derived(card ? `${card.title} · MAKROskop` : current ? `${current.label} · MAKROskop` : 'MAKROskop');
const ogImage = $derived(card ? `${SITE_URL}/og/${card.image}` : `${SITE_URL}/og.png`);
const ogImageAlt = $derived(
	card?.imageAlt ??
		'MAKROskop: Dansk økonomi, beregnet et århundrede frem – kurve for realt BNP 1985–2100 fra MAKROs grundforløb.'
);
```
and in `<svelte:head>` change `<title>MAKROskop</title>` to `<title>{title}</title>`, delete the `<svelte:head>…</svelte:head>` blocks from `src/routes/+page.svelte`, `src/routes/pakke/+page.svelte` and `src/routes/validering/+page.svelte`, and replace the `og:image` and `og:image:alt` tags with
```svelte
	<meta property="og:image" content={ogImage} />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:image:alt" content={ogImageAlt} />
	{#if card}
		<link rel="canonical" href={card.url} />
		<meta property="og:url" content={card.url} />
	{/if}
```
(keep `og:type`, `og:site_name`, `og:title={ogTitle}`, `og:description={description}`, `og:locale`, `twitter:card`, `theme-color` as they are).

- [ ] **Step 4: Type-check, build and inspect a page**

Run: `bun run check && bun run build`
Expected: svelte-check clean; the build prerenders ≈ 940 extra pages (watch for "The following routes were marked as prerenderable, but were not prerendered" — that means `entries()` threw; run `bun -e "import('./src/lib/server/scenarios.ts').then(m => console.log(Object.keys(m.maxScales(m.readMeta())).length))"` to see the error).

```bash
ls build/scenarier | head; ls build/scenarier/Rente_ufin
grep -o '<title>[^<]*</title>\|<meta property="og:[a-z:]*" content="[^"]*"\|<link rel="canonical" href="[^"]*"' build/scenarier/Rente_ufin/0.5/index.html
grep -c 'property="og:title"' build/scenarier/Rente_ufin/0.5/index.html build/scenarier/index.html
```
Expected: `build/scenarier/Rente_ufin/{index.html,0.5,-0.5,…}`; the 0.5 page shows `<title>ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år · MAKROskop</title>`, `og:title` with the card title (without the site name), `og:image` ending in `/og/Rente_ufin_0.5.png`, canonical and `og:url` `https://makroskop.nodalit.com/scenarier/Rente_ufin/0.5/`; each file has exactly one `og:title`; the bare page now says `<title>Scenarier · MAKROskop</title>` (it read "MAKROskop" before), and `grep -o "<title>[^<]*</title>" build/index.html build/pakke/index.html build/validering/index.html` gives Grundforløb, Pakker and Validering.

- [ ] **Step 5: Browser check of the new route**

`bun run preview`, open `http://localhost:4173/scenarier/Rente_ufin/0.5/`:
1. No demo flash: the page opens with the Nøgletal row (prerendered values) and "Henter scenariet …", then the charts appear at ×0,5 with the slider on 0,5.
2. The variant chips and shock list work; switching to "Permanent, finansieret" changes the URL to `/scenarier/Rente_perm/`.
3. `http://localhost:4173/scenarier/Rente_ufin/3/` → 404 page (no such prerendered file).
Stop the preview server.

- [ ] **Step 6: Commit**

```bash
git add "src/routes/scenarier/[scenario]" src/routes/+layout.svelte src/routes/+page.svelte src/routes/pakke/+page.svelte src/routes/validering/+page.svelte
git commit -F - <<'MSG'
Share cards: prerendered /scenarier/<view>/<skala>/ pages with their own tags (makroskop-4w1)

entries() lists every solved scenario x allowed scale step (~940 pages); load() returns
only the card head — title, description, og:image name, canonical/og:url, the initial
selection and the three tiles — so the pages stay small and the scenario JSON is fetched
client-side. The layout swaps og:title/description/image(:alt) for page.data.card and
adds canonical + og:url; the bare /scenarier/ keeps the generic tags. The layout is now
the only owner of <title>: with both layout and page setting one, the built HTML kept the
layout's "MAKROskop" on /scenarier/ and /pakke/ but the page's on / and /validering/.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 7: `permalink` emits the path form

**Files:**
- Modify: `src/lib/export.ts:13-20`, `src/lib/export.test.ts:4-18`

**Interfaces:**
- Consumes: `viewPath` (Task 1).
- Produces: `permalink(origin, { stod, variant, skala })` → `${origin}/scenarier/<stod><variant>/[<skala>/]`.

- [ ] **Step 1: Update the tests**

Replace the `permalink` describe block in `src/lib/export.test.ts` with:
```ts
describe('permalink', () => {
	it('is the prerendered view page, scale as a path segment', () => {
		expect(permalink('https://makroskop.nodalit.com', { stod: 'Rente', variant: '_ufin', skala: 1.5 })).toBe(
			'https://makroskop.nodalit.com/scenarier/Rente_ufin/1.5/'
		);
	});
	it('omits the scale segment when it is 1', () => {
		expect(permalink('https://x.dk', { stod: 'Bundskat', variant: '_ufin', skala: 1 })).toBe('https://x.dk/scenarier/Bundskat_ufin/');
	});
	it('keeps negative (mirrored) scales', () => {
		expect(permalink('https://x.dk', { stod: 'Bundskat', variant: '_ufin', skala: -0.5 })).toBe('https://x.dk/scenarier/Bundskat_ufin/-0.5/');
	});
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `bun run test -- src/lib/export.test.ts`
Expected: three failures (query form still produced).

- [ ] **Step 3: Implement**

In `src/lib/export.ts` replace the `permalink` function with:
```ts
import { viewPath } from './card';

/** Deep link to a scenario view: its prerendered page, which carries the view's own share tags. */
export function permalink(origin: string, p: PermalinkParams): string {
	return new URL(viewPath(p.stod, p.variant, p.skala), origin).toString();
}
```
(put the import with the other imports at the top of the file). Update the comment on `PermalinkParams` if it mentions the query form.

- [ ] **Step 4: Run all tests and the type check**

Run: `bun run test && bun run check`
Expected: PASS, clean. Also `grep -rn "stod=" src/routes src/lib` must only show the Validering page's deep link and `wantedView()` in the explorer, both of which keep working.

- [ ] **Step 5: Commit**

```bash
git add src/lib/export.ts src/lib/export.test.ts
git commit -F - <<'MSG'
Share cards: "Kopiér link" and CSV/PNG stamps use the view page URL (makroskop-4w1)

permalink() now builds /scenarier/<view>/<skala>/ so every copied or exported link unfurls
with the view's own card. The ?stod= form is still accepted on /scenarier/.

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 8: `verify-build.ts`, Docker build and documentation

**Files:**
- Create: `scripts/verify-build.ts`
- Modify: `README.md` (app), `../CLAUDE.md` (Layout section)

**Interfaces:**
- Consumes: `shareViews`, `imageFile`, `parseSkala` (Task 1); `readMeta`, `maxScales` (Task 4); `build/` output.
- Produces: `bun run verify:build` exits 0 only when pages, tags and images agree.

- [ ] **Step 1: Write the verifier**

`scripts/verify-build.ts`:
```ts
/** Post-build assertions for the share pages: every view has a page and an image, the
 *  sample page carries exactly one of each tag, the bare page keeps the generic ones.
 *  Run after `bun run build` (package.json "verify:build"); exits 1 on any failure. */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { shareViews } from '../src/lib/card';
import { maxScales, readMeta } from '../src/lib/server/scenarios';

const build = join(process.cwd(), 'build');
const failures: string[] = [];
const check = (ok: boolean, message: string) => { if (!ok) failures.push(message); };
const count = (html: string, pattern: RegExp) => (html.match(pattern) ?? []).length;

const meta = readMeta();
const views = shareViews(meta, maxScales(meta));
for (const view of views) {
	const dir = join(build, 'scenarier', view.scenario, view.skala ?? '');
	check(existsSync(join(dir, 'index.html')), `missing page ${dir}/index.html`);
	const image = `${view.scenario}${view.skala ? `_${view.skala}` : ''}.png`;
	check(existsSync(join(build, 'og', image)), `missing image build/og/${image}`);
}

const sample = readFileSync(join(build, 'scenarier', 'Rente_ufin', '0.5', 'index.html'), 'utf8');
check(count(sample, /<title>/g) === 1, 'sample: not exactly one <title>');
check(sample.includes('<title>ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år · MAKROskop</title>'), 'sample: <title> is not the card title');
for (const tag of ['og:title', 'og:description', 'og:image', 'og:image:alt', 'og:url']) {
	check(count(sample, new RegExp(`property="${tag}"`, 'g')) === 1, `sample: not exactly one ${tag}`);
}
check(sample.includes('content="https://makroskop.nodalit.com/og/Rente_ufin_0.5.png"'), 'sample: og:image is not the view image');
check(sample.includes('<link rel="canonical" href="https://makroskop.nodalit.com/scenarier/Rente_ufin/0.5/"'), 'sample: canonical missing');
check(sample.includes('vist som år efter stødet, lineært skaleret'), 'sample: honesty line missing from description');

const bare = readFileSync(join(build, 'scenarier', 'index.html'), 'utf8');
check(bare.includes('content="Scenarier · MAKROskop"'), 'bare page lost its generic og:title');
check(bare.includes('<title>Scenarier · MAKROskop</title>'), 'bare page: <title> is not the page name');
check(bare.includes('content="https://makroskop.nodalit.com/og.png"'), 'bare page lost the site og:image');
check(count(bare, /property="og:url"/g) === 0, 'bare page must not carry og:url');

if (failures.length) {
	console.error(`verify-build: ${failures.length} problem(s)\n` + failures.slice(0, 20).join('\n'));
	process.exit(1);
}
console.log(`verify-build: ${views.length} views, pages and images present, tags correct`);
```

- [ ] **Step 2: Run the full build and the verifier**

Run: `bun run build && bun run verify:build`
Expected: `verify-build: N views, pages and images present, tags correct` with N equal to the og-images count printed by the build.

- [ ] **Step 3: Docker build and smoke test (repo root)**

```bash
cd .. && docker build -t makroskop . && docker run --rm -d -p 8089:80 --name makroskop-test makroskop && sleep 2
curl -s http://localhost:8089/scenarier/Rente_ufin/0.5/ | grep -o '<meta property="og:title" content="[^"]*"'
curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download}\n" http://localhost:8089/og/Rente_ufin_0.5.png
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8089/scenarier/?stod=Rente
docker stop makroskop-test; cd app
```
Expected: the og:title line with the card title; `200 image/png` and a size between 20 000 and 200 000; `200` for the old query link. If the Docker build fails inside `og-images` with a resvg load error, the linux package is missing from `bun.lock`: run `bun install` locally with `--os linux`-independent lockfile regeneration (`rm -rf node_modules bun.lock && bun install`) and check `grep resvg-js-linux-x64-gnu bun.lock` before rebuilding.

- [ ] **Step 4: Documentation**

Append to `README.md` (app):
```markdown
## Delingskort (share cards)

Hvert løst scenarie i hver tilladt skala har sin egen prerenderede side,
`/scenarier/<Stød><variant>/<skala>/` (fx `/scenarier/Rente_ufin/0.5/`), med egen titel,
beskrivelse og `og:image`. Teksten kommer fra `src/lib/card.ts`, billedet fra
`src/lib/card-svg.ts` + `scripts/og-images.ts` (resvg, kører som en del af `bun run build`
og skriver til `build/og/`, som aldrig committes). Skrifterne i `fonts/` er statiske
TTF-instanser (OFL) — `bun fonts/fetch.ts` henter dem igen. `bun run verify:build` tjekker
sider, tags og billeder efter et build.
```

In `../CLAUDE.md`, in the Layout bullet for `app/`, after the Validering sentence add:
```
  Share cards: one prerendered page per scenario view at `/scenarier/<view>/<skala>/`
  (`src/routes/scenarier/[scenario]/[[skala]]/`, copy in `lib/card.ts`, image in
  `lib/card-svg.ts` rendered by `scripts/og-images.ts` during `bun run build`; fonts vendored
  in `app/fonts/`). `bun run verify:build` checks the output. Design: docs/superpowers/specs/2026-09-10-share-cards-design.md.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/verify-build.ts README.md ../CLAUDE.md
git commit -F - <<'MSG'
Share cards: verify-build script and docs (makroskop-4w1)

bun run verify:build asserts, after a build, that every view has a page and an og image,
that the sample page carries exactly one of each share tag with the card's title, image,
canonical and honesty line, and that the bare /scenarier/ keeps the generic tags.
Docker build smoke-tested locally (page tags, PNG served, old ?stod= link still 200).

Claude-Session: https://claude.ai/code/session_01ADUnj1baUFSSvS7ksK5W9Z
MSG
```

---

### Task 9: Final review, issue close, deploy decision

- [ ] **Step 1: Full quality gates**

```bash
bun run check && bun run test && bun run build && bun run verify:build
git status --short   # expected: clean (build/ is ignored)
```

- [ ] **Step 2: Render the ECB card and look at it once more**

`open build/og/Rente_ufin_0.5.png` (or Read it): headline "ECB-renten +0,5 pct.-point", subline "Varigt stød", tiles −5.500 personer / −0,6 pct. / −0,5 pct. af BNP, footer with the model name. Compare against `static/og.png` for type and spacing.

- [ ] **Step 3: Close the issue and hand off**

```bash
cd .. && bd close makroskop-4w1 --reason="Per-view prerendered share pages with card.ts copy, resvg og images at build, ScenarioExplorer extraction, verify-build; docker-tested." && cd app
```

Report to the user: commits made, the ECB link to share (`https://makroskop.nodalit.com/scenarier/Rente_ufin/0.5/`), and ask before `git push origin main` (push = public deploy). After the push and the Dokploy rebuild: `curl -s https://makroskop.nodalit.com/scenarier/Rente_ufin/0.5/ | grep -o '<meta property="og:[a-z:]*" content="[^"]*"'`, fetch the PNG, and paste the link into a Slack DM to yourself and into https://www.opengraph.xyz/ to see the unfurl.
