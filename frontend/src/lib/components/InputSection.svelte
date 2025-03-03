<script lang="ts">
	export let secretKey = '';
	export let words = '';
	export let onGenerateGrid: () => void;
	export let onGenerateClues: () => void;
	export let onExportPdf: () => void;
	export let isGeneratingGrid = false;
	export let isGeneratingClues = false;
	export let isExportingPdf = false;
	export let cluesGenerated = false;
	export let gridGenerated = false;
</script>

<div class="input-section">
	<div style="margin-bottom: 15px;">
		<label for="secretInput">Secret Key:</label>
		<input
			type="password"
			id="secretInput"
			placeholder="Enter secret key"
			bind:value={secretKey}
			style="padding: 8px; width: 98%; margin-top: 5px;"
		/>
	</div>
	<h2>Input Words</h2>
	<p>Enter one word per line:</p>
	<textarea id="wordsInput" placeholder="Enter words here, one per line..." bind:value={words}
	></textarea>

	<!-- Action Buttons -->
	<button on:click={onGenerateGrid} disabled={isGeneratingGrid}>
		{#if isGeneratingGrid}
			<span class="spinner"></span> Generating...
		{:else}
			Generate Grid
		{/if}
	</button>

	<button on:click={onGenerateClues} disabled={!gridGenerated || isGeneratingClues}>
		{#if isGeneratingClues}
			<span class="spinner"></span> Generating...
		{:else}
			Generate Clues
		{/if}
	</button>

	<button on:click={onExportPdf} disabled={!cluesGenerated || isExportingPdf}>
		{#if isExportingPdf}
			<span class="spinner"></span> Exporting...
		{:else}
			Export PDF
		{/if}
	</button>
</div>

<style>
	.input-section {
		flex: 1;
		min-width: 300px;
	}

	textarea {
		width: 98%;
		min-height: 200px;
		margin-bottom: 10px;
		padding: 8px;
	}

	button {
		padding: 10px 15px;
		margin-right: 10px;
		margin-bottom: 10px;
		background-color: #4caf50;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
	}

	button:disabled {
		background-color: #cccccc;
		cursor: not-allowed;
	}

	.spinner {
		display: inline-block;
		width: 20px;
		height: 20px;
		border: 3px solid rgba(255, 255, 255, 0.3);
		border-radius: 50%;
		border-top-color: white;
		animation: spin 1s ease-in-out infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
