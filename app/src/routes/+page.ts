import { loadBaseline } from '$lib/data';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	return { baseline: await loadBaseline(fetch) };
};
