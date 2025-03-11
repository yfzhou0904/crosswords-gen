<script lang="ts">
	import type { UserInfo } from '$lib/types';
	
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
	export let isAuthenticated = false;
	export let isCheckingAuth = false;
	export let userInfo: UserInfo | null = null;
</script>

<div class="input-section">
	<div style="margin-bottom: 15px;">
		{#if isCheckingAuth}
			<div class="auth-status">
				<p>Checking authentication status...</p>
			</div>
		{:else if isAuthenticated}
			<div class="auth-status">
				<p>
					Logged in as <strong>{userInfo?.display_name || userInfo?.username}</strong>
					<span class="auth-badge">✓</span>
				</p>
			</div>
		{:else}
			<div class="auth-status">
				<p>
					Not logged in. You can <a href="https://auth.yfzhou.fyi/login" target="_blank" rel="noopener">sign in</a> 
					or use a secret key:
				</p>
			</div>
			<label for="secretInput">Secret Key:</label>
			<input
				type="password"
				id="secretInput"
				placeholder="Enter secret key"
				bind:value={secretKey}
				style="padding: 8px; width: 98%; margin-top: 5px;"
			/>
		{/if}
	</div>
	<h2>Input Words</h2>
	<p>Enter one word per line:</p>
	<textarea id="wordsInput" placeholder="Enter words here, one per line..." bind:value={words}
	></textarea>

	<!-- Action Buttons -->
	<button on:click={onGenerateGrid} disabled={isGeneratingGrid || (!isAuthenticated && !secretKey)}>
		{#if isGeneratingGrid}
			<span class="spinner"></span> Generating...
		{:else}
			Generate Grid
		{/if}
	</button>

	<button on:click={onGenerateClues} disabled={!gridGenerated || isGeneratingClues || (!isAuthenticated && !secretKey)}>
		{#if isGeneratingClues}
			<span class="spinner"></span> Generating...
		{:else}
			Generate Clues
		{/if}
	</button>

	<button on:click={onExportPdf} disabled={!cluesGenerated || isExportingPdf || (!isAuthenticated && !secretKey)}>
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

	.auth-status {
		padding: 8px;
		border-radius: 4px;
		margin-bottom: 10px;
	}

	.auth-badge {
		display: inline-block;
		background-color: #4caf50;
		color: white;
		border-radius: 50%;
		width: 18px;
		height: 18px;
		text-align: center;
		font-size: 12px;
		line-height: 18px;
		margin-left: 5px;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
