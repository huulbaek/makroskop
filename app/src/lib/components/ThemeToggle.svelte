<script lang="ts">
	import { browser } from '$app/environment';
	import { STORAGE_KEY, otherTheme, resolveTheme, type Theme } from '$lib/theme';

	/** <html data-theme> is the single source of truth; app.html sets it before first paint. */
	function current(): Theme {
		return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light';
	}

	function apply(theme: Theme) {
		document.documentElement.dataset.theme = theme;
		active = theme;
	}

	function storedChoice(): string | null {
		try {
			return localStorage.getItem(STORAGE_KEY);
		} catch {
			return null;
		}
	}

	// Prerendered as light; on the client it starts from the attribute so the label is right
	// from the first frame. The icons are switched by CSS on the same attribute.
	let active = $state<Theme>(browser ? current() : 'light');

	function toggle() {
		const next = otherTheme(active);
		apply(next);
		try {
			localStorage.setItem(STORAGE_KEY, next);
		} catch {
			/* private mode: the choice lasts for this page view only */
		}
	}

	// Keep following the OS while the visitor has not chosen; app.html only runs once.
	$effect(() => {
		const query = matchMedia('(prefers-color-scheme: dark)');
		const follow = () => apply(resolveTheme(storedChoice(), query.matches));
		query.addEventListener('change', follow);
		return () => query.removeEventListener('change', follow);
	});
</script>

<button
	type="button"
	class="theme-toggle"
	onclick={toggle}
	aria-label={active === 'dark' ? 'Skift til lyst tema' : 'Skift til mørkt tema'}
>
	<!-- moon: shown in light mode (the action is "go dark"); sun: shown in dark mode -->
	<svg class="moon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
		<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
	</svg>
	<svg class="sun" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
		<circle cx="12" cy="12" r="4" />
		<path
			d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"
		/>
	</svg>
</button>

<style>
	.theme-toggle {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		padding: 0;
		border: 0;
		border-radius: var(--radius);
		background: none;
		color: var(--ink-secondary);
		cursor: pointer;
		transition: color 0.12s;
	}

	.theme-toggle:hover {
		color: var(--ink);
	}

	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 1.75;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.sun {
		display: none;
	}

	:global(:root[data-theme='dark']) .sun {
		display: block;
	}

	:global(:root[data-theme='dark']) .moon {
		display: none;
	}
</style>
