<script lang="ts">
  import { cn } from "$lib/utils.js";
  import { Progress } from "$lib/components/ui/progress/index.js";

  type Props = {
    value: number;
    max?: number;
    label?: string;
    detail?: string;
    class?: string;
  };

  let { value, max = 100, label = "Required fields", detail, class: className }: Props = $props();

  const percent = $derived(Math.min(100, Math.max(0, max > 0 ? Math.round((value / max) * 100) : 0)));
</script>

<div class={cn("rounded-lg border border-panel-border bg-background px-4 py-3", className)}>
  <div class="mb-2 flex items-center justify-between gap-3 text-sm">
    <span class="font-medium text-foreground">{label}</span>
    <span class="text-foreground/75">
      {#if detail}
        {detail}
      {:else}
        {percent}%
      {/if}
    </span>
  </div>
  <Progress value={percent} max={100} class="bg-white/12" />
</div>
