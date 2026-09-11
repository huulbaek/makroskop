/** Build-time readers for the committed data JSON (static/data). Used by the prerendered
 *  view route (+page.server.ts) and by scripts/og-images.ts, so both see the same files.
 *  Paths resolve from the working directory, which is app/ for `vite build`, `vite dev`
 *  and the bun scripts (the Dockerfile's WORKDIR is /app). Relative imports only: the bun
 *  script has no `$lib` alias. */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { solvedScenarios, type CardLevels } from '../card';
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
	return Object.fromEntries(
		solvedScenarios(meta).map(({ file }) => [file, readScenario(file).definition?.maxScale ?? null])
	);
}
