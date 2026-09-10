/** Vendors static TTF instances of the site's fonts for the build-time card renderer.
 *  Google Fonts serves modern browsers variable fonts, which resvg cannot instance (it
 *  ignores variation axes), but hands a `curl` User-Agent format('truetype') static
 *  instances at the requested weights. Run `bun fonts/fetch.ts` and commit the result.
 *  Licences: SIL Open Font License 1.1 for all three families (fonts/OFL.txt). */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const CSS =
	'https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;1,500' +
	'&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400';
const OFL = 'https://openfontlicense.org/documents/OFL.txt';
const dir = fileURLToPath(new URL('./', import.meta.url));

const css = await (await fetch(CSS, { headers: { 'User-Agent': 'curl/8.0' } })).text();
const faces = [...css.matchAll(/@font-face\s*{([^}]*)}/g)].map((m) => m[1]);
let count = 0;
for (const face of faces) {
	const family = /font-family:\s*'([^']+)'/.exec(face)?.[1];
	const style = /font-style:\s*(\w+)/.exec(face)?.[1];
	const weight = /font-weight:\s*(\d+)/.exec(face)?.[1];
	const url = /url\((https:[^)]+\.ttf)\)/.exec(face)?.[1];
	if (!family || !style || !weight || !url) throw new Error(`unexpected @font-face block:\n${face}`);
	const name = `${family.replace(/\s+/g, '')}-${style}-${weight}.ttf`;
	writeFileSync(`${dir}${name}`, new Uint8Array(await (await fetch(url)).arrayBuffer()));
	console.log(`${name} <- ${url}`);
	count++;
}
writeFileSync(`${dir}OFL.txt`, await (await fetch(OFL)).text());
if (count !== 6) throw new Error(`expected 6 font files, got ${count}`);
