<script lang="ts">
	import ScenarioExplorer from '$lib/components/ScenarioExplorer.svelte';

	let { data } = $props();
</script>

<ScenarioExplorer meta={data.meta} initialScenario={data.initialScenario} />
