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
