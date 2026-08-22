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
	model: { name: string; commit: string };
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

export interface Scenario {
	shock: string;
	variation: string;
	synthetic: boolean;
	labelDa?: string;
	hbi: number | null;
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
