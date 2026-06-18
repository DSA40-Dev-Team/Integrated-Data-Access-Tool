<script lang="ts">
  import { cn, type WithElementRef } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";
  import { type VariantProps, tv } from "tailwind-variants";

  export const alertVariants = tv({
    base: "relative w-full rounded-lg border px-4 py-3 text-sm",
    variants: {
      variant: {
        default: "surface-card",
        info: "border-primary/30 bg-primary/10 text-foreground",
        destructive: "border-destructive/30 bg-destructive/5 text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  });

  type Props = WithElementRef<HTMLAttributes<HTMLDivElement>> &
    VariantProps<typeof alertVariants>;

  let {
    ref = $bindable(null),
    class: className,
    variant = "default",
    children,
    ...restProps
  }: Props = $props();
</script>

<div
  bind:this={ref}
  data-slot="alert"
  role="alert"
  class={cn(alertVariants({ variant }), className)}
  {...restProps}
>
  {@render children?.()}
</div>
