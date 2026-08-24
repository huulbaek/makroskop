<script lang="ts">
	import StatTile from '$lib/components/StatTile.svelte';

	let { data } = $props();

	const validation = $derived(data.validation);
	const flagship = $derived(validation.oracles.find((o) => o.flagship));
	const others = $derived(validation.oracles.filter((o) => !o.flagship));

	const daInt = new Intl.NumberFormat('da-DK');

	/** "1,1 × 10⁻¹⁵"-style scientific notation parts. */
	function sci(value: number): { mantissa: string; exponent: number } {
		if (value === 0) return { mantissa: '0', exponent: 0 };
		const exponent = Math.floor(Math.log10(Math.abs(value)));
		const mantissa = value / Math.pow(10, exponent);
		return { mantissa: mantissa.toFixed(1).replace('.', ','), exponent };
	}
</script>

<svelte:head>
	<title>Validering · MAKROskop</title>
</svelte:head>

<section class="intro">
	<p class="eyebrow">Uafhængig kontrol · {validation.model.name}</p>
	<h1>Kan man stole på tallene?</h1>
	<p class="lede">
		MAKROskops frie beregningsmotor løser MAKROs ligninger uden kommerciel software. For at
		efterprøve den har vi løst <em>præcis de samme stød-scenarier</em> med to uafhængige værktøjer:
		den officielle GAMS-platform (solveren IPOPT) og vores egen frie Newton-løser. Hvis begge
		regner rigtigt, skal de nå frem til samme svar — og det gør de.
	</p>
</section>

<div class="tiles">
	<StatTile
		label="Typisk uenighed mellem de to løsere"
		value="1,1 × 10⁻¹⁵"
		note="median, relativt — maskinpræcision"
		tone="good"
	/>
	<StatTile
		label="Ligninger i testsystemet"
		value={daInt.format(validation.system.windowEquations)}
		note="10-års udsnit ({validation.system.windowYears}) af MAKROs {daInt.format(validation.system.fullEquations)} ligninger"
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

<section class="method card">
	<h2>Sådan testede vi</h2>
	<ol>
		<li>
			<strong>Samme ligninger.</strong> MAKRO-repositoriet indeholder hele modellen i udfoldet form
			({daInt.format(validation.system.fullEquations)} ligninger). Vores motor genlæser dem tegn for
			tegn; ved modellens egen løsning er den største ligningsfejl
			{@html `${sci(validation.system.maxResidualAtSolution).mantissa} × 10<sup>${sci(validation.system.maxResidualAtSolution).exponent}</sup>`}
			— ren afrundingsstøj.
		</li>
		<li>
			<strong>Samme stød, to løsere.</strong> Et veldefineret stød (fx renten +1 pct.-point i 2124)
			lægges ind i begge systemer. GAMS/IPOPT kører under en gyldig licens; den frie løser bruger
			kun open source-komponenter.
		</li>
		<li>
			<strong>Sammenlign alt.</strong> Alle {daInt.format(validation.system.windowEquations)}
			ubekendte sammenlignes variabel for variabel — både niveauer og selve stød-effekterne
			(afvigelsen fra grundforløbet, det tal en artikel ville citere).
		</li>
	</ol>
</section>

{#if flagship}
	<section class="card flagship">
		<h2>{flagship.labelDa}</h2>
		<p class="shock-spec mono">{flagship.shock}</p>
		<div class="result-grid">
			<table class="results">
				<caption>Uenighed mellem løserne, {daInt.format(validation.system.windowEquations)} variable</caption>
				<tbody>
					<tr>
						<th>Median (relativt)</th>
						<td>{@html `${sci(flagship.medianRel).mantissa} × 10<sup>${sci(flagship.medianRel).exponent}</sup>`}</td>
					</tr>
					<tr>
						<th>99,9-percentil</th>
						<td>{@html `${sci(flagship.p999Rel).mantissa} × 10<sup>${sci(flagship.p999Rel).exponent}</sup>`}</td>
					</tr>
					<tr>
						<th>Størst (IPOPTs egen tolerance)</th>
						<td>{@html `${sci(flagship.maxRel).mantissa} × 10<sup>${sci(flagship.maxRel).exponent}</sup>`}</td>
					</tr>
					<tr>
						<th>Stød-effekter, median-afvigelse</th>
						<td>{@html `${sci(flagship.irfMedian ?? 0).mantissa} × 10<sup>${sci(flagship.irfMedian ?? 0).exponent}</sup>`} af effekten</td>
					</tr>
					<tr>
						<th>GAMS/IPOPT</th>
						<td>{flagship.gams.seconds}s · {flagship.gams.status}</td>
					</tr>
					<tr>
						<th>Fri løser, slutresidual</th>
						<td>{@html `${sci(flagship.free.finalResidual).mantissa} × 10<sup>${sci(flagship.free.finalResidual).exponent}</sup>`}</td>
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
						<thead><tr><th>Iteration</th><th>‖fejl‖<sub>∞</sub></th></tr></thead>
						<tbody>
							{#each flagship.trace.iterations as residual, i (i)}
								<tr>
									<td>{i === 0 ? 'start' : i}</td>
									<td>{@html `${sci(residual).mantissa} × 10<sup>${sci(residual).exponent}</sup>`}</td>
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
		<section class="card">
			<h2 class="minor-title">{oracle.labelDa}</h2>
			<p class="shock-spec mono">{oracle.shock}</p>
			<table class="results">
				<tbody>
					<tr>
						<th>Median-uenighed</th>
						<td>{@html `${sci(oracle.medianRel).mantissa} × 10<sup>${sci(oracle.medianRel).exponent}</sup>`}</td>
					</tr>
					<tr>
						<th>99,9-percentil</th>
						<td>{@html `${sci(oracle.p999Rel).mantissa} × 10<sup>${sci(oracle.p999Rel).exponent}</sup>`}</td>
					</tr>
					<tr>
						<th>Fri løser</th>
						<td>{oracle.free.note}</td>
					</tr>
				</tbody>
			</table>
			{#if oracle.noteDa}<p class="footnote">{oracle.noteDa}</p>{/if}
		</section>
	{/each}

	<section class="card">
		<h2 class="minor-title">Genfinder modellens egen løsning</h2>
		<p class="shock-spec">
			Alle {daInt.format(validation.system.windowEquations)} variable forstyrres tilfældigt; Newton
			skal finde tilbage.
		</p>
		<table class="results mono-table">
			<thead><tr><th>Iteration</th><th>‖fejl‖<sub>∞</sub></th></tr></thead>
			<tbody>
				{#each validation.recovery.iterations as residual, i (i)}
					<tr>
						<td>{i === 0 ? 'start' : i}</td>
						<td>{@html `${sci(residual).mantissa} × 10<sup>${sci(residual).exponent}</sup>`}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="footnote">
			Løsningen genfindes med median-afvigelse
			{@html `${sci(validation.recovery.medianRecovery).mantissa} × 10<sup>${sci(validation.recovery.medianRecovery).exponent}</sup>`}
			fra CONOPTs original.
		</p>
	</section>
</div>

<section class="card caveats">
	<h2>Forbehold — læs dem</h2>
	<ul>
		<li>
			Testene er kørt på et 10-års udsnit af modellen ({validation.system.windowYears}), fordi
			testmaskinen er en almindelig bærbar ({validation.machine}). Fuldt 100-års horisont kræver
			mere hukommelse og er næste skridt.
		</li>
		<li>
			Stødene er matematiske testscenarier — ikke DREAMs officielle standardstød. Sammenligning mod
			DREAMs publicerede stød-rapporter kommer, når fuld horisont er på plads.
		</li>
		<li>
			Kolonnen "størst" afspejler IPOPTs stop-tolerance, ikke den frie løsers præcision; den frie
			løsers egne residualer er 100-1000 gange strammere.
		</li>
		<li>
			Alt kan efterprøves: koden er open source, og MAKRO-modellen er MIT-licenseret. Reproduktion:
			<code>{validation.reproduce}</code>.
		</li>
	</ul>
</section>

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
		max-width: 62ch;
		margin: 10px 0 0;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 10px;
		margin: 22px 0;
	}

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 10px;
		padding: 16px 18px;
		margin-bottom: 14px;
	}

	.card h2 {
		font-size: 18px;
		margin-bottom: 8px;
	}

	.minor-title {
		font-size: 15px;
	}

	.method ol {
		margin: 0;
		padding-left: 20px;
		color: var(--ink-secondary);
		font-size: 14px;
		display: grid;
		gap: 8px;
	}

	.method strong {
		color: var(--ink);
	}

	.flagship {
		border-color: var(--makro);
	}

	.shock-spec {
		color: var(--ink-muted);
		font-size: 12px;
		margin: 0 0 12px;
	}

	.result-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 20px;
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
		padding: 5px 10px 5px 0;
		border-bottom: 1px solid var(--grid);
	}

	table.results td {
		text-align: right;
		font-variant-numeric: tabular-nums;
		font-weight: 600;
		color: var(--ink);
		padding: 5px 0;
		border-bottom: 1px solid var(--grid);
		white-space: nowrap;
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
		font-size: 13px;
		margin-bottom: 4px;
	}

	.trace-note {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 0 0 8px;
	}

	.minor-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 14px;
		margin-bottom: 14px;
	}

	.minor-grid .card {
		margin-bottom: 0;
	}

	.footnote {
		font-size: 12px;
		color: var(--ink-muted);
		margin: 8px 0 0;
	}

	.caveats ul {
		margin: 0;
		padding-left: 20px;
		color: var(--ink-secondary);
		font-size: 13.5px;
		display: grid;
		gap: 6px;
	}

	.caveats code {
		color: var(--makro-strong);
		background: var(--makro-wash);
		padding: 1px 5px;
		border-radius: 3px;
		font-size: 12px;
	}
</style>
