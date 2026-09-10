import { describe, expect, it } from 'vitest';
import { cardSvg } from '../src/lib/card-svg';
import { sample } from '../src/lib/card.fixture';
import { assertFonts, pngSize, renderPng } from './render-card';

describe('renderPng', () => {
	it('finds the vendored fonts', () => {
		expect(() => assertFonts()).not.toThrow();
	});
	it('rasterises a card to a 1200×630 PNG', () => {
		const png = renderPng(cardSvg(sample));
		expect(Array.from(png.slice(0, 4))).toEqual([0x89, 0x50, 0x4e, 0x47]);
		expect(pngSize(png)).toEqual({ width: 1200, height: 630 });
		expect(png.byteLength).toBeGreaterThan(10_000);
	});
});
