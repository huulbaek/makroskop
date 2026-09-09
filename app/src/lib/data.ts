export interface SeriesMeta {
	key: string;
	labelDa: string;
	labelEn: string;
	group: string;
	unit: string;
	devMode: 'pct' | 'pp' | 'gdp_pp';
	sector: string | null;
}

export interface ShockMeta {
	name: string;
	labelDa: string;
	labelEn: string;
	group: string;
	/** variation suffixes for which a solved GDX has been ingested */
	available: string[];
}

export interface VariationMeta {
	suffix: string;
	labelDa: string;
	labelEn: string;
}

export interface Meta {
	model: { name: string; commit: string; fingerprint?: string; dataBasisDa?: string };
	yearStart: number;
	yearEnd: number;
	lastDataYear: number;
	defaultShockYear: number;
	sectors: Record<string, string>;
	series: SeriesMeta[];
	shocks: ShockMeta[];
	variations: VariationMeta[];
}

export interface Baseline {
	years: number[];
	series: Record<string, (number | null)[]>;
	indicators: { rHBI: number | null };
}

/** How the free solver implemented the shock (written by etl/extract.py from catalog.SHOCK_RUNS). */
export interface ScenarioDefinition {
	instrument: string;
	instrumentDa: string;
	changeDa: string;
	factor: number;
	delta: number;
	firstYear: number;
	lastYear: number;
	profileDa: string;
	closureDa: string;
	dreamDa: string;
	seriesKey: string | null;
	solver: string;
	linearityDa: string;
	/** Largest |scale| the slider may offer, where the model has a boundary the solver
	 *  could not cross. null = the UI default. */
	maxScale: number | null;
	maxScaleDa: string | null;
	/** Plain-language mechanism text for readers, when the catalog has one. */
	explainerDa?: string | null;
}

/** Which MAKRO version a scenario was solved on. `source` is "gdx" when the solver
 *  stamped the result file, "assumed" when an unstamped file was taken to match the
 *  MAKRO checkout at extract time. */
export interface ScenarioModelVersion {
	name: string;
	commit: string;
	fingerprint: string;
	source: 'gdx' | 'assumed';
}

export interface Scenario {
	shock: string;
	variation: string;
	synthetic: boolean;
	labelDa?: string;
	hbi: number | null;
	definition?: ScenarioDefinition | null;
	modelVersion?: ScenarioModelVersion | null;
	deviations: Record<string, (number | null)[]>;
}

export async function loadMeta(fetcher: typeof fetch): Promise<Meta> {
	const response = await fetcher('/data/meta.json');
	return response.json();
}

export async function loadBaseline(fetcher: typeof fetch): Promise<Baseline> {
	const response = await fetcher('/data/baseline.json');
	return response.json();
}

export async function loadScenario(fetcher: typeof fetch, file: string): Promise<Scenario | null> {
	const response = await fetcher(`/data/shocks/${file}.json`);
	if (!response.ok) return null;
	return response.json();
}

export function seriesByKey(meta: Meta): Map<string, SeriesMeta> {
	return new Map(meta.series.map((s) => [s.key, s]));
}
