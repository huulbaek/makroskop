/** Colour scheme: the visitor's explicit choice (stored) or, failing that, the OS setting.
 *  The inline script in app.html applies the same rule before first paint; keep them in step. */

export type Theme = 'light' | 'dark';

/** localStorage key holding the visitor's explicit choice; absent = follow the OS. */
export const STORAGE_KEY = 'makroskop-theme';

export function isTheme(value: unknown): value is Theme {
	return value === 'light' || value === 'dark';
}

export function resolveTheme(stored: string | null, systemDark: boolean): Theme {
	if (isTheme(stored)) return stored;
	return systemDark ? 'dark' : 'light';
}

export function otherTheme(theme: Theme): Theme {
	return theme === 'dark' ? 'light' : 'dark';
}
