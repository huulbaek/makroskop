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

	/** What the page is showing, for a polite live region: the visual cues (dimmed grid,
	 *  swapped heading) say nothing to a screen reader. */
	const statusText = $derived.by(() => {
		if (loading) return 'Henter scenariet …';
		if (!scenario) return `${selectedShock.labelDa}: endnu ikke beregnet.`;
		if (selectedName === '_demo') return 'Viser det syntetiske demo-scenarie.';
		return `Viser ${selectedShock.labelDa}, ${closureLabel.toLowerCase()}.`;
	});

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
			aria-pressed={selectedName === '_demo'}
			onclick={() => select('_demo', '')}
		>
			Syntetisk demo-scenarie
		</button>

		{#each [...shockGroups] as [group, shocks] (group)}
			<h2>{group}</h2>
			{#each shocks as shock (shock.name)}
				{@const pending = shock.available.length === 0}
				<button
					class="shock"
					class:selected={selectedName === shock.name}
					class:pending={pending}
					aria-pressed={selectedName === shock.name}
					title={pending ? 'Afventer modelkørsel' : undefined}
					onclick={() => select(shock.name, shock.available[0] ?? meta.variations[1]?.suffix ?? '_midl')}
				>
					{shock.labelDa}{#if pending}<span class="sr-only"> – afventer modelkørsel</span>{/if}
				</button>
			{/each}
		{/each}
	</aside>

	<div class="detail">
		<div class="sr-only" role="status">{statusText}</div>
		<div class="sr-only" role="status">{copied ? 'Link kopieret til udklipsholderen.' : ''}</div>
		<div class="sr-only" role="status">{exporting ? 'Laver PNG …' : ''}</div>
		<div class="detail-head">
			<h2>{selectedShock.labelDa}</h2>
			{#if selectedName !== '_demo'}
				<div class="chip-row" role="group" aria-label="Variant">
					{#each meta.variations as variation (variation.suffix)}
						<button
							class="chip"
							class:active={selectedVariation === variation.suffix}
							aria-pressed={selectedVariation === variation.suffix}
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
					<div class="cell" class:instrument={chart.isInstrument}>
						{#if scenario.synthetic}<span class="badge warm" aria-hidden="true">Demo</span>{/if}
						{#if chart.isInstrument}<span class="badge accent">Stødet (input)</span>{/if}
						{#if scale !== 1 && !chart.isInstrument}<span class="badge warm">×{daScale.format(scale)} {mirrored ? 'spejlet' : 'tilnærmet'}</span>{/if}
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

		<div class="method">
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
	.demo-entry {
		margin-bottom: 14px;
	}

	.detail-head {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 14px;
	}

	.detail-head h2 {
		font-size: 30px;
	}

	.explainer {
		font-family: var(--font-display);
		font-size: 19px;
		line-height: 1.45;
		color: var(--ink-secondary);
		max-width: 62ch;
		margin: 0 0 20px;
	}

	.definition {
		margin-bottom: 18px;
		border-left: 3px solid var(--makro);
	}

	.definition h3 {
		font-size: 20px;
		margin-bottom: 10px;
	}

	.definition dl {
		margin: 0;
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 6px 18px;
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
	}

	.definition .muted {
		color: var(--ink-muted);
		font-size: 12px;
	}

	.dream-note {
		font-size: 12.5px;
		color: var(--ink-muted);
		margin: 12px 0 0;
		max-width: 80ch;
	}

	.scaler {
		margin-top: 14px;
		padding-top: 14px;
		border-top: 1px solid var(--rule);
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

	.scale-readout .approx {
		margin-left: 6px;
		white-space: nowrap;
		font-family: var(--font-mono);
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--warm-text);
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

	.scale-note {
		grid-column: 1 / -1;
		margin: 4px 0 0;
		font-size: 12px;
		color: var(--ink-muted);
		max-width: 80ch;
	}

	.hbi-row {
		max-width: 320px;
		margin-bottom: 18px;
		border-top: 1px solid var(--rule-strong);
		padding-top: 12px;
	}

	.hbi-row :global(.figure) {
		border-left: 0;
		padding-left: 0;
	}

	.cell.instrument {
		border-top: 3px solid var(--makro);
	}

	/* keep the caption clear of a badge */
	.is-demo .cell :global(figcaption),
	.cell.instrument :global(figcaption) {
		padding-right: 110px;
	}

	.pending h3 {
		margin-bottom: 8px;
	}

	.pending p {
		color: var(--ink-secondary);
		font-size: 14px;
		margin: 0 0 8px;
	}

	@media (max-width: 520px) {
		.definition dl {
			grid-template-columns: 1fr;
			gap: 2px;
		}
		.definition dt {
			margin-top: 6px;
		}
		.scaler {
			grid-template-columns: 1fr;
		}
	}
</style>
