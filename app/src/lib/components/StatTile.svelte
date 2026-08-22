<script lang="ts">
	let {
		label,
		value,
		unit = '',
		note = '',
		tone = 'neutral'
	}: {
		label: string;
		value: string;
		unit?: string;
		note?: string;
		tone?: 'neutral' | 'good' | 'bad';
	} = $props();
</script>

<div class="tile">
	<div class="label">{label}</div>
	<div class="value" class:good={tone === 'good'} class:bad={tone === 'bad'}>
		{value}<span class="unit">{unit}</span>
	</div>
	{#if note}<div class="note">{note}</div>{/if}
</div>

<style>
	.tile {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 12px 14px;
		min-width: 0;
	}

	.label {
		font-size: 12px;
		color: var(--ink-secondary);
	}

	.value {
		font-family: var(--font-display);
		font-size: 26px;
		font-weight: 600;
		letter-spacing: -0.01em;
		margin-top: 2px;
		color: var(--ink);
	}

	.value.good {
		color: var(--good);
	}

	.value.bad {
		color: var(--bad);
	}

	.unit {
		font-size: 13px;
		font-weight: 400;
		color: var(--ink-muted);
		margin-left: 5px;
		font-family: var(--font-body);
	}

	.note {
		font-size: 11px;
		color: var(--ink-muted);
		margin-top: 2px;
	}
</style>
