import { existsSync, mkdtempSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { buildCard, solvedViews } from '../src/lib/card';
import { fitHeadline } from '../src/lib/card-svg';
import { levelsAt, maxScales, readBaseline, readMeta, readScenario, scenarioExists } from '../src/lib/server/scenarios';
import { generateCards } from './og-images';

const DISPLAY_EM = 0.46;
const HEADLINE_WIDTH = 690;

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

describe('every real headline fits the image', () => {
	it('fitHeadline neither throws nor drops words for any of the 932 views', () => {
		const meta = readMeta();
		const baseline = readBaseline();
		let checked = 0;
		for (const { shock, file, scale } of solvedViews(meta, maxScales(meta))) {
			const scenario = readScenario(file);
			const definition = scenario.definition!;
			const levels = levelsAt(baseline, definition.firstYear);
			const card = buildCard({ shock, scenario, definition, yearStart: meta.yearStart, modelName: meta.model.name, levels, scale });
			const { size, lines } = fitHeadline(card.headline);
			expect(lines.join(' ')).toBe(card.headline);
			for (const line of lines) expect(line.length * DISPLAY_EM * size).toBeLessThanOrEqual(HEADLINE_WIDTH);
			checked++;
		}
		expect(checked).toBe(932);
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
