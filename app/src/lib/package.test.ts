import { describe, expect, it } from 'vitest';
import {
	ALL_SCALE_STEPS,
	financedCostLine,
	unfinancedCostLine,
	gdpPpToKr,
	packageLine,
	packageQuery,
	parsePackageQuery,
	pctToLevel,
	scaleSteps,
	superpose
} from './package';

const SHOCKS = ['Bundskat', 'Offentligt_forbrug', 'Rente'];
const VARIANTS = ['_perm', '_ufin'];

describe('parsePackageQuery', () => {
	it('reads components in parameter order with their signed scales', () => {
		const params = new URLSearchParams('Offentligt_forbrug=0.5&Bundskat=-1&variant=_ufin');
		expect(parsePackageQuery(params, SHOCKS, VARIANTS)).toEqual({
			components: [
				{ name: 'Offentligt_forbrug', scale: 0.5 },
				{ name: 'Bundskat', scale: -1 }
			],
			variant: '_ufin'
		});
	});
	it('drops unknown shocks, unparsable and zero scales', () => {
		const params = new URLSearchParams('Bundskat=abc&Rente=0&Momsx=1&Offentligt_forbrug=1');
		expect(parsePackageQuery(params, SHOCKS, VARIANTS).components).toEqual([
			{ name: 'Offentligt_forbrug', scale: 1 }
		]);
	});
	it('falls back to the financed closure when the variant is missing or unknown', () => {
		expect(parsePackageQuery(new URLSearchParams('Bundskat=1'), SHOCKS, VARIANTS).variant).toBe('_perm');
		expect(parsePackageQuery(new URLSearchParams('variant=_blip'), SHOCKS, VARIANTS).variant).toBe('_perm');
	});
	it('keeps only the first occurrence of a repeated shock', () => {
		const params = new URLSearchParams('Bundskat=1&Bundskat=2');
		expect(parsePackageQuery(params, SHOCKS, VARIANTS).components).toEqual([{ name: 'Bundskat', scale: 1 }]);
	});
});

describe('packageQuery', () => {
	it('serialises components and always writes the variant', () => {
		expect(packageQuery([{ name: 'Bundskat', scale: -1 }, { name: 'Offentligt_forbrug', scale: 0.5 }], '_perm')).toBe(
			'Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm'
		);
	});
	it('round-trips through parsePackageQuery', () => {
		const components = [{ name: 'Rente', scale: 1.25 }, { name: 'Bundskat', scale: -0.75 }];
		const parsed = parsePackageQuery(new URLSearchParams(packageQuery(components, '_ufin')), SHOCKS, VARIANTS);
		expect(parsed).toEqual({ components, variant: '_ufin' });
	});
});

describe('scaleSteps', () => {
	it('offers the full ladder without a cap', () => {
		expect(scaleSteps(null)).toEqual(ALL_SCALE_STEPS);
	});
	it('trims both sides to the magnitude cap and keeps 1', () => {
		expect(scaleSteps(0.5)).toEqual([-0.5, -0.25, 0.25, 0.5, 1]);
	});
});

describe('superpose', () => {
	it('returns the values unchanged for a single part at scale 1', () => {
		expect(superpose([{ scale: 1, values: [null, 0, 1.5] }])).toEqual([null, 0, 1.5]);
	});
	it('adds weighted parts and is null where any part is null', () => {
		expect(
			superpose([
				{ scale: -1, values: [null, 1, 2, 3] },
				{ scale: 0.5, values: [null, 2, null, 4] }
			])
		).toEqual([null, 0, null, -1]);
	});
	it('is empty for no parts', () => {
		expect(superpose([])).toEqual([]);
	});
});

describe('conversions', () => {
	it('turns a percentage deviation into a level change', () => {
		expect(pctToLevel(-0.2, 3000)).toBeCloseTo(-6);
		expect(pctToLevel(null, 3000)).toBeNull();
		expect(pctToLevel(1, undefined)).toBeNull();
	});
	it('turns pct.-points of GDP into kr.', () => {
		expect(gdpPpToKr(0.36, 3877)).toBeCloseTo(13.957);
		expect(gdpPpToKr(0.36, null)).toBeNull();
	});
});

describe('packageLine', () => {
	it('lists each component with its size and marks mirrored ones', () => {
		expect(
			packageLine(
				[
					{ labelDa: 'Bundskat', scale: -1, changeDa: '-1 pct.-point' },
					{ labelDa: 'Offentligt forbrug', scale: 0.5, changeDa: '+0,5 pct.' }
				],
				'Permanent, finansieret'
			)
		).toBe('Pakke: Bundskat ×-1 (-1 pct.-point, spejlet) + Offentligt forbrug ×0,5 (+0,5 pct.) — permanent, finansieret');
	});
});

describe('unfinancedCostLine', () => {
	it('says what the package costs the public finances, rounded like the table', () => {
		expect(unfinancedCostLine(2035, -0.34, -15.62)).toBe(
			'I 2035 koster pakken de offentlige finanser ca. 15,6 mia. kr. om året (-0,34 pct.-point af BNP).'
		);
	});
	it('says what the package gives', () => {
		expect(unfinancedCostLine(2035, 0.02, 0.92)).toBe(
			'I 2035 giver pakken de offentlige finanser ca. 0,92 mia. kr. om året (+0,02 pct.-point af BNP).'
		);
	});
	it('shows a small amount the table also shows, with the pct.-point rounded to 0', () => {
		expect(unfinancedCostLine(2035, 0.001, 0.03)).toBe(
			'I 2035 giver pakken de offentlige finanser ca. 0,03 mia. kr. om året (0 pct.-point af BNP).'
		);
	});
	it('calls the package neutral only when the kr. round to zero', () => {
		expect(unfinancedCostLine(2035, 0.0001, 0.004)).toBe('I 2035 er pakken omtrent neutral for de offentlige finanser.');
		expect(unfinancedCostLine(2035, -0.0001, -0.004)).toBe('I 2035 er pakken omtrent neutral for de offentlige finanser.');
	});
	it('returns an empty string without numbers', () => {
		expect(unfinancedCostLine(2035, null, null)).toBe('');
		expect(unfinancedCostLine(2035, -0.3, null)).toBe('');
	});
});

describe('financedCostLine', () => {
	it('states the closure tax change without claiming the yearly saldo is unchanged', () => {
		expect(financedCostLine(1.46)).toBe(
			'Finansieret: lukkeskatten skal hæves 1,46 pct.-point, for at de offentlige finanser forbliver holdbare på langt sigt.'
		);
		expect(financedCostLine(-0.7)).toBe(
			'Finansieret: pakken giver råderum – lukkeskatten kan sænkes 0,7 pct.-point, og de offentlige finanser forbliver holdbare.'
		);
	});
	it('treats a change that rounds to zero as none', () => {
		expect(financedCostLine(0.001)).toBe('Finansieret: pakken kræver ingen nævneværdig ændring af lukkeskatten.');
	});
	it('returns an empty string without a number', () => {
		expect(financedCostLine(null)).toBe('');
	});
});
