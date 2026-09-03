<script lang="ts">
	import LineChart from '$lib/components/LineChart.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import { formatSigned } from '$lib/format';
	import { loadScenario, type Scenario, type ShockMeta } from '$lib/data';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import {
		downloadBlob, exportFilename, permalink, provenanceLine, scenarioCsv, svgToPngBlob
	} from '$lib/export';

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
	const daScale = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 2 });
	let override: Scenario | null | 'unset' = $state.raw('unset');
	let loading = $state(false);
	const scenario = $derived(override === 'unset' ? data.initialScenario : override);

	/** Client-side linear rescaling of a solved scenario (1 = as solved).
	 *  Negative steps mirror the shock: the catalog only holds increases, so a cut is
	 *  shown by flipping the deviations. That is a first-order extrapolation to the other
	 *  side of the baseline — no worse than the ×2 we already allow, but it is labelled. */
	const ALL_SCALE_STEPS = [-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
	const UNSCALED = 1;
	/** Steps this scenario allows. Where the model has a boundary the solver could not
	 *  cross, the catalog caps how far we may extrapolate (`maxScale`); the cap is on the
	 *  magnitude, so it trims the mirrored side too. */
	const scaleSteps = $derived.by(() => {
		const cap = scenario?.definition?.maxScale;
		const steps = cap == null ? ALL_SCALE_STEPS : ALL_SCALE_STEPS.filter((s) => Math.abs(s) <= cap);
		return steps.includes(UNSCALED) ? steps : [...steps, UNSCALED].sort((a, b) => a - b);
	});
	let scaleIdx = $state(ALL_SCALE_STEPS.indexOf(UNSCALED));
	/** scaleIdx indexes scaleSteps, which shrinks when a scenario carries a cap. */
	const boundedIdx = $derived(
		scaleIdx >= 0 && scaleIdx < scaleSteps.length ? scaleIdx : scaleSteps.indexOf(UNSCALED)
	);
	const scale = $derived(scaleSteps[boundedIdx]);
	const mirrored = $derived(scale < 0);

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
		scaleIdx = ALL_SCALE_STEPS.indexOf(UNSCALED);
		const shock = name === '_demo' ? DEMO : meta.shocks.find((s) => s.name === name);
		if (name === '_demo' && location.search) replaceState(resolve('/scenarier/'), {});
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
			if (scaleSteps.includes(wantedScale)) scaleIdx = scaleSteps.indexOf(wantedScale);
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
	const years = $derived(Array.from({ length: meta.yearEnd - meta.yearStart + 1 }, (_, i) => meta.yearStart + i));

	// ------------------------------------------------------------------------------------
	// Sharing: every solved view is a permalink, and every export carries the source stamp.
	const shareable = $derived(!!scenario && !scenario.synthetic && selectedName !== '_demo');
	const closureLabel = $derived(
		meta.variations.find((v) => v.suffix === selectedVariation)?.labelDa ?? 'Ufinansieret'
	);
	const shareUrl = $derived(
		shareable ? permalink(page.url.origin, { stod: selectedName, variant: selectedVariation, skala: scale }) : ''
	);
	const provenance = $derived(
		provenanceLine({
			model: scenario?.modelVersion?.name ?? meta.model.name,
			commit: scenario?.modelVersion?.commit ?? meta.model.commit ?? '',
			closure: closureLabel,
			date: __BUILD_DATE__
		})
	);
	/** The scenario in one line, as it appears on exports. */
	const scenarioLine = $derived.by(() => {
		const def = scenario?.definition;
		if (!def) return selectedShock.labelDa;
		const scaled = scale !== 1 ? ` · ×${daScale.format(scale)} ${mirrored ? 'spejlet' : 'lineær tilnærmelse'}` : '';
		return `${selectedShock.labelDa}: ${def.changeDa} fra ${def.firstYear}, ${closureLabel.toLowerCase()}${scaled}`;
	});

	// Keep the address bar in sync, so the URL a reader copies reproduces the view.
	$effect(() => {
		if (!shareable) return;
		const url = new URL(shareUrl);
		if (url.search !== location.search) replaceState(url, {});
	});

	let chartSvgs: Record<string, SVGSVGElement | undefined> = $state({});
	let copied = $state(false);
	let exporting: string | null = $state(null);

	async function copyLink() {
		await navigator.clipboard.writeText(shareUrl);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function downloadCsv() {
		const csv = scenarioCsv({
			years,
			columns: charts.map((c) => ({ key: c.key, label: c.title, unit: c.suffix.trim(), values: c.values })),
			provenance: [
				scenarioLine,
				'Afvigelser fra grundforløbet: pct. for mængder og priser, pct.-point for satser og saldi',
				provenance,
				`Kilde: ${shareUrl}`
			]
		});
		// BOM so Excel reads the Danish characters and the decimal commas correctly.
		downloadBlob(
			new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }),
			exportFilename({ stod: selectedName, variant: selectedVariation, key: null, skala: scale, ext: 'csv' })
		);
	}

	async function downloadPng(chart: (typeof charts)[number]) {
		const svg = chartSvgs[chart.key];
		if (!svg) return;
		exporting = chart.key;
		try {
			const theme = getComputedStyle(document.documentElement);
			const cssVar = (name: string) => theme.getPropertyValue(name).trim();
			const blob = await svgToPngBlob(svg, {
				header: [`${chart.title} — ${chart.unit}`, scenarioLine],
				footer: [provenance, shareUrl],
				colors: { background: cssVar('--surface'), ink: cssVar('--ink'), muted: cssVar('--ink-muted') },
				fonts: { display: cssVar('--font-display'), body: cssVar('--font-body') }
			});
			downloadBlob(
				blob,
				exportFilename({ stod: selectedName, variant: selectedVariation, key: chart.key, skala: scale, ext: 'png' })
			);
		} finally {
			exporting = null;
		}
	}
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
		{#if scenario?.definition?.explainerDa}
			<p class="explainer">{scenario.definition.explainerDa}</p>
		{/if}

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
							max={scaleSteps.length - 1}
							step="1"
							bind:value={scaleIdx}
							aria-valuetext={`${daScale.format(scale)} gange stødet${mirrored ? ' — spejlet, altså en lempelse' : ''}`}
						/>
						<output for="scale" class="scale-readout">
							<span class="scale-value"><strong>×{daScale.format(scale)}</strong> = {scaledChange}</span>
							<!-- Always rendered: the badge sits next to the slider, so popping it in and out
							     would resize the track mid-drag. -->
							<span class="approx" class:blank={scale === 1} class:mirror={mirrored}>
								{mirrored ? 'spejlet' : 'lineær tilnærmelse'}
							</span>
						</output>
						<p class="scale-note">
							Kurverne skaleres i browseren — det er <em>ikke</em> en ny modelkørsel. Modellen er
							tæt på lineær for stød af denne størrelse, men ikke helt: {def.linearityDa}
						</p>
						{#if mirrored}
							<p class="scale-note mirror-note">
								<strong>Negativ skala spejler stødet.</strong> Kataloget indeholder kun forhøjelser,
								så en lempelse vises ved at vende fortegnet på afvigelserne. Det er en lineær
								tilnærmelse på den anden side af grundforløbet — retningen er rigtig, men størrelsen
								er ikke løst i modellen. En rigtig nedsættelse kræver en ny modelkørsel.
							</p>
						{/if}
						{#if def.maxScaleDa}
							<p class="scale-note">{def.maxScaleDa}</p>
						{/if}
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
			{#if shareable}
				<div class="share-row" role="group" aria-label="Del og hent">
					<button class="chip" onclick={copyLink}>{copied ? 'Link kopieret ✓' : 'Kopiér link'}</button>
					<button class="chip" onclick={downloadCsv}>Hent tal (CSV)</button>
					{#if selectedVariation === '_perm' || selectedVariation === '_ufin'}
						<a class="chip" href={`${resolve('/pakke/')}?${selectedName}=${scale}&variant=${selectedVariation}`}>Læg i en pakke →</a>
					{/if}
					<span class="share-hint">Linket gengiver præcis denne visning; hver graf kan hentes som PNG med kildeangivelse.</span>
				</div>
			{/if}
			<div class="chart-grid" class:is-demo={scenario.synthetic} style:opacity={loading ? 0.5 : 1}>
				{#each charts as chart (chart.key)}
					<div class="card chart-card" class:instrument={chart.isInstrument}>
						{#if scenario.synthetic}<span class="demo-badge" aria-hidden="true">DEMO</span>{/if}
						{#if chart.isInstrument}<span class="instrument-badge">Stødet (input)</span>{/if}
						{#if scale !== 1 && !chart.isInstrument}<span class="scaled-badge">×{daScale.format(scale)} {mirrored ? 'spejlet' : 'tilnærmet'}</span>{/if}
						<LineChart
							title={chart.title}
							code={chart.key}
							unit={chart.unit}
							{years}
							series={[{ key: chart.key, label: chart.title, values: chart.values }]}
							fromYear={fromYear}
							toYear={toYear}
							zeroLine
							height={200}
							suffix={chart.suffix}
							bind:svg={chartSvgs[chart.key]}
						/>
						{#if shareable}
							<div class="card-tools">
								<button class="png-btn" onclick={() => downloadPng(chart)} disabled={exporting === chart.key}>
									{exporting === chart.key ? 'Henter …' : 'Hent PNG'}
								</button>
							</div>
						{/if}
					</div>
				{/each}
			</div>
			{#if shareable}
				<p class="kilde">Kilde: {provenance} · <a href={shareUrl}>{shareUrl}</a></p>
			{/if}
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
				(AR-profil), permanent finansieret (den beregningstekniske lukkeskat reagerer, som i DREAMs
				egne beregninger) og permanent ufinansieret. De midlertidige varianter er indtil videre
				ufinansierede.
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
		/* Both flexible columns are content-independent on purpose: with a max-content
		   readout the track resized as the readout text changed, and a track that
		   changes width mid-drag makes the thumb slide out from under the pointer. */
		grid-template-columns: max-content minmax(0, 1fr) minmax(0, 1fr);
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
	}

	.scale-readout .scale-value {
		white-space: nowrap;
	}

	.scale-readout .approx.blank {
		visibility: hidden;
	}

	.scale-readout .approx.mirror {
		color: var(--bad);
	}

	.mirror-note {
		color: var(--ink-secondary);
	}

	.mirror-note strong {
		color: var(--bad);
	}

	.scale-readout .approx {
		margin-left: 6px;
		white-space: nowrap;
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

	.explainer {
		max-width: 72ch;
		font-size: 15px;
		line-height: 1.5;
		color: var(--ink-secondary);
		margin: -4px 0 14px;
	}

	.share-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
		margin-bottom: 10px;
	}
	.share-hint {
		font-size: 12px;
		color: var(--ink-muted);
	}

	.card-tools {
		display: flex;
		justify-content: flex-end;
		margin-top: 4px;
	}
	.png-btn {
		font: inherit;
		font-size: 11.5px;
		padding: 2px 8px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--ink-muted);
		cursor: pointer;
	}
	.png-btn:hover:not(:disabled) {
		color: var(--ink);
		border-color: var(--ink-muted);
	}
	.png-btn:disabled {
		cursor: progress;
	}

	.kilde {
		font-family: var(--font-mono);
		font-size: 11.5px;
		color: var(--ink-muted);
		margin: 12px 0 0;
		overflow-wrap: anywhere;
	}
	.kilde a {
		color: inherit;
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
