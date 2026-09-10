/** Post-build assertions for the share pages: every view has a page and an image, the
 *  sample page carries exactly one of each tag, the bare page keeps the generic ones.
 *  Run after `bun run build` (package.json "verify:build"); exits 1 on any failure. */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { shareViews } from '../src/lib/card';
import { maxScales, readMeta } from '../src/lib/server/scenarios';

const build = join(process.cwd(), 'build');
const failures: string[] = [];
const check = (ok: boolean, message: string) => { if (!ok) failures.push(message); };
const count = (html: string, pattern: RegExp) => (html.match(pattern) ?? []).length;

const meta = readMeta();
const views = shareViews(meta, maxScales(meta));
for (const view of views) {
	const dir = join(build, 'scenarier', view.scenario, view.skala ?? '');
	check(existsSync(join(dir, 'index.html')), `missing page ${dir}/index.html`);
	const image = `${view.scenario}${view.skala ? `_${view.skala}` : ''}.png`;
	check(existsSync(join(build, 'og', image)), `missing image build/og/${image}`);
}

const sample = readFileSync(join(build, 'scenarier', 'Rente_ufin', '0.5', 'index.html'), 'utf8');
check(count(sample, /<title>/g) === 1, 'sample: not exactly one <title>');
check(sample.includes('<title>ECB-renten +0,5 pct.-point: BNP −0,6 pct. efter 3 år · MAKROskop</title>'), 'sample: <title> is not the card title');
for (const tag of ['og:title', 'og:description', 'og:image', 'og:image:alt', 'og:url']) {
	check(count(sample, new RegExp(`property="${tag}"`, 'g')) === 1, `sample: not exactly one ${tag}`);
}
check(sample.includes('content="https://makroskop.nodalit.com/og/Rente_ufin_0.5.png"'), 'sample: og:image is not the view image');
check(sample.includes('<link rel="canonical" href="https://makroskop.nodalit.com/scenarier/Rente_ufin/0.5/"'), 'sample: canonical missing');
check(sample.includes('vist som år efter stødet, lineært skaleret'), 'sample: honesty line missing from description');
check(sample.includes('key-figures'), 'sample: prerendered HTML is missing the key-figures tiles');
check(!sample.includes('Endnu ikke beregnet'), 'sample: prerendered HTML still shows the pending-scenario card');
check(!sample.includes('<h2>Syntetisk demo-scenarie</h2>'), 'sample: prerendered HTML still shows the demo scenario');

const bare = readFileSync(join(build, 'scenarier', 'index.html'), 'utf8');
check(bare.includes('content="Scenarier · MAKROskop"'), 'bare page lost its generic og:title');
check(bare.includes('<title>Scenarier · MAKROskop</title>'), 'bare page: <title> is not the page name');
check(bare.includes('content="https://makroskop.nodalit.com/og.png"'), 'bare page lost the site og:image');
check(count(bare, /property="og:url"/g) === 0, 'bare page must not carry og:url');

if (failures.length) {
	console.error(`verify-build: ${failures.length} problem(s)\n` + failures.slice(0, 20).join('\n'));
	process.exit(1);
}
console.log(`verify-build: ${views.length} views, pages and images present, tags correct`);
