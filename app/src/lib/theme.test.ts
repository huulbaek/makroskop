import { describe, expect, it } from 'vitest';
import { otherTheme, resolveTheme } from './theme';

describe('resolveTheme', () => {
	it('honours a stored choice over the system preference', () => {
		expect(resolveTheme('light', true)).toBe('light');
		expect(resolveTheme('dark', false)).toBe('dark');
	});
	it('follows the system preference when nothing is stored', () => {
		expect(resolveTheme(null, true)).toBe('dark');
		expect(resolveTheme(null, false)).toBe('light');
	});
	it('ignores garbage in storage', () => {
		expect(resolveTheme('sepia', true)).toBe('dark');
		expect(resolveTheme('', false)).toBe('light');
	});
});

describe('otherTheme', () => {
	it('flips between the two themes', () => {
		expect(otherTheme('light')).toBe('dark');
		expect(otherTheme('dark')).toBe('light');
	});
});
