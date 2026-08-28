/** Sharing helpers for the scenario page: permalinks, provenance stamps, CSV and PNG export.
 *  The pure functions are unit-tested; the DOM/canvas ones are verified in the browser. */

export const SITE_HOST = 'makroskop.nodalit.com';

export interface PermalinkParams {
	stod: string;
	variant: string;
	skala: number;
}

/** Deep link to a scenario view; the scale is omitted when the view is the solved size. */
export function permalink(origin: string, p: PermalinkParams): string {
	const url = new URL('/scenarier/', origin);
	url.searchParams.set('stod', p.stod);
	url.searchParams.set('variant', p.variant);
	if (p.skala !== 1) url.searchParams.set('skala', String(p.skala));
	return url.toString();
}

export interface Provenance {
	model: string;
	commit: string;
	closure: string;
	date: string;
}

/** One-line source stamp that travels with every export and screenshot. */
export function provenanceLine(p: Provenance): string {
	const model = p.commit ? `${p.model} (${p.commit})` : p.model;
	return ['MAKROskop', SITE_HOST, model, p.closure.toLowerCase(), p.date].join(' · ');
}

export interface CsvColumn {
	key: string;
	label: string;
	unit: string;
	values: (number | null)[];
}

function csvNumber(v: number | null): string {
	if (v == null) return '';
	return Number(v.toFixed(4)).toString().replace('.', ',');
}

/** Danish-locale CSV (semicolons, decimal commas) with `#` provenance lines on top. */
export function scenarioCsv(opts: { years: number[]; columns: CsvColumn[]; provenance: string[] }): string {
	const lines = opts.provenance.map((line) => `# ${line}`);
	lines.push(['År', ...opts.columns.map((c) => `${c.label} (${c.unit})`)].join(';'));
	// Skip the empty pre-shock years: deviations start with the shock, history has none.
	const first = opts.years.findIndex((_, i) => opts.columns.some((c) => c.values[i] != null));
	opts.years.forEach((year, i) => {
		if (first < 0 || i < first) return;
		lines.push([String(year), ...opts.columns.map((c) => csvNumber(c.values[i]))].join(';'));
	});
	return lines.join('\n') + '\n';
}

/** Greedy word wrap against a text measurer (canvas measureText in practice). */
export function wrapLines(measure: (text: string) => number, text: string, maxWidth: number): string[] {
	const lines: string[] = [];
	let current = '';
	for (const word of text.split(' ')) {
		const candidate = current ? `${current} ${word}` : word;
		if (current && measure(candidate) > maxWidth) {
			lines.push(current);
			current = word;
		} else {
			current = candidate;
		}
	}
	if (current) lines.push(current);
	return lines;
}

export function exportFilename(p: { stod: string; variant: string; key: string | null; skala: number; ext: string }): string {
	const parts = [`makroskop_${p.stod}${p.variant}`];
	if (p.key) parts.push(p.key);
	if (p.skala !== 1) parts.push(`x${p.skala}`);
	return `${parts.join('_').replace(/[^A-Za-z0-9_.-]+/g, '-')}.${p.ext}`;
}

// ---------------------------------------------------------------------------------------
// Browser-only: PNG rasterisation of an inline SVG chart with a header and a source footer.

export interface PngOptions {
	/** Device-pixel multiplier; 2 gives crisp images in articles. */
	scale?: number;
	/** First line is the title (bold), the rest are subtitle lines. */
	header: string[];
	/** Small muted lines under the chart: the provenance stamp and the permalink. */
	footer: string[];
	colors: { background: string; ink: string; muted: string };
	fonts: { display: string; body: string };
}

const MIN_EXPORT_WIDTH = 720;
const TEXT_PROPS = ['fill', 'font-family', 'font-size', 'font-weight'] as const;
const SHAPE_PROPS = ['fill', 'stroke', 'stroke-width', 'opacity'] as const;

/** The chart is styled through CSS variables and component classes, which a serialized
 *  SVG loses; copy the computed values onto the clone as plain attributes. When the export
 *  is drawn larger than the card (`upscale` > 1), text and strokes are shrunk by the same
 *  factor so the enlarged chart keeps the proportions of the on-screen one. */
function inlineStyles(source: SVGSVGElement, clone: SVGSVGElement, upscale = 1): void {
	const originals = [source, ...Array.from(source.querySelectorAll('*'))];
	const copies = [clone, ...Array.from(clone.querySelectorAll('*'))];
	const shrink = (value: string) => `${parseFloat(value) / upscale}px`;
	originals.forEach((orig, i) => {
		const copy = copies[i];
		const style = getComputedStyle(orig);
		const props = orig.tagName === 'text' ? TEXT_PROPS : SHAPE_PROPS;
		for (const prop of props) {
			let value = style.getPropertyValue(prop);
			if (!value) continue;
			if (upscale > 1 && (prop === 'font-size' || prop === 'stroke-width')) value = shrink(value);
			copy.setAttribute(prop, value);
		}
		if (upscale > 1 && orig.tagName === 'circle') copy.setAttribute('r', String(parseFloat(copy.getAttribute('r') ?? '4') / upscale));
	});
}

function loadImage(url: string): Promise<HTMLImageElement> {
	return new Promise((resolve, reject) => {
		const image = new Image();
		image.onload = () => resolve(image);
		image.onerror = () => reject(new Error('SVG could not be rasterised'));
		image.src = url;
	});
}

export async function svgToPngBlob(svg: SVGSVGElement, opts: PngOptions): Promise<Blob> {
	const scale = opts.scale ?? 2;
	const svgWidth = svg.width.baseVal.value || svg.clientWidth;
	const svgHeight = svg.height.baseVal.value || svg.clientHeight;
	// Article-sized regardless of how narrow the card was: SVG scales losslessly.
	const width = Math.max(svgWidth, MIN_EXPORT_WIDTH);
	const height = Math.round((svgHeight * width) / svgWidth);
	const clone = svg.cloneNode(true) as SVGSVGElement;
	inlineStyles(svg, clone, width / svgWidth);
	clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
	clone.setAttribute('width', String(svgWidth));
	clone.setAttribute('height', String(svgHeight));
	clone.setAttribute('viewBox', `0 0 ${svgWidth} ${svgHeight}`);
	const markup = new XMLSerializer().serializeToString(clone);
	const url = URL.createObjectURL(new Blob([markup], { type: 'image/svg+xml;charset=utf-8' }));

	const pad = 18;
	const titleSize = 16;
	const subSize = 12.5;
	const footSize = 10.5;
	const textWidth = width - 2 * pad;

	// Measure with a scratch context so the layout is known before the canvas is sized.
	const scratch = document.createElement('canvas').getContext('2d');
	if (!scratch) throw new Error('canvas unavailable');
	const wrapWith = (font: string, text: string) => {
		scratch.font = font;
		return wrapLines((t) => scratch.measureText(t).width, text, textWidth);
	};
	const titleFont = `600 ${titleSize}px ${opts.fonts.display}`;
	const subFont = `400 ${subSize}px ${opts.fonts.body}`;
	const footFont = `400 ${footSize}px ${opts.fonts.body}`;
	const titleLines = wrapWith(titleFont, opts.header[0] ?? '');
	const subLines = opts.header.slice(1).flatMap((line) => wrapWith(subFont, line));
	const footLines = opts.footer.flatMap((line) => wrapWith(footFont, line));
	const headerHeight = pad + titleLines.length * (titleSize + 4) + subLines.length * (subSize + 5) + 10;
	const footerHeight = 6 + footLines.length * (footSize + 4) + pad;

	const canvas = document.createElement('canvas');
	canvas.width = Math.round(width * scale);
	canvas.height = Math.round((headerHeight + height + footerHeight) * scale);
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('canvas unavailable');
	ctx.scale(scale, scale);
	ctx.fillStyle = opts.colors.background;
	ctx.fillRect(0, 0, width, headerHeight + height + footerHeight);

	let y = pad;
	ctx.fillStyle = opts.colors.ink;
	ctx.font = titleFont;
	for (const line of titleLines) {
		y += titleSize;
		ctx.fillText(line, pad, y);
		y += 4;
	}
	ctx.font = subFont;
	ctx.fillStyle = opts.colors.muted;
	for (const line of subLines) {
		y += subSize;
		ctx.fillText(line, pad, y);
		y += 5;
	}

	try {
		const image = await loadImage(url);
		ctx.drawImage(image, 0, headerHeight, width, height);
	} finally {
		URL.revokeObjectURL(url);
	}

	y = headerHeight + height + 6 + footSize;
	ctx.font = footFont;
	ctx.fillStyle = opts.colors.muted;
	for (const line of footLines) {
		ctx.fillText(line, pad, y);
		y += footSize + 4;
	}

	return new Promise((resolve, reject) =>
		canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('PNG encoding failed'))), 'image/png')
	);
}

export function downloadBlob(blob: Blob, filename: string): void {
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = filename;
	document.body.appendChild(anchor);
	anchor.click();
	anchor.remove();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}
