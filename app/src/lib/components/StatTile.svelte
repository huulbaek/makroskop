<script lang="ts">
	let {
		label,
		value,
		unit = '',
		note = '',
		tag = '',
		tone = 'neutral'
	}: {
		label: string;
		value: string;
		unit?: string;
		/** Small line under the value (wraps; use `tag` when the cell must stay one line). */
		note?: string;
		/** Short uppercase status on the label row, coloured by `tone`. */
		tag?: string;
		tone?: 'neutral' | 'good' | 'bad';
	} = $props();
</script>

<!-- A key figure set in type, separated from its neighbours by a hairline rather than a box. -->
<div class="figure">
	<div class="label">
		<span>{label}</span>
		{#if tag}<span class="tag" class:good={tone === 'good'} class:bad={tone === 'bad'}>{tag}</span>{/if}
	</div>
	<div class="value" class:good={tone === 'good'} class:bad={tone === 'bad'}>
		<span class="number">{value}</span>{#if unit}<span class="unit">{unit}</span>{/if}
	</div>
	{#if note}<div class="note">{note}</div>{/if}
</div>

<style>
	.figure {
		border-right: 1px solid var(--rule);
		padding: 20px 24px;
		min-width: 0;
	}

	.label {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 8px;
		font-size: 13px;
		color: var(--ink-secondary);
		line-height: 1.3;
		margin-bottom: 8px;
	}

	.tag {
		flex: none;
		font-size: 11px;
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--ink-muted);
	}

	.tag.good {
		color: var(--good);
	}

	.tag.bad {
		color: var(--bad);
	}

	.value {
		display: flex;
		align-items: baseline;
		gap: 8px;
		font-family: var(--font-display);
		font-size: 36px;
		font-weight: 500;
		line-height: 1;
		letter-spacing: -0.01em;
		font-variant-numeric: tabular-nums;
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
		font-size: 13px;
		font-weight: 400;
		letter-spacing: 0;
		color: var(--ink-muted);
	}

	.note {
		font-size: 11.5px;
		color: var(--ink-muted);
		margin-top: 8px;
		line-height: 1.35;
	}
</style>
