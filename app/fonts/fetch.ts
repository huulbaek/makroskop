/** Vendors static TTF instances of the site's fonts for the build-time card renderer.
 *  Google Fonts serves modern browsers variable fonts, which resvg cannot instance (it
 *  ignores variation axes), but hands a `curl` User-Agent format('truetype') static
 *  instances at the requested weights. Run `bun fonts/fetch.ts` and commit the result.
 *  Licences: SIL Open Font License 1.1 for all three families, per family (fonts/OFL-*.txt). */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const CSS =
	'https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;1,500' +
	'&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400';
const NOTICES: Record<string, string> = {
	'OFL-Newsreader.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/newsreader/OFL.txt',
	'OFL-IBMPlexSans.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexsans/OFL.txt',
	'OFL-IBMPlexMono.txt': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ibmplexmono/OFL.txt'
};
const dir = fileURLToPath(new URL('./', import.meta.url));

async function get(url: string): Promise<Response> {
	const response = await fetch(url, { headers: { 'User-Agent': 'curl/8.0' } });
	if (!response.ok) throw new Error(`${response.status} ${response.statusText} for ${url}`);
	return response;
}

const css = await (await get(CSS)).text();
const faces = [...css.matchAll(/@font-face\s*{([^}]*)}/g)].map((m) => m[1]);
if (faces.length !== 6) throw new Error(`expected 6 @font-face blocks, got ${faces.length}`);
await Promise.all([
	...faces.map(async (face) => {
		const family = /font-family:\s*'([^']+)'/.exec(face)?.[1];
		const style = /font-style:\s*(\w+)/.exec(face)?.[1];
		const weight = /font-weight:\s*(\d+)/.exec(face)?.[1];
		const url = /url\((https:[^)]+\.ttf)\)/.exec(face)?.[1];
		if (!family || !style || !weight || !url) throw new Error(`unexpected @font-face block:\n${face}`);
		const name = `${family.replace(/\s+/g, '')}-${style}-${weight}.ttf`;
		writeFileSync(`${dir}${name}`, new Uint8Array(await (await get(url)).arrayBuffer()));
		console.log(`${name} <- ${url}`);
	}),
	...Object.entries(NOTICES).map(async ([name, url]) => {
		writeFileSync(`${dir}${name}`, await (await get(url)).text());
		console.log(`${name} <- ${url}`);
	})
]);
