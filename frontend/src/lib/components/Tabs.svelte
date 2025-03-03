<!-- src/lib/components/Tabs.svelte -->
<script lang="ts">
  export let tabs: string[] = [];
  export let activeTab: string;

  function setActiveTab(tab: string) {
    activeTab = tab;
  }
</script>

<div class="tabs">
  {#each tabs as tab}
    <button 
      class="tab {activeTab === tab ? 'active' : ''}" 
      on:click={() => setActiveTab(tab)}
    >
      {tab.charAt(0).toUpperCase() + tab.slice(1)}
    </button>
  {/each}
</div>

<style>
  .tabs {
    display: flex;
    margin-bottom: 10px;
  }

  .tab {
    padding: 10px 15px;
    cursor: pointer;
    background-color: #f1f1f1;
    border: 1px solid #ddd;
    border-bottom: none;
  }

  .tab.active {
    background-color: white;
    border-bottom: 1px solid white;
  }
</style>
