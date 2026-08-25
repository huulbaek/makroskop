<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { children, data } = $props();

	const links = [
		{ href: '/', label: 'Grundforløb' },
		{ href: '/scenarier/', label: 'Scenarier' },
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
		<a class="wordmark" href="/">
			MAKRO<span>skop</span>
		</a>
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
		<p>
			Bygget på <a href="https://github.com/DREAM-DK/MAKRO" rel="external">MAKRO</a> – den makroøkonomiske
			model udviklet af DREAM-gruppen til Finansministeriet m.fl. Grundforløbet er stiliseret og egner sig
			kun til marginale eksperimenter, ikke som prognose. MAKROskop er en uafhængig prototype og ikke et
			produkt fra DREAM eller Finansministeriet.
		</p>
		<p class="stamp mono">
			{data.meta.model.name} · {data.meta.model.commit} · sidste dataår {data.meta.lastDataYear}
			<span class="sep">·</span> MAKROskop{__APP_COMMIT__ ? ` ${__APP_COMMIT__}` : ''} · bygget {__BUILD_DATE__}
		</p>
	</footer>
</div>

<style>
	.shell {
		max-width: 1120px;
		margin: 0 auto;
		padding: 0 20px;
		display: flex;
		flex-direction: column;
		min-height: 100vh;
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 18px 0 14px;
		border-bottom: 1px solid var(--border);
	}

	.wordmark {
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 20px;
		letter-spacing: -0.02em;
		color: var(--ink);
	}

	.wordmark span {
		color: var(--makro);
	}

	.wordmark:hover {
		text-decoration: none;
	}

	nav {
		display: flex;
		gap: 4px;
	}

	nav a {
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 14px;
		color: var(--ink-secondary);
	}

	nav a:hover {
		text-decoration: none;
		background: var(--makro-wash);
		color: var(--ink);
	}

	nav a.active {
		background: var(--makro-wash);
		color: var(--makro-strong);
		font-weight: 600;
	}

	main {
		flex: 1;
		padding: 24px 0 48px;
	}

	footer {
		border-top: 1px solid var(--border);
		padding: 18px 0 28px;
		font-size: 12px;
		color: var(--ink-muted);
		max-width: 72ch;
	}

	footer p {
		margin: 0 0 6px;
	}

	.stamp {
		font-size: 11px;
	}

	.sep {
		margin: 0 4px;
		opacity: 0.6;
	}
</style>
