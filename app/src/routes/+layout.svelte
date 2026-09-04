<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';

	let { children, data } = $props();

	/** Nav entries double as the per-page <meta name="description">, so each page gets
	 *  one description and the layout never emits a duplicate tag. */
	const links = [
		{
			href: '/',
			label: 'Grundforløb',
			description:
				'MAKROs grundforløb for dansk økonomi: BNP, beskæftigelse, priser, offentlige finanser og renter – historiske data og modelfremskrivning frem til 2100.'
		},
		{
			href: '/scenarier/',
			label: 'Scenarier',
			description:
				'Hvad sker der i MAKRO, hvis bundskatten ændres, det offentlige forbrug stiger eller renten hæves? Modellens standardstød vist som afvigelser fra grundforløbet.'
		},
		{
			href: '/pakke/',
			label: 'Pakker',
			description:
				'Sæt flere standardstød sammen til én politikpakke og se, hvad MAKRO siger om BNP, beskæftigelse og de offentlige finanser – med prisen i kroner.'
		},
		{
			href: '/validering/',
			label: 'Validering',
			description:
				'Kan man stole på tallene? MAKROskops frie løser er efterprøvet mod GAMS/IPOPT på de samme stød og ved at genfinde løsningen for alle modellens ligninger.'
		}
	];

	/** Public origin, for tags that must be absolute (og:image). */
	const SITE_URL = 'https://makroskop.nodalit.com';

	const REPO_URL = 'https://github.com/huulbaek/makroskop';

	const SITE_DESCRIPTION =
		'MAKROskop er en fri, licensløs udgave af MAKRO – den makroøkonomiske model bag Finansministeriets regnestykker: grundforløb, stød-scenarier og politikpakker.';

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href.replace(/\/$/, ''));
	}

	const current = $derived(links.find((link) => isActive(link.href)));
	const description = $derived(current?.description ?? SITE_DESCRIPTION);
	const ogTitle = $derived(current ? `${current.label} · MAKROskop` : 'MAKROskop – udforsk MAKRO uden licens');

	let main: HTMLElement | undefined = $state();

	/** Skip link: move focus into <main> without touching the URL (the pages keep their own query). */
	function skipToContent(event: MouseEvent) {
		event.preventDefault();
		main?.focus();
		main?.scrollIntoView({ block: 'start' });
	}
</script>

<svelte:head>
	<title>MAKROskop</title>
	<meta name="description" content={description} />
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="MAKROskop" />
	<meta property="og:title" content={ogTitle} />
	<meta property="og:description" content={description} />
	<meta property="og:image" content="{SITE_URL}/og.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta
		property="og:image:alt"
		content="MAKROskop: Dansk økonomi, beregnet et århundrede frem – kurve for realt BNP 1985–2100 fra MAKROs grundforløb."
	/>
	<meta property="og:locale" content="da_DK" />
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="theme-color" content="#14AFA6" />
</svelte:head>

<a class="skip-link" href="#indhold" onclick={skipToContent}>Spring til indhold</a>

<div class="shell">
	<header>
		<a class="wordmark" href="/">MAKRO<span>skop</span></a>
		<nav aria-label="Hovednavigation">
			{#each links as link (link.href)}
				<a href={link.href} class:active={isActive(link.href)} aria-current={isActive(link.href) ? 'page' : undefined}>
					{link.label}
				</a>
			{/each}
		</nav>
		<div class="tools">
			<ThemeToggle />
			<a class="repo" href={REPO_URL} rel="external" aria-label="Kildekode på GitHub">
				<svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" focusable="false">
					<path
						d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"
					/>
				</svg>
			</a>
		</div>
	</header>

	<main id="indhold" tabindex="-1" bind:this={main}>
		{@render children()}
	</main>

	<footer>
		<p class="about">
			Bygget på <a href="https://github.com/DREAM-DK/MAKRO" rel="external">MAKRO</a>, den makroøkonomiske
			model udviklet af DREAM-gruppen til Finansministeriet m.fl. Grundforløbet er stiliseret og egner sig
			kun til marginale eksperimenter, ikke som prognose. MAKROskop er en uafhængig prototype og ikke et
			produkt fra DREAM eller Finansministeriet.
		</p>
		<dl class="stamp">
			<dt>Model</dt>
			<dd class="mono">{data.meta.model.name} {data.meta.model.commit}</dd>
			<dt>Sidste dataår</dt>
			<dd class="mono">{data.meta.lastDataYear}</dd>
			<dt>MAKROskop</dt>
			<dd class="mono">{__APP_COMMIT__ ? `${__APP_COMMIT__}, ` : ''}bygget {__BUILD_DATE__}</dd>
		</dl>
	</footer>
</div>

<style>
	.shell {
		/* 1440px frame, 80px gutters → 1280px content width shared by every section */
		max-width: 1440px;
		margin: 0 auto;
		padding: 0 clamp(20px, 5.5vw, 80px);
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
	}

	header {
		display: flex;
		align-items: stretch;
		gap: 24px;
		height: 64px;
		border-bottom: 1px solid var(--rule);
	}

	.wordmark {
		display: flex;
		align-items: center;
		font-family: var(--font-display);
		font-weight: 500;
		font-size: 25px;
		letter-spacing: -0.01em;
		color: var(--ink);
	}

	.wordmark span {
		color: var(--makro-strong);
		font-style: italic;
	}

	.wordmark,
	.wordmark:hover {
		text-decoration: none;
	}

	/* Off-screen until it receives focus; then a small tab at the top-left of the page. */
	.skip-link {
		position: absolute;
		top: 8px;
		left: 8px;
		z-index: 10;
		padding: 8px 14px;
		background: var(--ink);
		color: var(--page);
		font-size: 14px;
		font-weight: 500;
		text-decoration: none;
		border-radius: var(--radius);
		transform: translateY(-200%);
	}

	.skip-link:focus-visible {
		transform: none;
		outline-color: var(--makro);
	}

	nav {
		display: flex;
		gap: 26px;
		margin-left: auto;
	}

	nav a {
		display: flex;
		align-items: center;
		font-size: 14.5px;
		font-weight: 500;
		color: var(--ink-secondary);
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		text-decoration: none;
		transition: color 0.12s;
	}

	nav a:hover {
		color: var(--ink);
	}

	nav a.active {
		color: var(--ink);
		border-bottom-color: var(--makro);
	}

	/* theme toggle + repo link: quiet icons behind a hairline, right of the nav */
	.tools {
		display: flex;
		align-items: center;
		gap: 6px;
		padding-left: 18px;
		border-left: 1px solid var(--rule);
		margin: 16px 0;
	}

	.repo {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		color: var(--ink-secondary);
		text-decoration: none;
		transition: color 0.12s;
	}

	.repo:hover {
		color: var(--ink);
		text-decoration: none;
	}

	.repo svg {
		fill: currentColor;
	}

	main {
		flex: 1;
		padding: 40px 0 0;
	}

	/* The skip link lands here; <main> is a landmark, not a control, so no ring around the page. */
	main:focus {
		outline: none;
	}

	footer {
		border-top: 1px solid var(--rule-strong);
		margin-top: 96px;
		padding: 32px 0 36px;
		font-size: 13px;
		line-height: 1.6;
		color: var(--ink-muted);
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 48px;
	}

	.about {
		margin: 0;
		max-width: 520px;
	}

	.stamp {
		margin: 0;
		display: grid;
		grid-template-columns: max-content 1fr;
		column-gap: 32px;
		row-gap: 6px;
		align-content: start;
		justify-self: end;
	}

	.stamp dt {
		margin: 0;
		color: var(--ink-muted);
	}

	.stamp dd {
		margin: 0;
		color: var(--ink-secondary);
	}

	@media (max-width: 1100px) {
		footer {
			grid-template-columns: 1fr;
			gap: 24px;
		}
		.stamp {
			justify-self: start;
		}
	}

	@media (max-width: 700px) {
		/* two rows: wordmark + tools, then the nav on its own line */
		header {
			height: auto;
			flex-wrap: wrap;
			align-items: center;
			padding: 12px 0 0;
			gap: 0 12px;
		}
		nav {
			flex-basis: 100%;
			order: 3;
			margin-left: 0;
			gap: 18px;
		}
		.tools {
			margin: 0 0 0 auto;
			padding-left: 0;
			border-left: 0;
		}
		nav a {
			padding: 6px 0 10px;
		}
		main {
			padding-top: 28px;
		}
		footer {
			margin-top: 64px;
		}
	}
</style>
