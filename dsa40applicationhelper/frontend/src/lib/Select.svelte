<script lang="ts">
  import * as Select from "$lib/components/ui/select/index.ts";

  type Props = {
    id: string;
    value: string;
    options: string[];
    onchange?: (value: string) => void;
  };

  let { id, value = $bindable(""), options, onchange }: Props = $props();
  const triggerContent = $derived(
    options.find((o) => o === value) ?? "Select an option",
  );
  const hasSelection = $derived(Boolean(value));
</script>

<Select.Root
  type="single"
  bind:value
  onValueChange={(v) => onchange?.(v ?? "")}
>
  <Select.Trigger class="w-full max-w-lg {hasSelection ? '' : 'text-field-hint'}">
    {triggerContent}
  </Select.Trigger>
  <Select.Content>
    <Select.Group>
      {#each options as opt}
        <Select.Item value={opt} label={opt}>
          {opt}
        </Select.Item>
      {/each}
    </Select.Group>
  </Select.Content>
</Select.Root>
