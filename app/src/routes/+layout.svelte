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

	<main>
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
			<div>
				<dt>Model</dt>
				<dd class="mono">{data.meta.model.name} {data.meta.model.commit}</dd>
			</div>
			<div>
				<dt>Sidste dataår</dt>
				<dd class="mono">{data.meta.lastDataYear}</dd>
			</div>
			<div>
				<dt>MAKROskop</dt>
				<dd class="mono">{__APP_COMMIT__ ? `${__APP_COMMIT__}, ` : ''}bygget {__BUILD_DATE__}</dd>
			</div>
		</dl>
	</footer>
</div>

<style>
	.shell {
		max-width: 1180px;
		margin: 0 auto;
		padding: 0 24px;
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
		border-top: 3px solid var(--ink);
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

	.wordmark:hover {
		text-decoration: none;
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
		transition: color 0.12s;
	}

	nav a:hover {
		text-decoration: none;
		color: var(--ink);
	}

	nav a.active {
		color: var(--ink);
		border-bottom-color: var(--makro);
	}

	main {
		flex: 1;
		padding: 40px 0 64px;
	}

	footer {
		border-top: 1px solid var(--rule-strong);
		padding: 22px 0 36px;
		font-size: 12.5px;
		line-height: 1.5;
		color: var(--ink-muted);
		display: grid;
		grid-template-columns: minmax(0, 64ch) auto;
		justify-content: space-between;
		gap: 24px 48px;
	}

	.about {
		margin: 0;
	}

	.stamp {
		margin: 0;
		display: grid;
		gap: 6px;
		font-size: 11.5px;
		align-content: start;
	}

	.stamp div {
		display: grid;
		grid-template-columns: 90px auto;
		gap: 12px;
	}

	.stamp dt {
		color: var(--ink-muted);
	}

	.stamp dd {
		margin: 0;
		color: var(--ink-secondary);
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
			grid-template-columns: 1fr;
		}
	}
</style>
