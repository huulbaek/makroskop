import { loadBaseline } from '$lib/data';
import type { PageLoad } from './$types';

/** The baseline levels turn the package's pct. deviations into kr. and persons. */
export const load: PageLoad = async ({ fetch }) => {
	return { baseline: await loadBaseline(fetch) };
};
