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
	if (!/[1-9]/.test(text)) return text.replace(/^-/, ''); // rounds to zero: no sign at all
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
	const formattedValue = formatSigned(def.delta !== 0 ? def.delta * 100 * scale : (def.factor - 1) * 100 * scale).replace('-', MINUS);
	const unit = def.delta !== 0 ? 'pct.-point' : 'pct.';
	return `${formattedValue} ${unit}`;
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
		sparkline: Array.from({ length: 16 }, (_, k) => at('qBNP', y1 - 1 + k)),
		model: input.modelName
	};
}
