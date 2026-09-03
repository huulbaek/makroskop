/** Pure helpers for the Pakke-værksted: a policy package is an ordered list of catalog
 *  shocks with signed sizes, superposed linearly in the browser. Everything here is
 *  unit-tested; the page owns the loading and the rendering. */

export interface PackageComponent {
	name: string;
	scale: number;
}

/** The same ladder the Scenarier slider offers: negative steps mirror the shock
 *  (the catalog only holds increases), ×1 is the solved size. */
export const ALL_SCALE_STEPS = [-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
export const UNSCALED = 1;
export const DEFAULT_VARIANT = '_perm';
const VARIANT_PARAM = 'variant';

/** Steps allowed for one shock. Where the model has a boundary the solver could not
 *  cross, the catalog caps the magnitude, which trims the mirrored side too. */
export function scaleSteps(maxScale: number | null | undefined): number[] {
	const steps = maxScale == null ? ALL_SCALE_STEPS : ALL_SCALE_STEPS.filter((s) => Math.abs(s) <= maxScale);
	return steps.includes(UNSCALED) ? steps : [...steps, UNSCALED].sort((a, b) => a - b);
}

/** `?Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm` → components in parameter order.
 *  Unknown shocks, unparsable or zero sizes and repeated names are dropped; an unknown
 *  variant falls back to the financed default. */
export function parsePackageQuery(
	params: URLSearchParams,
	shockNames: Iterable<string>,
	variantSuffixes: Iterable<string>,
	defaultVariant: string = DEFAULT_VARIANT
): { components: PackageComponent[]; variant: string } {
	const known = new Set(shockNames);
	const variants = new Set(variantSuffixes);
	const components: PackageComponent[] = [];
	const seen = new Set<string>();
	for (const [name, raw] of params) {
		if (name === VARIANT_PARAM || !known.has(name) || seen.has(name)) continue;
		const scale = Number(raw);
		if (!Number.isFinite(scale) || scale === 0) continue;
		seen.add(name);
		components.push({ name, scale });
	}
	const wanted = params.get(VARIANT_PARAM);
	const variant = wanted != null && variants.has(wanted) ? wanted : defaultVariant;
	return { components, variant };
}

/** Inverse of parsePackageQuery. The variant is always written so a link says what it
 *  shows even when the default changes later. Shock names are plain ASCII identifiers,
 *  so the string is readable as-is. */
export function packageQuery(components: PackageComponent[], variant: string): string {
	const params = new URLSearchParams();
	for (const c of components) params.set(c.name, String(c.scale));
	params.set(VARIANT_PARAM, variant);
	return params.toString();
}

/** Linear superposition of deviation columns: Σ scale·values, null wherever any part
 *  has no value (the solved windows all start in the same year, so this only masks the
 *  pre-window history). */
export function superpose(parts: { scale: number; values: (number | null)[] }[]): (number | null)[] {
	if (parts.length === 0) return [];
	const length = Math.max(...parts.map((p) => p.values.length));
	const out: (number | null)[] = new Array(length);
	for (let i = 0; i < length; i++) {
		let sum = 0;
		let missing = false;
		for (const part of parts) {
			const v = part.values[i];
			if (v == null) {
				missing = true;
				break;
			}
			sum += part.scale * v;
		}
		out[i] = missing ? null : sum;
	}
	return out;
}

/** A pct. deviation applied to a baseline level, in the level's own unit. */
export function pctToLevel(pct: number | null, base: number | null | undefined): number | null {
	if (pct == null || base == null) return null;
	return (base * pct) / 100;
}

/** Pct.-points of GDP into the currency of the nominal GDP passed in. */
export function gdpPpToKr(pp: number | null, vBNP: number | null | undefined): number | null {
	if (pp == null || vBNP == null) return null;
	return (vBNP * pp) / 100;
}

const daScale = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 2 });

/** Danish ×-factor as it appears in readouts and exports. */
export function formatScale(scale: number): string {
	return daScale.format(scale);
}

/** The package in one line, for the page header and every export:
 *  "Pakke: Bundskat ×−1 (−1 pct.-point, spejlet) + Offentligt forbrug ×0,5 (+0,5 pct.) — permanent, finansieret" */
export function packageLine(
	items: { labelDa: string; scale: number; changeDa: string }[],
	closureLabel: string
): string {
	const parts = items.map((item) => {
		const mirrored = item.scale < 0 ? ', spejlet' : '';
		return `${item.labelDa} ×${formatScale(item.scale)} (${item.changeDa}${mirrored})`;
	});
	return `Pakke: ${parts.join(' + ')} — ${closureLabel.toLowerCase()}`;
}
