<script lang="ts">
  import type { InputType, DsaQuestion } from "@api/types.gen";
  import Select from "$lib/Select.svelte";
  import CountryCombobox from "$lib/CountryCombobox.svelte";
  import RepeatableGroup from "$lib/RepeatableGroup.svelte";
  import CompositeGroup from "$lib/CompositeGroup.svelte";
  import FileUploadInput from "$lib/FileUploadInput.svelte";
  import { Input } from "./components/ui/input";
  import { Badge } from "./components/ui/badge/index.js";

  type Props = {
    id: string;
    text: string;
    required: boolean;
    visible: boolean;
    input_type: InputType;
    help_text?: string | null;
    config?: DsaQuestion["config"];
    options?: string[] | null;
    value?: string;
    validation?: string | string[] | null;
    formValues?: Record<string, string | undefined>;
    conditions?: import("$lib/conditions").ConditionsMap;
    platforms?: { id: string; name: string }[];
    embedded?: boolean;
    requiredFieldIds?: Set<string>;
  };

  let {
    id,
    text,
    required,
    visible,
    input_type,
    help_text,
    config,
    options,
    value = $bindable(""),
    validation,
    formValues = {},
    conditions = {},
    platforms = [],
    embedded = false,
    requiredFieldIds = new Set<string>(),
  }: Props = $props();

  const selectOptions = $derived(
    config?.type === "selection" ? config.options : (options ?? []),
  );

  const isYesNoSelection = $derived(
    input_type === "selection" &&
      selectOptions.length === 2 &&
      selectOptions.includes("Yes") &&
      selectOptions.includes("No"),
  );

  function parseMultiValue(raw: string): string[] {
    return raw
      .split(/;\s*/)
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function toggleMultiOption(option: string, checked: boolean) {
    const current = parseMultiValue(value);
    const next = checked
      ? current.includes(option)
        ? current
        : [...current, option]
      : current.filter((item) => item !== option);
    value = next.join("; ");
  }

  const validationErrors = $derived(
    Array.isArray(validation) ? validation : validation ? [validation] : [],
  );
  const hidden = $derived(!(required ?? false) && !(visible ?? true));
  const isMultilineText = $derived(
    input_type === "text" && Boolean(config && "multiline" in config && config.multiline),
  );
  const textareaRows = $derived(Number(config?.rows ?? 4));
  const fieldWidthClass = $derived(isMultilineText ? "max-w-2xl" : "max-w-lg");
</script>

{#if !hidden}
  {#if embedded}
    <div class="embedded-question">
      {#if text}
        <p class="text-sm font-medium text-card-foreground">{text}</p>
      {/if}
      {#if help_text}
        <p class="field-hint-text mt-1">{help_text}</p>
      {/if}
      <div class="mt-3 {fieldWidthClass}">
        {#if input_type === "text"}
          {#if isMultilineText}
            <textarea
              {id}
              bind:value
              rows={textareaRows}
              class="field-input min-h-[96px]"
            ></textarea>
          {:else}
            <Input {id} type="text" bind:value class="w-full" />
          {/if}
        {:else if input_type === "file_upload"}
          <FileUploadInput {id} name={id} bind:value required={required} />
        {:else if input_type === "date_select"}
          <Input {id} type="date" bind:value class="w-full" />
        {:else if input_type === "selection"}
          {#if isYesNoSelection}
            <div class="flex flex-wrap gap-x-5 gap-y-3" role="radiogroup" aria-labelledby={id}>
              {#each selectOptions as opt (opt)}
                <label class="flex cursor-pointer items-center gap-2 text-sm text-card-foreground">
                  <input
                    type="radio"
                    value={opt}
                    checked={value === opt}
                    onchange={() => (value = opt)}
                    class="size-4 accent-primary"
                  />
                  {opt}
                </label>
              {/each}
            </div>
          {:else}
            <Select {id} bind:value options={selectOptions} />
          {/if}
        {:else if input_type === "multi_select"}
          {#if selectOptions.length > 0}
            <div class="flex flex-col gap-2.5 rounded-lg border border-field-border bg-card-muted p-3">
              {#each selectOptions as opt (opt)}
                <label class="flex cursor-pointer items-center gap-2.5 text-sm">
                  <input
                    type="checkbox"
                    value={opt}
                    checked={parseMultiValue(value).includes(opt)}
                    onchange={(e) => toggleMultiOption(opt, e.currentTarget.checked)}
                    class="size-4 accent-primary"
                  />
                  {opt}
                </label>
              {/each}
            </div>
          {:else}
            <textarea
              {id}
              bind:value
              rows="3"
              placeholder="Enter keywords or topics, separated by semicolons"
              class="field-input min-h-[80px]"
            ></textarea>
          {/if}
        {:else if input_type === "iso-3166-1"}
          <CountryCombobox {id} value={value} options={options ?? []} onchange={(v) => (value = v)} />
        {:else if input_type === "repeatable_group"}
          <RepeatableGroup {id} {config} {formValues} {conditions} bind:value {validation} />
        {:else if input_type === "composite_group"}
          <CompositeGroup {id} {config} bind:value {validation} {conditions} {formValues} {platforms} {requiredFieldIds} />
        {/if}
      </div>
      {#if validationErrors.length > 0}
        <ul class="mt-2 space-y-0.5" role="alert">
          {#each validationErrors as err}
            <li class="text-sm text-destructive">{err}</li>
          {/each}
        </ul>
      {/if}
    </div>
  {:else}
  <fieldset class="py-5">
    <legend class="font-heading text-base font-bold leading-snug text-card-foreground">
      {text}
      <Badge variant={required ? "required" : "secondary"} class="ml-1.5 align-middle">
        {required ? "Required" : "Optional"}
      </Badge>
    </legend>

    {#if help_text}
      <p class="field-hint-text mt-1.5">{help_text}</p>
    {/if}

    <div class="mt-3 {fieldWidthClass}">
      {#if input_type === "text"}
        {#if isMultilineText}
          <textarea
            {id}
            bind:value
            rows={textareaRows}
            class="field-input min-h-[96px]"
          ></textarea>
        {:else}
          <Input {id} type="text" bind:value class="w-full" />
        {/if}
      {:else if input_type === "file_upload"}
        <FileUploadInput {id} name={id} bind:value required={required} />
      {:else if input_type === "date_select"}
        <Input {id} type="date" bind:value class="w-full" />
      {:else if input_type === "selection"}
        {#if isYesNoSelection}
          <div class="flex flex-wrap gap-x-5 gap-y-3" role="radiogroup" aria-labelledby={id}>
            {#each selectOptions as opt (opt)}
              <label class="flex cursor-pointer items-center gap-2 text-sm text-card-foreground">
                <input
                  type="radio"
                  value={opt}
                  checked={value === opt}
                  onchange={() => (value = opt)}
                  class="size-4 accent-primary"
                />
                {opt}
              </label>
            {/each}
          </div>
        {:else}
          <Select {id} bind:value options={selectOptions} />
        {/if}
      {:else if input_type === "multi_select"}
        {#if selectOptions.length > 0}
          <div class="flex flex-col gap-2.5 rounded-lg border border-field-border bg-card-muted p-3">
            {#each selectOptions as opt (opt)}
              <label class="flex cursor-pointer items-center gap-2.5 text-sm">
                <input
                  type="checkbox"
                  value={opt}
                  checked={parseMultiValue(value).includes(opt)}
                  onchange={(e) => toggleMultiOption(opt, e.currentTarget.checked)}
                  class="size-4 accent-primary"
                />
                {opt}
              </label>
            {/each}
          </div>
        {:else}
          <textarea
            {id}
            bind:value
            rows="3"
            placeholder="Enter keywords or topics, separated by semicolons"
            class="field-input min-h-[80px]"
          ></textarea>
        {/if}
      {:else if input_type === "iso-3166-1"}
        <CountryCombobox {id} value={value} options={options ?? []} onchange={(v) => (value = v)} />
      {:else if input_type === "repeatable_group"}
        <RepeatableGroup {id} {config} {formValues} {conditions} bind:value {validation} />
      {:else if input_type === "composite_group"}
        <CompositeGroup {id} {config} bind:value {validation} {conditions} {formValues} {platforms} {requiredFieldIds} />
      {/if}
    </div>

    {#if validationErrors.length > 0}
      <ul class="mt-2 space-y-0.5" role="alert">
        {#each validationErrors as err}
          <li class="text-sm text-destructive">{err}</li>
        {/each}
      </ul>
    {/if}
  </fieldset>
  {/if}
{/if}
