<script lang="ts">
  import { Dialog } from "bits-ui";
  import { cn } from "$lib/utils.js";
  import { Button } from "$lib/components/ui/button/index.js";

  type Props = {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    title: string;
    description: string;
    confirmLabel?: string;
    cancelLabel?: string;
    onConfirm: () => void;
  };

  let {
    open = $bindable(false),
    onOpenChange,
    title,
    description,
    confirmLabel = "Continue",
    cancelLabel = "Cancel",
    onConfirm,
  }: Props = $props();

  function handleOpenChange(next: boolean) {
    open = next;
    onOpenChange?.(next);
  }

  function confirm() {
    onConfirm();
    handleOpenChange(false);
  }
</script>

<Dialog.Root bind:open onOpenChange={handleOpenChange}>
  <Dialog.Portal>
    <Dialog.Overlay class="fixed inset-0 z-50 bg-black/40" />
    <Dialog.Content
      class={cn(
        "surface-card fixed top-1/2 left-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 p-6 shadow-lg outline-none",
      )}
    >
      <Dialog.Title class="font-heading text-lg font-bold text-collaboratory-navy">{title}</Dialog.Title>
      <Dialog.Description class="mt-2 text-sm leading-relaxed text-muted-foreground">
        {description}
      </Dialog.Description>
      <div class="mt-6 flex flex-wrap justify-end gap-2">
        <Button variant="outline" onclick={() => handleOpenChange(false)}>{cancelLabel}</Button>
        <Button class="btn-collaboratory" onclick={confirm}>{confirmLabel}</Button>
      </div>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
