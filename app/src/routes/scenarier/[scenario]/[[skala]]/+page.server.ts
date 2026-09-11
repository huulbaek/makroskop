/** One prerendered page per scenario view (shock + variant + scale) so link unfurls carry
 *  that view's title, description and og:image — crawlers do not run JavaScript and a
 *  static site cannot vary HTML by query string. Only the head data is returned: the
 *  scenario JSON itself is fetched on the client, as the ?stod= deep links do. */
import { error } from '@sveltejs/kit';
import type { EntryGenerator, PageServerLoad } from './$types';
import { buildCard, parseSkala, scaleSteps, shareViews, splitView, type CardHead } from '$lib/card';
import { levelsAt, maxScales, readBaseline, readMeta, readScenario, scenarioExists } from '$lib/server/scenarios';
import { SITE_URL } from '$lib/site';

export const prerender = true;

export const entries: EntryGenerator = () => {
	const meta = readMeta();
	return shareViews(meta, maxScales(meta));
};

export const load: PageServerLoad = ({ params }): { card: CardHead } => {
	const meta = readMeta();
	const view = splitView(params.scenario, meta.variations.map((v) => v.suffix));
	const scale = parseSkala(params.skala);
	const shock = view && meta.shocks.find((s) => s.name === view.name);
	if (!view || scale == null || !shock || !shock.available.includes(view.variation) || !scenarioExists(params.scenario)) {
		error(404, 'Ukendt scenarie');
	}
	const scenario = readScenario(params.scenario);
	const definition = scenario.definition;
	if (!definition || !scaleSteps(definition.maxScale).includes(scale)) error(404, 'Ukendt scenarie');
	const card = buildCard({
		shock, scenario, definition, yearStart: meta.yearStart, modelName: meta.model.name,
		levels: levelsAt(readBaseline(), definition.firstYear), scale
	});
	return {
		card: {
			title: card.title,
			description: card.description,
			imageAlt: card.imageAlt,
			image: card.image,
			url: `${SITE_URL}${card.path}`,
			initial: { name: view.name, variation: view.variation, scale },
			tiles: card.tiles
		}
	};
};
