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

export interface SolvedScenario {
	shock: ShockMeta;
	variation: string;
	/** the scenario file stem, `<name><variation>` */
	file: string;
}

/** Every solved scenario the catalog lists, in catalog order. */
export function solvedScenarios(meta: Pick<Meta, 'shocks'>): SolvedScenario[] {
	return meta.shocks.flatMap((shock) =>
		shock.available.map((variation) => ({ shock, variation, file: `${shock.name}${variation}` }))
	);
}

/** Every view that gets a page and an image: each solved scenario at each allowed step. */
export function solvedViews(
	meta: Pick<Meta, 'shocks'>, maxScales: Record<string, number | null>
): (SolvedScenario & { scale: number })[] {
	return solvedScenarios(meta).flatMap((solved) =>
		scaleSteps(maxScales[solved.file]).map((scale) => ({ ...solved, scale }))
	);
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
const daScale = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 2 });

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

/** Whether the instrument moves in a unit the numeric rule can state and scale: a plain rate
 *  change (factor 1, |delta| < 1 → pct.-point) or a plain percentage increase (delta 0, factor > 1).
 *  Anything else (a factor below 1 on a disutility parameter, a delta in mia. kr.) is worded by the
 *  catalog's own changeDa. */
export function scalableChange(def: Pick<ScenarioDefinition, 'delta' | 'factor'>): boolean {
	return (def.delta !== 0 && def.factor === 1 && Math.abs(def.delta) < 1) || (def.delta === 0 && def.factor > 1);
}

/** The scale as a bare Danish number with the true minus ("0,5", "−1"). */
export function formatScale(scale: number): string {
	return daScale.format(scale).replace('-', MINUS);
}

/** "×<scale>" — the short image headline for a scaled shock whose full change text (catalog
 *  changeDa plus the "af standardstødet" note) is too long to fit. */
export function scaleLabel(scale: number): string {
	return `×${formatScale(scale)}`;
}

/** The shock size in the instrument's own unit, the page's rule. */
export function changeText(def: Pick<ScenarioDefinition, 'delta' | 'factor' | 'changeDa'>, scale: number): string {
	if (!scalableChange(def)) {
		return scale === 1 ? def.changeDa : `${scaleLabel(scale)} af standardstødet (${def.changeDa})`;
	}
	if (def.delta !== 0) return `${formatSigned(def.delta * 100 * scale).replace('-', MINUS)} pct.-point`;
	const suffix = def.changeDa.endsWith('af satsen') ? ' af satsen' : '';
	return `${formatSigned((def.factor - 1) * 100 * scale).replace('-', MINUS)} pct.${suffix}`;
}

const PROFILE_WORD: Record<string, string> = { _perm: 'varigt', _ufin: 'varigt', _midl: 'midlertidigt', _blip: 'i ét år' };
const PROFILE_SUBLINE: Record<string, string> = {
	_perm: 'Varigt stød', _ufin: 'Varigt stød', _midl: 'Midlertidigt stød (AR-profil)', _blip: '1-årigt stød'
};
const MAX_INSTRUMENT_CHARS = 24;

/** Headline subject where the catalog label names the other side of the instrument: the Loen shock
 *  lowers the employers' Nash weight, which the catalog labels as workers' bargaining power. The
 *  numeric sign only holds against the side that moves. A catalog `shortDa` is the proper home. */
const INSTRUMENT_SHORT: Record<string, string> = { Loen: 'Arbejdsgivernes forhandlingsvægt' };

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

/** The prerender entry list: one `{ scenario, skala? }` per view (`skala` absent at the solved size). */
export function shareViews(
	meta: Pick<Meta, 'shocks'>, maxScales: Record<string, number | null>
): { scenario: string; skala?: string }[] {
	return solvedViews(meta, maxScales).map(({ file, scale }) =>
		scale === 1 ? { scenario: file } : { scenario: file, skala: String(scale) }
	);
}

/** Scaled deviation of a series in a calendar year, null where the series has no value. */
function deviationAt(scenario: Pick<Scenario, 'deviations'>, yearStart: number, scale: number) {
	return (key: string, year: number): number | null => {
		const value = scenario.deviations[key]?.[year - yearStart];
		return value == null ? null : value * scale;
	};
}

export interface TileInput {
	scenario: Pick<Scenario, 'deviations'>;
	definition: Pick<ScenarioDefinition, 'firstYear'>;
	yearStart: number;
	levels: CardLevels | null;
	scale: number;
}

/** The three fixed headline figures, in layout order: Beskæftigelse år 1 (persons), BNP år 3,
 *  Offentlig saldo år 1. Cheap enough for the page to recompute on every slider step. */
export function cardTiles({ scenario, definition, yearStart, levels, scale }: TileInput): CardTile[] {
	const at = deviationAt(scenario, yearStart, scale);
	const y1 = definition.firstYear;
	const employment = at('nL', y1);
	const gdp = at('qBNP', y1 + 2);
	const balance = at('saldo2bnp', y1);
	return [
		{ key: 'nL', label: 'Beskæftigelse', year: 1, unit: 'personer',
			value: employment == null || levels == null ? null : formatPersons((employment / 100) * levels.nL * 1000) },
		{ key: 'qBNP', label: 'BNP', year: 3, unit: 'pct.', value: gdp == null ? null : formatTileValue(gdp) },
		{ key: 'saldo2bnp', label: 'Offentlig saldo', year: 1, unit: 'pct. af BNP', value: balance == null ? null : formatTileValue(balance) }
	];
}

export function buildCard(input: {
	shock: ShockMeta; scenario: Scenario; definition: ScenarioDefinition; yearStart: number; modelName: string;
	levels: CardLevels | null; scale: number;
}): CardData {
	const { shock, scenario, definition: def, yearStart, levels, scale } = input;
	const at = deviationAt(scenario, yearStart, scale);
	const y1 = def.firstYear;
	const tiles = cardTiles({ scenario, definition: def, yearStart, levels, scale });
	const [persons, bnp, saldo] = tiles;

	const instrument = INSTRUMENT_SHORT[shock.name] ?? (def.instrumentDa.length <= MAX_INSTRUMENT_CHARS ? def.instrumentDa : shock.labelDa);
	const change = changeText(def, scale);
	const headline = `${instrument} ${change}`;
	/** A scaled catalog-worded shock's full change text ("×0,5 af standardstødet (+10 mia. kr.
	 *  årligt)") can run to three unfittable lines on the image. Title and description keep the
	 *  full text; the image headline shortens to the bare scale, moving the standardstød to the
	 *  subline. */
	const shortForm = !scalableChange(def) && scale !== 1;
	const profileWord = PROFILE_SUBLINE[scenario.variation] ?? 'Varigt stød';
	const cardHeadline = shortForm ? `${instrument} ${scaleLabel(scale)}` : headline;
	const subline = shortForm ? `${profileWord} · standardstød ${def.changeDa}` : profileWord;
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
		headline: cardHeadline,
		subline,
		kicker: `Scenarie · ${closure} · stødår ${y1}, vist som år efter stødet`,
		closure,
		tiles,
		sparkline: Array.from({ length: 16 }, (_, k) => at('qBNP', y1 - 1 + k)),
		model: input.modelName
	};
}
