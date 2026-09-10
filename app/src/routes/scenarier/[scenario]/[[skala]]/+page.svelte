<script lang="ts">
	import ScenarioExplorer from '$lib/components/ScenarioExplorer.svelte';

	let { data } = $props();
</script>

<ScenarioExplorer meta={data.meta} initialScenario={null} initial={data.card.initial} initialTiles={data.card.tiles} />
