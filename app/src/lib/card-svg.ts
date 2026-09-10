/** The share card as an SVG string: wordmark, kicker, headline, sparkline, three tiles,
 *  footer. Light palette only — a static image cannot follow the viewer's theme — with the
 *  light-theme tokens of src/app.css (:root). Rasterised by scripts/render-card.ts. */
import type { CardData } from './card';
import { wrapLines } from './text';

/** src/app.css :root light tokens: --page, --ink, --ink-secondary, --ink-muted, --rule, --axis, --series-1, --makro */
export const LIGHT = {
	page: '#fbfbf8',
	ink: '#171d1c',
	secondary: '#4e5957',
	muted: '#67746f',
	rule: 'rgba(23, 29, 28, 0.16)',
	axis: '#848e8a',
	series: '#2a78d6',
	makro: '#0f9a92'
};

export const FONT_FAMILIES = { display: 'Newsreader', body: 'IBM Plex Sans', mono: 'IBM Plex Mono' };

const W = 1200;
const H = 630;
const M = 72;
const HEADLINE_WIDTH = 690; // leaves room for the sparkline on the right
const HEADLINE_SIZES = [72, 62, 54];
const DISPLAY_EM = 0.46; // average advance of Newsreader SemiBold, em per character

export function escapeXml(text: string): string {
	return text
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

/** Largest size at which the headline fits two lines; three lines at the smallest size otherwise. */
export function fitHeadline(text: string): { size: number; lines: string[] } {
	for (const size of HEADLINE_SIZES) {
		const lines = wrapLines((t) => t.length * DISPLAY_EM * size, text, HEADLINE_WIDTH);
		if (lines.length <= 2) return { size, lines };
	}
	const size = HEADLINE_SIZES[HEADLINE_SIZES.length - 1];
	return { size, lines: wrapLines((t) => t.length * DISPLAY_EM * size, text, HEADLINE_WIDTH).slice(0, 3) };
}

/** Polyline through the non-null values, y scaled to the box with zero inside it. */
export function sparklinePath(
	values: (number | null)[], box: { x: number; y: number; w: number; h: number }
): { line: string; zeroY: number } {
	const present = values.filter((v): v is number => v != null);
	const lo = Math.min(0, ...present);
	const hi = Math.max(0, ...present);
	const span = hi - lo || 1;
	const y = (v: number) => box.y + box.h - ((v - lo) / span) * box.h;
	const step = values.length > 1 ? box.w / (values.length - 1) : 0;
	let line = '';
	values.forEach((v, i) => {
		if (v == null) return;
		line += `${line ? 'L' : 'M'}${(box.x + i * step).toFixed(1)} ${y(v).toFixed(1)}`;
	});
	return { line, zeroY: y(0) };
}

function text(x: number, y: number, content: string, attrs: string): string {
	return `<text x="${x}" y="${y}" ${attrs}>${escapeXml(content)}</text>`;
}

export function cardSvg(card: CardData): string {
	const { display, body, mono } = FONT_FAMILIES;
	const parts: string[] = [];
	parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`);
	parts.push(`<rect width="${W}" height="${H}" fill="${LIGHT.page}"/>`);

	// wordmark and kicker
	parts.push(`<text x="${M}" y="96" font-family="${display}" font-size="40" font-weight="500" fill="${LIGHT.ink}">MAKRO<tspan font-style="italic" fill="${LIGHT.makro}">skop</tspan></text>`);
	parts.push(text(W - M, 94, card.kicker, `text-anchor="end" font-family="${body}" font-size="20" font-weight="500" fill="${LIGHT.muted}"`));

	// headline + subline
	const { size, lines } = fitHeadline(card.headline);
	const lineHeight = size * 1.08;
	let y = 150 + size;
	for (const line of lines) {
		parts.push(text(M, Math.round(y), line, `font-family="${display}" font-size="${size}" font-weight="600" fill="${LIGHT.ink}"`));
		y += lineHeight;
	}
	const lastHeadlineBaseline = y - lineHeight;
	parts.push(text(M, Math.round(lastHeadlineBaseline + 40), card.subline, `font-family="${body}" font-size="26" fill="${LIGHT.muted}"`));

	// sparkline: qBNP years 0..15 after the shock, texture at the right
	const box = { x: 828, y: 168, w: 300, h: 110 };
	const { line, zeroY } = sparklinePath(card.sparkline, box);
	parts.push(`<line x1="${box.x}" y1="${zeroY.toFixed(1)}" x2="${box.x + box.w}" y2="${zeroY.toFixed(1)}" stroke="${LIGHT.axis}" stroke-width="1"/>`);
	if (line) parts.push(`<path d="${line}" fill="none" stroke="${LIGHT.series}" stroke-width="3" stroke-opacity="0.6" stroke-linejoin="round" stroke-linecap="round"/>`);
	parts.push(text(box.x, box.y + box.h + 28, 'BNP, år 0–15 efter stødet', `font-family="${body}" font-size="18" fill="${LIGHT.muted}"`));

	// three tiles
	const column = (W - 2 * M) / 3;
	card.tiles.forEach((tile, i) => {
		const x = M + i * column;
		parts.push(text(x, 420, `${tile.label}, år ${tile.year}`, `font-family="${body}" font-size="22" font-weight="500" fill="${LIGHT.muted}"`));
		if (tile.value == null) {
			parts.push(text(x, 510, '–', `font-family="${display}" font-size="84" font-weight="500" fill="${LIGHT.muted}"`));
		} else {
			parts.push(text(x, 510, tile.value, `font-family="${display}" font-size="84" font-weight="500" fill="${LIGHT.ink}"`));
			parts.push(text(x, 550, tile.unit, `font-family="${body}" font-size="24" fill="${LIGHT.muted}"`));
		}
	});

	// footer
	parts.push(`<line x1="${M}" y1="584" x2="${W - M}" y2="584" stroke="${LIGHT.rule}" stroke-width="1"/>`);
	parts.push(text(M, 614, `${card.model} · MAKROskops frie løser`, `font-family="${body}" font-size="20" fill="${LIGHT.muted}"`));
	parts.push(text(W - M, 614, 'makroskop.nodalit.com', `text-anchor="end" font-family="${mono}" font-size="20" fill="${LIGHT.muted}"`));
	parts.push('</svg>');
	return parts.join('\n');
}
