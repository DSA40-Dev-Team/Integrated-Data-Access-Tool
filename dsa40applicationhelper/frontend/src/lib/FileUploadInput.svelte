<script lang="ts">
  import { Input } from "$lib/components/ui/input";

  type Props = {
    id: string;
    name?: string;
    value?: string;
    required?: boolean;
    class?: string;
    onchange?: (value: string) => void;
  };

  let {
    id,
    name = undefined,
    value = $bindable(""),
    required = false,
    class: className = "w-full max-w-md",
    onchange,
  }: Props = $props();

  let displayName = $state("");
  let hasNewFile = $state(false);

  $effect(() => {
    if (!hasNewFile && value?.trim()) {
      const base = value.split("/").pop() ?? value;
      displayName = base.replace(/^\d+_/, "");
    }
  });

  function onFileChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    hasNewFile = true;
    displayName = file.name;
    value = file.name;
    onchange?.(value);
  }

  function clearSelection() {
    hasNewFile = false;
    displayName = "";
    value = "";
    onchange?.("");
  }

  const showStoredPath = $derived(
    !hasNewFile && Boolean(value?.trim()) && value.includes("/"),
  );
</script>

<div class="file-upload-field">
  <Input {id} {name} type="file" class={className} {required} onchange={onFileChange} />

  {#if displayName || showStoredPath}
    <div class="file-chip" role="status">
      <span class="file-chip-label" title={value}>
        {displayName || value}
      </span>
      {#if showStoredPath}
        <span class="file-chip-note">Previously uploaded — select again to replace</span>
      {/if}
      <button type="button" class="file-chip-clear" onclick={clearSelection}>Clear</button>
    </div>
  {/if}

  <p class="file-hint">
    Files are stored locally for generation. Re-attach on each platform’s own form when submitting.
  </p>
</div>

<style>
  .file-upload-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .file-chip {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid var(--field-border);
    border-radius: 0.5rem;
    background: var(--field-bg);
    padding: 0.5rem 0.75rem;
    font-size: 0.8125rem;
  }
  .file-chip-label {
    font-weight: 600;
    color: var(--collaboratory-navy);
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .file-chip-note {
    color: var(--card-muted-foreground);
    font-size: 0.75rem;
  }
  .file-chip-clear {
    margin-left: auto;
    border: none;
    background: none;
    color: var(--collaboratory-navy);
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 2px;
    padding: 0;
  }
  .file-hint {
    margin: 0;
    font-size: 0.75rem;
    color: var(--field-hint);
  }
</style>
