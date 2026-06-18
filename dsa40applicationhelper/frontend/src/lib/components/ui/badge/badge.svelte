<script lang="ts">
  import { cn, type WithElementRef } from "$lib/utils.js";
  import type { HTMLAttributes } from "svelte/elements";
  import { type VariantProps, tv } from "tailwind-variants";

  export const badgeVariants = tv({
    base: "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium uppercase tracking-wide",
    variants: {
      variant: {
        default: "border-transparent bg-collaboratory-navy text-white",
        required: "border-transparent bg-transparent px-0 py-0 font-semibold text-required-accent",
        secondary: "border border-field-border bg-card-muted text-card-muted-foreground",
        outline: "border-border text-muted-foreground",
        destructive: "border-transparent bg-destructive/10 text-destructive",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  });

  type Props = WithElementRef<HTMLAttributes<HTMLSpanElement>> &
    VariantProps<typeof badgeVariants>;

  let {
    ref = $bindable(null),
    class: className,
    variant = "default",
    children,
    ...restProps
  }: Props = $props();
</script>

<span
  bind:this={ref}
  data-slot="badge"
  class={cn(badgeVariants({ variant }), className)}
  {...restProps}
>
  {@render children?.()}
</span>
