<script lang="ts">
	import LineChart from '$lib/components/LineChart.svelte';
	import StatTile from '$lib/components/StatTile.svelte';
	import { formatSigned } from '$lib/format';
	import { loadScenario, type Scenario, type ShockMeta } from '$lib/data';
	import {
		financedCostLine,
		formatScale,
		gdpPpToKr,
		packageLine,
		packageQuery,
		parsePackageQuery,
		pctToLevel,
		scaleSteps,
		superpose,
		unfinancedCostLine,
		type PackageComponent
	} from '$lib/package';
	import {
		downloadBlob, packageFilename, packagePermalink, provenanceLine, scenarioCsv, svgToPngBlob
	} from '$lib/export';
	import { page } from '$app/state';
	import { replaceState } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';

	let { data } = $props();

	const meta = $derived(data.meta);
	const baseline = $derived(data.baseline);

	/** The two closures a package can be solved under. Temporary profiles are not offered:
	 *  they are unfinanced-only and not yet solved for the catalog. */
	const CLOSURES = ['_perm', '_ufin'];

	let components: PackageComponent[] = $state([]);
	let variant = $state('_perm');
	/** Loaded scenario files, keyed by `<shock><variant>`; null = the file is missing. */
	let cache: Map<string, Scenario | null> = $state.raw(new Map());
	let loading = $state(0);
	let indicator = $state('qBNP');

	const shocksByName = $derived(new Map(meta.shocks.map((s) => [s.name, s])));
	const closureLabel = $derived(meta.variations.find((v) => v.suffix === variant)?.labelDa ?? 'Permanent, finansieret');

	const shockGroups = $derived.by(() => {
		const groups = new Map<string, ShockMeta[]>();
		for (const shock of meta.shocks) {
			const list = groups.get(shock.group) ?? [];
			list.push(shock);
			groups.set(shock.group, list);
		}
		return groups;
	});

	async function ensureLoaded(file: string) {
		if (cache.has(file)) return;
		loading++;
		try {
			const scenario = await loadScenario(fetch, file);
			cache = new Map(cache).set(file, scenario);
		} finally {
			loading--;
		}
	}

	function add(name: string) {
		if (components.some((c) => c.name === name)) return;
		components = [...components, { name, scale: 1 }];
		void ensureLoaded(`${name}${variant}`);
	}

	function remove(name: string) {
		components = components.filter((c) => c.name !== name);
	}

	function toggle(name: string) {
		if (components.some((c) => c.name === name)) remove(name);
		else add(name);
	}

	function setScale(name: string, scale: number) {
		components = components.map((c) => (c.name === name ? { ...c, scale } : c));
	}

	function setVariant(next: string) {
		variant = next;
		for (const c of components) {
			if (shocksByName.get(c.name)?.available.includes(next)) void ensureLoaded(`${c.name}${next}`);
		}
	}

	function apply(query: string) {
		const parsed = parsePackageQuery(new URLSearchParams(query), shocksByName.keys(), CLOSURES);
		variant = parsed.variant;
		components = parsed.components;
		for (const c of components) {
			if (shocksByName.get(c.name)?.available.includes(variant)) void ensureLoaded(`${c.name}${variant}`);
		}
	}

	// Deep link: /pakke/?Bundskat=-1&Offentligt_forbrug=0.5&variant=_perm
	onMount(() => {
		if (page.url.search) apply(page.url.search);
	});

	/** One row per component: its catalog entry, the loaded scenario (if any) and the
	 *  slider ladder it is allowed. */
	const rows = $derived.by(() =>
		components.map((c) => {
			const shock = shocksByName.get(c.name);
			const available = shock?.available.includes(variant) ?? false;
			const file = `${c.name}${variant}`;
			const scenario = available ? (cache.get(file) ?? undefined) : undefined;
			const steps = scaleSteps(scenario?.definition?.maxScale);
			return {
				...c,
				shock,
				available,
				scenario,
				missing: available && cache.has(file) && scenario == null,
				steps,
				stepIdx: steps.indexOf(c.scale)
			};
		})
	);

	/** Rows that actually enter the sums. */
	const active = $derived(rows.filter((r) => r.scenario != null && r.available));
	const ready = $derived(active.length > 0);

	function deviation(key: string): (number | null)[] {
		return superpose(active.map((r) => ({ scale: r.scale, values: r.scenario!.deviations[key] ?? [] })));
	}

	/** The change a component's size implies, in the instrument's own units. */
	function scaledChange(row: (typeof rows)[number]): string {
		const def = row.scenario?.definition;
		if (!def) return '';
		if (def.delta !== 0) return `${formatSigned(def.delta * 100 * row.scale)} pct.-point`;
		return `${formatSigned((def.factor - 1) * 100 * row.scale)} pct.`;
	}

	const years = $derived(Array.from({ length: meta.yearEnd - meta.yearStart + 1 }, (_, i) => meta.yearStart + i));
	const fromYear = $derived(meta.defaultShockYear - 1);
	const toYear = 2060;
	const yearIndex = (year: number) => year - meta.yearStart;

	// ------------------------------------------------------------------------------------
	// Headline numbers: first shock year, medium run, long run.
	const headlineYears = $derived([meta.defaultShockYear, meta.defaultShockYear + 5, 2050]);
	const HEADLINE_INDICATORS = [
		{ key: 'qBNP', label: 'BNP (realt)', devUnit: 'pct.', levelUnit: 'mia. 2020-kr.' },
		{ key: 'nL', label: 'Beskæftigelse', devUnit: 'pct.', levelUnit: 'personer' },
		{ key: 'saldo2bnp', label: 'Offentlig saldo', devUnit: 'pct.-point af BNP', levelUnit: 'mia. kr.' }
	];

	function levelOf(key: string, dev: number | null, year: number): number | null {
		const i = yearIndex(year);
		if (key === 'qBNP') return pctToLevel(dev, baseline.series.qBNP?.[i]);
		if (key === 'nL') {
			const persons = pctToLevel(dev, baseline.series.nL?.[i]);
			return persons == null ? null : Math.round(persons * 1000);
		}
		if (key === 'saldo2bnp') return gdpPpToKr(dev, baseline.series.vBNP?.[i]);
		return null;
	}

	/** One cell per headline year: the (scaled) deviation and its kr./persons equivalent. */
	function cellsOf(key: string, values: (number | null)[], scale = 1) {
		return headlineYears.map((year) => {
			const v = values[yearIndex(year)];
			const dev = v == null ? null : v * scale;
			return { year, dev, level: levelOf(key, dev, year) };
		});
	}

	const headline = $derived.by(() => {
		if (!ready) return [];
		return HEADLINE_INDICATORS.map((ind) => ({ ...ind, cells: cellsOf(ind.key, deviation(ind.key)) }));
	});

	/** The closure tax reaction: how much the fiscal rule had to move to pay for the package.
	 *  Only the financed closure has one. */
	const lukkeskat = $derived.by(() => {
		if (!ready || variant !== '_perm') return null;
		return cellsOf('tLukning', deviation('tLukning'));
	});

	/** Index of the year the hero tiles and the cost sentence quote (medium run). */
	const HERO = 1;
	const heroYear = $derived(headlineYears[HERO]);

	/** "I 2035 koster pakken de offentlige finanser ca. 15,6 mia. kr. om året" — the number
	 *  a costing sheet leads with. */
	const costText = $derived.by(() => {
		if (lukkeskat) return financedCostLine(lukkeskat[HERO]?.dev ?? null);
		const saldo = headline.find((h) => h.key === 'saldo2bnp')?.cells[HERO];
		return unfinancedCostLine(heroYear, saldo?.dev ?? null, saldo?.level ?? null);
	});

	// ------------------------------------------------------------------------------------
	// Charts of the package total.
	const chartKeys = ['qBNP', 'nL', 'saldo2bnp', 'qC', 'pBolig', 'vhW', 'ledighedsgrad', 'nettoformue2bnp'];

	const charts = $derived.by(() => {
		if (!ready) return [];
		const bySeriesKey = new Map(meta.series.map((s) => [s.key, s]));
		const keys = variant === '_perm' ? [...chartKeys, 'tLukning'] : chartKeys;
		return keys
			.map((key) => ({ key, values: deviation(key) }))
			.filter((c) => c.values.some((v) => v != null))
			.map(({ key, values }) => {
				const info = bySeriesKey.get(key);
				const pct = info?.devMode === 'pct';
				return {
					key,
					title: info?.labelDa ?? key,
					unit: pct ? 'afvigelse fra grundforløb, pct.' : 'afvigelse, pct.-point',
					suffix: pct ? ' pct.' : ' pct.-point',
					values
				};
			});
	});

	// ------------------------------------------------------------------------------------
	// Contributions: which part of the package does what.
	const contributionIndicator = $derived(HEADLINE_INDICATORS.find((i) => i.key === indicator) ?? HEADLINE_INDICATORS[0]);

	const contributions = $derived.by(() => {
		if (!ready) return [];
		const key = contributionIndicator.key;
		const lines = active.map((r) => ({
			name: r.name,
			label: r.shock?.labelDa ?? r.name,
			scale: r.scale,
			cells: cellsOf(key, r.scenario!.deviations[key] ?? [], r.scale)
		}));
		// The total row is the same row the Hovedtal table shows, so the two cannot drift.
		const total = headline.find((h) => h.key === key)?.cells ?? cellsOf(key, deviation(key));
		return [...lines, { name: '__total', label: 'Pakken i alt', scale: null, cells: total }];
	});

	/** True when any component was solved on a different MAKRO version than the baseline shown. */
	const versionMismatch = $derived(
		active.some((r) => {
			const version = r.scenario?.modelVersion;
			if (!version) return false;
			if (meta.model.fingerprint && version.fingerprint) return version.fingerprint !== meta.model.fingerprint;
			return version.commit !== meta.model.commit;
		})
	);

	// ------------------------------------------------------------------------------------
	// Sharing: the URL reproduces the package; every export carries the source stamp.
	const query = $derived(packageQuery(components, variant));
	const shareUrl = $derived(components.length > 0 ? packagePermalink(page.url.origin, query) : '');
	const provenance = $derived(
		provenanceLine({ model: meta.model.name, commit: meta.model.commit ?? '', closure: closureLabel, date: __BUILD_DATE__ })
	);
	const packageDescription = $derived(
		packageLine(
			active.map((r) => ({ labelDa: r.shock?.labelDa ?? r.name, scale: r.scale, changeDa: scaledChange(r) })),
			closureLabel
		)
	);
	const METHOD_LINE = 'Lineær sum af enkeltvis løste standardstød, skaleret i browseren — ikke en ny modelkørsel';

	// Keep the address bar in sync, so the URL a reader copies reproduces the package.
	$effect(() => {
		if (components.length === 0) {
			if (location.search) replaceState(resolve('/pakke/'), {});
			return;
		}
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
				packageDescription,
				METHOD_LINE,
				'Afvigelser fra grundforløbet: pct. for mængder og priser, pct.-point for satser og saldi',
				provenance,
				`Kilde: ${shareUrl}`
			]
		});
		downloadBlob(
			new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' }),
			packageFilename(components, variant, null, 'csv')
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
				header: [`${chart.title} — ${chart.unit}`, packageDescription, METHOD_LINE],
				footer: [provenance, shareUrl],
				colors: { background: cssVar('--surface'), ink: cssVar('--ink'), muted: cssVar('--ink-muted') },
				fonts: { display: cssVar('--font-display'), body: cssVar('--font-body') }
			});
			downloadBlob(blob, packageFilename(components, variant, chart.key, 'png'));
		} finally {
			exporting = null;
		}
	}

	/** Worked examples for the empty state, as package queries. */
	const EXAMPLES = [
		{
			title: 'Lavere bundskat, betalt med mindre offentligt forbrug',
			note: 'Ufinansieret, så saldoen viser, om pakken balancerer.',
			query: 'Bundskat=-1&Offentligt_forbrug=-0.5&variant=_ufin'
		},
		{
			title: 'Velfærdspakke: flere offentligt ansatte og højere overførsler',
			note: 'Finansieret med lukkeskatten, som i DREAMs egne beregninger.',
			query: 'Offentlig_Beskaeftigelse=1&Skattepligtig_indkomstoverforsel=1&variant=_perm'
		},
		{
			title: 'Grøn omlægning: højere energiafgift, lavere bundskat',
			note: 'Ufinansieret; se om provenuet rækker til skattelettelsen.',
			query: 'Energiafgift=1&Bundskat=-0.25&variant=_ufin'
		}
	];

	/** Deviations rounded to what the table shows, so a −0,004 reads "0" rather than "-0". */
	function fmtDev(value: number | null): string {
		if (value == null) return '–';
		const rounded = Math.round(value * 100) / 100;
		return rounded === 0 ? '0' : formatSigned(rounded);
	}

	function fmtLevel(key: string, value: number | null): string {
		if (value == null) return '–';
		const rounded = key === 'nL' ? Math.round(value) : Math.round(value * 100) / 100;
		return rounded === 0 ? '0' : formatSigned(rounded);
	}
</script>

<svelte:head>
	<title>Pakker · MAKROskop</title>
</svelte:head>

<section class="intro">
	<p class="eyebrow">Pakke-værksted</p>
	<h1>Hvad koster pakken?</h1>
	<p class="lede">
		Sæt flere standardstød sammen til én politik-pakke – fx lavere bundskat betalt med mindre offentligt
		forbrug – og se, hvad MAKRO siger om BNP, beskæftigelse og de offentlige finanser. Pakken er summen af
		de enkelte stød, skaleret i browseren; hvert stød er løst i modellen én gang.
	</p>
</section>

<div class="workbench">
	<aside aria-label="Stødkatalog">
		<p class="aside-hint">Klik for at lægge et stød i pakken.</p>
		{#each [...shockGroups] as [group, shocks] (group)}
			<h3>{group}</h3>
			{#each shocks as shock (shock.name)}
				{@const inPackage = components.some((c) => c.name === shock.name)}
				{@const usable = shock.available.includes(variant)}
				<button
					class="shock"
					class:selected={inPackage}
					disabled={!usable && !inPackage}
					title={usable ? '' : shock.available.length > 0 ? `Kun løst ${meta.variations.find((v) => v.suffix === shock.available[0])?.labelDa?.toLowerCase()}` : 'Afventer modelkørsel'}
					aria-pressed={inPackage}
					onclick={() => toggle(shock.name)}
				>
					<span class="dot" class:ready={usable} aria-hidden="true"></span>
					{shock.labelDa}
				</button>
			{/each}
		{/each}
	</aside>

	<div class="detail">
		<div class="detail-head">
			<h2>Pakkens indhold</h2>
			<div class="chip-row" role="group" aria-label="Finansiering">
				{#each CLOSURES as suffix (suffix)}
					<button class="chip" class:active={variant === suffix} onclick={() => setVariant(suffix)}>
						{meta.variations.find((v) => v.suffix === suffix)?.labelDa ?? suffix}
					</button>
				{/each}
			</div>
		</div>

		{#if components.length === 0}
			<section class="card empty">
				<h3>Pakken er tom</h3>
				<p>Vælg stød i kataloget til venstre – eller start fra et eksempel:</p>
				<ul class="examples">
					{#each EXAMPLES as example (example.query)}
						<li>
							<a
								href={`${resolve('/pakke/')}?${example.query}`}
								onclick={(e) => {
									e.preventDefault();
									apply(example.query);
								}}>{example.title}</a
							>
							<span class="muted">{example.note}</span>
						</li>
					{/each}
				</ul>
			</section>
		{:else}
			<section class="card package" aria-label="Pakkens stød">
				<ol class="rows">
					{#each rows as row (row.name)}
						<li class="row" class:inactive={!row.available || row.missing}>
							<div class="row-head">
								<span class="row-name">{row.shock?.labelDa ?? row.name}</span>
								<button class="remove" onclick={() => remove(row.name)} aria-label={`Fjern ${row.shock?.labelDa ?? row.name}`}>Fjern</button>
							</div>
							{#if !row.available}
								<p class="row-note">Ikke løst {closureLabel.toLowerCase()} – indgår ikke i summen. Skift finansiering for at bruge stødet.</p>
							{:else if row.missing}
								<p class="row-note">Resultatfilen kunne ikke hentes – indgår ikke i summen.</p>
							{:else if row.scenario}
								{@const def = row.scenario.definition}
								<div class="scaler">
									<input
										type="range"
										min="0"
										max={row.steps.length - 1}
										step="1"
										value={row.stepIdx < 0 ? row.steps.indexOf(1) : row.stepIdx}
										oninput={(e) => setScale(row.name, row.steps[Number(e.currentTarget.value)])}
										aria-label={`Størrelse af ${row.shock?.labelDa ?? row.name}`}
										aria-valuetext={`${formatScale(row.scale)} gange stødet${row.scale < 0 ? ' — spejlet, altså en lempelse' : ''}`}
									/>
									<output class="scale-readout">
										<span class="scale-value"><strong>×{formatScale(row.scale)}</strong> = {scaledChange(row)}</span>
										<span class="approx" class:blank={row.scale === 1} class:mirror={row.scale < 0}>
											{row.scale < 0 ? 'spejlet' : 'lineær tilnærmelse'}
										</span>
									</output>
								</div>
								{#if def}
									<p class="row-note">{def.instrumentDa} · løst som {def.changeDa}{def.maxScaleDa ? ` · ${def.maxScaleDa}` : ''}</p>
								{/if}
							{:else}
								<p class="row-note">Henter …</p>
							{/if}
						</li>
					{/each}
				</ol>
				{#if active.length < components.length}
					<p class="count-note">{active.length} af {components.length} stød indgår i summen.</p>
				{/if}
			</section>
		{/if}

		{#if versionMismatch}
			<div class="banner warn" role="alert">
				<strong>Versionsforskel.</strong> Mindst ét stød i pakken er løst på en anden MAKRO-version end
				grundforløbet her ({meta.model.name}, {meta.model.commit}). Omregningen til kroner og personer bruger
				grundforløbets niveauer og bør tages med forbehold.
			</div>
		{/if}

		{#if ready}
			<div class="hero" aria-label={`Hovedtal i ${heroYear}`}>
				{#each headline as ind (ind.key)}
					{@const cell = ind.cells[HERO]}
					<StatTile
						label={`${ind.label} i ${heroYear}`}
						value={fmtDev(cell.dev)}
						unit={ind.devUnit}
						note={cell.level == null ? '' : `≈ ${fmtLevel(ind.key, cell.level)} ${ind.levelUnit}`}
						tone={ind.key === 'saldo2bnp' && cell.dev != null ? (cell.dev >= 0 ? 'good' : 'bad') : 'neutral'}
					/>
				{/each}
			</div>

			<section class="card facts" aria-label="Hovedtal">
				<h3>Hovedtal – afvigelse fra grundforløbet</h3>
				{#if costText}<p class="cost">{costText}</p>{/if}
				<div class="table-wrap">
					<table>
						<thead>
							<tr>
								<th scope="col"></th>
								{#each headlineYears as year (year)}<th scope="col">{year}</th>{/each}
							</tr>
						</thead>
						<tbody>
							{#each headline as ind (ind.key)}
								<tr>
									<th scope="row">{ind.label}<span class="unit">{ind.devUnit} · {ind.levelUnit}</span></th>
									{#each ind.cells as cell (cell.year)}
										<td>
											<span class="dev">{fmtDev(cell.dev)}</span>
											<span class="level">{cell.level == null ? '' : fmtLevel(ind.key, cell.level)}</span>
										</td>
									{/each}
								</tr>
							{/each}
							{#if lukkeskat}
								<tr>
									<th scope="row">Lukkeskat (finansieringen)<span class="unit">pct.-point · beregningsteknisk</span></th>
									{#each lukkeskat as cell (cell.year)}
										<td><span class="dev">{fmtDev(cell.dev)}</span></td>
									{/each}
								</tr>
							{/if}
						</tbody>
					</table>
				</div>
				<p class="facts-note">
					Kroner og personer er omregnet med grundforløbets niveauer i det pågældende år (BNP i 2020-priser,
					saldo i løbende priser). {#if lukkeskat}Lukkeskatten er den beregningstekniske skat, DREAM lader
					reagere, så de offentlige finanser forbliver holdbare: positiv = pakken skal finansieres, negativ =
					pakken giver råderum.{/if}
				</p>
			</section>

			<section class="card contributions" aria-label="Bidrag fra de enkelte stød">
				<div class="contrib-head">
					<h3>Hvad bidrager med hvad?</h3>
					<div class="chip-row" role="group" aria-label="Indikator">
						{#each HEADLINE_INDICATORS as ind (ind.key)}
							<button class="chip" class:active={indicator === ind.key} onclick={() => (indicator = ind.key)}>{ind.label}</button>
						{/each}
					</div>
				</div>
				<div class="table-wrap">
					<table>
						<thead>
							<tr>
								<th scope="col" class="lead">{contributionIndicator.label}<span class="unit">{contributionIndicator.devUnit} · {contributionIndicator.levelUnit}</span></th>
								{#each headlineYears as year (year)}<th scope="col">{year}</th>{/each}
							</tr>
						</thead>
						<tbody>
							{#each contributions as line (line.name)}
								<tr class:total={line.scale == null}>
									<th scope="row">{line.label}{#if line.scale != null}<span class="unit">×{formatScale(line.scale)}</span>{/if}</th>
									{#each line.cells as cell (cell.year)}
										<td>
											<span class="dev">{fmtDev(cell.dev)}</span>
											<span class="level">{cell.level == null ? '' : fmtLevel(contributionIndicator.key, cell.level)}</span>
										</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</section>

			<div class="share-row" role="group" aria-label="Del og hent">
				<button class="chip" onclick={copyLink}>{copied ? 'Link kopieret ✓' : 'Kopiér link'}</button>
				<button class="chip" onclick={downloadCsv}>Hent tal (CSV)</button>
				<span class="share-hint">Linket gengiver præcis denne pakke; hver graf kan hentes som PNG med kildeangivelse.</span>
			</div>

			<div class="chart-grid" style:opacity={loading > 0 ? 0.5 : 1}>
				{#each charts as chart (chart.key)}
					<div class="card chart-card">
						<LineChart
							title={chart.title}
							code={chart.key}
							unit={chart.unit}
							{years}
							series={[{ key: chart.key, label: 'Pakken i alt', values: chart.values }]}
							fromYear={fromYear}
							toYear={toYear}
							zeroLine
							height={200}
							suffix={chart.suffix}
							bind:svg={chartSvgs[chart.key]}
						/>
						<div class="card-tools">
							<button class="png-btn" onclick={() => downloadPng(chart)} disabled={exporting === chart.key}>
								{exporting === chart.key ? 'Henter …' : 'Hent PNG'}
							</button>
						</div>
					</div>
				{/each}
			</div>
			<p class="kilde">{packageDescription}<br />Kilde: {provenance} · <a href={shareUrl}>{shareUrl}</a></p>
		{:else if components.length > 0 && loading > 0}
			<p class="muted">Henter stødene …</p>
		{/if}

		<div class="method card">
			<h2>Sådan er pakken regnet</h2>
			<p>
				Hvert stød i kataloget er løst i MAKRO én gang, i sin egen størrelse. Pakken er den <em>lineære
				sum</em> af de valgte stød, hver ganget med den valgte størrelse – regnet i browseren, ikke som en ny
				modelkørsel. MAKRO er tæt på lineær for stød af denne størrelse (målt 1–2 pct. afvigelse pr. stød),
				men samspil mellem stødene indgår ikke, og fejlen vokser med pakkens størrelse.
			</p>
			<p>
				Negative størrelser spejler stødet: kataloget indeholder kun forhøjelser, så en lempelse vises ved at
				vende fortegnet. Finansieringen gælder hele pakken: <em>finansieret</em> betyder, at den
				beregningstekniske lukkeskat reagerer på hvert stød, som i DREAMs egne beregninger; <em>ufinansieret</em>
				betyder, at ingen skat reagerer, så saldoen viser pakkens egen virkning på de offentlige finanser.
				Størrelserne er MAKROskops egne stødstørrelser – ikke DREAMs normering til 1 pct. af BNP.
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

	.aside-hint {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 0 0 4px;
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

	.shock:hover:not(:disabled) {
		background: var(--makro-wash);
		color: var(--ink);
	}

	.shock.selected {
		background: var(--makro-wash);
		color: var(--makro-strong);
		font-weight: 600;
	}

	.shock:disabled {
		opacity: 0.45;
		cursor: not-allowed;
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

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 14px 16px;
	}

	.card h3 {
		font-size: 15px;
		margin-bottom: 8px;
	}

	.empty p {
		color: var(--ink-secondary);
		font-size: 14px;
		margin: 0 0 8px;
	}

	.examples {
		margin: 0;
		padding-left: 18px;
		font-size: 14px;
	}

	.examples li {
		margin-bottom: 6px;
	}

	.examples .muted {
		display: block;
		font-size: 12.5px;
		color: var(--ink-muted);
	}

	.muted {
		color: var(--ink-muted);
	}

	.package {
		border-color: var(--makro);
		margin-bottom: 14px;
	}

	.rows {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.row {
		padding: 10px 0;
		border-top: 1px solid var(--grid);
	}

	.row:first-child {
		border-top: 0;
		padding-top: 0;
	}

	.row.inactive .row-name {
		color: var(--ink-muted);
	}

	.row-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 10px;
	}

	.row-name {
		font-weight: 600;
		font-size: 14.5px;
	}

	.remove {
		font: inherit;
		font-size: 11.5px;
		padding: 2px 8px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--ink-muted);
		cursor: pointer;
	}

	.remove:hover {
		color: var(--bad);
		border-color: var(--bad);
	}

	.row-note {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 4px 0 0;
	}

	.count-note {
		font-size: 12.5px;
		color: var(--ink-secondary);
		margin: 8px 0 0;
	}

	.scaler {
		margin-top: 6px;
		display: grid;
		/* Both columns content-independent: a track that changes width mid-drag makes
		   the thumb slide out from under the pointer. */
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: 4px 14px;
		align-items: center;
		font-size: 13px;
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
		color: var(--series-2);
	}

	.scale-readout .approx.blank {
		visibility: hidden;
	}

	.scale-readout .approx.mirror {
		color: var(--bad);
	}

	@media (max-width: 520px) {
		.scaler {
			grid-template-columns: 1fr;
		}
	}

	.banner {
		border: 1px solid var(--series-2);
		background: color-mix(in srgb, var(--series-2) 8%, var(--surface));
		border-radius: 8px;
		padding: 10px 14px;
		font-size: 13px;
		margin-bottom: 14px;
	}

	.banner.warn {
		border-color: var(--bad);
		background: color-mix(in srgb, var(--bad) 8%, var(--surface));
	}

	.hero {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 10px;
		margin-bottom: 12px;
	}

	.facts,
	.contributions {
		margin-bottom: 12px;
	}

	.contrib-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 6px;
	}

	.contrib-head h3 {
		margin-bottom: 0;
	}

	.table-wrap {
		overflow-x: auto;
	}

	table {
		border-collapse: collapse;
		width: 100%;
		font-size: 13.5px;
		font-variant-numeric: tabular-nums;
	}

	th,
	td {
		text-align: right;
		padding: 6px 10px;
		border-bottom: 1px solid var(--grid);
		vertical-align: top;
	}

	th[scope='row'] {
		text-align: left;
		font-weight: 500;
		color: var(--ink);
	}

	thead th {
		font-size: 12px;
		color: var(--ink-muted);
		font-weight: 600;
		border-bottom: 1px solid var(--axis);
	}

	.unit {
		display: block;
		font-size: 11px;
		font-weight: 400;
		color: var(--ink-muted);
	}

	.dev {
		display: block;
		font-weight: 600;
	}

	.level {
		display: block;
		font-size: 12px;
		color: var(--ink-muted);
	}

	tr.total th,
	tr.total td {
		border-top: 2px solid var(--axis);
		border-bottom: 0;
		font-weight: 700;
	}

	.cost {
		font-size: 15px;
		line-height: 1.45;
		color: var(--ink);
		margin: 0 0 10px;
		max-width: 70ch;
	}

	thead th.lead {
		text-align: left;
	}

	.facts-note {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 8px 0 0;
		max-width: 80ch;
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

	.chart-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 12px;
		transition: opacity 0.15s;
	}

	.chart-card {
		position: relative;
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

	.method {
		margin-top: 18px;
		max-width: 76ch;
	}

	.method h2 {
		font-size: 16px;
		margin-bottom: 6px;
	}

	.method p {
		margin: 0 0 8px;
		color: var(--ink-secondary);
		font-size: 13.5px;
	}
</style>
