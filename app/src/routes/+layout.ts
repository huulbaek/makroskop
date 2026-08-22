import { loadMeta } from '$lib/data';
import type { LayoutLoad } from './$types';

export const prerender = true;
export const trailingSlash = 'always';

export const load: LayoutLoad = async ({ fetch }) => {
	return { meta: await loadMeta(fetch) };
};
