<script lang="ts">
  export let visible = false;
  export let progress = 0;
  export let statusText = '';
</script>

<div class="progress-container" style="display: {visible ? 'block' : 'none'}">
  <div class="progress-bar">
    <div class="progress-fill" style="width: {progress}%"></div>
  </div>
  <div class="progress-text">{statusText}</div>
</div>

<style>
  .progress-container {
    margin: 20px 0;
  }

  .progress-bar {
    width: 100%;
    height: 20px;
    background-color: #f0f0f0;
    border-radius: 10px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background-color: #4CAF50;
    width: 0%;
    transition: width 0.3s ease;
  }

  .progress-text {
    margin-top: 10px;
    text-align: center;
    font-size: 14px;
    color: #666;
  }
</style>
