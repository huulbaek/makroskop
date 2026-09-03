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

	const groupSeries = $derived(
		meta.series.filter((s) => s.group === activeGroup && s.key in baseline.series && s.key !== 'qBNP')
	);

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

<section class="opener">
	<div class="opener-text">
		<h1>Dansk økonomi, beregnet et århundrede frem</h1>
		<p class="lede">
			MAKRO er modellen bag Finansministeriets regnestykker. Her ses dens stiliserede grundforløb:
			historiske data frem til {t}, modelfremskrivning derefter – helt til {meta.yearEnd}.
		</p>
		<p class="model-note">{meta.model.name}</p>
	</div>

	<div class="opener-chart">
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
			height={300}
		/>
	</div>
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
		note="Finanspolitikken er {hbi != null && hbi >= 0 ? 'overholdbar' : 'uholdbar'} i grundforløbet"
	/>
</section>

<section class="browser">
	<div class="filters" role="group" aria-label="Filtre">
		<div class="chip-row" role="group" aria-label="Emne">
			{#each groups as group (group)}
				<button class="chip" class:active={activeGroup === group} onclick={() => (activeGroup = group)}>
					{group}
				</button>
			{/each}
		</div>
		<div class="chip-row" role="group" aria-label="Periode">
			{#each rangePresets as preset (preset.label)}
				<button
					class="chip"
					class:active={range.from === preset.from && range.to === preset.to}
					onclick={() => (range = { from: preset.from, to: preset.to })}
				>
					{preset.label}
				</button>
			{/each}
		</div>
	</div>

	<div class="chart-grid">
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
					height={210}
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
	.opener {
		display: grid;
		grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
		gap: 48px;
		align-items: end;
	}

	.opener h1 {
		max-width: 16ch;
	}

	.model-note {
		font-family: var(--font-mono);
		font-size: 11.5px;
		color: var(--ink-muted);
		margin: 18px 0 0;
	}

	.opener-chart {
		min-width: 0;
	}

	.figures {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		margin-top: 36px;
		padding: 18px 0;
		border-top: 1px solid var(--rule-strong);
		border-bottom: 1px solid var(--rule);
	}

	.figures > :global(.figure:first-child) {
		border-left: 0;
		padding-left: 0;
	}

	.browser {
		margin-top: 40px;
	}

	.filters {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 10px 24px;
		margin-bottom: 20px;
	}

	@media (max-width: 900px) {
		.opener {
			grid-template-columns: 1fr;
			gap: 28px;
		}
		.figures {
			grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
			row-gap: 18px;
		}
	}

	@media (max-width: 600px) {
		.figures > :global(.figure) {
			border-left: 0;
			padding-left: 0;
			border-top: 1px solid var(--rule);
			padding-top: 10px;
		}
		.figures > :global(.figure:first-child) {
			border-top: 0;
			padding-top: 0;
		}
	}
</style>
