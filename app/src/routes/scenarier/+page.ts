import { loadScenario } from '$lib/data';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	return { initialScenario: await loadScenario(fetch, '_demo') };
};
