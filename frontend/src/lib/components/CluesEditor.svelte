<!-- src/lib/components/CluesEditor.svelte -->
<script lang="ts">
  import type { CluesData } from '../types';
  
  export let cluesData: CluesData | null = null;
  export let onUpdateClues: () => void;
  
  $: acrossClues = cluesData ? 
    Object.entries(cluesData.across)
      .sort(([a], [b]) => parseInt(a) - parseInt(b)) : [];
  
  $: downClues = cluesData ? 
    Object.entries(cluesData.down)
      .sort(([a], [b]) => parseInt(a) - parseInt(b)) : [];
</script>

<div class="clues-container">
  <div class="clues-editor">
    <div class="clue-column">
      <h3>Across</h3>
      <div id="acrossClues">
        {#if cluesData}
          {#each acrossClues as [number, clueInfo]}
            <div class="clue-item" data-number={number} data-word={clueInfo.word}>
              <label for={`across-${number}`}>{number}. ({clueInfo.word.length}) {clueInfo.word}</label>
              <input id={`across-${number}`} type="text" class="clue-input" bind:value={cluesData.across[number].clue}>
            </div>
          {/each}
        {/if}
      </div>
    </div>
    <div class="clue-column">
      <h3>Down</h3>
      <div id="downClues">
        {#if cluesData}
          {#each downClues as [number, clueInfo]}
            <div class="clue-item" data-number={number} data-word={clueInfo.word}>
              <label for={`down-${number}`}>{number}. ({clueInfo.word.length}) {clueInfo.word}</label>
              <input id={`down-${number}`} type="text" class="clue-input" bind:value={cluesData.down[number].clue}>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
  {#if cluesData}
    <button on:click={onUpdateClues}>Update Clues</button>
  {/if}
</div>

<style>
  .clues-container {
    margin-top: 20px;
  }

  .clues-editor {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
  }

  .clue-column {
    flex: 1;
    min-width: 300px;
  }

  .clue-item {
    margin-bottom: 10px;
  }

  .clue-input {
    width: 95%;
    padding: 8px;
  }

  button {
    padding: 10px 15px;
    margin-top: 10px;
    background-color: #4CAF50;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
