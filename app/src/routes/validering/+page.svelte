<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';

	let { data } = $props();

	const validation = $derived(data.validation);
	const full = $derived(validation.fullHorizon);
	const solve = $derived(validation.scenario);
	const scenario = $derived(data.scenario);
	const flagship = $derived(validation.oracles.find((o) => o.flagship));
	const others = $derived(validation.oracles.filter((o) => !o.flagship));

	const daInt = new Intl.NumberFormat('da-DK');
	const daSigned = new Intl.NumberFormat('da-DK', {
		minimumFractionDigits: 1,
		maximumFractionDigits: 1,
		signDisplay: 'always'
	});
	const daOne = new Intl.NumberFormat('da-DK', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
	const daTwo = new Intl.NumberFormat('da-DK', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

	/** "1,1 × 10⁻¹⁵"-style scientific notation as HTML. The superscript is for the eye;
	 *  assistive tech gets a spoken form ("1,1 gange 10 i minus 15") instead. */
	function sci(value: number): string {
		if (value === 0) return '0';
		const exponent = Math.floor(Math.log10(Math.abs(value)));
		const mantissa = (value / Math.pow(10, exponent)).toFixed(1).replace('.', ',');
		const spoken = `${mantissa} gange 10 i ${exponent < 0 ? 'minus ' : ''}${Math.abs(exponent)}`;
		return `<span aria-hidden="true">${mantissa} × 10<sup>${exponent}</sup></span><span class="sr-only">${spoken}</span>`;
	}

	/** Deviation of one series in a given year (null when the scenario is not ingested). */
	function at(key: string, year: number): number | null {
		const series = scenario?.deviations[key];
		if (!series) return null;
		const index = data.years.indexOf(year);
		return index >= 0 ? (series[index] ?? null) : null;
	}

	/** Most negative value of a series and the year it occurs. */
	function trough(key: string): { value: number; year: number } | null {
		const series = scenario?.deviations[key];
		if (!series) return null;
		let best: { value: number; year: number } | null = null;
		series.forEach((value, index) => {
			if (value !== null && (best === null || value < best.value)) best = { value, year: data.years[index] };
		});
		return best;
	}

	/** First year after `from` where |deviation| stays below `tolerance`. */
	function settles(key: string, from: number, tolerance: number): number | null {
		const series = scenario?.deviations[key];
		if (!series) return null;
		for (let index = 0; index < series.length; index++) {
			const value = series[index];
			if (data.years[index] > from && value !== null && Math.abs(value) < tolerance) return data.years[index];
		}
		return null;
	}

	const story = $derived.by(() => {
		if (!scenario) return null;
		const gdpTrough = trough('qBNP');
		const jobsTrough = trough('nL');
		return {
			gdp2030: at('qBNP', 2030),
			gdpTrough,
			gdp2100: at('qBNP', 2100),
			jobsTrough,
			jobsBack: settles('nL', 2030, 0.05),
			houses2030: at('pBolig', 2030),
			houses2050: at('pBolig', 2050),
			wages: trough('vhW'),
			balance2030: at('saldo2bnp', 2030),
			balance2050: at('saldo2bnp', 2050)
		};
	});

	function pct(value: number | null | undefined): string {
		return value === null || value === undefined ? '–' : `${daSigned.format(value)} pct.`;
	}

	function pp(value: number | null | undefined): string {
		return value === null || value === undefined ? '–' : `${daSigned.format(value)} pct.-point`;
	}

	const multipliers = $derived(data.multipliers);

	/** Rows with a note get a running footnote number in table order. */
	const multiplierNotes = $derived.by(() => {
		const notes: { id: string; marker: number; text: string }[] = [];
		for (const row of multipliers.rows) {
			if (row.noteDa !== null) notes.push({ id: row.id, marker: notes.length + 1, text: row.noteDa });
		}
		return notes;
	});

	function noteMarker(id: string): number | null {
		return multiplierNotes.find((note) => note.id === id)?.marker ?? null;
	}

	/** Multiplier with Danish decimal comma, two decimals; "–" when DREAM has no figure. */
	function mult(value: number | null | undefined): string {
		return value === null || value === undefined ? '–' : daTwo.format(value);
	}

	const dream = $derived(data.dreamComparison);

	/** Series label and DREAM unit for a comparison row. */
	function dreamSeries(key: string): { labelDa: string; unitDa: string } {
		return dream.series.find((s) => s.key === key) ?? { labelDa: key, unitDa: '' };
	}

	/** Reading or scaled value with Danish decimal comma — one decimal for persons, two for
	 *  percentages; "–" where DREAM's figure was not read. */
	function reading(value: number | null | undefined, key: string): string {
		if (value === null || value === undefined) return '–';
		const rounded = key === 'nL' ? Math.round(value * 10) / 10 : Math.round(value * 100) / 100;
		const clean = rounded === 0 ? 0 : rounded; // never "-0,0"
		return key === 'nL' ? daOne.format(clean) : daTwo.format(clean);
	}
</script>

<svelte:head>
	<title>Validering · MAKROskop</title>
</svelte:head>

<section class="intro">
	<h1>Kan man stole på tallene?</h1>
	<p class="lede">
		MAKROskops frie beregningsmotor løser MAKROs ligninger uden kommerciel software. Vi har
		efterprøvet den på to måder: ved at løse <em>præcis de samme stød-scenarier</em> med den
		officielle GAMS-platform (solveren IPOPT) og med vores egen frie Newton-løser — og ved at
		lade den frie løser genfinde modellens egen løsning for <em>alle
		{daInt.format(full.equations)} ligninger</em> over hele horisonten. Begge prøver bestås:
		forskellene ligger på computerens afrundingsniveau, det man kalder maskinpræcision.
	</p>
</section>

<div class="figures">
	<StatTile
		label="Typisk uenighed mellem de to løsere"
		value="1,1 × 10⁻¹⁵"
		note="median, relativt — maskinpræcision"
		tone="good"
	/>
	<StatTile
		label="Ligninger løst i fuld skala"
		value={daInt.format(full.equations)}
		note="hele horisonten {full.years} på én lejet server"
	/>
	<StatTile
		label="Variable der reagerede på rentestødet"
		value={daInt.format(flagship?.responders ?? 0)}
		note="alle sammenlignet én for én"
	/>
	<StatTile
		label="Enighed om selve stød-effekterne"
		value="12 cifre"
		note="median-afvigelse 2,0 × 10⁻¹² af effektens størrelse"
		tone="good"
	/>
</div>

<section class="steps">
	<h2>Sådan testede vi</h2>
	<ol>
		<li>
			<strong>Samme ligninger.</strong> MAKRO-repositoriet indeholder hele modellen i udfoldet form
			({daInt.format(validation.system.fullEquations)} ligninger). Vores motor genlæser dem tegn for
			tegn; ved modellens egen løsning er den største ligningsfejl
			{@html sci(validation.system.maxResidualAtSolution)} — ren afrundingsstøj.
		</li>
		<li>
			<strong>Samme stød, to løsere.</strong> Et veldefineret stød (fx renten +1 pct.-point i 2124)
			lægges ind i begge systemer. GAMS/IPOPT kører under en gyldig licens; den frie løser bruger
			kun open source-komponenter. Alle {daInt.format(validation.system.windowEquations)} ubekendte i
			et 10-års udsnit sammenlignes variabel for variabel — både niveauer og selve stød-effekterne.
		</li>
		<li>
			<strong>Fuld skala.</strong> På en lejet server med 64 GB hukommelse forstyrres alle
			{daInt.format(full.equations)} variable i hele modellen tilfældigt, og den frie løser skal finde
			tilbage til modellens egen løsning. Derefter løses det første rigtige scenarie over hele
			horisonten.
		</li>
	</ol>
</section>

<section class="block flagship">
	<h2>Hele modellen, hele horisonten</h2>
	<p class="shock-spec mono">
		{daInt.format(full.equations)} ligninger · {full.yearCount} år ({full.years}) · {full.machine}
	</p>
	<div class="result-grid">
		<div>
			<table class="results">
				<caption>Genfinder modellens egen løsning efter tilfældig forstyrrelse</caption>
				<tbody>
					<tr>
						<th scope="row">Forstyrrelse af alle variable</th>
						<td>±{daTwo.format(full.perturbation * 100)} pct. relativt</td>
					</tr>
					<tr>
						<th scope="row">Slutresidual, ‖fejl‖<sub>∞</sub></th>
						<td>{@html sci(full.finalResidual)}</td>
					</tr>
					<tr>
						<th scope="row">Median-afvigelse fra CONOPTs original</th>
						<td>{@html sci(full.medianRecovery)}</td>
					</tr>
					<tr>
						<th scope="row">Størst afvigelse (enkelte NPV-variable)</th>
						<td>{@html sci(full.maxRelDev)}</td>
					</tr>
					<tr>
						<th scope="row">Én faktorisering, UMFPACK</th>
						<td>{daInt.format(Math.round(full.factorSecondsUmfpack))} s</td>
					</tr>
					<tr>
						<th scope="row">Newton-iterationer</th>
						<td>{full.iterations.length - 1}</td>
					</tr>
				</tbody>
			</table>
			<p class="footnote">
				Lineære systemer løses af {validation.solver.linear}. Hver faktorisering efterprøves mod en
				kendt højreside, før den bruges; i denne kørsel blev Pardiso afvist ved iteration 4 og
				UMFPACK tog over — kæden er designet, så en tvivlsom faktorisering aldrig kommer igennem.
				Desuden: {validation.solver.refinement}.
			</p>
		</div>
		<div class="trace">
			<h3>Newton på {daInt.format(full.equations)} ligninger</h3>
			<p class="trace-note">
				Fejlen falder fra {@html sci(full.iterations[0])} til {@html sci(full.finalResidual)} på
				{full.iterations.length - 1} iterationer — samme kvadratiske signatur som i det lille udsnit.
			</p>
			<table class="results mono-table">
				<thead><tr><th scope="col">Iteration</th><th scope="col">‖fejl‖<sub>∞</sub></th></tr></thead>
				<tbody>
					{#each full.iterations as residual, i (i)}
						<tr>
							<td>{i === 0 ? 'start' : i}</td>
							<td>{@html sci(residual)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</section>

<section class="block scenario">
	<h2>Det første rigtige scenarie: {solve.labelDa}</h2>
	<p class="shock-spec mono">{solve.shock}</p>
	<div class="result-grid">
		<div>
			{#if story}
				<p class="story">
					En permanent forhøjelse af ECB-renten med ét procentpoint fra 2030 lægger BNP
					<strong>{pct(story.gdp2030)}</strong> under grundforløbet det første år og
					<strong>{pct(story.gdpTrough?.value)}</strong> på det dybeste ({story.gdpTrough?.year});
					i 2100 er afvigelsen {pct(story.gdp2100)}. Beskæftigelsen ligger
					<strong>{pct(story.jobsTrough?.value)}</strong> i {story.jobsTrough?.year} og er
					{#if story.jobsBack}tilbage ved udgangspunktet i {story.jobsBack}{:else}derefter
					stort set uændret{/if}
					— det klassiske V, fordi lønnen tilpasser sig ({pct(story.wages?.value)} på det laveste).
					Boligpriserne tager det største slag: <strong>{pct(story.houses2030)}</strong> i 2030,
					stadig {pct(story.houses2050)} i 2050. Den offentlige saldo svækkes med
					<strong>{pp(story.balance2030)}</strong> af BNP i 2030, men vender til
					{pp(story.balance2050)} i 2050 — stødet er ufinansieret, så ingen skattesats reagerer, og
					rentevirkningen på de offentlige finanser akkumulerer over tid.
				</p>
				<p class="footnote">
					Størrelsesordenerne svarer til DREAMs egne publicerede rentestød. Alle kurver kan
					udforskes under <a href="/scenarier/?stod=Rente&variant=_ufin">Scenarier</a>.
				</p>
			{:else}
				<p class="story">
					Scenariet er løst, men datafilen <code>Rente_ufin.json</code> er ikke indlæst i denne
					udgave af MAKROskop.
				</p>
			{/if}
		</div>
		<div>
			<table class="results">
				<caption>Sådan blev det løst</caption>
				<tbody>
					<tr>
						<th scope="row">Ligninger i løsningsvinduet</th>
						<td>{daInt.format(solve.windowEquations)} ({solve.windowYears})</td>
					</tr>
					<tr>
						<th scope="row">Kontinuationstrin</th>
						<td>{solve.stagesConverged} konvergerede · {solve.stagesRejected} afvist og halveret</td>
					</tr>
					<tr>
						<th scope="row">Faktoriseringer (UMFPACK)</th>
						<td>{solve.freshFactorizations} · {daOne.format(solve.factorHours)} timer</td>
					</tr>
					<tr>
						<th scope="row">Slutresidual, ‖fejl‖<sub>∞</sub></th>
						<td>{@html sci(solve.finalResidual)}</td>
					</tr>
				</tbody>
			</table>
			<div class="trace">
				<h3>{solve.lastStageLabelDa}</h3>
				<table class="results mono-table">
					<thead><tr><th scope="col">Iteration</th><th scope="col">‖fejl‖<sub>∞</sub></th></tr></thead>
					<tbody>
						{#each solve.lastStageIterations as residual, i (i)}
							<tr>
								<td>{i === 0 ? 'start' : i}</td>
								<td>{@html sci(residual)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
				<p class="trace-note">
					Iteration 1–2 lader fejlen eksplodere: det er langsigtede nutidsværdi-variable, der
					lægger sig til rette efter et fuldt Newton-skridt. Løseren accepterer det bevidst
					(ikke-monoton linjesøgning) og lander derefter på afrundingsniveau.
				</p>
			</div>
		</div>
	</div>
</section>

<section class="block multipliers">
	<h2>Sammenlignet med DREAMs egne multiplikatorer</h2>
	<p class="story">
		DREAM har offentliggjort finanspolitiske multiplikatorer for MAKRO i
		<a href={multipliers.reference.url} target="_blank" rel="noopener noreferrer"
			>Finanspolitiske multiplikatorer i MAKRO<span class="sr-only"> (åbner i nyt vindue)</span></a
		> (december 2021). {multipliers.definitionDa} Begge sæt tal gælder permanente, ufinansierede
		stød; MAKROskops stødår er {multipliers.shockYear}, mens DREAMs reference er
		{multipliers.reference.modelDa}.
	</p>
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- Focusable on purpose: the table scrolls sideways on narrow screens. -->
	<div class="table-scroll" tabindex="0" role="region" aria-label="Multiplikatorer, tabel">
		<table class="results multiplier-table">
			<thead>
				<tr>
					<th scope="col">Instrument</th>
					<th scope="col">Impuls (pct. af BNP)</th>
					<th scope="col">År 1 — MAKROskop</th>
					<th scope="col">År 1 — DREAM</th>
					<th scope="col">År 2 — MAKROskop</th>
					<th scope="col">År 2 — DREAM</th>
				</tr>
			</thead>
			<tbody>
				{#each multipliers.rows as row (row.id)}
					{@const marker = noteMarker(row.id)}
					<tr>
						<th scope="row">
							{row.labelDa}{#if marker !== null}<sup class="note-marker">{marker}</sup>{/if}
						</th>
						{#if row.ours}
							<td>{daTwo.format(row.ours.impulsePctGdp)}</td>
							<td>{daTwo.format(row.ours.year1)}</td>
							<td>{mult(row.dream.year1)}</td>
							<td>{daTwo.format(row.ours.year2)}</td>
							<td>{mult(row.dream.year2)}</td>
						{:else}
							<td>–</td>
							<td class="pending">afventer beregning</td>
							<td>{mult(row.dream.year1)}</td>
							<td class="pending">afventer beregning</td>
							<td>{mult(row.dream.year2)}</td>
						{/if}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
	{#if multiplierNotes.length > 0}
		<ol class="notes">
			{#each multiplierNotes as note (note.id)}
				<li value={note.marker}>{note.text}</li>
			{/each}
		</ol>
	{/if}
	<p class="footnote">
		<strong>Forbehold.</strong> DREAMs tal stammer fra beta-versionen fra 2021 med stødår 2026 og en
		finansierings- og lukningsopsætning, der afviger i detaljerne. Overensstemmelse inden for cirka
		±0,2 er, hvad man bør forvente; større afstande peger på forskelle i instrument eller
		konfiguration.
	</p>
	<p class="footnote">
		Kilde:
		<a href={multipliers.reference.url} target="_blank" rel="noopener noreferrer"
			>{multipliers.reference.source}<span class="sr-only"> (åbner i nyt vindue)</span></a
		>.
	</p>
</section>

<section class="block dream">
	<h2>Sammenlignet med DREAMs stød-reaktioner (maj 2025)</h2>
	<p class="story">
		I maj 2025 offentliggjorde DREAM notatet
		<a href={dream.reference.url} target="_blank" rel="noopener noreferrer"
			>Shock Reactions in MAKRO<span class="sr-only"> (åbner i nyt vindue)</span></a
		> med figurer for, hvordan {dream.reference.modelDa} reagerer på en række standardstød fra
		{dream.shockYear}. Her står de aflæste værdier ved siden af MAKROskops egne, ufinansierede
		scenarier omregnet til DREAMs enheder: beskæftigelse i 1.000 personer, eksport og privat
		forbrug i pct.-point af BNP, BNP og timeløn i pct. Hvor DREAM normaliserer stødet til 1 pct.
		af BNP, er MAKROskops tal skaleret lineært op til samme størrelse. {dream.shockYear} er
		stødåret (år 1).
	</p>
	<div class="dream-grid">
		{#each dream.shocks as shock (shock.id)}
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<!-- Focusable on purpose: the table scrolls sideways on narrow screens. -->
			<div class="table-scroll" tabindex="0" role="region" aria-label="{shock.labelDa}, sammenligning med DREAM">
				<table class="results dream-table">
					<caption>
						<strong>{shock.labelDa}</strong> · {shock.scaleNoteDa}
					</caption>
					<thead>
						<tr>
							<th scope="col">Serie</th>
							<th scope="col"><span class="sr-only">Kilde</span></th>
							{#each dream.columns as year (year)}
								<th scope="col">{year}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each shock.rows as row (row.series)}
							{@const label = dreamSeries(row.series)}
							<tr>
								<th scope="row" rowspan="2">
									{label.labelDa}<span class="unit">{label.unitDa}</span>
								</th>
								<td class="who">DREAM</td>
								{#each dream.columns as year (year)}
									<td>{reading(row.dream[String(year)], row.series)}</td>
								{/each}
							</tr>
							<tr class="ours">
								<td class="who">MAKROskop</td>
								{#each dream.columns as year (year)}
									<td>{reading(row.ours[String(year)], row.series)}</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
				{#if shock.noteDa}<p class="footnote">{shock.noteDa}</p>{/if}
			</div>
		{/each}
	</div>
	<p class="footnote">
		<strong>Forbehold.</strong> DREAMs tal er {dream.reference.methodDa}, og notatet bygger på
		{dream.reference.modelDa}, mens MAKROskop regner på juni 2026-versionen. Den lineære
		opskalering er en tilnærmelse: MAKRO er tæt på lineær for små stød, men for de offentlige
		varekøb (faktor 11,8) og den offentlige beskæftigelse (faktor 6,6) er den grov. Forskelle på
		10–40 pct. bør derfor ikke overfortolkes; systematiske forskelle i forløbet over tid — fx hvor
		hurtigt beskæftigelsen vender tilbage — er mere sigende.
	</p>
	<p class="footnote">
		Kilde:
		<a href={dream.reference.url} target="_blank" rel="noopener noreferrer"
			>{dream.reference.source}<span class="sr-only"> (åbner i nyt vindue)</span></a
		>.
	</p>
</section>

{#if flagship}
	<section class="block oracle">
		<h2>To løsere, samme svar: {flagship.labelDa}</h2>
		<p class="shock-spec mono">{flagship.shock} · 10-års udsnit {validation.system.windowYears}</p>
		<div class="result-grid">
			<table class="results">
				<caption>Uenighed mellem løserne, {daInt.format(validation.system.windowEquations)} variable</caption>
				<tbody>
					<tr>
						<th scope="row">Median (relativt)</th>
						<td>{@html sci(flagship.medianRel)}</td>
					</tr>
					<tr>
						<th scope="row">99,9-percentil</th>
						<td>{@html sci(flagship.p999Rel)}</td>
					</tr>
					<tr>
						<th scope="row">Størst (IPOPTs egen tolerance)</th>
						<td>{@html sci(flagship.maxRel)}</td>
					</tr>
					<tr>
						<th scope="row">Stød-effekter, median-afvigelse</th>
						<td>{@html sci(flagship.irfMedian ?? 0)} af effekten</td>
					</tr>
					<tr>
						<th scope="row">GAMS/IPOPT</th>
						<td>{flagship.gams.seconds}s · {flagship.gams.status}</td>
					</tr>
					<tr>
						<th scope="row">Fri løser, slutresidual</th>
						<td>{@html sci(flagship.free.finalResidual)}</td>
					</tr>
				</tbody>
			</table>

			{#if flagship.trace}
				<div class="trace">
					<h3>{flagship.trace.labelDa}</h3>
					<p class="trace-note">
						Newtons metode må midlertidigt lade fejlen vokse (skridt 1) — derefter falder den
						kvadratisk mod nul. Det er signaturen på en korrekt løsning, ikke en tilnærmelse.
					</p>
					<table class="results mono-table">
						<thead><tr><th scope="col">Iteration</th><th scope="col">‖fejl‖<sub>∞</sub></th></tr></thead>
						<tbody>
							{#each flagship.trace.iterations as residual, i (i)}
								<tr>
									<td>{i === 0 ? 'start' : i}</td>
									<td>{@html sci(residual)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</section>
{/if}

<div class="minor-grid">
	{#each others as oracle (oracle.id)}
		<section class="block">
			<h2 class="minor-title">{oracle.labelDa}</h2>
			<p class="shock-spec mono">{oracle.shock}</p>
			<table class="results">
				<tbody>
					<tr>
						<th scope="row">Median-uenighed</th>
						<td>{@html sci(oracle.medianRel)}</td>
					</tr>
					<tr>
						<th scope="row">99,9-percentil</th>
						<td>{@html sci(oracle.p999Rel)}</td>
					</tr>
					<tr>
						<th scope="row">Fri løser</th>
						<td>{oracle.free.note}</td>
					</tr>
				</tbody>
			</table>
			{#if oracle.noteDa}<p class="footnote">{oracle.noteDa}</p>{/if}
		</section>
	{/each}

	<section class="block">
		<h2 class="minor-title">Genfinder løsningen i udsnittet</h2>
		<p class="shock-spec">
			Alle {daInt.format(validation.system.windowEquations)} variable forstyrres tilfældigt på en
			bærbar; Newton skal finde tilbage.
		</p>
		<table class="results mono-table">
			<thead><tr><th scope="col">Iteration</th><th scope="col">‖fejl‖<sub>∞</sub></th></tr></thead>
			<tbody>
				{#each validation.recovery.iterations as residual, i (i)}
					<tr>
						<td>{i === 0 ? 'start' : i}</td>
						<td>{@html sci(residual)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="footnote">
			Løsningen genfindes med median-afvigelse {@html sci(validation.recovery.medianRecovery)} fra
			CONOPTs original.
		</p>
	</section>
</div>

<section class="block caveats">
	<h2>Forbehold — læs dem</h2>
	<ul>
		<li>
			Krydstjekket mod GAMS/IPOPT er kørt på et 10-års udsnit ({validation.system.windowYears}) på
			en almindelig bærbar. I fuld skala har vi kun den frie løsers egen kontrol (genfinding af
			modellens løsning til {@html sci(full.medianRecovery)}); en GAMS-løsning af samme
			fuld-horisont-scenarie kræver licens og mange timer og er ikke gjort.
		</li>
		<li>
			Rentescenariet er et rigtigt scenarie, men afvigelserne måles mod modellens
			kalibreringsforløb — ikke DREAMs officielle grundforløb, som ikke kan genskabes uden
			licenseret software. Til marginale eksperimenter gør det ingen forskel; tallene bør
			ikke citeres som "Finansministeriets".
		</li>
		<li>
			Kolonnen "størst" i to-løser-testen afspejler IPOPTs stop-tolerance, ikke den frie løsers
			præcision; den frie løsers egne residualer er 100-1000 gange strammere. I fuld skala er
			de største afvigelser nutidsværdi-variable langt ude i horisonten, som er dårligt bestemte
			i selve modellen.
		</li>
		<li>
			Maskiner: {validation.machine}. Alt kan efterprøves: koden er open source, og MAKRO-modellen
			er MIT-licenseret. Reproduktion: <code>{validation.reproduce}</code>.
		</li>
	</ul>
</section>

<style>
	.figures {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		border-top: 1px solid var(--rule-strong);
		border-bottom: 1px solid var(--rule);
		margin: 32px 0 36px;
	}

	.figures > :global(.figure:first-child) {
		padding-left: 0;
	}

	.figures > :global(.figure:last-child) {
		border-right: 0;
		padding-right: 0;
	}

	@media (max-width: 1100px) {
		.figures {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.figures > :global(.figure:nth-child(2n)) {
			border-right: 0;
			padding-right: 0;
		}
		.figures > :global(.figure:nth-child(2n + 1)) {
			padding-left: 0;
		}
	}

	@media (max-width: 600px) {
		.figures {
			grid-template-columns: 1fr;
		}
		.figures > :global(.figure) {
			border-right: 0;
			padding: 14px 0;
			border-top: 1px solid var(--rule);
		}
		.figures > :global(.figure:first-child) {
			border-top: 0;
		}
	}

	.steps {
		margin-bottom: 36px;
		max-width: 80ch;
	}

	.steps h2 {
		margin-bottom: 12px;
	}

	.steps ol {
		margin: 0;
		padding-left: 22px;
		color: var(--ink-secondary);
		font-size: 14.5px;
		display: grid;
		gap: 10px;
	}

	.steps strong {
		color: var(--ink);
	}

	.block {
		border-top: 1px solid var(--rule-strong);
		padding-top: 18px;
		margin-bottom: 36px;
	}

	.block h2 {
		margin-bottom: 8px;
	}

	.flagship {
		border-top: 3px solid var(--makro);
	}

	.scenario {
		border-top: 3px solid var(--series-1);
	}

	.minor-title {
		font-size: 19px;
	}

	.story {
		font-size: 15px;
		color: var(--ink-secondary);
		margin: 0;
		line-height: 1.6;
		max-width: 68ch;
	}

	.story strong {
		color: var(--ink);
		font-variant-numeric: tabular-nums;
	}

	.shock-spec {
		color: var(--ink-muted);
		font-size: 12px;
		margin: 0 0 16px;
	}

	.result-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 36px;
	}

	@media (max-width: 700px) {
		.result-grid {
			grid-template-columns: 1fr;
		}
	}

	table.results {
		width: 100%;
		border-collapse: collapse;
		font-size: 13.5px;
	}

	table.results caption {
		text-align: left;
		font-size: 12px;
		color: var(--ink-muted);
		margin-bottom: 6px;
	}

	table.results th {
		text-align: left;
		font-weight: 400;
		color: var(--ink-secondary);
		padding: 6px 10px 6px 0;
		border-bottom: 1px solid var(--rule);
	}

	table.results td {
		text-align: right;
		font-variant-numeric: tabular-nums;
		font-weight: 600;
		color: var(--ink);
		padding: 6px 0;
		border-bottom: 1px solid var(--rule);
		white-space: nowrap;
	}

	.multipliers .story {
		max-width: 72ch;
		margin-bottom: 16px;
	}

	.table-scroll {
		overflow-x: auto;
	}

	.multiplier-table {
		min-width: 560px;
	}

	.multiplier-table th,
	.multiplier-table td {
		padding: 7px 14px 7px 0;
	}

	.multiplier-table thead th {
		font-size: 12px;
		color: var(--ink-muted);
		vertical-align: bottom;
		border-bottom-color: var(--rule-strong);
	}

	.multiplier-table thead th:not(:first-child),
	.multiplier-table td {
		text-align: right;
	}

	.multiplier-table tbody th {
		color: var(--ink);
		white-space: nowrap;
	}

	.multiplier-table td:last-child,
	.multiplier-table th:last-child {
		padding-right: 0;
	}

	.multiplier-table .pending {
		font-weight: 400;
		font-style: italic;
		color: var(--ink-secondary);
	}

	.note-marker {
		font-size: 10px;
		margin-left: 2px;
		color: var(--ink-muted);
	}

	.dream .story {
		max-width: 72ch;
		margin-bottom: 16px;
	}

	.dream-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(560px, 1fr));
		column-gap: 36px;
		row-gap: 24px;
	}

	@media (max-width: 640px) {
		.dream-grid {
			grid-template-columns: 1fr;
		}
	}

	.dream-table {
		min-width: 560px;
	}

	.dream-table caption {
		color: var(--ink-secondary);
		font-size: 12.5px;
	}

	.dream-table caption strong {
		color: var(--ink);
	}

	.dream-table th,
	.dream-table td {
		padding: 5px 10px 5px 0;
		font-size: 12.5px;
	}

	.dream-table thead th {
		font-size: 11px;
		color: var(--ink-muted);
		vertical-align: bottom;
		border-bottom-color: var(--rule-strong);
	}

	.dream-table thead th:nth-child(n + 3),
	.dream-table td:nth-child(n + 2) {
		text-align: right;
	}

	.dream-table tbody th {
		color: var(--ink);
		white-space: nowrap;
		vertical-align: top;
		border-bottom-color: var(--rule);
	}

	.dream-table tbody th .unit {
		display: block;
		font-size: 11px;
		color: var(--ink-muted);
	}

	.dream-table tr:not(.ours) td {
		border-bottom: 0;
		padding-bottom: 1px;
	}

	.dream-table tr.ours td {
		padding-top: 1px;
	}

	.dream-table td.who {
		text-align: left;
		font-weight: 400;
		font-size: 11px;
		color: var(--ink-muted);
	}

	.dream-table tr:not(.ours) td:not(.who) {
		font-weight: 400;
		color: var(--ink-secondary);
	}

	.dream-table td:last-child,
	.dream-table th:last-child {
		padding-right: 0;
	}

	.notes {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 10px 0 0;
		padding-left: 18px;
		display: grid;
		gap: 3px;
	}

	.mono-table td,
	.mono-table th {
		font-family: var(--font-mono);
		font-size: 12.5px;
	}

	.mono-table thead th {
		font-weight: 500;
		font-size: 11px;
		color: var(--ink-muted);
	}

	.trace h3 {
		font-family: var(--font-body);
		font-weight: 600;
		font-size: 13px;
		margin-bottom: 4px;
	}

	.scenario .trace {
		margin-top: 16px;
	}

	.trace-note {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 0 0 8px;
	}

	.trace .mono-table + .trace-note {
		margin: 8px 0 0;
	}

	.minor-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		column-gap: 36px;
		margin-bottom: 0;
	}

	.minor-grid .block {
		border-top-width: 1px;
	}

	.footnote {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 10px 0 0;
		max-width: 80ch;
	}

	.caveats ul {
		margin: 0;
		padding-left: 20px;
		color: var(--ink-secondary);
		font-size: 14px;
		display: grid;
		gap: 6px;
	}

	.caveats code {
		color: var(--makro-strong);
		font-size: 12px;
	}
</style>
