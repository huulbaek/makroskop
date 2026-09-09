import { describe, expect, it } from 'vitest';
import { permalink, provenanceLine, scenarioCsv, exportFilename, wrapLines, packagePermalink, packageFilename } from './export';

describe('permalink', () => {
	it('encodes shock, variant and a non-unit scale', () => {
		expect(permalink('https://makroskop.nodalit.com', { stod: 'Rente', variant: '_ufin', skala: 1.5 })).toBe(
			'https://makroskop.nodalit.com/scenarier/?stod=Rente&variant=_ufin&skala=1.5'
		);
	});
	it('omits the scale when it is 1', () => {
		expect(permalink('https://x.dk', { stod: 'Bundskat', variant: '_ufin', skala: 1 })).toBe(
			'https://x.dk/scenarier/?stod=Bundskat&variant=_ufin'
		);
	});
	it('keeps negative (mirrored) scales', () => {
		expect(permalink('https://x.dk', { stod: 'Bundskat', variant: '_ufin', skala: -0.5 })).toContain('skala=-0.5');
	});
});

describe('provenanceLine', () => {
	it('joins the stamp with middle dots', () => {
		expect(
			provenanceLine({ model: 'MAKRO 2026-June', commit: '01f2a43', closure: 'Permanent, ufinansieret', date: '2026-08-28' })
		).toBe('MAKROskop · makroskop.nodalit.com · MAKRO 2026-June (01f2a43) · permanent, ufinansieret · 2026-08-28');
	});
	it('cites the data basis next to the model version when known', () => {
		expect(
			provenanceLine({
				model: 'MAKRO 2026-June',
				commit: '01f2a43',
				dataBasis: 'Nationalregnskabsdata fra marts 2026',
				closure: 'Permanent, ufinansieret',
				date: '2026-08-28'
			})
		).toBe(
			'MAKROskop · makroskop.nodalit.com · MAKRO 2026-June (01f2a43), Nationalregnskabsdata fra marts 2026 · permanent, ufinansieret · 2026-08-28'
		);
	});
	it('drops an empty commit', () => {
		expect(provenanceLine({ model: 'MAKRO 2026-June', commit: '', closure: 'X', date: '2026-08-28' })).toContain(
			'· MAKRO 2026-June · x ·'
		);
	});
});

describe('scenarioCsv', () => {
	const csv = scenarioCsv({
		years: [2029, 2030, 2031],
		columns: [
			{ key: 'qBNP', label: 'BNP, real', unit: 'pct.', values: [0, -0.1234, null] },
			{ key: 'saldo2bnp', label: 'Saldo', unit: 'pct.-point', values: [0, 0.5, 1.23456] }
		],
		provenance: ['MAKROskop · test', 'Kilde: https://x.dk/scenarier/?stod=Rente']
	});
	const lines = csv.split('\n');
	it('starts with # provenance lines', () => {
		expect(lines[0]).toBe('# MAKROskop · test');
		expect(lines[1]).toBe('# Kilde: https://x.dk/scenarier/?stod=Rente');
	});
	it('uses semicolons and units in the header', () => {
		expect(lines[2]).toBe('År;BNP, real (pct.);Saldo (pct.-point)');
	});
	it('writes Danish decimal commas, 4 decimals, blanks for missing', () => {
		expect(lines[3]).toBe('2029;0;0');
		expect(lines[4]).toBe('2030;-0,1234;0,5');
		expect(lines[5]).toBe('2031;;1,2346');
	});
	it('ends with a newline', () => {
		expect(csv.endsWith('\n')).toBe(true);
	});
});

describe('exportFilename', () => {
	it('builds a safe, descriptive name', () => {
		expect(exportFilename({ stod: 'Rente', variant: '_ufin', key: 'qBNP', skala: 1, ext: 'png' })).toBe(
			'makroskop_Rente_ufin_qBNP.png'
		);
		expect(exportFilename({ stod: 'Bundskat', variant: '_ufin', key: null, skala: -0.5, ext: 'csv' })).toBe(
			'makroskop_Bundskat_ufin_x-0.5.csv'
		);
	});
});

describe('scenarioCsv trimming', () => {
	it('drops leading years where every column is empty', () => {
		const csv = scenarioCsv({
			years: [2027, 2028, 2029, 2030],
			columns: [{ key: 'a', label: 'A', unit: 'pct.', values: [null, null, 0, 1] }],
			provenance: []
		});
		expect(csv.split('\n').slice(0, 3)).toEqual(['År;A (pct.)', '2029;0', '2030;1']);
	});
});

describe('wrapLines', () => {
	// a fake measurer: 10 px per character
	const measure = (s: string) => s.length * 10;
	it('returns the line unchanged when it fits', () => {
		expect(wrapLines(measure, 'kort tekst', 200)).toEqual(['kort tekst']);
	});
	it('breaks at spaces to fit the width', () => {
		expect(wrapLines(measure, 'en to tre fire fem seks', 100)).toEqual(['en to tre', 'fire fem', 'seks']);
	});
	it('keeps an overlong single word on its own line', () => {
		expect(wrapLines(measure, 'https://very-long-url-without-spaces x', 100)).toEqual([
			'https://very-long-url-without-spaces',
			'x'
		]);
	});
});

describe('packagePermalink', () => {
	it('points at the package page with the query as given', () => {
		expect(packagePermalink('https://x.dk', 'Bundskat=-1&variant=_perm')).toBe(
			'https://x.dk/pakke/?Bundskat=-1&variant=_perm'
		);
	});
});

describe('packageFilename', () => {
	it('names the file after the components, closure and chart', () => {
		expect(
			packageFilename([{ name: 'Bundskat', scale: -1 }, { name: 'Moms', scale: 1 }], '_perm', 'qBNP', 'png')
		).toBe('makroskop_pakke_Bundskat_x-1_Moms_perm_qBNP.png');
	});
	it('omits the chart key for the CSV', () => {
		expect(packageFilename([{ name: 'Rente', scale: 1.5 }], '_ufin', null, 'csv')).toBe(
			'makroskop_pakke_Rente_x1.5_ufin.csv'
		);
	});
});
