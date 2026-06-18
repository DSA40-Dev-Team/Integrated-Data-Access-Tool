<script lang="ts">
  import { cn, type WithElementRef } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";

  type Props = WithElementRef<HTMLAttributes<HTMLDivElement>> & {
    value?: number;
    max?: number;
  };

  let {
    ref = $bindable(null),
    class: className,
    value = 0,
    max = 100,
    ...restProps
  }: Props = $props();

  const percent = $derived(Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0)));
</script>

<div
  bind:this={ref}
  data-slot="progress"
  role="progressbar"
  aria-valuenow={value}
  aria-valuemin={0}
  aria-valuemax={max}
  class={cn("h-2 w-full overflow-hidden rounded-full bg-accent", className)}
  {...restProps}
>
  <div
    class="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
    style="width: {percent}%"
  ></div>
</div>
