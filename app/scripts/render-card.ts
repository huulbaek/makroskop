/** SVG → PNG for the share cards, with the vendored fonts and nothing from the system, so
 *  the image is identical on a laptop and in the Docker build. */
import { Resvg } from '@resvg/resvg-js';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const FONT_NAMES = [
	'Newsreader-normal-500.ttf', 'Newsreader-normal-600.ttf', 'Newsreader-italic-500.ttf',
	'IBMPlexSans-normal-400.ttf', 'IBMPlexSans-normal-500.ttf', 'IBMPlexMono-normal-400.ttf'
];
export const FONT_FILES = FONT_NAMES.map((name) => fileURLToPath(new URL(`../fonts/${name}`, import.meta.url)));

export function assertFonts(): void {
	const missing = FONT_FILES.filter((file) => !existsSync(file));
	if (missing.length) throw new Error(`missing font files (run: bun fonts/fetch.ts):\n${missing.join('\n')}`);
}

export function renderPng(svg: string): Uint8Array {
	const resvg = new Resvg(svg, {
		fitTo: { mode: 'width', value: 1200 },
		font: { fontFiles: FONT_FILES, loadSystemFonts: false, defaultFontFamily: 'IBM Plex Sans' }
	});
	return resvg.render().asPng();
}

/** Width and height from the IHDR chunk. */
export function pngSize(png: Uint8Array): { width: number; height: number } {
	const view = new DataView(png.buffer, png.byteOffset, png.byteLength);
	return { width: view.getUint32(16), height: view.getUint32(20) };
}
