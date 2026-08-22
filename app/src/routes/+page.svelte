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

<section class="hero">
	<div class="hero-text">
		<p class="eyebrow">Grundforløbet · {meta.model.name}</p>
		<h1>Dansk økonomi, beregnet et århundrede frem</h1>
		<p class="lede">
			MAKRO er modellen bag Finansministeriets regnestykker. Her ses dens stiliserede grundforløb:
			historiske data frem til {t}, modelfremskrivning derefter – helt til {meta.yearEnd}.
		</p>
	</div>

	<div class="tiles">
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
	</div>

	<div class="card hero-chart">
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

<section class="browser">
	<div class="filters" role="group" aria-label="Filtre">
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
		<div class="chip-row" role="group" aria-label="Emne">
			{#each groups as group (group)}
				<button class="chip" class:active={activeGroup === group} onclick={() => (activeGroup = group)}>
					{group}
				</button>
			{/each}
		</div>
	</div>

	<div class="chart-grid">
		{#each groupSeries as s (s.key)}
			<div class="card">
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

<section class="method card">
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
	.hero {
		display: flex;
		flex-direction: column;
		gap: 18px;
	}

	.eyebrow {
		font-family: var(--font-mono);
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--makro-strong);
		margin: 0 0 6px;
	}

	h1 {
		font-size: clamp(26px, 4vw, 38px);
		line-height: 1.12;
		max-width: 22ch;
	}

	.lede {
		color: var(--ink-secondary);
		max-width: 58ch;
		margin: 10px 0 0;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
		gap: 10px;
	}

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 14px 16px;
	}

	.browser {
		margin-top: 30px;
	}

	.filters {
		display: flex;
		flex-wrap: wrap;
		gap: 10px 22px;
		margin-bottom: 14px;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.chip {
		font: inherit;
		font-size: 13px;
		padding: 5px 12px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--ink-secondary);
		cursor: pointer;
	}

	.chip:hover {
		border-color: var(--makro);
		color: var(--ink);
	}

	.chip.active {
		background: var(--makro-wash);
		border-color: var(--makro);
		color: var(--makro-strong);
		font-weight: 600;
	}

	.chart-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 12px;
	}

	.method {
		margin-top: 30px;
		max-width: 76ch;
	}

	.method h2 {
		font-size: 17px;
		margin-bottom: 6px;
	}

	.method p {
		margin: 0;
		color: var(--ink-secondary);
		font-size: 14px;
	}

	.method code {
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 1px 5px;
		border-radius: 3px;
	}
</style>
