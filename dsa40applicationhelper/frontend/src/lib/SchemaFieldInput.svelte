<script lang="ts">
  import Select from "$lib/Select.svelte";
  import CountryCombobox from "$lib/CountryCombobox.svelte";
  import FileUploadInput from "$lib/FileUploadInput.svelte";
  import { Input } from "$lib/components/ui/input";
  import type { SchemaField } from "$lib/structured";

  type Props = {
    field: SchemaField;
    id: string;
    name?: string;
    value?: string;
    options?: string[] | null;
    onchange?: (value: string) => void;
  };

  let {
    field,
    id,
    value = "",
    options = null,
    onchange,
  }: Props = $props();

  let local = $state(value);

  $effect(() => {
    local = value;
  });

  const selectOptions = $derived(
    field.config?.type === "selection" ||
      field.config?.type === "multi_select" ||
      field.config?.i_type === "selection"
      ? ((field.config.options as string[] | undefined) ?? [])
      : (options ?? field.options ?? []),
  );

  function parseMultiValue(raw: string): string[] {
    return raw
      .split(/;\s*/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function update(next: string) {
    local = next;
    onchange?.(next);
  }

  function toggleMultiOption(option: string, checked: boolean) {
    const current = parseMultiValue(local);
    const next = checked
      ? current.includes(option)
        ? current
        : [...current, option]
      : current.filter((item) => item !== option);
    update(next.join("; "));
  }

  const isMultiline = $derived(Boolean(field.config?.multiline));
  const textareaRows = $derived(Number(field.config?.rows ?? 4));
  const isYesNoSelection = $derived(
    field.type === "selection" &&
      selectOptions.length === 2 &&
      selectOptions.includes("Yes") &&
      selectOptions.includes("No"),
  );
</script>

{#if field.type === "text"}
  {#if isMultiline}
    <textarea
      {id}
      value={local}
      rows={textareaRows}
      class="field-input min-h-[96px]"
      oninput={(e) => update(e.currentTarget.value)}
    ></textarea>
  {:else}
    <Input
      {id}
      type="text"
      value={local}
      oninput={(e) => update(e.currentTarget.value)}
      class="w-full"
    />
  {/if}
{:else if field.type === "date_select"}
  <Input
    {id}
    type="date"
    value={local}
    oninput={(e) => update(e.currentTarget.value)}
    class="w-full"
  />
{:else if field.type === "selection"}
  {#if isYesNoSelection}
    <div class="yes-no-group" role="radiogroup" aria-labelledby={id}>
      {#each selectOptions as opt (opt)}
        <label class="yes-no-option">
          <input
            type="radio"
            value={opt}
            checked={local === opt}
            onchange={() => update(opt)}
            class="yes-no-radio"
          />
          {opt}
        </label>
      {/each}
    </div>
  {:else}
    <Select {id} bind:value={local} options={selectOptions} onchange={update} />
  {/if}
{:else if field.type === "multi_select"}
  {#if selectOptions.length > 0}
    <div class="multi-select">
      {#each selectOptions as opt (opt)}
        <label class="multi-option">
          <input
            type="checkbox"
            value={opt}
            checked={parseMultiValue(local).includes(opt)}
            onchange={(e) => toggleMultiOption(opt, e.currentTarget.checked)}
            class="multi-checkbox"
          />
          {opt}
        </label>
      {/each}
    </div>
  {:else}
    <textarea
      {id}
      value={local}
      rows="3"
      placeholder="Enter values separated by semicolons"
      class="field-input min-h-[80px]"
      oninput={(e) => update(e.currentTarget.value)}
    ></textarea>
  {/if}
{:else if field.type === "file_upload"}
  <FileUploadInput {id} bind:value={local} onchange={update} />
{:else if field.type === "iso-3166-1"}
  <CountryCombobox
    {id}
    value={local}
    options={selectOptions.length > 0 ? selectOptions : (options ?? field.options ?? [])}
    onchange={update}
  />
{:else if field.type === "orcid"}
  <Input
    {id}
    type="text"
    placeholder="0000-0002-1825-0097"
    value={local}
    oninput={(e) => update(e.currentTarget.value)}
    class="w-full"
  />
{:else}
  <Input
    {id}
    type="text"
    value={local}
    oninput={(e) => update(e.currentTarget.value)}
    class="w-full"
  />
{/if}

<style>
  .multi-select {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    border: 1px solid var(--field-border);
    border-radius: 0.5rem;
    padding: 0.75rem;
    background: var(--card-muted);
  }
  .multi-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
  }
  .multi-checkbox {
    width: 1rem;
    height: 1rem;
    accent-color: var(--primary);
  }
  .yes-no-group {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem 1.25rem;
  }
  .yes-no-option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
  }
  .yes-no-radio {
    width: 1rem;
    height: 1rem;
    accent-color: var(--primary, #2563eb);
  }
</style>
