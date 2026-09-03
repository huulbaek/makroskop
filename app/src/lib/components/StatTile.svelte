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

<!-- A key figure set in type, separated from its neighbours by a hairline rather than a box. -->
<div class="figure">
	<div class="label">{label}</div>
	<div class="value" class:good={tone === 'good'} class:bad={tone === 'bad'}>
		{value}<span class="unit">{unit}</span>
	</div>
	{#if note}<div class="note">{note}</div>{/if}
</div>

<style>
	.figure {
		border-left: 1px solid var(--rule);
		padding: 2px 16px 4px 14px;
		min-width: 0;
	}

	.label {
		font-size: 12.5px;
		color: var(--ink-secondary);
		line-height: 1.3;
	}

	.value {
		font-family: var(--font-display);
		font-size: 34px;
		font-weight: 500;
		line-height: 1.1;
		letter-spacing: -0.01em;
		font-variant-numeric: tabular-nums;
		margin-top: 6px;
		color: var(--ink);
	}

	.value.good {
		color: var(--good);
	}

	.value.bad {
		color: var(--bad);
	}

	.unit {
		font-family: var(--font-body);
		font-size: 12.5px;
		font-weight: 400;
		color: var(--ink-muted);
		margin-left: 6px;
	}

	.note {
		font-size: 11.5px;
		color: var(--ink-muted);
		margin-top: 4px;
		line-height: 1.35;
	}
</style>
