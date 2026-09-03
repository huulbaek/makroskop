<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { children, data } = $props();

	const links = [
		{ href: '/', label: 'Grundforløb' },
		{ href: '/scenarier/', label: 'Scenarier' },
		{ href: '/pakke/', label: 'Pakker' },
		{ href: '/validering/', label: 'Validering' }
	];

	function isActive(href: string): boolean {
		if (href === '/') return page.url.pathname === '/';
		return page.url.pathname.startsWith(href.replace(/\/$/, ''));
	}

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
	<meta
		name="description"
		content="Udforsk dansk økonomi gennem MAKRO – den makroøkonomiske model bag Finansministeriets regnestykker."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="MAKROskop" />
	<meta property="og:title" content="MAKROskop – udforsk MAKRO uden licens" />
	<meta
		property="og:description"
		content="Grundforløb, stød-scenarier og en uafhængig validering af DREAMs makroøkonomiske model MAKRO – beregnet med en fri løser."
	/>
	<meta property="og:locale" content="da_DK" />
	<meta name="twitter:card" content="summary" />
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
		justify-content: space-between;
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
		header {
			height: auto;
			flex-direction: column;
			align-items: flex-start;
			padding: 12px 0 0;
			gap: 6px;
		}
		nav {
			gap: 18px;
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
