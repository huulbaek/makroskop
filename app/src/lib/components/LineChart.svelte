<script lang="ts">
	import { formatTick, formatValue, formatSigned, niceTicks } from '$lib/format';

	interface ChartSeries {
		key: string;
		label: string;
		values: (number | null)[];
		color?: string;
	}

	let {
		title,
		code = '',
		unit = '',
		years,
		series,
		fromYear,
		toYear,
		lastDataYear = 0,
		zeroLine = false,
		nowLabel = false,
		height = 240,
		suffix = ''
	}: {
		title: string;
		code?: string;
		unit?: string;
		years: number[];
		series: ChartSeries[];
		fromYear: number;
		toYear: number;
		lastDataYear?: number;
		zeroLine?: boolean;
		nowLabel?: boolean;
		height?: number;
		suffix?: string;
	} = $props();

	let width = $state(640);
	let hoverYear: number | null = $state(null);

	const margin = { top: 14, right: 18, bottom: 26, left: 52 };

	const visible = $derived.by(() => {
		const indices: number[] = [];
		for (let i = 0; i < years.length; i++) {
			if (years[i] < fromYear || years[i] > toYear) continue;
			if (series.some((s) => s.values[i] != null)) indices.push(i);
		}
		return indices;
	});

	const domain = $derived.by(() => {
		let min = Infinity;
		let max = -Infinity;
		for (const i of visible) {
			for (const s of series) {
				const v = s.values[i];
				if (v == null) continue;
				if (v < min) min = v;
				if (v > max) max = v;
			}
		}
		if (min === Infinity) return { min: 0, max: 1 };
		if (zeroLine) {
			min = Math.min(min, 0);
			max = Math.max(max, 0);
		}
		const pad = (max - min || Math.abs(max) || 1) * 0.06;
		return { min: min - pad, max: max + pad };
	});

	const ticks = $derived(niceTicks(domain.min, domain.max, 4));

	const plotW = $derived(Math.max(80, width - margin.left - margin.right));
	const plotH = $derived(height - margin.top - margin.bottom);

	function xPos(year: number): number {
		return margin.left + ((year - fromYear) / Math.max(1, toYear - fromYear)) * plotW;
	}

	function yPos(value: number): number {
		return margin.top + plotH - ((value - domain.min) / (domain.max - domain.min)) * plotH;
	}

	const yearTicks = $derived.by(() => {
		const span = toYear - fromYear;
		const step = span > 80 ? 20 : span > 40 ? 10 : span > 16 ? 5 : span > 8 ? 2 : 1;
		const result: number[] = [];
		for (let y = Math.ceil(fromYear / step) * step; y <= toYear; y += step) result.push(y);
		return result;
	});

	function linePath(s: ChartSeries): string {
		let d = '';
		let pen = false;
		for (const i of visible) {
			const v = s.values[i];
			if (v == null) {
				pen = false;
				continue;
			}
			d += `${pen ? 'L' : 'M'}${xPos(years[i]).toFixed(1)},${yPos(v).toFixed(1)}`;
			pen = true;
		}
		return d;
	}

	function areaPath(s: ChartSeries): string {
		const base = (zeroLine ? yPos(0) : margin.top + plotH).toFixed(1);
		const segments: { x: string; y: string }[][] = [];
		let current: { x: string; y: string }[] = [];
		for (const i of visible) {
			const v = s.values[i];
			if (v == null) {
				if (current.length > 0) segments.push(current);
				current = [];
				continue;
			}
			current.push({ x: xPos(years[i]).toFixed(1), y: yPos(v).toFixed(1) });
		}
		if (current.length > 0) segments.push(current);
		return segments
			.map((points) => {
				const line = points.map((p) => `L${p.x},${p.y}`).join('');
				return `M${points[0].x},${base}${line}L${points[points.length - 1].x},${base}Z`;
			})
			.join('');
	}

	const seriesColor = (s: ChartSeries, index: number) =>
		s.color ?? (index === 0 ? 'var(--series-1)' : 'var(--series-2)');

	const nuVisible = $derived(lastDataYear >= fromYear && lastDataYear <= toYear);

	function nearestYear(clientX: number, target: SVGRectElement): number | null {
		const rect = target.getBoundingClientRect();
		const frac = (clientX - rect.left) / rect.width;
		const raw = fromYear + frac * (toYear - fromYear);
		let best: number | null = null;
		let bestDist = Infinity;
		for (const i of visible) {
			const dist = Math.abs(years[i] - raw);
			if (dist < bestDist) {
				bestDist = dist;
				best = years[i];
			}
		}
		return best;
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight' && event.key !== 'Escape') return;
		event.preventDefault();
		if (event.key === 'Escape') {
			hoverYear = null;
			return;
		}
		const yearsVisible = visible.map((i) => years[i]);
		if (yearsVisible.length === 0) return;
		const current = hoverYear ?? yearsVisible[yearsVisible.length - 1];
		const pos = yearsVisible.indexOf(current);
		const next = event.key === 'ArrowRight' ? Math.min(yearsVisible.length - 1, pos + 1) : Math.max(0, pos - 1);
		hoverYear = yearsVisible[next];
	}

	const hoverIndex = $derived(hoverYear == null ? -1 : years.indexOf(hoverYear));

	const tooltipRows = $derived.by(() => {
		if (hoverIndex < 0) return [];
		return series
			.map((s, i) => ({ label: s.label, color: seriesColor(s, i), value: s.values[hoverIndex] }))
			.filter((r) => r.value != null) as { label: string; color: string; value: number }[];
	});

	const tooltipLeft = $derived.by(() => {
		if (hoverYear == null) return 0;
		const x = xPos(hoverYear);
		return Math.min(Math.max(x - 80, 4), Math.max(4, width - 170));
	});

	const tableStride = $derived(Math.max(1, Math.ceil(visible.length / 25)));

	function fmt(v: number): string {
		return (zeroLine ? formatSigned(v) : formatValue(v)) + suffix;
	}
</script>

<figure class="chart" bind:clientWidth={width}>
	<figcaption>
		<span class="title">{title}</span>
		{#if code}<span class="code">{code}</span>{/if}
		{#if unit}<span class="unit">{unit}</span>{/if}
	</figcaption>

	{#if series.length > 1}
		<div class="legend">
			{#each series as s, i (s.key)}
				<span class="legend-item"><span class="key" style:background={seriesColor(s, i)}></span>{s.label}</span>
			{/each}
		</div>
	{/if}

	{#if visible.length === 0}
		<div class="empty" style:height="{height}px">Ingen data i det valgte interval.</div>
	{:else}
		<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
		<!-- Focusable on purpose: arrow keys move the readout; values are also in the table view below. -->
		<div
			class="plot"
			role="application"
			aria-label="{title}. Linjediagram {fromYear} til {toYear}. Brug piletaster for at aflæse værdier."
			tabindex="0"
			onkeydown={onKeydown}
		>
			<svg {width} {height} aria-hidden="true">
				<!-- projection region -->
				{#if nuVisible}
					<rect
						x={xPos(lastDataYear)}
						y={margin.top}
						width={margin.left + plotW - xPos(lastDataYear)}
						height={plotH}
						fill="var(--projection-wash)"
					/>
				{/if}

				<!-- gridlines + y ticks -->
				{#each ticks as t (t)}
					<line
						x1={margin.left}
						x2={margin.left + plotW}
						y1={yPos(t)}
						y2={yPos(t)}
						stroke={zeroLine && t === 0 ? 'var(--axis)' : 'var(--grid)'}
						stroke-width="1"
					/>
					<text class="tick" x={margin.left - 8} y={yPos(t) + 3.5} text-anchor="end">{formatTick(t)}</text>
				{/each}

				<!-- x ticks -->
				{#each yearTicks as y (y)}
					<text class="tick" x={xPos(y)} y={margin.top + plotH + 16} text-anchor="middle">{y}</text>
				{/each}

				<!-- nu-linje: history ends, projection begins -->
				{#if nuVisible}
					<line
						x1={xPos(lastDataYear)}
						x2={xPos(lastDataYear)}
						y1={margin.top - 4}
						y2={margin.top + plotH}
						stroke="var(--axis)"
						stroke-width="1"
					/>
					{#if nowLabel}
						<text class="nu-label" x={xPos(lastDataYear) + 6} y={margin.top + 6}>fremskrivning →</text>
					{/if}
				{/if}

				<!-- area wash (single series only) -->
				{#if series.length === 1}
					<path d={areaPath(series[0])} fill={seriesColor(series[0], 0)} opacity="0.09" />
				{/if}

				<!-- lines -->
				{#each series as s, i (s.key)}
					<path d={linePath(s)} fill="none" stroke={seriesColor(s, i)} stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
				{/each}

				<!-- crosshair + markers -->
				{#if hoverYear != null && hoverIndex >= 0}
					<line x1={xPos(hoverYear)} x2={xPos(hoverYear)} y1={margin.top} y2={margin.top + plotH} stroke="var(--ink-muted)" stroke-width="1" />
					{#each series as s, i (s.key)}
						{#if s.values[hoverIndex] != null}
							<circle
								cx={xPos(hoverYear)}
								cy={yPos(s.values[hoverIndex] as number)}
								r="4.5"
								fill={seriesColor(s, i)}
								stroke="var(--surface)"
								stroke-width="2"
							/>
						{/if}
					{/each}
				{/if}

				<!-- hover capture: pointer-only layer; keyboard readout lives on the wrapper -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<rect
					x={margin.left}
					y={margin.top}
					width={plotW}
					height={plotH}
					fill="transparent"
					onpointermove={(e) => (hoverYear = nearestYear(e.clientX, e.currentTarget))}
					onpointerleave={() => (hoverYear = null)}
				/>
			</svg>

			{#if hoverYear != null && tooltipRows.length > 0}
				<div class="tooltip" style:left="{tooltipLeft}px">
					<div class="tooltip-year">{hoverYear}{#if lastDataYear && hoverYear > lastDataYear}<span class="proj">fremskrivning</span>{/if}</div>
					{#each tooltipRows as row (row.label)}
						<div class="tooltip-row">
							<span class="key" style:background={row.color}></span>
							<span class="tooltip-value">{fmt(row.value)}</span>
							<span class="tooltip-label">{row.label}</span>
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<details class="table-view">
			<summary>Vis som tabel</summary>
			<table>
				<thead>
					<tr>
						<th>År</th>
						{#each series as s (s.key)}<th>{s.label}</th>{/each}
					</tr>
				</thead>
				<tbody>
					{#each visible.filter((_, n) => n % tableStride === 0) as i (i)}
						<tr>
							<td>{years[i]}</td>
							{#each series as s (s.key)}
								<td>{s.values[i] == null ? '–' : fmt(s.values[i] as number)}</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</details>
	{/if}
</figure>

<style>
	.chart {
		margin: 0;
		min-width: 0;
	}

	figcaption {
		display: flex;
		align-items: baseline;
		gap: 8px;
		flex-wrap: wrap;
		margin-bottom: 2px;
	}

	.title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 14px;
		color: var(--ink);
	}

	.code {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 1px 5px;
		border-radius: 3px;
	}

	.unit {
		font-size: 12px;
		color: var(--ink-muted);
	}

	.legend {
		display: flex;
		gap: 14px;
		font-size: 12px;
		color: var(--ink-secondary);
		margin: 2px 0 0;
	}

	.legend-item {
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.key {
		display: inline-block;
		width: 14px;
		height: 3px;
		border-radius: 2px;
	}

	.plot {
		position: relative;
	}

	.plot:focus-visible {
		outline: 2px solid var(--makro);
		outline-offset: 2px;
		border-radius: 4px;
	}

	svg {
		display: block;
	}

	svg text.tick {
		font-family: var(--font-body);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
		fill: var(--ink-muted);
	}

	svg text.nu-label {
		font-size: 10px;
		fill: var(--ink-muted);
		font-family: var(--font-body);
	}

	.tooltip {
		position: absolute;
		top: 8px;
		pointer-events: none;
		background: var(--surface-raised);
		border: 1px solid var(--border);
		border-radius: 6px;
		padding: 7px 10px;
		box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
		min-width: 150px;
		z-index: 2;
	}

	.tooltip-year {
		font-size: 11px;
		font-weight: 600;
		color: var(--ink-secondary);
		margin-bottom: 3px;
		display: flex;
		gap: 6px;
		align-items: baseline;
	}

	.tooltip-year .proj {
		font-weight: 400;
		color: var(--ink-muted);
		font-size: 10px;
	}

	.tooltip-row {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		padding: 1px 0;
	}

	.tooltip-value {
		font-weight: 600;
		color: var(--ink);
		font-variant-numeric: tabular-nums;
	}

	.tooltip-label {
		color: var(--ink-secondary);
		font-size: 11px;
	}

	.empty {
		display: grid;
		place-items: center;
		color: var(--ink-muted);
		font-size: 13px;
		background: var(--projection-wash);
		border-radius: 6px;
	}

	.table-view {
		margin-top: 4px;
	}

	.table-view summary {
		font-size: 11px;
		color: var(--ink-muted);
		cursor: pointer;
		user-select: none;
	}

	.table-view table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
		margin-top: 6px;
	}

	.table-view th,
	.table-view td {
		text-align: right;
		padding: 3px 8px;
		border-bottom: 1px solid var(--grid);
		font-variant-numeric: tabular-nums;
	}

	.table-view th:first-child,
	.table-view td:first-child {
		text-align: left;
	}

	.table-view th {
		color: var(--ink-secondary);
		font-weight: 500;
	}
</style>
