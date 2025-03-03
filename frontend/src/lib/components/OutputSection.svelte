<script lang="ts">
  import { onMount } from 'svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import Tabs from '$lib/components/Tabs.svelte';
  import CluesEditor from './CluesEditor.svelte';
  import type { CluesData } from '../types';

  export let gridImage = '';
  export let answerImage = '';
  export let cluesData: CluesData | null = null;
  export let progressVisible = false;
  export let progressValue = 0;
  export let progressText = '';
  export let onUpdateClues: () => void;

  let activeTab = 'puzzle';
  const tabs = ['puzzle', 'answer', 'clues'];
</script>

<div class="output-section">
  <ProgressBar 
    visible={progressVisible} 
    progress={progressValue} 
    statusText={progressText} 
  />

  <Tabs {tabs} bind:activeTab />

  <!-- Grid Tab Content -->
  <div class="tab-content {activeTab === 'puzzle' ? 'active' : ''}" id="puzzleTab">
    <div class="image-container">
      {#if gridImage}
        <img src={gridImage} alt="Crossword grid" />
      {:else}
        <p>Generate a grid to see the crossword puzzle.</p>
      {/if}
    </div>
  </div>

  <!-- Clues Tab Content -->
  <div class="tab-content {activeTab === 'clues' ? 'active' : ''}" id="cluesTab">
    <CluesEditor {cluesData} {onUpdateClues} />
  </div>

  <!-- Answer Tab Content -->
  <div class="tab-content {activeTab === 'answer' ? 'active' : ''}" id="answerTab">
    <div class="image-container">
      {#if answerImage}
        <img src={answerImage} alt="Answer grid" />
      {:else}
        <p>Generate a grid to see the answer.</p>
      {/if}
    </div>
  </div>
</div>

<style>
  .output-section {
    flex: 2;
    min-width: 500px;
  }

  .tab-content {
    display: none;
    padding: 15px;
    border: 1px solid #ddd;
  }

  .tab-content.active {
    display: block;
  }

  .image-container {
    margin-top: 20px;
    text-align: center;
  }

  .image-container img {
    max-width: 100%;
    border: 1px solid #ddd;
  }
</style>
