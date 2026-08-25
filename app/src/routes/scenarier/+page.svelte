<script lang="ts">
	import LineChart from '$lib/components/LineChart.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import { formatSigned } from '$lib/format';
	import { loadScenario, type Scenario, type ShockMeta } from '$lib/data';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	let { data } = $props();

	const meta = $derived(data.meta);

	const DEMO: ShockMeta = {
		name: '_demo',
		labelDa: 'Syntetisk demo-scenarie',
		labelEn: 'Synthetic demo',
		group: 'Demo',
		available: ['']
	};

	let selectedName = $state('_demo');
	let selectedVariation = $state('');
	/** Client-side linear rescaling of a solved scenario (1 = as solved). */
	let scale = $state(1);
	const SCALE_STEPS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
	const daScale = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 2 });
	let override: Scenario | null | 'unset' = $state.raw('unset');
	let loading = $state(false);
	const scenario = $derived(override === 'unset' ? data.initialScenario : override);

	const selectedShock = $derived(
		selectedName === '_demo' ? DEMO : (meta.shocks.find((s) => s.name === selectedName) ?? DEMO)
	);

	const shockGroups = $derived.by(() => {
		const groups = new Map<string, ShockMeta[]>();
		for (const shock of meta.shocks) {
			const list = groups.get(shock.group) ?? [];
			list.push(shock);
			groups.set(shock.group, list);
		}
		return groups;
	});

	async function select(name: string, variation: string) {
		selectedName = name;
		selectedVariation = variation;
		scale = 1;
		const shock = name === '_demo' ? DEMO : meta.shocks.find((s) => s.name === name);
		if (!shock || !shock.available.includes(variation)) {
			override = null;
			return;
		}
		loading = true;
		override = await loadScenario(fetch, `${name}${variation}`);
		loading = false;
	}

	// Deep link: /scenarier/?stod=Rente&variant=_ufin (used from the validation page)
	onMount(() => {
		const name = page.url.searchParams.get('stod');
		const shock = name ? meta.shocks.find((s) => s.name === name) : undefined;
		if (!shock) return;
		const wanted = page.url.searchParams.get('variant') ?? '';
		const variation = shock.available.includes(wanted)
			? wanted
			: (shock.available[0] ?? meta.variations[1]?.suffix ?? '_midl');
		const wantedScale = Number(page.url.searchParams.get('skala'));
		void select(shock.name, variation).then(() => {
			if (SCALE_STEPS.includes(wantedScale)) scale = wantedScale;
		});
	});

	const chartKeys = [
		'qBNP', 'nL', 'ledighedsgrad',
		'qC', 'qX', 'qM',
		'qI', 'vhW', 'pC',
		'pBolig', 'saldo2bnp', 'primsaldo2bnp'
	];

	const charts = $derived.by(() => {
		if (!scenario) return [];
		const bySeriesKey = new Map(meta.series.map((s) => [s.key, s]));
		// The shocked instrument itself leads, so the cause is visible next to the effects.
		const instrument = scenario.definition?.seriesKey;
		const keys = instrument && !chartKeys.includes(instrument) ? [instrument, ...chartKeys] : chartKeys;
		return keys
			.filter((key) => scenario!.deviations[key]?.some((v) => v != null))
			.map((key) => {
				const info = bySeriesKey.get(key);
				const pct = info?.devMode === 'pct';
				return {
					key,
					title: info?.labelDa ?? key,
					isInstrument: key === instrument,
					unit: pct ? 'afvigelse fra grundforløb, pct.' : 'afvigelse, pct.-point',
					suffix: pct ? ' pct.' : ' pct.-point',
					values:
						scale === 1
							? scenario!.deviations[key]
							: scenario!.deviations[key].map((v) => (v == null ? null : v * scale))
				};
			});
	});

	/** The shock size implied by the slider, in the instrument's own units. */
	const scaledChange = $derived.by(() => {
		const def = scenario?.definition;
		if (!def) return '';
		if (def.delta !== 0) return `${formatSigned(def.delta * 100 * scale)} pct.-point`;
		return `${formatSigned((def.factor - 1) * 100 * scale)} pct.`;
	});

	/** True when the scenario was solved on a different MAKRO version than the baseline shown. */
	const versionMismatch = $derived.by(() => {
		const version = scenario?.modelVersion;
		if (!version) return false;
		if (meta.model.fingerprint && version.fingerprint) return version.fingerprint !== meta.model.fingerprint;
		return version.commit !== meta.model.commit;
	});

	const fromYear = $derived(meta.defaultShockYear - 1);
	const toYear = 2060;
</script>

<svelte:head>
	<title>Scenarier · MAKROskop</title>
</svelte:head>

<section class="intro">
	<p class="eyebrow">Scenarie-værksted</p>
	<h1>Hvad sker der, hvis&nbsp;…?</h1>
	<p class="lede">
		MAKRO leveres med et katalog af standardstød: veldefinerede politik-eksperimenter, der viser modellens
		svar på fx højere offentligt forbrug eller lavere bundskat. Alle kurver er <em>afvigelser fra
		grundforløbet</em> – ikke niveauer.
	</p>
</section>

<div class="workbench">
	<aside aria-label="Stødkatalog">
		<button
			class="shock demo-entry"
			class:selected={selectedName === '_demo'}
			onclick={() => select('_demo', '')}
		>
			<span class="dot demo-dot" aria-hidden="true"></span>
			Syntetisk demo-scenarie
		</button>

		{#each [...shockGroups] as [group, shocks] (group)}
			<h3>{group}</h3>
			{#each shocks as shock (shock.name)}
				<button
					class="shock"
					class:selected={selectedName === shock.name}
					onclick={() => select(shock.name, shock.available[0] ?? meta.variations[1]?.suffix ?? '_midl')}
				>
					<span
						class="dot"
						class:ready={shock.available.length > 0}
						title={shock.available.length > 0 ? 'Data beregnet' : 'Afventer modelkørsel'}
						aria-hidden="true"
					></span>
					{shock.labelDa}
				</button>
			{/each}
		{/each}
	</aside>

	<div class="detail">
		<div class="detail-head">
			<h2>{selectedShock.labelDa}</h2>
			{#if selectedName !== '_demo'}
				<div class="chip-row" role="group" aria-label="Variant">
					{#each meta.variations as variation (variation.suffix)}
						<button
							class="chip"
							class:active={selectedVariation === variation.suffix}
							disabled={!selectedShock.available.includes(variation.suffix)}
							onclick={() => select(selectedName, variation.suffix)}
						>
							{variation.labelDa}
						</button>
					{/each}
				</div>
			{/if}
		</div>

		{#if scenario?.synthetic}
			<div class="banner" role="note">
				<strong>Syntetisk demo.</strong> Kurverne her er opdigtede tal, der kun viser, hvordan værktøjet
				virker. De er <strong>ikke</strong> en MAKRO-beregning. Rigtige scenarier kræver én modelkørsel med
				GAMS – resultatfilerne lægges i <code>etl/shock_gdx/</code> og indlæses automatisk.
			</div>
		{/if}

		{#if scenario?.definition}
			{@const def = scenario.definition}
			<section class="card definition" aria-label="Stødets definition">
				<h3>Sådan er stødet defineret</h3>
				<dl>
					<div>
						<dt>Instrument</dt>
						<dd><code class="mono">{def.instrument}</code> — {def.instrumentDa}</dd>
					</div>
					<div>
						<dt>Ændring</dt>
						<dd><strong>{def.changeDa}</strong> i forhold til grundforløbet, hvert år fra {def.firstYear}</dd>
					</div>
					<div>
						<dt>Profil</dt>
						<dd>{def.profileDa} Modellen løses frem til {def.lastYear}.</dd>
					</div>
					<div>
						<dt>Finansiering</dt>
						<dd>{def.closureDa}</dd>
					</div>
					<div>
						<dt>Beregnet med</dt>
						<dd>{def.solver} — <a href="/validering/">se valideringen</a></dd>
					</div>
					{#if scenario.modelVersion}
						<div>
							<dt>Modelversion</dt>
							<dd>
								{scenario.modelVersion.name}
								<code class="mono">{scenario.modelVersion.commit || scenario.modelVersion.fingerprint}</code>
								{#if scenario.modelVersion.source === 'assumed'}
									<span class="muted">(antaget — resultatfilen bærer intet versionsstempel)</span>
								{/if}
							</dd>
						</div>
					{/if}
				</dl>
				<p class="dream-note">{def.dreamDa}</p>
				{#if !scenario.synthetic}
					<div class="scaler">
						<label for="scale">Prøv en anden størrelse</label>
						<input
							id="scale"
							type="range"
							min="0"
							max={SCALE_STEPS.length - 1}
							step="1"
							value={SCALE_STEPS.indexOf(scale)}
							oninput={(e) => (scale = SCALE_STEPS[Number(e.currentTarget.value)])}
							aria-valuetext={`${daScale.format(scale)} gange stødet`}
						/>
						<output for="scale" class="scale-readout">
							<strong>×{daScale.format(scale)}</strong> = {scaledChange}
							{#if scale !== 1}<span class="approx">lineær tilnærmelse</span>{/if}
						</output>
						<p class="scale-note">
							Kurverne skaleres i browseren — det er <em>ikke</em> en ny modelkørsel. Modellen er
							tæt på lineær for stød af denne størrelse, men ikke helt: {def.linearityDa}
						</p>
					</div>
				{/if}
			</section>
		{/if}

		{#if scenario && versionMismatch}
			<div class="banner warn" role="alert">
				<strong>Versionsforskel.</strong> Scenariet er løst på
				{scenario.modelVersion?.name} ({scenario.modelVersion?.commit || scenario.modelVersion?.fingerprint}),
				men grundforløbet her er {meta.model.name} ({meta.model.commit}). Afvigelserne gælder den ældre
				version og bør genberegnes, før de sammenlignes med grundforløbet.
			</div>
		{/if}

		{#if scenario}
			{#if scenario.hbi != null}
				<div class="hbi-row">
					<StatTile
						label="Holdbarhedsindikator (HBI) i scenariet"
						value={formatSigned(scenario.hbi * 100)}
						unit="pct. af BNP"
						tone={scenario.hbi >= 0 ? 'good' : 'bad'}
					/>
				</div>
			{/if}
			<div class="chart-grid" class:is-demo={scenario.synthetic} style:opacity={loading ? 0.5 : 1}>
				{#each charts as chart (chart.key)}
					<div class="card chart-card" class:instrument={chart.isInstrument}>
						{#if scenario.synthetic}<span class="demo-badge" aria-hidden="true">DEMO</span>{/if}
						{#if chart.isInstrument}<span class="instrument-badge">Stødet (input)</span>{/if}
						{#if scale !== 1 && !chart.isInstrument}<span class="scaled-badge">×{daScale.format(scale)} tilnærmet</span>{/if}
						<LineChart
							title={chart.title}
							code={chart.key}
							unit={chart.unit}
							years={Array.from({ length: meta.yearEnd - meta.yearStart + 1 }, (_, i) => meta.yearStart + i)}
							series={[{ key: chart.key, label: chart.title, values: chart.values }]}
							fromYear={fromYear}
							toYear={toYear}
							zeroLine
							height={200}
							suffix={chart.suffix}
						/>
					</div>
				{/each}
			</div>
		{:else}
			<div class="pending card">
				<h3>Endnu ikke beregnet</h3>
				<p>
					Dette stød er defineret i MAKROs standardkatalog
					(<code>Analysis/Standard_shocks/standard_shocks.gms</code>), men er ikke løst i MAKROskop
					endnu. Hvert scenarie er én kørsel med den frie løser over hele modellens horisont — det
					kræver en maskine med ca. 64 GB hukommelse og tager nogle timer.
				</p>
				<p>
					Når resultatfilen (fx <code class="mono">{selectedName}_ufin.gdx</code>) lægges i
					<code>etl/shock_gdx/</code> og <code>extract.py</code> køres igen, dukker kurverne op her
					automatisk — sammen med stødets definition.
				</p>
			</div>
		{/if}

		<div class="method card">
			<h2>Sådan skal kurverne læses</h2>
			<p>
				Kurverne viser forskellen mellem scenariet og grundforløbet – i procent for mængder og priser, i
				procentpoint for satser og saldi. Stødet lægges ind i {meta.defaultShockYear}; den nøjagtige
				størrelse og hvad der ændres, står i boksen "Sådan er stødet defineret" for hvert beregnet
				scenarie. Varianterne følger MAKROs standardprofiler: et enkelt år, midlertidigt aftrappet
				(AR-profil), permanent finansieret og permanent ufinansieret — indtil videre er kun de
				ufinansierede varianter løst.
			</p>
		</div>
	</div>
</div>

<style>
	.eyebrow {
		font-family: var(--font-mono);
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--makro-strong);
		margin: 0 0 6px;
	}

	h1 {
		font-size: clamp(24px, 3.4vw, 34px);
	}

	.lede {
		color: var(--ink-secondary);
		max-width: 60ch;
		margin: 10px 0 0;
	}

	.definition {
		margin-bottom: 14px;
		border-color: var(--makro);
	}

	.definition h3 {
		font-size: 15px;
		margin-bottom: 8px;
	}

	.definition dl {
		margin: 0;
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 6px 14px;
		font-size: 13.5px;
	}

	.definition dl > div {
		display: contents;
	}

	.definition dt {
		color: var(--ink-muted);
		font-size: 12px;
		padding-top: 2px;
	}

	.definition dd {
		margin: 0;
		color: var(--ink-secondary);
	}

	.definition dd strong {
		color: var(--ink);
	}

	.definition code {
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 1px 5px;
		border-radius: 3px;
	}

	.definition .muted {
		color: var(--ink-muted);
		font-size: 12px;
	}

	.banner.warn {
		border-color: var(--bad);
		background: color-mix(in srgb, var(--bad) 8%, var(--surface));
	}

	.dream-note {
		font-size: 12.5px;
		color: var(--ink-muted);
		margin: 10px 0 0;
		max-width: 80ch;
	}

	.scaler {
		margin-top: 12px;
		padding-top: 12px;
		border-top: 1px solid var(--grid);
		display: grid;
		grid-template-columns: max-content 1fr max-content;
		gap: 4px 14px;
		align-items: center;
		font-size: 13px;
	}

	.scaler label {
		color: var(--ink-secondary);
	}

	.scaler input[type='range'] {
		width: 100%;
		accent-color: var(--makro);
	}

	.scale-readout {
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.scale-readout .approx {
		margin-left: 6px;
		font-family: var(--font-mono);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--series-2);
	}

	.scale-note {
		grid-column: 1 / -1;
		margin: 4px 0 0;
		font-size: 12px;
		color: var(--ink-muted);
		max-width: 80ch;
	}

	.scaled-badge {
		position: absolute;
		top: 8px;
		right: 10px;
		font-family: var(--font-mono);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--series-2);
		background: color-mix(in srgb, var(--series-2) 10%, var(--surface));
		padding: 2px 6px;
		border-radius: 3px;
	}

	@media (max-width: 520px) {
		.scaler {
			grid-template-columns: 1fr;
		}
	}

	.chart-card.instrument {
		border-color: var(--makro);
		position: relative;
	}

	.instrument-badge {
		position: absolute;
		top: 8px;
		right: 10px;
		font-family: var(--font-mono);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 2px 6px;
		border-radius: 3px;
	}

	@media (max-width: 520px) {
		.definition dl {
			grid-template-columns: 1fr;
			gap: 2px;
		}
		.definition dt {
			margin-top: 6px;
		}
	}

	.workbench {
		display: grid;
		grid-template-columns: 250px 1fr;
		gap: 24px;
		margin-top: 26px;
		align-items: start;
	}

	@media (max-width: 780px) {
		.workbench {
			grid-template-columns: 1fr;
		}
	}

	aside h3 {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		color: var(--ink-muted);
		margin: 14px 0 4px;
		font-family: var(--font-body);
		font-weight: 600;
	}

	.shock {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		text-align: left;
		font: inherit;
		font-size: 13px;
		padding: 5px 8px;
		border: 0;
		border-radius: 6px;
		background: none;
		color: var(--ink-secondary);
		cursor: pointer;
	}

	.shock:hover {
		background: var(--makro-wash);
		color: var(--ink);
	}

	.shock.selected {
		background: var(--makro-wash);
		color: var(--makro-strong);
		font-weight: 600;
	}

	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--grid);
		flex-shrink: 0;
	}

	.dot.ready {
		background: var(--makro);
	}

	.demo-dot {
		background: var(--series-2);
	}

	.demo-entry {
		margin-bottom: 4px;
	}

	.detail-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		margin-bottom: 12px;
	}

	.detail-head h2 {
		font-size: 20px;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.chip {
		font: inherit;
		font-size: 12px;
		padding: 4px 10px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--ink-secondary);
		cursor: pointer;
	}

	.chip.active {
		background: var(--makro-wash);
		border-color: var(--makro);
		color: var(--makro-strong);
		font-weight: 600;
	}

	.chip:disabled {
		opacity: 0.45;
		cursor: not-allowed;
	}

	.banner {
		border: 1px solid var(--series-2);
		background: color-mix(in srgb, var(--series-2) 8%, var(--surface));
		border-radius: 8px;
		padding: 10px 14px;
		font-size: 13px;
		margin-bottom: 14px;
	}

	.banner code {
		font-size: 12px;
	}

	.hbi-row {
		max-width: 320px;
		margin-bottom: 12px;
	}

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 14px 16px;
	}

	.chart-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 12px;
		transition: opacity 0.15s;
	}

	.chart-card {
		position: relative;
	}

	/* keep the caption clear of the DEMO badge */
	.is-demo .chart-card :global(figcaption) {
		padding-right: 56px;
	}

	.demo-badge {
		position: absolute;
		top: 10px;
		right: 12px;
		font-family: var(--font-mono);
		font-size: 10px;
		letter-spacing: 0.1em;
		color: var(--series-2);
		border: 1px solid var(--series-2);
		border-radius: 4px;
		padding: 1px 6px;
		opacity: 0.85;
		z-index: 1;
	}

	.pending h3 {
		font-size: 16px;
		margin-bottom: 6px;
	}

	.pending p {
		color: var(--ink-secondary);
		font-size: 14px;
		margin: 0 0 8px;
	}

	.method {
		margin-top: 18px;
		max-width: 76ch;
	}

	.method h2 {
		font-size: 16px;
		margin-bottom: 6px;
	}

	.method p {
		margin: 0;
		color: var(--ink-secondary);
		font-size: 13.5px;
	}

	code {
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 1px 5px;
		border-radius: 3px;
	}
</style>
