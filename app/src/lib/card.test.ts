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
