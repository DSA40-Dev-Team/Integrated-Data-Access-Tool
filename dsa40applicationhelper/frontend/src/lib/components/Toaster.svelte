<script lang="ts">
  import { toasts } from "$lib/toast";
  import CheckIcon from "@lucide/svelte/icons/check";
</script>

<div
  class="pointer-events-none fixed right-4 bottom-4 z-[100] flex w-full max-w-sm flex-col gap-2"
  aria-live="polite"
>
  {#each $toasts as item (item.id)}
    <div
      class="surface-card pointer-events-auto flex items-start gap-2 px-4 py-3 text-sm shadow-md {item.variant ===
      'success'
        ? 'border-primary/30'
        : ''}"
      role="status"
    >
      {#if item.variant === "success"}
        <CheckIcon class="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
      {/if}
      <span class="text-card-foreground">{item.message}</span>
    </div>
  {/each}
</div>
