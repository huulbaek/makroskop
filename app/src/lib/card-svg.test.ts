import { describe, expect, it } from 'vitest';
import { sample } from './card.fixture';
import { cardSvg, escapeXml, fitHeadline, sparklinePath } from './card-svg';

describe('escapeXml', () => {
	it('escapes the five XML specials', () => {
		expect(escapeXml('a & b < c > "d" \'e\'')).toBe('a &amp; b &lt; c &gt; &quot;d&quot; &apos;e&apos;');
	});
});

describe('fitHeadline', () => {
	it('keeps a short headline on one 72 px line', () => {
		expect(fitHeadline('Rente +1 pct.-point')).toEqual({ size: 72, lines: ['Rente +1 pct.-point'] });
	});
	it('wraps to two lines before shrinking, and shrinks before allowing three', () => {
		const two = fitHeadline('Skattepligtige overførsler +1 pct.');
		expect(two.lines.length).toBeLessThanOrEqual(2);
		const long = fitHeadline('Offentlig beskæftigelse og offentligt varekøb +12,5 pct. i alle brancher');
		expect(long.size).toBeLessThan(72);
		expect(long.lines.length).toBeLessThanOrEqual(3);
	});
});

describe('sparklinePath', () => {
	it('draws a polyline through the box with the zero line inside it', () => {
		const { line, zeroY } = sparklinePath([0, -1, 1, null, 0.5], { x: 100, y: 200, w: 300, h: 100 });
		expect(line.startsWith('M100')).toBe(true);
		expect(line.split(/[ML]/).filter(Boolean)).toHaveLength(4);
		expect(zeroY).toBeGreaterThan(200);
		expect(zeroY).toBeLessThan(300);
	});
});

describe('cardSvg', () => {
	const svg = cardSvg(sample);
	it('is a 1200×630 document in the light palette', () => {
		expect(svg).toContain('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"');
		expect(svg).toContain('fill="#fbfbf8"');
	});
	it('carries the headline, subline, kicker, tiles and footer', () => {
		for (const text of ['ECB-renten +0,5 pct.-point', 'Varigt stød', 'stødår 2030', '−5.500', 'personer', 'Beskæftigelse, år 1', 'BNP, år 3', '−0,6', 'Offentlig saldo, år 1', 'MAKRO 2026-June', 'makroskop.nodalit.com']) {
			expect(svg).toContain(text);
		}
	});
	it('renders a missing tile value as an en dash and escapes text', () => {
		expect(svg).toContain('>–<');
		expect(cardSvg({ ...sample, headline: 'A & B' })).toContain('A &amp; B');
	});
});
