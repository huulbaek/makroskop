import { describe, expect, it } from 'vitest';
import { wrapLines } from './text';

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
