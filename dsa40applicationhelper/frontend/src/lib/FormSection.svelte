<script lang="ts">
  import type { Snippet } from "svelte";
  import type { SectionStats } from "$lib/formSections";

  type Props = {
    id: string;
    label: string;
    stats?: SectionStats;
    flat?: boolean;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    children: Snippet;
  };

  let {
    id,
    label,
    stats,
    flat = false,
    open = true,
    onOpenChange,
    children,
  }: Props = $props();
</script>

<section {id} class="form-section surface-card rounded-xl">
  {#if flat}
    <div class="border-b border-card-border px-4 py-4 sm:px-6">
      <h2 class="font-heading text-lg font-bold text-collaboratory-navy">{label}</h2>
      {#if stats}
        <p class="mt-1 text-sm text-muted-foreground">
          {#if stats.requiredTotal > 0}
            {stats.requiredFilled} of {stats.requiredTotal} required fields
            <span class="text-muted-foreground/70"> · </span>
          {/if}
          {stats.filled} of {stats.total} fields answered
          {#if stats.errorCount > 0}
            <span class="text-destructive"> · {stats.errorCount} issue{stats.errorCount === 1 ? "" : "s"}</span>
          {/if}
        </p>
      {/if}
    </div>
    <div class="px-4 pb-8 sm:px-6 sm:pb-10">
      {@render children()}
    </div>
  {:else}
    <button
      type="button"
      class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
      aria-expanded={open}
      onclick={() => onOpenChange?.(!open)}
    >
      <div class="min-w-0">
        <h2 class="font-heading text-base font-bold text-collaboratory-navy">{label}</h2>
        {#if stats}
          <p class="mt-0.5 text-xs text-muted-foreground">
            {#if stats.requiredTotal > 0}
              {stats.requiredFilled} / {stats.requiredTotal} required
              <span class="text-muted-foreground/70"> · </span>
            {/if}
            {stats.filled} / {stats.total} fields
            {#if stats.errorCount > 0}
              <span class="text-destructive"> · {stats.errorCount} issue{stats.errorCount === 1 ? "" : "s"}</span>
            {/if}
          </p>
        {/if}
      </div>
      <span class="shrink-0 text-sm text-muted-foreground" aria-hidden="true">{open ? "−" : "+"}</span>
    </button>

    {#if open}
      <div class="divide-y divide-card-border border-t border-card-border px-4 pb-8 sm:px-6 sm:pb-10">
        {@render children()}
      </div>
    {/if}
  {/if}
</section>
