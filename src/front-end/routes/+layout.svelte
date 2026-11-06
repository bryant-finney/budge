<!--
  App shell: banner + primary navigation, then the current view in main.

  ref: https://svelte.dev/docs/kit/routing#layout

  pattern: every in-app href starts with #/ (hash router)
-->
<script lang="ts">
  import type { Snippet } from 'svelte';

  const { children }: { children: Snippet } = $props();
</script>

<header>
  <nav aria-label="Primary">
    <ul>
      <li><a href="#/">Spending</a></li>
      <li><a href="#/connections">Banks</a></li>
    </ul>
  </nav>
</header>

<main>
  {@render children()}
</main>

<style>
  ul {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  a {
    display: inline-block;
    min-block-size: 24px;
    padding-block: 0.25rem;
  }
</style>
