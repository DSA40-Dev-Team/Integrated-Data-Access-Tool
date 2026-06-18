<script>
  let { children } = $props();
  import "../app.css";
  import Toaster from "$lib/components/Toaster.svelte";
</script>

<div class="flex min-h-svh flex-col">
  <main class="flex-1">
    {@render children()}
  </main>
  <Toaster />
</div>
