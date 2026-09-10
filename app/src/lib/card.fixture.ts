import type { CardData } from './card';

/** Rente_ufin at ×0.5 as buildCard produces it, with one tile left empty on purpose. */
export const sample: CardData = {
	name: 'Rente', variation: '_ufin', scale: 0.5, path: '/scenarier/Rente_ufin/0.5/', image: 'Rente_ufin_0.5.png',
	title: 'ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år',
	description: 'x', imageAlt: 'x',
	headline: 'ECB-renten +0,5 pct.-point', subline: 'Varigt stød',
	kicker: 'Scenarie · ufinansieret · stødår 2030, vist som år efter stødet', closure: 'ufinansieret',
	tiles: [
		{ key: 'nL', label: 'Beskæftigelse', year: 1, value: '−5.500', unit: 'personer' },
		{ key: 'qBNP', label: 'BNP', year: 3, value: '−0,6', unit: 'pct.' },
		{ key: 'saldo2bnp', label: 'Offentlig saldo', year: 1, value: null, unit: 'pct. af BNP' }
	],
	sparkline: [-0.42, -0.55, -0.58, -0.58, -0.57, -0.58, -0.6, -0.62, -0.64, -0.65, -0.66, -0.67, -0.68, -0.69, -0.7, -0.71],
	model: 'MAKRO 2026-June'
};
