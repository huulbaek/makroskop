<script lang="ts">
	import LineChart from '$lib/components/LineChart.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import { formatValue, formatSigned } from '$lib/format';

	let { data } = $props();

	const meta = $derived(data.meta);
	const baseline = $derived(data.baseline);

	const rangePresets = [
		{ label: '1990–2030', from: 1990, to: 2030 },
		{ label: '1985–2060', from: 1985, to: 2060 },
		{ label: 'Hele forløbet', from: 1985, to: 2100 }
	];
	let range = $state({ from: 1990, to: 2030 });

	const groups = ['Nationalregnskab', 'Arbejdsmarked', 'Priser og løn', 'Offentlige finanser', 'Renter', 'Brancher'];
	let activeGroup = $state('Nationalregnskab');

	/** Not browsed here (DREAM's review, Sep 2026): nominal GDP gives way to real GDP under
	 *  Nationalregnskab, and the price/wage index levels to their growth rates under Priser og løn.
	 *  The level series stay in the catalog for the scenario pages. */
	const hiddenInGrid = new Set(['vBNP', 'pC', 'pBVT', 'pBolig', 'vhW']);
	const groupSeries = $derived(
		meta.series.filter((s) => s.group === activeGroup && s.key in baseline.series && !hiddenInGrid.has(s.key))
	);

	/** 4 columns for 8/12/16 charts, 3 for 6/9/18; otherwise whichever leaves fewer empty slots. */
	function columnsFor(count: number): number {
		if (count % 4 === 0) return 4;
		if (count % 3 === 0) return 3;
		const empty4 = (4 - (count % 4)) % 4;
		const empty3 = (3 - (count % 3)) % 3;
		return empty3 < empty4 ? 3 : 4;
	}
	const columns = $derived(columnsFor(groupSeries.length));

	function valueAt(key: string, year: number): number | null {
		const column = baseline.series[key];
		if (!column) return null;
		const index = baseline.years.indexOf(year);
		return index < 0 ? null : column[index];
	}

	function chartSeries(key: string, label: string) {
		return [{ key, label, values: baseline.series[key] ?? [] }];
	}

	const t = $derived(meta.lastDataYear);
	const bnp = $derived(valueAt('vBNP', t));
	const beskaeftigelse = $derived(valueAt('nL', t));
	const ledighed = $derived(valueAt('ledighedsgrad', t));
	const saldo = $derived(valueAt('saldo2bnp', t));
	const hbi = $derived(baseline.indicators.rHBI);

	function sectorLabel(s: { sector: string | null; labelDa: string }): string {
		if (!s.sector) return s.labelDa;
		const name = meta.sectors[s.sector] ?? s.sector;
		return s.labelDa.replace(`, ${s.sector}`, `, ${name.toLowerCase()}`);
	}
</script>

<svelte:head>
	<title>Grundforløb · MAKROskop</title>
</svelte:head>

<section class="opener">
	<h1>Dansk økonomi, beregnet et århundrede frem</h1>
	<p class="lede">
		MAKRO er modellen bag Finansministeriets regnestykker. Her ses dens stiliserede grundforløb:
		historiske data frem til {t}, modelfremskrivning derefter – helt til {meta.yearEnd}.
	</p>
</section>

<section class="figures" aria-label="Nøgletal">
	<StatTile label="BNP ({t})" value={bnp == null ? '–' : formatValue(bnp)} unit="mia. kr." />
	<StatTile
		label="Beskæftigelse ({t})"
		value={beskaeftigelse == null ? '–' : formatValue(beskaeftigelse / 1000)}
		unit="mio. personer"
	/>
	<StatTile label="Bruttoledighed ({t})" value={ledighed == null ? '–' : formatValue(ledighed)} unit="pct." />
	<StatTile
		label="Offentlig saldo ({t})"
		value={saldo == null ? '–' : formatSigned(saldo)}
		unit="pct. af BNP"
		tone={saldo != null && saldo >= 0 ? 'good' : 'bad'}
	/>
	<StatTile
		label="Holdbarhed (HBI)"
		value={hbi == null ? '–' : formatSigned(hbi * 100)}
		unit="pct. af BNP"
		tone={hbi != null && hbi >= 0 ? 'good' : 'bad'}
		tag={hbi == null ? '' : hbi >= 0 ? 'Overholdbar' : 'Uholdbar'}
	/>
</section>

<section class="century" aria-label="BNP over hele forløbet">
	<LineChart
		title="Bruttonationalprodukt, realt"
		code="qBNP"
		unit="mia. 2020-kr."
		years={baseline.years}
		series={chartSeries('qBNP', 'BNP, realt')}
		fromYear={1985}
		toYear={2100}
		lastDataYear={t}
		nowLabel
		height={320}
	/>
</section>

<section class="browser">
	<div class="filters" role="group" aria-label="Filtre">
		<div class="chip-row" role="group" aria-label="Emne">
			{#each groups as group (group)}
				<button
					class="chip"
					class:active={activeGroup === group}
					aria-pressed={activeGroup === group}
					onclick={() => (activeGroup = group)}
				>
					{group}
				</button>
			{/each}
		</div>
		<div class="chip-row" role="group" aria-label="Periode">
			{#each rangePresets as preset (preset.label)}
				<button
					class="chip"
					class:active={range.from === preset.from && range.to === preset.to}
					aria-pressed={range.from === preset.from && range.to === preset.to}
					onclick={() => (range = { from: preset.from, to: preset.to })}
				>
					{preset.label}
				</button>
			{/each}
		</div>
	</div>

	<div class="chart-grid" style:--cols={columns}>
		{#each groupSeries as s (s.key)}
			<div class="cell">
				<LineChart
					title={sectorLabel(s)}
					code={s.key}
					unit={s.unit}
					years={baseline.years}
					series={chartSeries(s.key, s.labelDa)}
					fromYear={range.from}
					toYear={range.to}
					lastDataYear={t}
					height={180}
				/>
			</div>
		{/each}
	</div>
</section>

<section class="method">
	<h2>Hvad kigger du på?</h2>
	<p>
		Grundforløbet er MAKROs indbyggede basisscenarie: en stiliseret fremskrivning af dansk økonomi, som
		politik-eksperimenter måles op imod. Værdier efter den lodrette linje ({t}) er modellens fremskrivning,
		ikke en prognose. Beløb er omregnet til løbende priser med modellens vækst- og inflationsfaktorer.
		Koden i <code>grøn</code> er variablens navn i modellens kildekode – samme navn som i
		<a href="https://github.com/DREAM-DK/MAKRO" rel="external">MAKRO-repositoriet</a> og dokumentationen.
	</p>
</section>

<style>
	/* Hero: title takes 3/5 of the width, the lede sits bottom-aligned in the remaining 2/5. */
	.opener {
		display: grid;
		grid-template-columns: 3fr 2fr;
		gap: 48px;
		align-items: end;
		padding: 24px 0 48px; /* main already adds 40px under the masthead → 64px in total */
	}

	.opener h1 {
		font-size: clamp(40px, 4.6vw, 64px);
		line-height: 1.05;
		letter-spacing: -0.02em;
	}

	.opener .lede {
		font-size: 18px;
		line-height: 1.55;
		max-width: 520px;
		margin: 0 0 8px;
	}

	/* KPI strip: five equal cells between two rules */
	.figures {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		border-top: 1px solid var(--rule-strong);
		border-bottom: 1px solid var(--rule-strong);
	}

	.figures > :global(.figure:first-child) {
		padding-left: 0;
	}

	.figures > :global(.figure:last-child) {
		border-right: 0;
		padding-right: 0;
	}

	/* Hero chart: header 12px above the plot (LineChart), table toggle 12px below */
	.century {
		padding: 40px 0 0;
	}

	.century :global(.table-view) {
		margin-top: 12px;
	}

	/* Filter bar */
	.filters {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 12px 24px;
		padding: 56px 0 24px;
		border-bottom: 1px solid var(--rule);
	}

	/* Chart sheet: column count chosen per tab so the last row is full */
	.chart-grid {
		grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
		column-gap: 40px;
		row-gap: 40px;
		padding-top: 32px;
	}

	.chart-grid > .cell {
		padding: 14px 0 0;
	}

	/* Explainer: heading left, text right, on the same two-column rhythm as the hero */
	.method {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 48px;
		max-width: none;
		margin-top: 64px;
		padding-top: 72px;
	}

	.method h2 {
		font-size: 28px;
		line-height: 1.2;
		margin: 0;
	}

	.method p {
		font-size: 16px;
		line-height: 1.6;
		margin: 0;
	}

	@media (max-width: 1100px) {
		.opener,
		.method {
			grid-template-columns: 1fr;
			gap: 20px;
		}
		.opener .lede {
			margin-bottom: 0;
		}
		.method {
			padding-top: 48px;
		}
		.figures {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
		.figures > :global(.figure) {
			border-right: 1px solid var(--rule);
			padding: 20px 24px;
		}
		.figures > :global(.figure:nth-child(3n)) {
			border-right: 0;
			padding-right: 0;
		}
		.figures > :global(.figure:nth-child(3n + 1)) {
			padding-left: 0;
		}
		.chart-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			column-gap: 32px;
		}
	}

	@media (max-width: 640px) {
		.figures {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.figures > :global(.figure) {
			border-right: 1px solid var(--rule);
			padding: 16px 16px;
		}
		.figures > :global(.figure:nth-child(3n)),
		.figures > :global(.figure:nth-child(3n + 1)) {
			border-right: 1px solid var(--rule);
			padding: 16px 16px;
		}
		.figures > :global(.figure:nth-child(2n)) {
			border-right: 0;
			padding-right: 0;
		}
		.figures > :global(.figure:nth-child(2n + 1)) {
			padding-left: 0;
		}
		.filters {
			padding-top: 40px;
		}
		.chart-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
